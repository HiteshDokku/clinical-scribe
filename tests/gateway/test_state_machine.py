import uuid
import pytest
import pytest_asyncio
import asyncio
from contextlib import asynccontextmanager
from unittest.mock import patch, AsyncMock, MagicMock
from httpx import AsyncClient, ASGITransport
from httpx_ws import aconnect_ws
from httpx_ws.transport import ASGIWebSocketTransport

from src.main import app, get_db
from src.db import engine as prod_engine
from src.models import Base
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import StaticPool

engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
TestingSessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)

async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session

app.dependency_overrides[get_db] = override_get_db

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()

@asynccontextmanager
async def get_client():
    async with ASGIWebSocketTransport(app=app) as transport:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

@pytest.mark.asyncio
async def test_happy_path_and_fhir_spy():
    async with get_client() as client:
        # 1. Create Encounter
        resp = await client.post("/api/v1/encounters", json={"clinician_id": "dr_smith", "patient_ref": "pat_123"})
        assert resp.status_code == 200
        enc_id = resp.json()["id"]
        assert resp.json()["state"] == "created"
        
        # Spy on httpx post
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_resp = MagicMock()
            mock_resp.raise_for_status = MagicMock()
            mock_post.return_value = mock_resp
            
            # 2. WebSocket for Consent and Recording
            with patch("websockets.connect", new_callable=AsyncMock) as mock_ws_connect:
                mock_ws = AsyncMock()
                mock_ws_connect.return_value = mock_ws
                
                async with aconnect_ws(f"ws://test/api/v1/encounters/{enc_id}/stream", client=client) as ws:
                    await ws.send_json({"t": "consent", "value": "granted"})
                    await ws.send_json({"t": "audio", "data": "dummy_pcm"})
                    await ws.send_json({"t": "stop"})
                    await asyncio.sleep(0.1)
            
            mock_post.assert_not_called()
            
            # 3. Generate note
            resp = await client.request("POST", f"/api/v1/encounters/{enc_id}/generate")
            assert resp.status_code == 200
            mock_post.assert_not_called()
            
            # 4. Patch Note
            resp = await client.request("PATCH", f"/api/v1/encounters/{enc_id}/note", json={"content": {"foo": "bar"}})
            assert resp.status_code == 200
            mock_post.assert_not_called()
            
            # 5. Sign Note
            resp = await client.request("POST", f"/api/v1/encounters/{enc_id}/sign")
            assert resp.status_code == 200
            
            # Now FHIR should have been called!
            mock_post.assert_called_once()
            args, kwargs = mock_post.call_args
            assert args[0] == "http://fhir-gateway:8003/push"
            assert kwargs["json"]["encounter_id"] == enc_id

@pytest.mark.asyncio
async def test_declined_consent():
    async with get_client() as client:
        resp = await client.post("/api/v1/encounters", json={"clinician_id": "dr_smith", "patient_ref": "pat_123"})
        enc_id = resp.json()["id"]
        
        with patch("websockets.connect", new_callable=AsyncMock) as mock_ws_connect:
            mock_ws = AsyncMock()
            mock_ws_connect.return_value = mock_ws
            
            async with aconnect_ws(f"ws://test/api/v1/encounters/{enc_id}/stream", client=client) as ws:
                await ws.send_json({"t": "consent", "value": "declined"})
                await ws.send_json({"t": "audio", "data": "dummy"})
                await asyncio.sleep(0.1)
                msg = await ws.receive_json()
                assert "error" in msg
                assert "without consent" in msg["error"]
                
        resp = await client.get(f"/api/v1/encounters/{enc_id}/audit")
        assert resp.status_code == 200
        logs = resp.json()
        assert any(log["action"] == "consent_recorded" and log["diff"]["after"]["consent_state"] == "declined" for log in logs)

@pytest.mark.asyncio
async def test_degraded_path():
    async with get_client() as client:
        resp = await client.post("/api/v1/encounters", json={"clinician_id": "dr_smith", "patient_ref": "pat_123"})
        enc_id = resp.json()["id"]
        
        with patch("websockets.connect", new_callable=AsyncMock):
            async with aconnect_ws(f"ws://test/api/v1/encounters/{enc_id}/stream", client=client) as ws:
                await ws.send_json({"t": "consent", "value": "granted"})
                await ws.send_json({"t": "audio", "data": "dummy"})
                await ws.send_json({"t": "error", "reason": "ASR crashed"})
                await asyncio.sleep(0.1)
            
        resp = await client.request("POST", f"/api/v1/encounters/{enc_id}/generate")
        assert resp.status_code == 400
        assert "degraded" in resp.json()["detail"]
        
        resp = await client.get(f"/api/v1/encounters/{enc_id}/audit")
        logs = resp.json()
        assert any(log["action"] == "state_change" and log["diff"]["after"]["state"] == "degraded" for log in logs)

@pytest.mark.asyncio
async def test_audit_immutability():
    async with get_client() as client:
        resp = await client.post("/api/v1/encounters", json={"clinician_id": "dr_smith", "patient_ref": "pat_123"})
        enc_id = resp.json()["id"]
        
        resp = await client.get(f"/api/v1/encounters/{enc_id}/audit")
        logs = resp.json()
        assert len(logs) == 1
        assert logs[0]["action"] == "create_encounter"
        assert logs[0]["diff"]["after"]["state"] == "created"
