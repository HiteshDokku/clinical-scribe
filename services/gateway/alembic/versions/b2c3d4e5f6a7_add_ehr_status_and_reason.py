"""Add ehr_status to encounters and reason to note_versions

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-10-11 16:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE encounters ADD COLUMN IF NOT EXISTS ehr_status VARCHAR NOT NULL DEFAULT 'pending';")
    op.execute("ALTER TABLE note_versions ADD COLUMN IF NOT EXISTS reason VARCHAR;")


def downgrade() -> None:
    op.execute("ALTER TABLE encounters DROP COLUMN IF EXISTS ehr_status;")
    op.execute("ALTER TABLE note_versions DROP COLUMN IF EXISTS reason;")
