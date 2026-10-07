import os
import uuid
import httpx
import asyncio
import base64
import json
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fhir.resources.bundle import Bundle

app = FastAPI(title="fhir-gateway")

FHIR_ALLOWLIST_HOST = os.getenv("FHIR_ALLOWLIST_HOST", "hapi-fhir.internal.hospital.example")
FHIR_ALLOWLIST_PORT = os.getenv("FHIR_ALLOWLIST_PORT", "8443")
FHIR_MTLS_CERT_PATH = os.getenv("FHIR_MTLS_CERT_PATH", "")
FHIR_MTLS_KEY_PATH = os.getenv("FHIR_MTLS_KEY_PATH", "")
GATEWAY_URL = "http://gateway:8000"

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "fhir-gateway"}

class PushRequest(BaseModel):
    encounter_id: str
    target_url: str = None  # Optional override for testing

async def execute_fhir_push(target_url: str, bundle_dict: dict):
    # Egress restriction
    scheme = "https" if str(FHIR_ALLOWLIST_PORT) == "8443" else "http"
    expected_prefix = f"{scheme}://{FHIR_ALLOWLIST_HOST}:{FHIR_ALLOWLIST_PORT}"
    if not target_url.startswith(expected_prefix):
        raise ValueError(f"Egress restricted. Target {target_url} not in allowlist.")
        
    cert = None
    if FHIR_MTLS_CERT_PATH and FHIR_MTLS_KEY_PATH:
        if os.path.exists(FHIR_MTLS_CERT_PATH) and os.path.exists(FHIR_MTLS_KEY_PATH):
            cert = (FHIR_MTLS_CERT_PATH, FHIR_MTLS_KEY_PATH)
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # We use verify=False for local tests with self-signed certs
            async with httpx.AsyncClient(cert=cert, verify=False) as client:
                resp = await client.post(target_url, json=bundle_dict, timeout=10.0, headers={"Idempotency-Key": bundle_dict["id"]})
                resp.raise_for_status()
                return resp.json()
        except Exception as e:
            if attempt == max_retries - 1:
                err_msg = getattr(e, "response", None)
                if err_msg is not None:
                    raise RuntimeError(f"FHIR upstream error: {err_msg.text}")
                raise RuntimeError(f"FHIR upstream error: {str(e)}")
            await asyncio.sleep(1)

@app.post("/push")
async def push_mock(payload: PushRequest):
    async with httpx.AsyncClient() as client:
        enc_res = await client.get(f"{GATEWAY_URL}/api/v1/encounters/{payload.encounter_id}")
        if enc_res.status_code != 200:
            print(f"DEBUG: Encounter fetch failed with {enc_res.status_code} {enc_res.text}")
            raise HTTPException(status_code=400, detail="Encounter not found")
        enc_data = enc_res.json()
        
        if enc_data.get("state") != "signed":
            print(f"DEBUG: Encounter not signed: {enc_data.get('state')}")
            raise HTTPException(status_code=400, detail="Cannot push unsigned note to FHIR")

        note_res = await client.get(f"{GATEWAY_URL}/api/v1/encounters/{payload.encounter_id}/note")
        if note_res.status_code != 200:
            print(f"DEBUG: Note fetch failed with {note_res.status_code} {note_res.text}")
            raise HTTPException(status_code=400, detail="Note not found")
        note_data = note_res.json()

    bundle_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"bundle_{payload.encounter_id}"))
    bundle_dict = {
        "resourceType": "Bundle",
        "id": bundle_id,
        "type": "transaction",
        "entry": []
    }
    
    namespace = uuid.UUID(payload.encounter_id)
    
    # 1. Encounter
    fhir_enc_id = str(uuid.uuid5(namespace, "Encounter"))
    bundle_dict["entry"].append({
        "fullUrl": f"urn:uuid:{fhir_enc_id}",
        "resource": {
            "resourceType": "Encounter",
            "id": fhir_enc_id,
            "status": "finished",
            "class": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "AMB"}]}]
        },
        "request": {"method": "PUT", "url": f"Encounter/{fhir_enc_id}"}
    })
    
    # 1.5 Patient (dummy to satisfy referential integrity)
    pat_id = str(uuid.uuid5(namespace, "Patient"))
    bundle_dict["entry"].append({
        "fullUrl": f"urn:uuid:{pat_id}",
        "resource": {
            "resourceType": "Patient",
            "id": pat_id,
            "active": True
        },
        "request": {"method": "PUT", "url": f"Patient/{pat_id}"}
    })
    
    # 2. DocumentReference
    doc_id = str(uuid.uuid5(namespace, "DocumentReference"))
    meta_tags = []
    
    # Find all statements to build provenance meta tags
    sections = note_data.get("sections", {})
    assessment_stmts = sections.get("assessment", {}).get("statements", [])
    for stmt in assessment_stmts:
        if "statement_type" in stmt:
            meta_tags.append({"system": "http://example.org/fhir/CodeSystem/statement-type", "code": stmt["statement_type"]})
        if "risk_tier" in stmt:
            meta_tags.append({"system": "http://example.org/fhir/CodeSystem/risk-tier", "code": stmt["risk_tier"]})
            
    note_content = base64.b64encode(json.dumps(note_data).encode()).decode()
    bundle_dict["entry"].append({
        "fullUrl": f"urn:uuid:{doc_id}",
        "resource": {
            "resourceType": "DocumentReference",
            "id": doc_id,
            "meta": {"tag": meta_tags} if meta_tags else None,
            "status": "current",
            "content": [{"attachment": {"contentType": "application/json", "data": note_content}}]
        },
        "request": {"method": "PUT", "url": f"DocumentReference/{doc_id}"}
    })
    
    # 3. MedicationRequest
    for idx, med in enumerate(note_data.get("medications", [])):
        med_id = str(uuid.uuid5(namespace, f"Medication_{idx}"))
        med_res = {
            "resourceType": "MedicationRequest",
            "id": med_id,
            "status": "active",
            "intent": "order",
            "subject": {"reference": f"Patient/{pat_id}"},
            "medication": {"concept": {"text": med.get("drug", med.get("verbatim", "Unknown"))}}
        }
        if med.get("needs_manual_confirmation"):
            med_res["note"] = [{"text": "Required manual entry due to high risk class"}]
            
        bundle_dict["entry"].append({
            "fullUrl": f"urn:uuid:{med_id}",
            "resource": med_res,
            "request": {"method": "PUT", "url": f"MedicationRequest/{med_id}"}
        })
        
    # Validate against FHIR schema
    try:
        Bundle.parse_obj(bundle_dict)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"FHIR schema validation failed: {str(e)}")

    scheme = "https" if str(FHIR_ALLOWLIST_PORT) == "8443" else "http"
    target_url = payload.target_url or f"{scheme}://{FHIR_ALLOWLIST_HOST}:{FHIR_ALLOWLIST_PORT}/fhir"
    
    try:
        await execute_fhir_push(target_url, bundle_dict)
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except RuntimeError as re:
        raise HTTPException(status_code=502, detail=str(re))
        
    return {"status": "ok", "message": "Pushed to FHIR successfully"}
