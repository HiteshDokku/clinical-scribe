"""
Round-trip tests for the generated Pydantic v2 models in packages/contracts/python/.

These tests are the canonical check that:
  1. A valid SoapNote payload survives a model_validate → model_dump round-trip unchanged.
  2. A statement with an empty evidence list raises ValidationError — enforcing the
     "no hallucinated claims" rule at the schema level.
"""
import sys
from pathlib import Path

# Ensure the repo root is on sys.path so `packages` is importable regardless
# of where pytest is invoked (gateway venv, root, container, etc.)
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import pytest
from pydantic import ValidationError
from packages.contracts.python.soap_note import (  # noqa: E402
    SoapNote,
    Model,
    Sections,
    StatementListItem,
    Grounding,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_VALID_PAYLOAD = {
    "encounter_id": "123e4567-e89b-12d3-a456-426614174000",
    "model": {
        "name": "llama-3-8b-instruct",
        "quant": "q4_k_m",
        "prompt_version": "v1.0",
    },
    "generated_at": "2026-09-20T12:00:00Z",
    "sections": {
        "subjective": [
            {
                "id": "sub1",
                "text": "Patient reports a persistent headache for three days.",
                "evidence": ["transcript:0:15"],
                "confidence": 0.95,
            }
        ],
        "objective": [],
        "assessment": [],
        "plan": [],
    },
    "grounding": {
        "statements_total": 1,
        "ungrounded": 0,
        "ungrounded_ids": [],
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_roundtrip_valid_payload():
    """A valid SOAP note survives validate → dump without data loss."""
    note = SoapNote.model_validate(_VALID_PAYLOAD)
    assert note.encounter_id == "123e4567-e89b-12d3-a456-426614174000"
    assert note.model.name == "llama-3-8b-instruct"
    assert len(note.sections.subjective.root) == 1

    dumped = note.model_dump(mode="json")
    assert dumped["model"]["name"] == "llama-3-8b-instruct"
    assert dumped["grounding"]["statements_total"] == 1


def test_empty_evidence_raises_validation_error():
    """
    A statement with evidence=[] MUST fail validation.
    This is the schema-level enforcement of "no hallucinated claims" — every
    assertion in a SOAP note must cite at least one transcript span.
    """
    bad_payload = {
        **_VALID_PAYLOAD,
        "sections": {
            "subjective": [
                {
                    "id": "sub1",
                    "text": "Patient reports a headache.",
                    "evidence": [],  # <-- violates minItems: 1
                }
            ],
            "objective": [],
            "assessment": [],
            "plan": [],
        },
    }

    with pytest.raises(ValidationError) as exc_info:
        SoapNote.model_validate(bad_payload)

    # Confirm the error actually mentions 'evidence'
    assert "evidence" in str(exc_info.value).lower()


def test_medication_empty_evidence_raises_validation_error():
    """Medications also carry an evidence field with minItems:1."""
    bad_payload = {
        **_VALID_PAYLOAD,
        "medications": [
            {
                "id": "med1",
                "verbatim": "aspirin 100mg",
                "evidence": [],  # <-- violates minItems: 1
                "flags": [],
            }
        ],
    }

    with pytest.raises(ValidationError) as exc_info:
        SoapNote.model_validate(bad_payload)

    assert "evidence" in str(exc_info.value).lower()
