"""
Shared fixtures for the test suite. Kept intentionally small at this stage
of the build — services/gateway/src/db.py provides the real connection
pool once M1 (contracts & data layer) is implemented; these fixtures wrap
it so tests/security/test_audit_immutable.py can run against the actual
`scribe_app` role rather than a superuser connection.
"""

import os
import uuid

# Ensure a long (>32 bytes) TEST key is active for test sessions if not explicitly set
if not os.environ.get("JWT_SECRET") or len(os.environ.get("JWT_SECRET", "").encode("utf-8")) < 32:
    os.environ["JWT_SECRET"] = "clinical_scribe_test_secret_key_distinct_from_dev_and_prod_environment_length_64_bytes_ok"

import psycopg
import pytest


@pytest.fixture(scope="session", autouse=True)
def guard_test_database():
    """
    Aborts test execution immediately if the database configured in the engine
    does not end with '_test', preventing accidental test pollution in the dev DB.
    """
    db_name = None
    try:
        from src.db import engine
        db_name = engine.url.database
    except ImportError:
        try:
            from services.gateway.src.db import engine
            db_name = engine.url.database
        except ImportError:
            pass

    if not db_name:
        db_name = os.environ.get("POSTGRES_DB", "")

    if not db_name or not str(db_name).endswith("_test"):
        pytest.exit(
            f"Aborting: tests must run against a database ending with _test (got '{db_name}'). Dev database must never be touched by tests.",
            returncode=1,
        )


@pytest.fixture
def pg_conn():
    """Connects as the application role (scribe_app), not a superuser —
    the whole point of test_audit_immutable.py is that this role's
    permissions, not application code, are what prevent tampering."""
    conn = psycopg.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=os.environ.get("POSTGRES_PORT", "5432"),
        dbname=os.environ.get("POSTGRES_DB", "clinical_scribe"),
        user=os.environ.get("POSTGRES_USER", "scribe_app"),
        password=os.environ.get("POSTGRES_PASSWORD", "changeme_in_local_env_only"),
        autocommit=True,
    )
    yield conn
    conn.close()


@pytest.fixture
def sample_encounter_id(pg_conn) -> str:
    encounter_id = str(uuid.uuid4())
    pg_conn.execute("SELECT set_config('app.current_user_id', 'test-clinician', false)")
    pg_conn.execute("SELECT set_config('app.current_role_id', 'clinician', false)")
    pg_conn.execute(
        """
        INSERT INTO encounters
            (id, clinician_id, patient_ref, consent_state, consent_logged_at,
             started_at, state)
        VALUES (%s, %s, %s, 'granted', now(), now(), 'created')
        """,
        (encounter_id, "test-clinician", "patient-ref-test"),
    )
    return encounter_id


@pytest.fixture
def access_token():
    from fastapi.testclient import TestClient
    from src.main import app
    client = TestClient(app)
    res = client.post("/api/v1/auth/login", json={"username": "dr-martinez", "password": "dev_clinician_pass"})
    return res.json()["access_token"], res.cookies.get("csrf_token")
