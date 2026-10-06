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
    AssessmentSection,
    Model as SoapNoteModel,
    Grounding,
    Sections,
)
from .schemas import ASRSegment, ExtractedEntities, DiagnoseLLMOutput, PrescribeLLMOutput

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


class ExtractDiagnoseRequest(BaseModel):
    encounter_id: str
    segments: list[ASRSegment]

class PrescribeRequest(BaseModel):
    encounter_id: str
    confirmed_diagnosis: str
    entities: list[dict]


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
    soap_output: DiagnoseLLMOutput,
    valid_segment_ids: set[str],
) -> tuple[list[str], list[str]]:
    """Verify every cited evidence ID actually exists in the transcript.

    Returns (ungrounded_statement_ids, invalid_evidence_ids).
    A statement citing a nonexistent ID is a bug — the caller should
    decide whether to retry or surface it as flagged/ungrounded.
    """
    ungrounded_ids: list[str] = []
    invalid_ids: list[str] = []

    for section_name in ("subjective", "objective"):
        section: SoapSection = getattr(soap_output.sections, section_name)
        for stmt in section.statements.root:
            bad = [eid for eid in stmt.evidence if eid not in valid_segment_ids]
            if bad:
                ungrounded_ids.append(stmt.id)
                invalid_ids.extend(bad)

    # For assessment, evidence is not strictly required if statement_type == "inferred_diagnosis"
    if hasattr(soap_output.sections, "assessment"):
        assessment = soap_output.sections.assessment
        for stmt in assessment.statements.root:
            if getattr(stmt.statement_type, "value", stmt.statement_type) == "grounded":
                bad = [eid for eid in (stmt.evidence or []) if eid not in valid_segment_ids]
                if bad:
                    ungrounded_ids.append(stmt.id)
                    invalid_ids.extend(bad)

    return ungrounded_ids, invalid_ids


@app.post("/extract_and_diagnose")
def extract_and_diagnose(req: ExtractDiagnoseRequest) -> dict:
    if not req.segments:
        raise HTTPException(
            status_code=400,
            detail="No transcript segments provided.",
        )

    valid_segment_ids = {seg.id for seg in req.segments}
    
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

    extract_template = env.get_template("extract_v1.j2")
    extract_prompt = extract_template.render(segments=mapped_segments)
    entities_data = call_llm(extract_prompt, ExtractedEntities)
    extracted = ExtractedEntities.model_validate(entities_data)

    diagnose_template = env.get_template("diagnose_v1.j2")
    diagnose_prompt = diagnose_template.render(
        entities=[e.model_dump() for e in extracted.entities]
    )

    diagnose_output: DiagnoseLLMOutput | None = None
    ungrounded_stmt_ids: list[str] = []
    last_invalid_ids: list[str] = []

    for attempt in range(MAX_GENERATION_ATTEMPTS):
        soap_data = call_llm(diagnose_prompt, DiagnoseLLMOutput)
        diagnose_output = DiagnoseLLMOutput.model_validate(soap_data)
        ungrounded_stmt_ids, last_invalid_ids = validate_grounding(diagnose_output, short_valid_ids)
        if not last_invalid_ids:
            break

    assert diagnose_output is not None
    return {
        "entities": [e.model_dump() for e in extracted.entities],
        "diagnosis": diagnose_output.model_dump(),
        "id_map": id_map,
        "ungrounded_ids": ungrounded_stmt_ids
    }

@app.post("/prescribe")
def prescribe(req: PrescribeRequest) -> dict:
    prescribe_template = env.get_template("prescribe_v1.j2")
    prescribe_prompt = prescribe_template.render(
        confirmed_diagnosis=req.confirmed_diagnosis,
        entities=req.entities
    )

    prescribe_data = call_llm(prescribe_prompt, PrescribeLLMOutput)
    prescribe_output = PrescribeLLMOutput.model_validate(prescribe_data)
    
    return prescribe_output.model_dump()


@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "llm"}
