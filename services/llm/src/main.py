"""LLM service entry point. Wraps the local OpenAI-compatible endpoint
(llama.cpp dev / vLLM prod) with extract()/compose() per docs/architecture.md
§7. Placeholder health check only in this scaffold — extract/compose are
implemented in milestone M3."""

import os
import json
import httpx
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from jinja2 import Environment, FileSystemLoader

from packages.contracts.python.soap_note import SoapNote, Model as SoapNoteModel, Grounding
from .schemas import ASRSegment, ExtractedEntities, SoapNoteLLMOutput

app = FastAPI(title="llm")

LLM_BACKEND = os.getenv("LLM_BACKEND", "http://localhost:8080/v1/chat/completions")
LLM_QUANT = os.getenv("LLM_QUANT", "unknown")

# Get path to templates
template_dir = os.path.join(os.path.dirname(__file__), "../prompts")
env = Environment(loader=FileSystemLoader(template_dir))

class GenerateRequest(BaseModel):
    encounter_id: str
    segments: list[ASRSegment]

def call_llm(system_prompt: str, response_model: type[BaseModel]) -> dict:
    payload = {
        "model": "llama-3-8b-instruct",
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
    
    with httpx.Client(timeout=120.0) as client:
        resp = client.post(LLM_BACKEND, json=payload)
        resp.raise_for_status()
        
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return json.loads(content)


@app.post("/generate_note", response_model=SoapNote)
def generate_note(req: GenerateRequest) -> SoapNote:
    # 1. Extract
    extract_template = env.get_template("extract_v1.j2")
    extract_prompt = extract_template.render(segments=[s.model_dump() for s in req.segments])
    
    entities_data = call_llm(extract_prompt, ExtractedEntities)
    extracted = ExtractedEntities.model_validate(entities_data)
    
    # 2. Compose
    compose_template = env.get_template("compose_v1.j2")
    compose_prompt = compose_template.render(entities=[e.model_dump() for e in extracted.entities])
    
    soap_data = call_llm(compose_prompt, SoapNoteLLMOutput)
    soap_output = SoapNoteLLMOutput.model_validate(soap_data)
    
    # 3. Assemble Grounding and Flags
    statements_total = 0
    for section in ["subjective", "objective", "assessment", "plan"]:
        stmts = getattr(soap_output.sections, section).root
        statements_total += len(stmts)
        
    grounding = Grounding(
        statements_total=statements_total,
        ungrounded=0,
        ungrounded_ids=[]
    )
    
    note = SoapNote(
        encounter_id=req.encounter_id,
        model=SoapNoteModel(
            name="llama-3-8b-instruct",
            quant=LLM_QUANT,
            prompt_version="v1"
        ),
        generated_at=datetime.now(timezone.utc),
        sections=soap_output.sections,
        medications=soap_output.medications or [],
        differential_considerations=soap_output.differential_considerations or [],
        safety_flags=[],
        grounding=grounding
    )
    return note

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "llm"}
