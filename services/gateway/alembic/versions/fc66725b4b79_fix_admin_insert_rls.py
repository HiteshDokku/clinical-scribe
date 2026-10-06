"""Fix admin insert rls

Revision ID: fc66725b4b79
Revises: fc66725b4b78
Create Date: 2026-10-07 03:04:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fc66725b4b79'
down_revision: Union[str, Sequence[str], None] = 'fc66725b4b78'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the old select-only policy
    op.execute("DROP POLICY IF EXISTS note_versions_admin_auditor_policy ON note_versions;")
    
    # Recreate the select policy
    op.execute("""
    CREATE POLICY note_versions_admin_auditor_select ON note_versions
    AS PERMISSIVE
    FOR SELECT
    TO PUBLIC
    USING (
        current_setting('app.current_role_id', true) IN ('admin', 'auditor')
    );
    """)

    # Create the new insert policy for admins
    op.execute("""
    CREATE POLICY note_versions_admin_insert ON note_versions
    AS PERMISSIVE
    FOR INSERT
    TO PUBLIC
    WITH CHECK (
        current_setting('app.current_role_id', true) = 'admin' 
        AND source = 'admin_correction'
    );
    """)


def downgrade() -> None:
    op.execute("DROP POLICY IF EXISTS note_versions_admin_insert ON note_versions;")
    op.execute("DROP POLICY IF EXISTS note_versions_admin_auditor_select ON note_versions;")
    
    op.execute("""
    CREATE POLICY note_versions_admin_auditor_policy ON note_versions
    AS PERMISSIVE
    FOR SELECT
    TO PUBLIC
    USING (
        current_setting('app.current_role_id', true) IN ('admin', 'auditor')
    );
    """)
