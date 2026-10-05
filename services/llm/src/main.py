"""LLM service entry point. Wraps the local OpenAI-compatible endpoint
(llama.cpp dev / vLLM prod) with extract()/compose() per docs/architecture.md
§7. Includes grounding validation: every cited evidence ID must exist in
the real transcript segment IDs."""

import logging
import os
import json
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader

from packages.contracts.python.soap_note import (
    SoapNote,
    SoapSection,
    Model as SoapNoteModel,
    Grounding,
    Sections,
)
from .schemas import ASRSegment, ExtractedEntities, SoapNoteLLMOutput

app = FastAPI(title="llm")

# Why REDACTED: AGENTS.md prohibits logging clinical text, patient
# identifiers, or raw transcripts. We log structure (counts, IDs) only.
logger = logging.getLogger("llm.service")

LLM_BACKEND = os.getenv("LLM_BACKEND", "http://localhost:8080/v1/chat/completions")
LLM_QUANT = os.getenv("LLM_QUANT", "unknown")
MAX_GENERATION_ATTEMPTS = 2

# Get path to templates
template_dir = os.path.join(os.path.dirname(__file__), "../prompts")
env = Environment(loader=FileSystemLoader(template_dir))


class GenerateRequest(BaseModel):
    encounter_id: str
    segments: list[ASRSegment]


class GroundingFailure(Exception):
    """Raised when the LLM's output cites segment IDs that don't exist
    in the transcript. This is a generation bug, not a user error."""
    def __init__(self, invalid_ids: list[str], statement_ids: list[str]) -> None:
        self.invalid_ids = invalid_ids
        self.statement_ids = statement_ids
        super().__init__(
            f"Grounding failure: statements {statement_ids} cite "
            f"non-existent segment IDs {invalid_ids}"
        )


def call_llm(system_prompt: str, response_model: type[BaseModel]) -> dict:
    """Send a structured-output request to the local LLM backend."""
    payload = {
        "model": os.getenv("LLM_MODEL_NAME", "llama3.1:latest"),
        "messages": [
            {"role": "system", "content": system_prompt}
        ],
        "temperature": 0.0,
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": response_model.__name__,
                "schema": response_model.model_json_schema(),
                "strict": True
            }
        }
    }

    if not LLM_BACKEND.startswith("http"):
        raise ValueError(f"Invalid LLM_BACKEND configured: {LLM_BACKEND}")

    try:
        with httpx.Client(timeout=120.0) as client:
            resp = client.post(LLM_BACKEND, json=payload)
            resp.raise_for_status()

            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            return json.loads(content)
    except Exception as e:
        logger.error("LLM call failed natively: %s", type(e).__name__)
        raise ValueError(f"LLM backend connection or generation failed: {e}") from e


def validate_grounding(
    soap_output: SoapNoteLLMOutput,
    valid_segment_ids: set[str],
) -> tuple[list[str], list[str]]:
    """Verify every cited evidence ID actually exists in the transcript.

    Returns (ungrounded_statement_ids, invalid_evidence_ids).
    A statement citing a nonexistent ID is a bug — the caller should
    decide whether to retry or surface it as flagged/ungrounded.
    """
    ungrounded_ids: list[str] = []
    invalid_ids: list[str] = []

    for section_name in ("subjective", "objective", "assessment", "plan"):
        section: SoapSection = getattr(soap_output.sections, section_name)
        for stmt in section.statements:
            bad = [eid for eid in stmt.evidence if eid not in valid_segment_ids]
            if bad:
                ungrounded_ids.append(stmt.id)
                invalid_ids.extend(bad)

    return ungrounded_ids, invalid_ids


@app.post("/generate_note", response_model=SoapNote)
def generate_note(req: GenerateRequest) -> SoapNote:
    if not req.segments:
        raise HTTPException(
            status_code=400,
            detail="No transcript segments provided. Cannot generate SOAP note.",
        )

    valid_segment_ids = {seg.id for seg in req.segments}
    logger.info(
        "generate_note: encounter=%s segment_count=%d",
        req.encounter_id,
        len(req.segments),
    )

    import re
    def extract_raw_id(raw: str) -> str:
        return re.sub(r"^seg_[^_]+_", "", raw)

    id_map = {str(i): extract_raw_id(seg.id) for i, seg in enumerate(req.segments)}
    short_valid_ids = set(id_map.keys())

    mapped_segments = []
    for i, seg in enumerate(req.segments):
        s_dump = seg.model_dump()
        s_dump["id"] = str(i)
        mapped_segments.append(s_dump)

    # 1. Extract
    extract_template = env.get_template("extract_v1.j2")
    extract_prompt = extract_template.render(
        segments=mapped_segments
    )

    entities_data = call_llm(extract_prompt, ExtractedEntities)
    extracted = ExtractedEntities.model_validate(entities_data)

    # 2. Compose (with retry on grounding failure)
    compose_template = env.get_template("compose_v1.j2")
    compose_prompt = compose_template.render(
        entities=[e.model_dump() for e in extracted.entities]
    )

    soap_output: SoapNoteLLMOutput | None = None
    ungrounded_stmt_ids: list[str] = []
    last_invalid_ids: list[str] = []

    for attempt in range(MAX_GENERATION_ATTEMPTS):
        soap_data = call_llm(compose_prompt, SoapNoteLLMOutput)
        soap_output = SoapNoteLLMOutput.model_validate(soap_data)

        ungrounded_stmt_ids, last_invalid_ids = validate_grounding(
            soap_output, short_valid_ids
        )

        if not last_invalid_ids:
            # All evidence IDs are valid
            break

        logger.warning(
            "Grounding failure attempt=%d invalid_ids=%s",
            attempt + 1,
            last_invalid_ids,
        )

    # After retries, if still invalid: keep the output but mark the
    # offending statements as ungrounded so the review UI can flag them.
    assert soap_output is not None

    # 3. Compute grounding stats and remap IDs back to real UUIDs
    statements_total = 0
    for section_name in ("subjective", "objective", "assessment", "plan"):
        section: SoapSection = getattr(soap_output.sections, section_name)
        statements_total += len(section.statements)
        for stmt in section.statements:
            stmt.evidence = [id_map.get(eid, eid) for eid in stmt.evidence]

    grounding = Grounding(
        statements_total=statements_total,
        ungrounded=len(ungrounded_stmt_ids),
        ungrounded_ids=ungrounded_stmt_ids,
    )

    note = SoapNote(
        encounter_id=req.encounter_id,
        model=SoapNoteModel(
            name="llama-3-8b-instruct",
            quant=LLM_QUANT,
            prompt_version="v1",
        ),
        generated_at=datetime.now(timezone.utc),
        sections=Sections(
            subjective=soap_output.sections.subjective,
            objective=soap_output.sections.objective,
            assessment=soap_output.sections.assessment,
            plan=soap_output.sections.plan,
        ),
        medications=soap_output.medications or [],
        differential_considerations=soap_output.differential_considerations or [],
        safety_flags=[],
        grounding=grounding,
    )
    return note


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "llm"}
