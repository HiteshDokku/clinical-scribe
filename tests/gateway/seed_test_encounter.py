import asyncio
import uuid
from datetime import datetime, timezone
import json
import sys
import os

# Ensure we can import from src
sys.path.append("/app")

from src.db import AsyncSessionLocal
from src.models import Encounter, EncounterState, NoteVersion, User

async def seed_test_encounter():
    async with AsyncSessionLocal() as session:
        from sqlalchemy import text
        # Get a clinician using a bypass or directly
        await session.execute(text("SET LOCAL app.current_role_id = 'admin'"))
        
        from sqlalchemy import select
        res = await session.execute(select(User).where(User.role_id == "clinician"))
        clinician = res.scalars().first()
        if not clinician:
            print("No clinician found. Run the seed migration first.")
            return

        # Now set the local variables so we can insert the encounter
        await session.execute(text(f"SET LOCAL app.current_user_id = '{clinician.id}'"))
        await session.execute(text("SET LOCAL app.current_role_id = 'clinician'"))

        enc_id = uuid.uuid4()
        now = datetime.now(timezone.utc)
        enc = Encounter(
            id=enc_id,
            clinician_id=clinician.id,
            patient_ref="Test Walkthrough Patient",
            consent_state="granted",
            consent_logged_at=now,
            started_at=now,
            state=EncounterState.diagnosis_review.value
        )
        session.add(enc)
        
        note_content = {
            "encounter_id": str(enc_id),
            "model": {"name": "test-model", "quant": "none", "prompt_version": "v1"},
            "sections": {
                "subjective": {"statements": [], "insufficient_content": False},
                "objective": {"statements": [], "insufficient_content": True, "reason": "Not discussed in this consultation"},
                "assessment": {
                    "statements": [
                        {
                            "id": "stmt_1",
                            "text": "Chest pain radiating to left arm",
                            "risk_tier": "red_flag",
                            "reasoning_basis": "Classic angina symptom"
                        }
                    ]
                },
                "plan": {"statements": []}
            },
            "medications": [
                {
                    "id": "med_1",
                    "verbatim": "Warfarin",
                    "needs_manual_confirmation": True,
                    "flags": []
                }
            ],
            "safety_flags": [],
            "grounding": {"statements_total": 1, "ungrounded": 0, "ungrounded_ids": []}
        }
        
        note_ver = NoteVersion(
            id=uuid.uuid4(),
            encounter_id=enc_id,
            version=1,
            source="ai",
            content_jsonb=note_content,
            model_name="test-model",
            model_hash="test_hash",
            prompt_version="v1",
            created_at=now
        )
        session.add(note_ver)
        await session.commit()
        
        print(f"{enc_id}")

if __name__ == "__main__":
    asyncio.run(seed_test_encounter())
