import pytest
import os
from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)

def test_mutation_without_matching_csrf_header_is_rejected():
    os.environ["ALLOW_MOCK_ROLE_HEADER"] = "false"
    
    import jwt
    token = jwt.encode({"sub": "admin123", "role_id": "admin"}, os.environ["JWT_SECRET"], algorithm="HS256")
    
    # Send a PATCH request to /api/v1/encounters/{id}/note
    # We will provide a valid httpOnly access_token cookie, and a valid csrf_token cookie.
    # But we will NOT provide the X-CSRF-Token header.
    
    payload = {
        "content": {"text": "test"}
    }
    
    response = client.patch(
        "/api/v1/encounters/123e4567-e89b-12d3-a456-426614174000/note",
        json=payload,
        cookies={
            "access_token": token,
            "csrf_token": "valid_csrf_token_12345"
        }
    )
    
    # Should be rejected with 403 CSRF token missing or mismatch
    assert response.status_code == 403
    assert response.json()["detail"] == "CSRF token missing or mismatch"
    
    # Now provide the matching header
    response = client.patch(
        "/api/v1/encounters/123e4567-e89b-12d3-a456-426614174000/note",
        json=payload,
        headers={"X-CSRF-Token": "valid_csrf_token_12345"},
        cookies={
            "access_token": token,
            "csrf_token": "valid_csrf_token_12345"
        }
    )
    
    # Should pass CSRF check and hit 404 (because encounter doesn't exist)
    assert response.status_code == 404
