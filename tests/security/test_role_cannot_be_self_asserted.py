import pytest
import os
import jwt
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_client_supplied_role_header_is_ignored_without_valid_jwt():
    # ensure ALLOW_MOCK_ROLE_HEADER is false
    os.environ["ALLOW_MOCK_ROLE_HEADER"] = "false"
    
    payload = {
        "section": "subjective",
        "corrected_text": "This is a test addendum",
        "reason": "Security test"
    }
    
    response = client.post(
        "/api/v1/encounters/123e4567-e89b-12d3-a456-426614174000/addendum",
        json=payload,
        headers={"X-Mock-Role": "admin"}
    )
    
    assert response.status_code == 401
    assert response.json()["detail"] == "Unauthorized"

def test_with_valid_jwt_allows_admin():
    os.environ["ALLOW_MOCK_ROLE_HEADER"] = "false"
    
    token = jwt.encode({"sub": "admin123", "role_id": "admin"}, os.environ["JWT_SECRET"], algorithm="HS256")
    
    payload = {
        "section": "subjective",
        "corrected_text": "This is a test addendum",
        "reason": "Security test"
    }
    
    response = client.post(
        "/api/v1/encounters/123e4567-e89b-12d3-a456-426614174000/addendum",
        json=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "X-CSRF-Token": "valid_csrf_token_12345"
        },
        cookies={"csrf_token": "valid_csrf_token_12345"}
    )
    
    # 404 means auth passed and it hit the DB query which failed to find the encounter
    assert response.status_code == 404
