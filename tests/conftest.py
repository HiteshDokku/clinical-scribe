"""
Shared fixtures for the test suite. Kept intentionally small at this stage
of the build — services/gateway/src/db.py provides the real connection
pool once M1 (contracts & data layer) is implemented; these fixtures wrap
it so tests/security/test_audit_immutable.py can run against the actual
`scribe_app` role rather than a superuser connection.
"""

import os
import uuid

import psycopg
import pytest


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
