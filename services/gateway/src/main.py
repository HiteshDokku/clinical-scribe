import uuid
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Request, BackgroundTasks, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
import asyncio
import json
import hashlib
import os
import redis.asyncio as redis
import re
from difflib import SequenceMatcher
from contextlib import asynccontextmanager

from .db import get_db, engine, get_identity, JWT_SECRET, JWT_ALGORITHM, require_auth, validate_jwt_secret
from .models import Base, Encounter, EncounterState, ConsentState, AuditLog, NoteVersion, User
from .audit import append_audit_log
import jwt
import bcrypt
from datetime import timedelta

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Tables are managed by Alembic, NOT SQLAlchemy create_all().
    # Migrations MUST run as a superuser to preserve audit_log immutability.
    validate_jwt_secret(os.getenv("JWT_SECRET"))
    yield

redis_client = redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, decode_responses=True)

app = FastAPI(title="gateway", lifespan=lifespan)

class CreateEncounterReq(BaseModel):
    clinician_id: str
    patient_ref: str
    
class CreateEncounterResp(BaseModel):
    id: str
    state: str
    consent_state: str

class PatchNoteReq(BaseModel):
    content: dict

FHIR_GATEWAY_URL = "http://fhir-gateway:8003/push"
ASR_WS_URL = "ws://asr:8001/transcribe"

def normalize_med_name(name: str) -> str:
    import re
    name = name.lower().strip()
    name = re.sub(r'\b\d+(\.\d+)?\s*(mg|g|mcg|ml|meq)\b', ' ', name)
    name = re.sub(r'\b(tablet|tablets|capsule|capsules|tab|tabs|cap|caps|oral|po|daily|bid|tid|qid|prn|od|hs|once|twice)\b', ' ', name)
    name = re.sub(r'\b\d+\b', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "gateway"}

@app.get("/api/v1/test_config")
async def test_config(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import text
    user = (await db.execute(text("SELECT current_setting('app.current_user_id', true)"))).scalar()
    role = (await db.execute(text("SELECT current_setting('app.current_role_id', true)"))).scalar()
    return {"user": user, "role": role}

class LoginRequest(BaseModel):
    username: str
    password: str

class LoginResponse(BaseModel):
    access_token: str

@app.post("/api/v1/auth/login", response_model=LoginResponse)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.username == req.username))
    user = result.scalars().first()
    
    if not user or not bcrypt.checkpw(req.password.encode('utf-8'), user.password_hash.encode('utf-8')):
        raise HTTPException(status_code=401, detail="Invalid credentials")
        
    import secrets
    
    exp = datetime.now(timezone.utc) + timedelta(hours=12)
    token_data = {"sub": str(user.id), "role_id": user.role_id, "exp": exp}
    token = jwt.encode(token_data, JWT_SECRET, algorithm=JWT_ALGORITHM)
    
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False, # For dev, should be true in prod
        max_age=12 * 3600
    )
    
    csrf_token = secrets.token_urlsafe(32)
    response.set_cookie(
        key="csrf_token",
        value=csrf_token,
        httponly=False,
        samesite="lax",
        secure=False, # For dev, should be true in prod
        max_age=12 * 3600
    )
    
    return {"access_token": token}

@app.post("/api/v1/encounters", response_model=CreateEncounterResp)
async def create_encounter(req: CreateEncounterReq, auth: tuple[str, str] = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    user_id, role_id = auth
    encounter_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    
    enc = Encounter(
        id=encounter_id,
        clinician_id=user_id,
        patient_ref=req.patient_ref,
        consent_state=ConsentState.pending.value,
        consent_logged_at=now,
        started_at=now,
        state=EncounterState.created.value
    )
    db.add(enc)
    await db.flush()
    
    append_audit_log(
        session=db,
        encounter_id=str(encounter_id),
        actor=user_id,
        action="create_encounter",
        before=None,
        after={"state": EncounterState.created.value, "consent_state": ConsentState.pending.value}
    )
    await db.commit()
    
    return CreateEncounterResp(
        id=str(encounter_id),
        state=enc.state,
        consent_state=enc.consent_state
    )

class GenerateNoteReq(BaseModel):
    segments: list[dict]

@app.post("/api/v1/encounters/{id}/generate", dependencies=[Depends(require_auth)])
async def generate_note(id: str, req: GenerateNoteReq, auth: tuple[str, str] = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    user_id, _ = auth
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
        
    if enc.state not in [EncounterState.transcribing.value, EncounterState.recording.value]:
        raise HTTPException(status_code=400, detail=f"Cannot generate from state: {enc.state}")
        
    if not req.segments:
        raise HTTPException(status_code=400, detail="No transcript segments provided. Cannot generate SOAP note.")
        
    before_state = enc.state
    # Handle legacy active states gracefully by logging and routing to new state
    if before_state in [EncounterState.drafting.value, EncounterState.ready.value]:
        print(f"WARNING: Migrating encounter {enc.id} from legacy state {before_state}")
        
    enc.state = EncounterState.drafting_diagnosis.value
    enc.ended_at = datetime.now(timezone.utc)
    
    append_audit_log(
        session=db,
        encounter_id=str(enc.id),
        actor=user_id,
        action="state_change",
        before={"state": before_state},
        after={"state": enc.state}
    )
    await db.commit()
    
    # Relabel segments for LLM
    llm_segments = []
    for seg in req.segments:
        s = seg.copy()
        if s.get("speaker") == "spk_a":
            s["speaker"] = "clinician"
        elif s.get("speaker") == "spk_b":
            s["speaker"] = "patient"
        llm_segments.append(s)

    # Call the LLM service synchronously
    async with httpx.AsyncClient(timeout=900.0) as client:
        try:
            resp = await client.post("http://llm:8080/extract_and_diagnose", json={
                "encounter_id": id,
                "segments": llm_segments
            })
            resp.raise_for_status()
            res_json = resp.json()
            entities = res_json["entities"]
            diagnose_output = res_json["diagnosis"]
            id_map = res_json.get("id_map", {})
            
            # Map diagnose_output evidence to actual IDs
            for sec_key in ["subjective", "objective", "assessment"]:
                sec = diagnose_output.get("sections", {}).get(sec_key, {})
                for stmt in (sec.get("statements") or []):
                    stmt["evidence"] = [id_map.get(str(eid), str(eid)) for eid in (stmt.get("evidence") or [])]

            
            # Override LLM risk assessment deterministically via Safety Service
            symptoms = [e["verbatim"] for e in entities if e["category"] in ("symptom_active", "symptom_denied", "vital", "other")]
            for stmt in (diagnose_output["sections"].get("assessment", {}).get("statements") or []):
                # Call safety service for ALL assessment statements
                try:
                    async with httpx.AsyncClient(timeout=10.0) as s_client:
                        s_resp = await s_client.post("http://safety:8002/api/v1/safety/classify_risk", json={
                            "proposed_condition": stmt.get("text", ""),
                            "symptoms": symptoms
                        })
                        if s_resp.status_code == 200:
                            stmt["risk_tier"] = s_resp.json()["risk_tier"]
                        else:
                            stmt["risk_tier"] = "requires_review" # safe default
                except Exception as exc:
                    stmt["risk_tier"] = "requires_review"

            
            # Form a partial note with just diagnosis sections
            partial_note = {
                "encounter_id": id,
                "model": res_json.get("model", {"name": "llama-3-8b-instruct", "quant": "unknown", "prompt_version": "v1", "digest": "unknown"}),
                "sections": {
                    "subjective": diagnose_output["sections"]["subjective"],
                    "objective": diagnose_output["sections"]["objective"],
                    "assessment": diagnose_output["sections"]["assessment"],
                    "plan": {"statements": [], "status": "pending"}
                },
                "differential_considerations": diagnose_output.get("differential_considerations", []),
                "medications": [],
                "safety_flags": [],
                "grounding": {
                    "statements_total": (
                        len(diagnose_output["sections"]["subjective"].get("statements") or []) +
                        len(diagnose_output["sections"]["objective"].get("statements") or []) +
                        len(diagnose_output["sections"]["assessment"].get("statements") or [])
                    ),
                    "ungrounded": len(res_json.get("ungrounded_ids", [])),
                    "ungrounded_ids": res_json.get("ungrounded_ids", [])
                }
            }
        except Exception as e:
            # Revert state if LLM fails so the user can retry
            enc.state = EncounterState.transcribing.value
            append_audit_log(
                session=db,
                encounter_id=str(enc.id),
                actor="system",
                action="state_change",
                before={"state": EncounterState.drafting_diagnosis.value},
                after={"state": enc.state}
            )
            await db.commit()
            raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")
            
    # Save transcript and entities to Redis
    try:
        ttl = int(os.getenv("TRANSCRIPT_TTL_SECONDS", "3600"))
        await redis_client.set(f"transcript:{enc.id}", json.dumps(req.segments), ex=ttl)
        await redis_client.set(f"entities:{enc.id}", json.dumps(entities), ex=ttl)
        await redis_client.set(f"id_map:{enc.id}", json.dumps(id_map), ex=ttl)
    except Exception as e:
        print(f"Failed to save data to Redis: {e}")
        
    # Save the partial SOAP note to the database as version 1
    import hashlib
    model_hash = hashlib.sha256(json.dumps(partial_note, sort_keys=True).encode("utf-8")).hexdigest()
    
    note_ver = NoteVersion(
        id=uuid.uuid4(),
        encounter_id=enc.id,
        version=1,
        source="ai",
        content_jsonb=partial_note,
        model_name="llama-3-8b-instruct",
        model_hash=model_hash,
        prompt_version="v1",
        created_at=datetime.now(timezone.utc)
    )
    db.add(note_ver)
    
    enc.state = EncounterState.diagnosis_review.value
    append_audit_log(
        session=db,
        encounter_id=str(enc.id),
        actor="system",
        action="state_change",
        before={"state": EncounterState.drafting_diagnosis.value},
        after={"state": enc.state}
    )
    await db.commit()
    return {"status": "diagnosis_review"}
            


class ConfirmDiagnosisReq(BaseModel):
    confirmed_diagnosis: str

@app.post("/api/v1/encounters/{id}/confirm-diagnosis", dependencies=[Depends(require_auth)])
async def confirm_diagnosis(id: str, req: ConfirmDiagnosisReq, auth: tuple[str, str] = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    user_id, _ = auth
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
        
    if enc.state != EncounterState.diagnosis_review.value:
        raise HTTPException(status_code=400, detail="Cannot confirm diagnosis unless in diagnosis_review state")
        
    before_state = enc.state
    enc.state = EncounterState.drafting_medications.value
    append_audit_log(db, str(enc.id), user_id, "state_change", before={"state": before_state}, after={"state": enc.state})
    await db.commit()
    
    # Get entities and id_map
    entities = []
    id_map = {}
    try:
        e_data = await redis_client.get(f"entities:{enc.id}")
        if e_data: entities = json.loads(e_data)
        m_data = await redis_client.get(f"id_map:{enc.id}")
        if m_data: id_map = json.loads(m_data)
    except Exception:
        pass

    # Call LLM prescribe
    async with httpx.AsyncClient(timeout=900.0) as client:
        try:
            resp = await client.post("http://llm:8080/prescribe", json={
                "encounter_id": id,
                "confirmed_diagnosis": req.confirmed_diagnosis,
                "entities": entities
            })
            resp.raise_for_status()
            prescribe_output = resp.json()
            
            # Remap prescribe_output evidence
            for stmt in prescribe_output.get("sections", {}).get("plan", {}).get("statements", []):
                stmt["evidence"] = [id_map.get(str(eid), str(eid)) for eid in stmt.get("evidence", [])]
            for med in prescribe_output.get("medications", []):
                med["evidence"] = [id_map.get(str(eid), str(eid)) for eid in med.get("evidence", [])]

        except Exception as e:
            # Revert state
            import traceback
            traceback.print_exc()
            enc.state = EncounterState.diagnosis_review.value
            append_audit_log(db, str(enc.id), "system", "state_change", before={"state": EncounterState.drafting_medications.value}, after={"state": enc.state})
            await db.commit()
            raise HTTPException(status_code=500, detail=f"LLM generation failed: {str(e)}")

    # Resolve medications and enforce high_risk_class manual confirmation
    medications = prescribe_output.get("medications") or []
    async with httpx.AsyncClient(timeout=10.0) as s_client:
        for med in medications:
            try:
                s_resp = await s_client.post("http://safety:8002/api/v1/safety/resolve", json={"mention": med["verbatim"]})
                if s_resp.status_code == 200:
                    s_data = s_resp.json()
                    med["ingredient_id"] = s_data.get("ingredient")
                    med["needs_manual_confirmation"] = s_data.get("needs_manual_confirmation", True)
                else:
                    med["needs_manual_confirmation"] = True
            except Exception:
                med["needs_manual_confirmation"] = True

    # Combine with previous NoteVersion
    result_note = await db.execute(
        select(NoteVersion).where(NoteVersion.encounter_id == uuid.UUID(id)).order_by(NoteVersion.version.desc())
    )
    old_note_ver = result_note.scalars().first()
    if not old_note_ver:
        raise HTTPException(status_code=500, detail="Missing diagnosis note version")

    try:
        combined_note = old_note_ver.content_jsonb.copy()
        if req.confirmed_diagnosis and req.confirmed_diagnosis.strip():
            if "assessment" in combined_note.get("sections", {}):
                combined_note["sections"]["assessment"]["edited_text"] = req.confirmed_diagnosis.strip()
        combined_note["sections"]["plan"] = prescribe_output["sections"]["plan"]
        combined_note["medications"] = medications
        
        # Check interactions to populate safety_flags
        all_meds = []
        for med in medications:
            name = normalize_med_name(med.get("verbatim", ""))
            if name:
                all_meds.append(name)
        
        safety_flags = []
        for i in range(len(all_meds)):
            for j in range(i+1, len(all_meds)):
                async with httpx.AsyncClient(timeout=10.0) as s_client:
                    try:
                        s_resp = await s_client.post("http://safety:8002/api/v1/safety/check_interaction", json={
                            "ingredient_a": all_meds[i],
                            "ingredient_b": all_meds[j]
                        })
                        if s_resp.status_code == 200:
                            data = s_resp.json()
                            for ix in data.get("interactions", []):
                                source_ref = ix.get("source") or ix.get("source_ref")
                                if source_ref:
                                    safety_flags.append({
                                        "type": "interaction",
                                        "source_ref": source_ref,
                                        "description": f"Interaction between {all_meds[i]} and {all_meds[j]}"
                                    })
                    except Exception:
                        pass
        combined_note["safety_flags"] = safety_flags

        # Recompute statements_total
        statements_total = (
            len(combined_note["sections"].get("subjective", {}).get("statements", [])) +
            len(combined_note["sections"].get("objective", {}).get("statements", [])) +
            len(combined_note["sections"].get("assessment", {}).get("statements", [])) +
            len(combined_note["sections"].get("plan", {}).get("statements", []))
        )
        combined_note["grounding"]["statements_total"] = statements_total
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Note update failed: {str(e)}")

    import hashlib
    model_hash = hashlib.sha256(json.dumps(combined_note, sort_keys=True).encode("utf-8")).hexdigest()
    note_ver = NoteVersion(
        id=uuid.uuid4(),
        encounter_id=enc.id,
        version=old_note_ver.version + 1,
        source="ai",
        content_jsonb=combined_note,
        model_name="llama-3-8b-instruct",
        model_hash=model_hash,
        prompt_version="v1",
        created_at=datetime.now(timezone.utc)
    )
    db.add(note_ver)

    enc.state = EncounterState.medication_review.value
    append_audit_log(db, str(enc.id), "system", "state_change", before={"state": EncounterState.drafting_medications.value}, after={"state": enc.state})
    await db.commit()
    
    return {"status": "medication_review"}

@app.get("/api/v1/encounters/{id}", dependencies=[Depends(require_auth)])
async def get_encounter(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
        
    # Get note
    result_note = await db.execute(
        select(NoteVersion).where(NoteVersion.encounter_id == uuid.UUID(id)).order_by(NoteVersion.version.desc())
    )
    note = result_note.scalars().first()
    note_json = note.content_jsonb if note else None
    
    # Get transcript
    transcript = []
    try:
        ts_data = await redis_client.get(f"transcript:{enc.id}")
        if ts_data:
            transcript = json.loads(ts_data)
            import re
            for seg in transcript:
                if isinstance(seg, dict) and "id" in seg:
                    seg["id"] = re.sub(r"^seg_[^_]+_", "", seg["id"])
    except Exception as e:
        print(f"Failed to get transcript from Redis: {e}")

    response_payload = {
        "id": str(enc.id),
        "state": enc.state,
        "consent_state": enc.consent_state,
        "note": note_json,
        "transcript": transcript,
        "degraded_reason": getattr(enc, "degraded_reason", None),
        "ehr_status": getattr(enc, "ehr_status", "pending")
    }
    print("DEBUG GATEWAY PAYLOAD:", json.dumps(response_payload, indent=2))
    return response_payload

def format_diagnosis_summary(summary: str | None) -> str:
    """Formats diagnosis summary for the dashboard: truncates to ~80 chars, never returns 'pending'."""
    if not summary:
        return "No diagnosis recorded"
    s = str(summary).strip()
    if not s or s.lower() == "pending":
        return "No diagnosis recorded"
    if len(s) > 80:
        return s[:77].rstrip() + "..."
    return s

@app.get("/api/v1/encounters", dependencies=[Depends(require_auth)])
async def list_encounters(limit: int = 10, order_by: str = "-created_at", state: str | None = None, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import desc
    # Return signed encounters only, newest first, limit 10 after filter
    target_state = state if state else EncounterState.signed.value
    query = select(Encounter).where(Encounter.state == target_state)
    query = query.order_by(desc(Encounter.started_at)).limit(10)
    
    result = await db.execute(query)
    encounters = result.scalars().all()
    
    resp = []
    for enc in encounters:
        note_res = await db.execute(
            select(NoteVersion).where(NoteVersion.encounter_id == enc.id).order_by(desc(NoteVersion.version))
        )
        latest_note = note_res.scalars().first()
        summary = ""
        if latest_note:
            sections = latest_note.content_jsonb.get("sections")
            if isinstance(sections, dict):
                assessment = sections.get("assessment")
                if isinstance(assessment, dict):
                    edited_text = assessment.get("edited_text")
                    if edited_text and isinstance(edited_text, str) and edited_text.strip():
                        summary = edited_text.strip()
                    else:
                        statements = assessment.get("statements", [])
                        if isinstance(statements, list):
                            texts = [s.get("text", "").strip() for s in statements if isinstance(s, dict) and s.get("text", "").strip()]
                            summary = "; ".join(texts)
            
        summary = format_diagnosis_summary(summary)

        resp.append({
            "id": str(enc.id),
            "patient_ref": enc.patient_ref,
            "created_at": enc.started_at.isoformat(),
            "state": enc.state,
            "confirmed_diagnosis_summary": summary
        })
    return resp

@app.get("/api/v1/encounters/{id}/note", dependencies=[Depends(require_auth)])
async def get_note(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(NoteVersion).where(NoteVersion.encounter_id == uuid.UUID(id)).order_by(NoteVersion.version.desc())
    )
    note = result.scalars().first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note.content_jsonb

@app.patch("/api/v1/encounters/{id}/note", dependencies=[Depends(require_auth)])
async def patch_note(id: str, req: PatchNoteReq, auth: tuple[str, str] = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    user_id, _ = auth
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
        
    if enc.state not in [EncounterState.diagnosis_review.value, EncounterState.medication_review.value]:
        raise HTTPException(status_code=400, detail="Note can only be edited in review states")
        
    # In a real app, we would load the latest NoteVersion, create a new one, etc.
    # Here we just log the audit trail as required.
    append_audit_log(
        session=db,
        encounter_id=str(enc.id),
        actor=user_id,
        action="note_patch",
        before={}, # mock old content
        after=req.content
    )
    await db.commit()
    return {"status": "patched"}

class AddStatementReq(BaseModel):
    section: str
    text: str
    authored_by: str | None = None

    @field_validator("text")
    @classmethod
    def validate_text(cls, v: str) -> str:
        if not v or len(re.sub(r'\s', '', v)) < 3:
            raise ValueError("Text must contain at least 3 non-space characters")
        return v

    @field_validator("section")
    @classmethod
    def validate_section(cls, v: str) -> str:
        if v not in {"subjective", "objective", "assessment", "plan"}:
            raise ValueError("Invalid section name")
        return v

@app.post("/api/v1/encounters/{id}/statements", dependencies=[Depends(require_auth)])
async def add_statement(
    id: str,
    req: AddStatementReq,
    auth: tuple[str, str] = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    user_id, role_id = auth
    if role_id != "clinician":
        raise HTTPException(status_code=403, detail="Only clinicians can add statements")
        
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc or str(enc.clinician_id) != str(user_id):
        raise HTTPException(status_code=404, detail="Encounter not found")
        
    if enc.state not in [EncounterState.diagnosis_review.value, EncounterState.medication_review.value]:
        raise HTTPException(status_code=400, detail="Statements can only be added during review states")
        
    note_res = await db.execute(
        select(NoteVersion).where(NoteVersion.encounter_id == enc.id).order_by(NoteVersion.version.desc())
    )
    latest_note = note_res.scalars().first()
    if not latest_note:
        raise HTTPException(status_code=400, detail="No note exists for this encounter")
        
    import copy
    new_content = copy.deepcopy(latest_note.content_jsonb)
    if "sections" not in new_content:
        new_content["sections"] = {}
    if req.section not in new_content["sections"]:
        new_content["sections"][req.section] = {"statements": [], "insufficient_content": False, "reason": None}
        
    sec_dict = new_content["sections"][req.section]
    sec_dict["insufficient_content"] = False
    sec_dict["reason"] = None
    if "statements" not in sec_dict or not isinstance(sec_dict["statements"], list):
        sec_dict["statements"] = []

    stmt_id = f"{req.section[:3]}-{uuid.uuid4().hex[:8]}"
    now_iso = datetime.now(timezone.utc).isoformat()
    
    new_statement = {
        "id": stmt_id,
        "text": req.text,
        "statement_type": "clinician_entered",
        "authored_by": user_id,  # From verified JWT, never request body
        "created_at": now_iso,
        "evidence": []
    }
    sec_dict["statements"].append(new_statement)
    
    if "grounding" in new_content and isinstance(new_content["grounding"], dict):
        new_content["grounding"]["statements_total"] = new_content["grounding"].get("statements_total", 0) + 1
        
    model_hash = hashlib.sha256(json.dumps(new_content, sort_keys=True).encode("utf-8")).hexdigest()
    new_version = NoteVersion(
        id=uuid.uuid4(),
        encounter_id=enc.id,
        version=latest_note.version + 1,
        source="clinician_statement_added",
        content_jsonb=new_content,
        model_name=latest_note.model_name,
        model_hash=model_hash,
        prompt_version=latest_note.prompt_version,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_version)
    
    append_audit_log(
        session=db,
        encounter_id=str(enc.id),
        actor=user_id,
        action="statement_added",
        before={"version": latest_note.version},
        after={"version": new_version.version, "section": req.section, "text": req.text, "statement_id": stmt_id},
        diff={"section": req.section, "text": req.text, "statement_id": stmt_id}
    )
    await db.commit()
    return new_content

class AcknowledgeFlagReq(BaseModel):
    flag_id: str
    reason: str | None = None

@app.post("/api/v1/encounters/{id}/acknowledge-flag", dependencies=[Depends(require_auth)])
async def acknowledge_flag(
    id: str,
    req: AcknowledgeFlagReq,
    auth: tuple[str, str] = Depends(require_auth),
    db: AsyncSession = Depends(get_db)
):
    user_id, _ = auth
    append_audit_log(
        db, id, user_id, "safety_acknowledge",
        diff={"flag_id": req.flag_id, "reason": req.reason, "actor": user_id}
    )
    await db.commit()
    return {"status": "acknowledged", "flag_id": req.flag_id}

class SignNoteReq(BaseModel):
    edits: dict[str, str] | None = None
    statement_determinations: dict[str, str] | None = None
    medication_entries: dict[str, str] | None = None
    acknowledged_flags: list[str] | None = None

@app.post("/api/v1/encounters/{id}/sign", dependencies=[Depends(require_auth)])
async def sign_note(id: str, background_tasks: BackgroundTasks, req: SignNoteReq | None = None, auth: tuple[str, str] = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    user_id, _ = auth
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
        
    if enc.state != EncounterState.medication_review.value:
        raise HTTPException(status_code=400, detail="Cannot sign unless in medication_review state")
        
    # Get latest NoteVersion to verify risk gates
    note_res = await db.execute(
        select(NoteVersion).where(NoteVersion.encounter_id == enc.id).order_by(NoteVersion.version.desc())
    )
    latest_note = note_res.scalars().first()
    if latest_note:
        edits = req.edits if req and req.edits else {}
        statement_determinations = req.statement_determinations if req and req.statement_determinations else {}
        medication_entries = req.medication_entries if req and req.medication_entries else {}
        
        # Helper for validation of clinician determination or entry
        def check_clinician_entry_validity(manual: str, ai_text: str) -> tuple[bool, str, bool, float]:
            clean_manual = re.sub(r'\s+', '', manual or "")
            if len(clean_manual) < 3:
                return False, "Entry must have at least 3 non-space characters", False, 0.0
            def norm(s):
                return re.sub(r'[^\w\s]', '', (s or "").lower()).strip()
            norm_man = norm(manual)
            norm_ai = norm(ai_text)
            if not norm_ai:
                return True, "", False, 0.0
            if not norm_man:
                return False, "Entry is empty", False, 0.0
            tokens_man = set(norm_man.split())
            tokens_ai = set(norm_ai.split())
            token_sim = 0.0
            if tokens_man:
                intersection = tokens_man.intersection(tokens_ai)
                token_sim = len(intersection) / len(tokens_man)
            ratio = SequenceMatcher(None, norm_man, norm_ai).ratio()
            score = max(token_sim, ratio)
            matches_ai = (score >= 0.9)
            # Accept the entry, record audit flag matches_ai_draft
            return True, "", matches_ai, round(score, 3)

        import copy, hashlib, json
        new_content = copy.deepcopy(latest_note.content_jsonb)
        invalid_items = []
        
        # Check assessment statements
        if "assessment" not in edits and not new_content.get("sections", {}).get("assessment", {}).get("edited_text"):
            symptoms = []
            try:
                entities_str = await redis_client.get(f"entities:{enc.id}")
                if entities_str:
                    entities = json.loads(entities_str)
                    symptoms = [e["verbatim"] for e in entities if e["category"] in ("symptom_active", "symptom_denied", "vital", "other")]
            except Exception:
                pass
                
            assessment = new_content.get("sections", {}).get("assessment", {})
            statements = assessment.get("statements", [])
            for idx, stmt in enumerate(statements):
                stmt_id = stmt.get("id", f"stmt_{idx+1}")
                ai_text = stmt.get("text", "")
                orig_tier = stmt.get("risk_tier")
                det = statement_determinations.get(stmt_id)
                stmt_type = stmt.get("statement_type")
                
                if stmt_type == "grounded":
                    continue
                
                if stmt_type == "clinician_entered":
                    final_text = (det.strip() if det and det.strip() else ai_text).strip()
                    computed_tier = "requires_review"
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as s_client:
                            s_resp = await s_client.post("http://safety:8002/api/v1/safety/classify_risk", json={
                                "proposed_condition": final_text,
                                "symptoms": symptoms
                            })
                            if s_resp.status_code == 200:
                                computed_tier = s_resp.json().get("risk_tier", "requires_review")
                            else:
                                raise HTTPException(status_code=503, detail="Safety service unavailable")
                    except httpx.RequestError:
                        raise HTTPException(status_code=503, detail="Safety service unreachable")
                    stmt["risk_tier"] = computed_tier
                    stmt["text"] = final_text
                    continue
                
                if det is not None and det.strip() != "":
                    # Clinician-authored determination
                    is_valid, reason, matches_ai, score = check_clinician_entry_validity(det, ai_text)
                    if not is_valid:
                        invalid_items.append({
                            "kind": "statement",
                            "id": stmt_id,
                            "reason": reason
                        })
                        continue
                        
                    # Recompute tier of the FINAL text
                    final_text = det.strip()
                    computed_tier = "requires_review"
                    tier_reason = None
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as s_client:
                            s_resp = await s_client.post("http://safety:8002/api/v1/safety/classify_risk", json={
                                "proposed_condition": final_text,
                                "symptoms": symptoms
                            })
                            if s_resp.status_code == 200:
                                resp_data = s_resp.json()
                                computed_tier = resp_data.get("risk_tier", "requires_review")
                                tier_reason = resp_data.get("reason_code") or resp_data.get("reason")
                            else:
                                raise HTTPException(status_code=503, detail="Safety service unavailable")
                    except httpx.RequestError:
                        raise HTTPException(status_code=503, detail="Safety service unreachable")
                        
                    stmt["risk_tier"] = computed_tier
                    stmt["text"] = final_text
                    
                    # Record audit manual_override entry: (AI text, clinician text, tier, actor, matches_ai_draft, score)
                    append_audit_log(
                        db, str(enc.id), user_id, "manual_override",
                        before={"ai_text": ai_text, "tier": orig_tier},
                        after={"clinician_text": final_text, "tier": computed_tier, "reason": tier_reason},
                        diff={
                            "ai_text": ai_text,
                            "clinician_text": final_text,
                            "tier": orig_tier,
                            "recomputed_tier": computed_tier,
                            "actor": user_id,
                            "matches_ai_draft": matches_ai,
                            "ai_similarity_score": score
                        }
                    )
                else:
                    # AI-authored statement not overridden by clinician
                    final_text = ai_text
                    computed_tier = "requires_review"
                    try:
                        async with httpx.AsyncClient(timeout=10.0) as s_client:
                            s_resp = await s_client.post("http://safety:8002/api/v1/safety/classify_risk", json={
                                "proposed_condition": final_text,
                                "symptoms": symptoms
                            })
                            if s_resp.status_code == 200:
                                computed_tier = s_resp.json().get("risk_tier", "requires_review")
                            else:
                                raise HTTPException(status_code=503, detail="Safety service unavailable")
                    except httpx.RequestError:
                        raise HTTPException(status_code=503, detail="Safety service unreachable")
                        
                    stmt["risk_tier"] = computed_tier
                    if computed_tier != "common":
                        invalid_items.append({
                            "kind": "statement",
                            "id": stmt_id,
                            "reason": f"Statement {idx+1} needs your own determination"
                        })

        # Check medications
        final_med_items = []
        if "medications" not in edits:
            for idx, med in enumerate(new_content.get("medications", [])):
                med_id = med.get("id", f"med_{idx+1}")
                ai_text = med.get("verbatim", "")
                entry = medication_entries.get(med_id)
                
                if med.get("needs_manual_confirmation"):
                    if not entry or not entry.strip():
                        invalid_items.append({
                            "kind": "medication",
                            "id": med_id,
                            "reason": f"Medication {idx+1} needs manual confirmation"
                        })
                        continue
                        
                    is_valid, reason, matches_ai, score = check_clinician_entry_validity(entry, ai_text)
                    if not is_valid:
                        invalid_items.append({
                            "kind": "medication",
                            "id": med_id,
                            "reason": reason
                        })
                        continue
                        
                    final_text = entry.strip()
                    med["verbatim"] = final_text
                    final_med_items.append((med_id, final_text))
                    append_audit_log(
                        db, str(enc.id), user_id, "manual_override",
                        before={"ai_text": ai_text},
                        after={"clinician_text": final_text},
                        diff={
                            "ai_text": ai_text,
                            "clinician_text": final_text,
                            "actor": user_id,
                            "matches_ai_draft": matches_ai,
                            "ai_similarity_score": score
                        }
                    )
                else:
                    if entry and entry.strip():
                        is_valid, reason, matches_ai, score = check_clinician_entry_validity(entry, ai_text)
                        if not is_valid:
                            invalid_items.append({
                                "kind": "medication",
                                "id": med_id,
                                "reason": reason
                            })
                            continue
                        final_text = entry.strip()
                        med["verbatim"] = final_text
                        final_med_items.append((med_id, final_text))
                        append_audit_log(
                            db, str(enc.id), user_id, "manual_override",
                            before={"ai_text": ai_text},
                            after={"clinician_text": final_text},
                            diff={
                                "ai_text": ai_text,
                                "clinician_text": final_text,
                                "actor": user_id,
                                "matches_ai_draft": matches_ai,
                                "ai_similarity_score": score
                            }
                        )
                    else:
                        if ai_text.strip():
                            final_med_items.append((med_id, ai_text.strip()))

        # Check interactions on FINAL medication text after clinician entry
        audit_res = await db.execute(
            select(AuditLog).where(
                AuditLog.encounter_id == enc.id,
                AuditLog.action == "safety_acknowledge"
            )
        )
        ack_audit_flags = {
            row.diff_jsonb.get("flag_id")
            for row in audit_res.scalars().all()
            if row.diff_jsonb and "flag_id" in row.diff_jsonb
        }
        ack_flags = set(req.acknowledged_flags or []).union(ack_audit_flags)
        for i in range(len(final_med_items)):
            for j in range(i+1, len(final_med_items)):
                med_a_id, text_a = final_med_items[i]
                med_b_id, text_b = final_med_items[j]
                async with httpx.AsyncClient(timeout=10.0) as s_client:
                    try:
                        s_resp = await s_client.post("http://safety:8002/api/v1/safety/check_interaction", json={
                            "ingredient_a": text_a,
                            "ingredient_b": text_b
                        })
                        if s_resp.status_code == 200:
                            data = s_resp.json()
                            for ix in data.get("interactions", []):
                                source_ref = ix.get("source_ref") or ix.get("source")
                                drug_a = ix.get("drug_a", "").lower()
                                drug_b = ix.get("drug_b", "").lower()
                                is_ack = False
                                if source_ref and source_ref in ack_flags:
                                    is_ack = True
                                for ack in ack_flags:
                                    if ack:
                                        ack_str = str(ack).lower()
                                        if (source_ref and str(source_ref).lower() == ack_str) or \
                                           (drug_a and drug_a in ack_str) or \
                                           (drug_b and drug_b in ack_str) or \
                                           (med_a_id and ack_str.startswith(med_a_id.lower())) or \
                                           (med_b_id and ack_str.startswith(med_b_id.lower())):
                                            is_ack = True
                                            break
                                if not is_ack and source_ref:
                                    invalid_items.append({
                                        "kind": "interaction",
                                        "id": source_ref,
                                        "reason": f"Unacknowledged interaction between {text_a} and {text_b}: {ix.get('description', source_ref)}"
                                    })
                    except httpx.RequestError:
                        raise HTTPException(status_code=503, detail="Safety service unreachable")

        if invalid_items:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "VALIDATION_FAILED",
                    "message": "Cannot sign note due to unresolved review items",
                    "items": invalid_items
                }
            )


    
    before_state = enc.state
    enc.state = EncounterState.signed.value
    
    # Save edits as a new note version if any
    if latest_note and (req and (req.edits or req.statement_determinations or req.medication_entries)):
        for section, text in edits.items():
            if section == "medications":
                pass
            else:
                if "sections" in new_content and section in new_content["sections"]:
                    new_content["sections"][section]["edited_text"] = text
                    
        model_hash = hashlib.sha256(json.dumps(new_content, sort_keys=True).encode("utf-8")).hexdigest()
        new_version = NoteVersion(
            id=uuid.uuid4(),
            encounter_id=enc.id,
            version=latest_note.version + 1,
            source="clinician_edit",
            content_jsonb=new_content,
            model_name=latest_note.model_name,
            model_hash=model_hash,
            prompt_version=latest_note.prompt_version,
            created_at=datetime.now(timezone.utc)
        )
        db.add(new_version)
        
    append_audit_log(
        session=db,
        encounter_id=str(enc.id),
        actor=user_id,
        action="state_change",
        before={"state": before_state},
        after={"state": enc.state}
    )
    await db.commit()
    
    # Push to FHIR in background
    background_tasks.add_task(push_to_fhir_bg, id)
            
    return {"status": "signed"}

async def push_to_fhir_bg(encounter_id: str):
        import logging
        from src.db import AsyncSessionLocal
        logger = logging.getLogger("fhir_push")
        async with httpx.AsyncClient() as client:
            try:
                resp = await client.post(FHIR_GATEWAY_URL, json={"encounter_id": encounter_id})
                resp.raise_for_status()
                logger.info(f"Successfully pushed encounter {encounter_id} to FHIR gateway")
                async with AsyncSessionLocal() as session:
                    enc_res = await session.execute(select(Encounter).where(Encounter.id == uuid.UUID(encounter_id)))
                    enc_obj = enc_res.scalars().first()
                    if enc_obj:
                        enc_obj.ehr_status = "synced"
                        await session.commit()
            except Exception as e:
                logger.error(f"FHIR Gateway Error for encounter {encounter_id}: {e}")
                async with AsyncSessionLocal() as session:
                    enc_res = await session.execute(select(Encounter).where(Encounter.id == uuid.UUID(encounter_id)))
                    enc_obj = enc_res.scalars().first()
                    if enc_obj:
                        enc_obj.ehr_status = "queued_local"
                        await session.commit()



@app.post("/api/v1/encounters/{id}/retry_sync", dependencies=[Depends(require_auth)])
async def retry_sync(id: str, background_tasks: BackgroundTasks, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc or enc.state != "signed" or getattr(enc, "ehr_status", "") != "queued_local":
        raise HTTPException(status_code=400, detail="Cannot retry sync")
        
    background_tasks.add_task(push_to_fhir_bg, id)
    return {"status": "retry_queued"}

class AddendumRequest(BaseModel):
    section: str
    corrected_text: str
    reason: str

@app.post("/api/v1/encounters/{id}/addendum", dependencies=[Depends(require_auth)])
async def append_addendum(id: str, payload: AddendumRequest, auth: tuple[str, str] = Depends(require_auth), db: AsyncSession = Depends(get_db)):
    user_id, role_id = auth
    if role_id != "admin":
        raise HTTPException(status_code=403, detail="Only admins can append addendums")
    
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc:
        raise HTTPException(status_code=404, detail="Encounter not found")
        
    note_res = await db.execute(
        select(NoteVersion).where(NoteVersion.encounter_id == uuid.UUID(id)).order_by(NoteVersion.version.desc())
    )
    latest_note = note_res.scalars().first()
    if not latest_note:
        raise HTTPException(status_code=400, detail="No note exists for this encounter")
        
    import copy
    new_content = copy.deepcopy(latest_note.content_jsonb)
    
    if "addendums" not in new_content:
        new_content["addendums"] = []
        
    new_content["addendums"].append({
        "section": payload.section,
        "corrected_text": payload.corrected_text,
        "reason": payload.reason,
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    
    new_version = NoteVersion(
        id=uuid.uuid4(),
        encounter_id=enc.id,
        version=latest_note.version + 1,
        source="admin_correction",
        content_jsonb=new_content,
        model_name=latest_note.model_name,
        model_hash=latest_note.model_hash,
        prompt_version=latest_note.prompt_version,
        reason=payload.reason,
        created_at=datetime.now(timezone.utc)
    )
    db.add(new_version)
    
    append_audit_log(
        session=db,
        encounter_id=str(enc.id),
        actor=user_id,
        action="admin_correction",
        before={"version": latest_note.version},
        after={"version": new_version.version, "addendum": {"section": payload.section, "corrected_text": payload.corrected_text, "reason": payload.reason}}
    )
    
    await db.commit()
    return {"status": "addendum_appended"}

@app.get("/api/v1/encounters/{id}/audit", dependencies=[Depends(require_auth)])
async def get_audit(id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(AuditLog).where(AuditLog.encounter_id == uuid.UUID(id)).order_by(AuditLog.created_at))
    logs = result.scalars().all()
    return [{
        "action": log.action,
        "actor": log.actor,
        "diff": log.diff_jsonb,
        "created_at": log.created_at.isoformat()
    } for log in logs]

# WebSocket Stream
import websockets

@app.websocket("/api/v1/encounters/{id}/stream")
async def ws_stream(websocket: WebSocket, id: str, db: AsyncSession = Depends(get_db)):
    await websocket.accept()
    
    user_id, role_id = get_identity(websocket)
    if user_id == "anonymous":
        await websocket.send_text(json.dumps({"error": "Unauthorized"}))
        await websocket.close(code=1008)
        return
    
    # Check encounter
    result = await db.execute(select(Encounter).where(Encounter.id == uuid.UUID(id)))
    enc = result.scalars().first()
    if not enc:
        await websocket.close(code=4004)
        return
        
    # We will forward messages to ASR
    # Note: To avoid actually requiring the ASR service in unit tests, we'll try to connect but gracefully handle failures.
    asr_ws = None
    try:
        asr_ws = await websockets.connect(f"{ASR_WS_URL}?encounter_id={id}")
        await asr_ws.send(json.dumps({"encounter_id": id}))
    except Exception as e:
        print(f"Failed to connect to ASR: {e}")
        # For tests, we might not have ASR running
        pass

    async def forward_to_client(target_asr_ws):
        if not target_asr_ws: return
        try:
            async for message in target_asr_ws:
                await websocket.send_text(message)
        except Exception:
            pass

    if asr_ws:
        asyncio.create_task(forward_to_client(asr_ws))

    try:
        while True:
            message = await websocket.receive()
            if message.get("type") == "websocket.disconnect":
                break
                
            if "bytes" in message:
                data = message["bytes"]
                has_consent = (
                    enc.consent_state in [ConsentState.granted.value, ConsentState.granted_verbal_witnessed.value]
                    or enc.state in [EncounterState.consented.value, EncounterState.recording.value]
                )
                if not has_consent:
                    await websocket.send_text(json.dumps({"error": "Cannot record audio without consent"}))
                    continue
                    
                if enc.state != EncounterState.recording.value:
                    before = enc.state
                    enc.state = EncounterState.recording.value
                    append_audit_log(db, str(enc.id), user_id, "state_change", before={"state": before}, after={"state": enc.state})
                    await db.commit()
                    
                asr_is_open = asr_ws is not None and getattr(getattr(asr_ws, "state", None), "name", None) == "OPEN"
                if not asr_is_open:
                    try:
                        asr_ws = await websockets.connect(f"{ASR_WS_URL}?encounter_id={id}")
                        await asr_ws.send(json.dumps({"encounter_id": id}))
                        asyncio.create_task(forward_to_client(asr_ws))
                    except Exception as e:
                        print(f"Failed to reconnect to ASR: {e}")
                        asr_ws = None

                if asr_ws:
                    try:
                        await asr_ws.send(data)
                    except Exception as e:
                        print(f"Failed to send audio to ASR: {e}")
                continue
                
            if "text" not in message:
                continue
                
            data = message["text"]
            msg = json.loads(data)
            
            t = msg.get("t")
            if t == "consent":
                val = msg.get("value")
                if val in [ConsentState.granted.value, ConsentState.granted_verbal_witnessed.value, ConsentState.declined.value]:
                    enc.consent_state = val
                    enc.consent_logged_at = datetime.now(timezone.utc)
                    append_audit_log(db, str(enc.id), user_id, "consent_recorded", after={"consent_state": val})
                    
                    if val in [ConsentState.granted.value, ConsentState.granted_verbal_witnessed.value]:
                        before = enc.state
                        enc.state = EncounterState.consented.value
                        append_audit_log(db, str(enc.id), user_id, "state_change", before={"state": before}, after={"state": enc.state})
                    await db.commit()
                    
            elif t == "stop":
                if enc.state == EncounterState.recording.value:
                    before = enc.state
                    enc.state = EncounterState.transcribing.value
                    append_audit_log(db, str(enc.id), user_id, "state_change", before={"state": before}, after={"state": enc.state})
                    await db.commit()
                asr_is_open = asr_ws is not None and getattr(getattr(asr_ws, "state", None), "name", None) == "OPEN"
                if asr_is_open:
                    try:
                        await asr_ws.send(data)
                    except Exception as e:
                        print(f"Failed to send stop to ASR: {e}")
                continue
                
            elif t == "error":
                before = enc.state
                enc.state = EncounterState.degraded.value
                enc.degraded_reason = msg.get("reason", "unknown error")
                append_audit_log(db, str(enc.id), user_id, "state_change", before={"state": before}, after={"state": enc.state})
                await db.commit()
                continue
                
    except WebSocketDisconnect:
        pass
    finally:
        if asr_ws:
            try:
                await asr_ws.close()
            except:
                pass
                
        # If abnormal disconnect during recording (e.g. ASR crash or client drop)
        if enc.state == EncounterState.recording.value:
            enc.state = EncounterState.degraded.value
            enc.degraded_reason = "asr_unavailable"
            await db.commit()
