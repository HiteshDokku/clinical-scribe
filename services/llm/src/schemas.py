from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    category: str = Field(
        ..., 
        description="One of: 'symptom_active', 'symptom_denied', 'medication', 'diagnosis', 'plan', 'vital', 'other'"
    )
    verbatim: str = Field(..., description="The clinical finding, medication name, or observation.")
    details: str | None = Field(
        None, 
        description="For medications: dose, frequency, etc. For symptoms: severity, duration, context."
    )
    evidence_span_ids: list[str] = Field(
        ..., 
        min_length=1, 
        description="List of segment IDs from the transcript that provide evidence."
    )


class ExtractedEntities(BaseModel):
    entities: list[ExtractedEntity]


class ASRSegment(BaseModel):
    """A single segment from the ASR service."""
    id: str = Field(..., description="Unique segment ID, e.g., 'seg_1'")
    text: str
    start_ms: int
    end_ms: int
    speaker: str | None = None


from packages.contracts.python.soap_note import (
    SoapSection,
    Medication,
    DifferentialConsideration,
)


class SoapNoteSections(BaseModel):
    subjective: SoapSection
    objective: SoapSection
    assessment: SoapSection
    plan: SoapSection


class SoapNoteLLMOutput(BaseModel):
    """Shape the LLM is asked to produce. Mirrors Sections but uses the
    new SoapSection type with insufficient_content support."""
    sections: SoapNoteSections
    medications: list[Medication] | None = None
    differential_considerations: list[DifferentialConsideration] | None = None
