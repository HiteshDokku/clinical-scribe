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
    AssessmentSection,
    Medication,
    DifferentialConsideration,
)


class DiagnosisSections(BaseModel):
    subjective: SoapSection
    objective: SoapSection
    assessment: AssessmentSection

class PrescriptionSections(BaseModel):
    plan: SoapSection


class DiagnoseLLMOutput(BaseModel):
    sections: DiagnosisSections
    differential_considerations: list[DifferentialConsideration] | None = None

class PrescribeLLMOutput(BaseModel):
    sections: PrescriptionSections
    medications: list[Medication] | None = None
