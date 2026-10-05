# generated from soap_note.schema.json
# re-generated after Phase 3 schema change: sections are now objects
# with { statements, insufficient_content, reason } instead of bare arrays.

from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import AwareDatetime, BaseModel, Field, confloat


class Model(BaseModel):
    name: Literal['llama-3-8b-instruct']
    quant: str
    prompt_version: str


class Dose(BaseModel):
    value: float | None = None
    unit: str | None = None


class DifferentialConsideration(BaseModel):
    label: str
    trigger_spans: list[str] = Field(..., min_length=1)
    rationale: str


class Grounding(BaseModel):
    statements_total: int
    ungrounded: int
    ungrounded_ids: list[str]


class StatementListItem(BaseModel):
    id: str
    text: str
    evidence: list[str] = Field(
        ...,
        description="Non-empty by design — a statement with no cited transcript span cannot exist. This is the schema-level enforcement of 'no hallucinated claims.'",
        min_length=1,
    )
    confidence: confloat(ge=0.0, le=1.0) | None = None


class SoapSection(BaseModel):
    """A single SOAP section (S/O/A/P). Contains either a non-empty
    statements list OR insufficient_content=True with a reason."""
    statements: list[StatementListItem] = Field(default_factory=list)
    insufficient_content: bool = False
    reason: str | None = Field(
        None,
        description="One-line explanation when insufficient_content is true, e.g. 'Not discussed in this consultation'. Null otherwise.",
    )


class Severity(Enum):
    low = 'low'
    moderate = 'moderate'
    high = 'high'


class Type(Enum):
    interaction = 'interaction'
    dose_range = 'dose_range'
    unresolved_medication = 'unresolved_medication'


class SafetyFlag(BaseModel):
    severity: Severity
    type: Type
    pair: list[str] | None = None
    source_ref: str = Field(
        ...,
        description="Mandatory citation, e.g. 'ONC-HighPriority#412' or 'DDInter2#88014'. Never null — an interaction flag with no source is not permitted.",
    )
    message: str


class Sections(BaseModel):
    subjective: SoapSection
    objective: SoapSection
    assessment: SoapSection
    plan: SoapSection


class Medication(BaseModel):
    id: str
    verbatim: str
    ingredient_id: str | None = Field(
        None,
        description='FK into the local ingredient_dictionary table. Null if unresolved.',
    )
    match_confidence: confloat(ge=0.0, le=1.0) | None = None
    needs_manual_confirmation: bool | None = False
    dose: Dose | None = None
    frequency: str | None = None
    route: str | None = None
    duration_days: int | None = None
    evidence: list[str] = Field(..., min_length=1)
    flags: list[SafetyFlag]


class SoapNote(BaseModel):
    encounter_id: str
    model: Model
    generated_at: AwareDatetime
    sections: Sections
    medications: list[Medication] | None = None
    differential_considerations: list[DifferentialConsideration] | None = None
    safety_flags: list[SafetyFlag] | None = None
    grounding: Grounding
