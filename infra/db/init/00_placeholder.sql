-- ============================================================
-- Bootstrap: runs ONCE as the postgres superuser on first
-- container start via /docker-entrypoint-initdb.d/.
--
-- Responsibility: create the application database and the
-- least-privilege application role (scribe_app).
--
-- IMPORTANT: Alembic migrations must run as 'postgres' (the
-- superuser), NOT as scribe_app.  A table owner is immune to
-- its own REVOKE — so the audit_log immutability test only
-- works if scribe_app is a non-owner role that had UPDATE/DELETE
-- explicitly withheld by the migration.
-- ============================================================

-- Create the application database (the POSTGRES_DB env var creates
-- a DB named after POSTGRES_USER; we want 'clinical_scribe' instead).
SELECT 'CREATE DATABASE clinical_scribe'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'clinical_scribe')\gexec

-- Create the restricted application role.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'scribe_app') THEN
    CREATE ROLE scribe_app WITH LOGIN PASSWORD 'changeme_in_local_env_only';
  END IF;
END $$;

-- Grant connection rights to the app role.
GRANT CONNECT ON DATABASE clinical_scribe TO scribe_app;
GRANT USAGE ON SCHEMA public TO scribe_app;
