import pytest
from httpx import AsyncClient
import pytest_asyncio
from src.main import app
from src.db import engine, get_db
from sqlalchemy import text
from unittest.mock import patch
import httpx

@pytest.mark.asyncio
async def test_safety_service_unreachable_returns_503(mocker):
    # Mock httpx.AsyncClient.post to raise httpx.RequestError
    mocker.patch("httpx.AsyncClient.post", side_effect=httpx.RequestError("Unreachable"))
    
    # We need a user and an encounter to sign
    # Let's use a dummy user and encounter
    # Let's mock db calls to bypass auth
    from src.db import get_identity
    app.dependency_overrides[get_identity] = lambda: {"sub": "123e4567-e89b-12d3-a456-426614174000", "role": "clinician"}
    
    # The encounter must be in diagnosis_review or medication_review
    # Let's just create an encounter in the DB
    async with engine.begin() as conn:
        user_id = "123e4567-e89b-12d3-a456-426614174000"
        enc_id = "223e4567-e89b-12d3-a456-426614174001"
        await conn.execute(text(f"INSERT INTO users (id, role) VALUES ('{user_id}', 'clinician') ON CONFLICT DO NOTHING"))
        await conn.execute(text(f"INSERT INTO encounters (id, clinician_id, state) VALUES ('{enc_id}', '{user_id}', 'medication_review') ON CONFLICT DO NOTHING"))
        
        await conn.execute(text(f"INSERT INTO note_versions (id, encounter_id, version, source, content_jsonb) VALUES ('323e4567-e89b-12d3-a456-426614174002', '{enc_id}', 1, 'model_generation', '{{\"sections\": {{\"assessment\": {{\"statements\": [{{\"id\": \"1\", \"text\": \"test diagnosis\", \"statement_type\": \"inferred_diagnosis\"}}]}}}}}}') ON CONFLICT DO NOTHING"))

    async with AsyncClient(app=app, base_url="http://test") as ac:
        response = await ac.post(f"/api/v1/encounters/{enc_id}/sign", json={"edits": {}, "statement_determinations": {}})
        assert response.status_code == 503
        assert response.json() == {"detail": "Safety service unreachable"}
