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

# We also need the ASR segment schema
class ASRSegment(BaseModel):
    id: str = Field(..., description="Unique segment ID, e.g., 'seg_0'")
    text: str
    start_ms: int
    end_ms: int

from packages.contracts.python.soap_note import Sections, Medication, DifferentialConsideration

class SoapNoteLLMOutput(BaseModel):
    sections: Sections
    medications: list[Medication] | None = None
    differential_considerations: list[DifferentialConsideration] | None = None
