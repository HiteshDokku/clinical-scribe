from typing import Literal
from pydantic import BaseModel


class SessionStart(BaseModel):
    encounter_id: str


class TranscriptEvent(BaseModel):
    id: str | None = None
    type: Literal["partial", "final"]
    text: str
    start_ms: int
    end_ms: int
    confidence: float
    speaker: str | None = None
    speaker_confidence: float | None = None
