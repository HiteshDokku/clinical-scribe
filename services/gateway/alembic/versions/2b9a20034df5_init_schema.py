"""init_schema

Revision ID: 2b9a20034df5
Revises:
Create Date: 2026-09-20 18:17:37.651258

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = '2b9a20034df5'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. encounters
    # ------------------------------------------------------------------
    op.create_table(
        'encounters',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('clinician_id', sa.String(), nullable=False),
        sa.Column('patient_ref', sa.String(), nullable=False),
        sa.Column('consent_state', sa.String(), nullable=False),
        sa.Column('consent_logged_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(), nullable=False),
        sa.Column('retention_opt_in', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('degraded_reason', sa.String(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 2. note_versions
    # ------------------------------------------------------------------
    op.create_table(
        'note_versions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('encounter_id', UUID(as_uuid=True),
                  sa.ForeignKey('encounters.id'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(), nullable=False),   # 'ai' | 'clinician'
        sa.Column('content_jsonb', JSONB(), nullable=False),
        sa.Column('model_name', sa.String(), nullable=False),
        sa.Column('model_hash', sa.String(), nullable=False),
        sa.Column('prompt_version', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )

    # ------------------------------------------------------------------
    # 3. audit_log  (append-only; permissions enforced below)
    # ------------------------------------------------------------------
    op.create_table(
        'audit_log',
        sa.Column('id', sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column('encounter_id', UUID(as_uuid=True),
                  sa.ForeignKey('encounters.id'), nullable=False),
        sa.Column('actor', sa.String(), nullable=False),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('field_path', sa.String(), nullable=True),
        sa.Column('before_hash', sa.String(), nullable=True),
        sa.Column('after_hash', sa.String(), nullable=True),
        sa.Column('diff_jsonb', JSONB(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )

    # ------------------------------------------------------------------
    # 4. medications
    #    rxcui is the RxNorm CUI for cross-referencing external datasets.
    #    ingredient_id is NOT present — matching is done via string rxcui.
    # ------------------------------------------------------------------
    op.create_table(
        'medications',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('encounter_id', UUID(as_uuid=True),
                  sa.ForeignKey('encounters.id'), nullable=False),
        sa.Column('note_version_id', UUID(as_uuid=True),
                  sa.ForeignKey('note_versions.id'), nullable=False),
        sa.Column('verbatim', sa.String(), nullable=False),
        sa.Column('rxcui', sa.String(), nullable=True),         # RxNorm CUI; nullable if unresolved
        sa.Column('dose_value', sa.Numeric(), nullable=True),
        sa.Column('dose_unit', sa.String(), nullable=True),
        sa.Column('frequency', sa.String(), nullable=True),
        sa.Column('route', sa.String(), nullable=True),
        sa.Column('flags_jsonb', JSONB(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 5. drug_interactions
    #    ingredient_a / ingredient_b are plain text RxNorm concept names —
    #    no FK, so the table can be seeded from external datasets without
    #    requiring a local dictionary.
    #    source_ref is NOT NULL: an interaction with no citation is invalid.
    # ------------------------------------------------------------------
    op.create_table(
        'drug_interactions',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('ingredient_a', sa.String(), nullable=False),
        sa.Column('ingredient_b', sa.String(), nullable=False),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('source_ref', sa.String(), nullable=False),   # NOT NULL — citation required
        sa.Column('note', sa.Text(), nullable=True),
    )

    # ------------------------------------------------------------------
    # 6. brand_map
    #    ingredient is a plain text RxNorm/local concept name — no FK.
    # ------------------------------------------------------------------
    op.create_table(
        'brand_map',
        sa.Column('id', UUID(as_uuid=True), primary_key=True),
        sa.Column('brand_name', sa.String(), nullable=False),
        sa.Column('ingredient', sa.String(), nullable=False),
        sa.Column('country', sa.String(), nullable=False),
    )

    # ------------------------------------------------------------------
    # 7. Role creation + immutability permissions
    #
    # CRITICAL: this migration MUST be run as the 'postgres' superuser,
    # NOT as scribe_app.  In PostgreSQL a table owner is immune to its
    # own REVOKE — so the audit_log immutability test
    # (test_audit_immutable.py) is only meaningful when scribe_app is a
    # non-owner whose UPDATE/DELETE have been explicitly withheld.
    # ------------------------------------------------------------------
    op.execute("""
    DO $$
    BEGIN
       IF NOT EXISTS (
          SELECT FROM pg_catalog.pg_roles WHERE rolname = 'scribe_app'
       ) THEN
          CREATE ROLE scribe_app WITH LOGIN PASSWORD 'changeme_in_local_env_only';
       END IF;
    END $$;
    """)

    # Grant broad access to all tables except audit_log
    for tbl in ('encounters', 'note_versions', 'medications',
                'drug_interactions', 'brand_map'):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tbl} TO scribe_app;")

    # Allow scribe_app to consume the BIGSERIAL sequence for audit_log.id
    op.execute("GRANT USAGE, SELECT ON SEQUENCE audit_log_id_seq TO scribe_app;")

    # audit_log: INSERT and SELECT ONLY — never UPDATE or DELETE (append-only)
    op.execute("GRANT INSERT, SELECT ON audit_log TO scribe_app;")
    op.execute("REVOKE UPDATE, DELETE ON audit_log FROM scribe_app;")


def downgrade() -> None:
    for tbl in ('audit_log', 'encounters', 'note_versions', 'medications',
                'drug_interactions', 'brand_map'):
        op.execute(f"REVOKE ALL ON {tbl} FROM scribe_app;")
    op.drop_table('brand_map')
    op.drop_table('drug_interactions')
    op.drop_table('medications')
    op.drop_table('audit_log')
    op.drop_table('note_versions')
    op.drop_table('encounters')
