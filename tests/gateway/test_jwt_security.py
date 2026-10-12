"""Tests for JWT secret validation and cryptographic integrity.
Label: [real-service]
"""
import pytest
import os
import jwt
import json
import base64
from fastapi.testclient import TestClient

from src.main import app, validate_jwt_secret
from src.db import JWT_SECRET, JWT_ALGORITHM

client = TestClient(app)


def test_startup_with_short_key_fails():
    """Refuse to run if key is missing or shorter than 32 bytes."""
    # 1. Missing / None
    with pytest.raises(RuntimeError, match="missing or empty"):
        validate_jwt_secret(None)

    # 2. Empty string
    with pytest.raises(RuntimeError, match="missing or empty"):
        validate_jwt_secret("")

    # 3. Short key (e.g. previous hardcoded 'supersecret' of 11 bytes)
    with pytest.raises(RuntimeError, match="shorter than 32 bytes"):
        validate_jwt_secret("supersecret")

    # 4. Exactly 31 bytes
    with pytest.raises(RuntimeError, match="shorter than 32 bytes"):
        validate_jwt_secret("x" * 31)

    # 5. Exactly 32 bytes (must pass)
    valid_32 = "a" * 32
    assert validate_jwt_secret(valid_32) == valid_32

    # 6. Long key (64 bytes, token_urlsafe)
    long_key = "k" * 64
    assert validate_jwt_secret(long_key) == long_key


def test_token_signed_with_another_key_is_rejected():
    """A token signed with another key must be rejected with 401 Unauthorized."""
    different_secret = "different_secret_key_at_least_32_bytes_long_which_does_not_match!"
    assert different_secret != JWT_SECRET

    rogue_token = jwt.encode(
        {"sub": "attacker", "role_id": "admin"},
        different_secret,
        algorithm=JWT_ALGORITHM
    )

    headers = {"Authorization": f"Bearer {rogue_token}", "X-CSRF-Token": "csrf123"}
    cookies = {"csrf_token": "csrf123"}

    res = client.get("/api/v1/encounters", headers=headers, cookies=cookies)
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert res.json()["detail"] == "Unauthorized"


def test_alg_none_token_is_rejected():
    """A token with alg=none must be rejected with 401 Unauthorized."""
    # Manually craft an alg=none unverified JWT token
    header_bytes = base64.urlsafe_b64encode(json.dumps({"alg": "none", "typ": "JWT"}).encode()).rstrip(b'=')
    payload_bytes = base64.urlsafe_b64encode(json.dumps({"sub": "attacker", "role_id": "admin"}).encode()).rstrip(b'=')
    none_token = f"{header_bytes.decode()}.{payload_bytes.decode()}."

    headers = {"Authorization": f"Bearer {none_token}", "X-CSRF-Token": "csrf123"}
    cookies = {"csrf_token": "csrf123"}

    res = client.get("/api/v1/encounters", headers=headers, cookies=cookies)
    assert res.status_code == 401, f"Expected 401, got {res.status_code}: {res.text}"
    assert res.json()["detail"] == "Unauthorized"
