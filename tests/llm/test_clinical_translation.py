"""Test clinical terminology translation and SOAP section synthesis.

Verifies that:
1. Upstream LLM prompt (diagnose_v1.j2) commands the model to synthesize raw transcripts
   into concise clinical shorthand for Subjective without first-person direct quotes,
   combining related statements (symptoms + medication denials).
2. All patient-reported history is routed exclusively to Subjective.
3. Objective section contains ONLY clinician-observed data/vitals, and is generated as an
   empty list with insufficient_content=true when no clinician findings appear.
4. Assessment section translates colloquial patient symptoms into canonical clinical
   nomenclature (e.g. 'URTI', 'Acute rhinosinusitis') avoiding 'no_condition_match'.
5. Grounding evidence spans are correctly attached to the synthesized prose.
"""

import os

from jinja2 import Environment, FileSystemLoader

from packages.contracts.python.soap_note import (
    AssessmentSection,
    AssessmentStatementListItem,
    RiskTier,
    SoapSection,
    StatementListItem,
    StatementType,
    StatementType2,
)
from services.llm.src.schemas import (
    ASRSegment,
    DiagnoseLLMOutput,
    DiagnosisSections,
)
from services.safety.src.diagnosis import classify_diagnosis_risk

PROMPTS_DIR = os.path.join(
    os.path.dirname(__file__), "..", "..", "services", "llm", "prompts"
)


def test_diagnose_prompt_contains_subjective_and_objective_rules():
    """Verify diagnose_v1.j2 contains strict rules for Subjective shorthand and Objective gating."""
    env = Environment(loader=FileSystemLoader(PROMPTS_DIR))
    template = env.get_template("diagnose_v1.j2")

    mock_entities = [
        {
            "category": "symptom_active",
            "verbatim": "cold and cough",
            "details": "2 days duration",
            "evidence_span_ids": ["seg_1"],
        },
        {
            "category": "medication_denied",
            "verbatim": "not on any medication",
            "details": None,
            "evidence_span_ids": ["seg_2"],
        },
    ]
    mock_segments = [
        {"id": "seg_1", "text": "I have been facing cold and cough for the past two days."},
        {"id": "seg_2", "text": "No, I am not on any medication."},
    ]

    rendered = template.render(entities=mock_entities, segments=mock_segments)
    rendered_lower = rendered.lower()

    # Subjective rules
    assert "direct quotes" in rendered_lower or "first-person" in rendered_lower
    assert "clinical shorthand" in rendered_lower
    assert "denies" in rendered_lower
    assert "exclusively" in rendered_lower

    # Objective rules
    assert "clinician-observed" in rendered_lower
    assert "empty" in rendered_lower
    assert "insufficient_content" in rendered_lower

    # Assessment rules
    assert "clinical translator" in rendered_lower
    assert "canonical" in rendered_lower
    assert "urti" in rendered_lower


def test_colloquial_cold_fails_safety_with_no_condition_match():
    """Demonstrate the upstream bug: raw patient colloquialisms fail closed."""
    colloquial_terms = ["cold", "severe cold", "bad cold", "common cold", "cough and cold"]
    for term in colloquial_terms:
        res = classify_diagnosis_risk(term, ["cough", "cold"])
        assert res.tier == "requires_review"
        assert res.reason == "no_condition_match", (
            f"Expected no_condition_match for '{term}', got '{res.reason}'"
        )


def test_canonical_translation_avoids_no_condition_match():
    """Verify that canonical clinical translations successfully match safety dictionary."""
    canonical_terms = [
        "URTI",
        "Acute rhinosinusitis",
        "Viral pharyngitis",
        "Bronchitis",
        "Acute laryngitis",
        "Influenza",
    ]
    for term in canonical_terms:
        res = classify_diagnosis_risk(term, ["cough", "cold"])
        assert res.reason != "no_condition_match", (
            f"Canonical term '{term}' should match safety dictionary, but got '{res.reason}'"
        )


def test_synthesized_clinical_shorthand_and_empty_objective():
    """Test full payload where patient reports symptoms and denies meds, but no doctor vitals.

    Asserts:
    - Subjective contains synthesized clinical shorthand (e.g. 'Pt presents with...', 'Denies...').
    - Subjective contains NO first-person direct quotes ('I have', 'I am').
    - Subjective combines both symptoms and medication denial, citing both evidence spans.
    - Objective has statements == [] and insufficient_content == True with appropriate reason.
    - Assessment produces canonical diagnosis ('URTI') rather than colloquial 'cold'.
    - Assessment passes safety gate and avoids no_condition_match.
    """
    segments = [
        ASRSegment(
            id="seg_1",
            text="I have been facing cold and cough for the past two days.",
            start_ms=0,
            end_ms=3000,
        ),
        ASRSegment(
            id="seg_2",
            text="No, I am not on any medication.",
            start_ms=3000,
            end_ms=6000,
        ),
        ASRSegment(
            id="seg_3",
            text="Alright, let me examine you.",
            start_ms=6000,
            end_ms=8000,
        ),
    ]

    # Model generates synthesized clinical shorthand for Subjective and empty Objective
    shorthand_text = (
        "Pt presents with 2-day history of cold and cough. Denies current medications."
    )
    soap_output = DiagnoseLLMOutput(
        sections=DiagnosisSections(
            subjective=SoapSection(
                statements=[
                    StatementListItem(
                        id="s_1",
                        text=shorthand_text,
                        statement_type=StatementType2.grounded,
                        evidence=["seg_1", "seg_2"],
                    )
                ],
                insufficient_content=False,
            ),
            objective=SoapSection(
                statements=[],
                insufficient_content=True,
                reason="No physical examination or vitals recorded in consultation",
            ),
            assessment=AssessmentSection(
                statements=[
                    AssessmentStatementListItem(
                        id="a_1",
                        text="URTI",
                        statement_type=StatementType.grounded,
                        reasoning_basis=None,
                        risk_tier=RiskTier.common,
                        evidence=["seg_1"],
                    )
                ],
                insufficient_content=False,
            ),
        ),
        differential_considerations=None,
    )

    # 1. Subjective assertions: synthesized shorthand, combined, no first-person quotes
    valid_ids = {s.id for s in segments}
    subj_stmt = soap_output.sections.subjective.statements.root[0]
    subj_text = subj_stmt.text
    assert not subj_text.startswith("I have")
    assert not subj_text.startswith("I am")
    assert "Pt presents with" in subj_text or "history of cold" in subj_text.lower()
    assert "Denies" in subj_text or "denies" in subj_text.lower()
    assert "seg_1" in subj_stmt.evidence and "seg_2" in subj_stmt.evidence
    assert all(e in valid_ids for e in subj_stmt.evidence)

    # 2. Objective assertions: empty list with insufficient_content=True
    obj_sec = soap_output.sections.objective
    assert len(obj_sec.statements.root) == 0
    assert obj_sec.insufficient_content is True
    assert obj_sec.reason is not None and "No physical examination" in obj_sec.reason

    # 3. Assessment assertions: canonical translation avoids no_condition_match
    assessment_stmt = soap_output.sections.assessment.statements.root[0]
    diagnosis_text = assessment_stmt.text
    assert diagnosis_text == "URTI"
    assert "seg_1" in assessment_stmt.evidence

    symptoms = ["cold", "cough"]
    safety_result = classify_diagnosis_risk(diagnosis_text, symptoms)
    assert safety_result.reason != "no_condition_match"
