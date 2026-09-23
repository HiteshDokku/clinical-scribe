"""safety service entry point."""

from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from src.db import get_db
from src.drugs import resolve_medication_mention, check_pair
from src.grounding import verify_grounding

app = FastAPI(title="safety")

class ResolveRequest(BaseModel):
    mention: str

class ResolveResponse(BaseModel):
    ingredient: Optional[str]
    needs_manual_confirmation: bool

class CheckPairRequest(BaseModel):
    ingredient_a: str
    ingredient_b: str

class Interaction(BaseModel):
    severity: str
    source: str
    description: Optional[str]

class CheckPairResponse(BaseModel):
    interactions: List[Interaction]

class GroundingRequest(BaseModel):
    statement: str
    evidence_spans: List[Tuple[int, int]]
    transcript_segments: List[Dict]

class GroundingResponse(BaseModel):
    is_grounded: bool

@app.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok", "service": "safety"}

@app.post("/api/v1/safety/resolve", response_model=ResolveResponse)
async def resolve(req: ResolveRequest, db: AsyncSession = Depends(get_db)):
    ingredient, needs_conf = await resolve_medication_mention(req.mention, db)
    return ResolveResponse(ingredient=ingredient, needs_manual_confirmation=needs_conf)

@app.post("/api/v1/safety/check_interaction", response_model=CheckPairResponse)
async def check_interaction(req: CheckPairRequest, db: AsyncSession = Depends(get_db)):
    interactions = await check_pair(req.ingredient_a, req.ingredient_b, db)
    return CheckPairResponse(interactions=interactions)

@app.post("/api/v1/safety/verify_grounding", response_model=GroundingResponse)
def verify(req: GroundingRequest):
    result = verify_grounding(req.statement, req.evidence_spans, req.transcript_segments)
    return GroundingResponse(is_grounded=result)
