"""
Enforces that audit_log is append-only at the database permission level,
not merely by application-code convention. Requires a `pg_conn` fixture
(see conftest.py) connected as the application role `scribe_app`, not a
superuser — that distinction is the entire point of this test.
"""

import psycopg
import pytest


def test_app_role_cannot_update_audit_log(pg_conn):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        pg_conn.execute("UPDATE audit_log SET action = 'tampered' WHERE id = 1")


def test_app_role_cannot_delete_audit_log(pg_conn):
    with pytest.raises(psycopg.errors.InsufficientPrivilege):
        pg_conn.execute("DELETE FROM audit_log WHERE id = 1")


def test_app_role_can_still_insert_and_select(pg_conn, sample_encounter_id):
    # Sanity check: the restriction is UPDATE/DELETE only, not a broken role.
    pg_conn.execute(
        "INSERT INTO audit_log (encounter_id, actor, action, field_path, diff_jsonb) "
        "VALUES (%s, 'test-suite', 'test.inserted', 'n/a', '{}')",
        (sample_encounter_id,),
    )
    rows = pg_conn.execute(
        "SELECT action FROM audit_log WHERE encounter_id = %s", (sample_encounter_id,)
    ).fetchall()
    assert any(r[0] == "test.inserted" for r in rows)
