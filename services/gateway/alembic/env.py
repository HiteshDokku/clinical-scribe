from logging.config import fileConfig
import os

from sqlalchemy import pool, create_engine
from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None


def get_url() -> str:
    """
    Build the DSN for the migration connection.

    Migrations MUST run as a superuser so that:
      1. Tables are owned by the superuser, NOT scribe_app.
      2. The subsequent GRANT / REVOKE statements on audit_log are meaningful —
         a table owner is immune to its own REVOKE, so the immutability test
         (test_audit_immutable.py) only passes if scribe_app is a non-owner.

    Provide POSTGRES_SUPERUSER / POSTGRES_SUPERUSER_PASSWORD to override.
    Falls back to POSTGRES_USER / POSTGRES_PASSWORD (still useful for CI
    environments where the single user already has superuser privileges).
    """
    user     = os.environ.get("POSTGRES_SUPERUSER",          os.environ.get("POSTGRES_USER",     "postgres"))
    password = os.environ.get("POSTGRES_SUPERUSER_PASSWORD", os.environ.get("POSTGRES_PASSWORD", "postgres"))
    host     = os.environ.get("POSTGRES_HOST", "localhost")
    port     = os.environ.get("POSTGRES_PORT", "5432")
    db       = os.environ.get("POSTGRES_DB",   "clinical_scribe")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emit SQL to stdout)."""
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (direct DB connection)."""
    connectable = create_engine(get_url(), poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
