"""seed users

Revision ID: a1b2c3d4e5f6
Revises: fc66725b4b79
Create Date: 2026-10-08 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID
import os
import logging
import bcrypt
import uuid

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'fc66725b4b79'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    
    if not inspector.has_table('roles'):
        op.create_table(
            'roles',
            sa.Column('id', sa.String(), primary_key=True),
            sa.Column('name', sa.String(), nullable=False)
        )
        
    if not inspector.has_table('users'):
        op.create_table(
            'users',
            sa.Column('id', UUID(as_uuid=True), primary_key=True),
            sa.Column('username', sa.String(), nullable=False, unique=True),
            sa.Column('password_hash', sa.String(), nullable=False),
            sa.Column('role_id', sa.String(), sa.ForeignKey('roles.id'), nullable=False)
        )
    else:
        # Table exists, check if password_hash column exists
        columns = [c['name'] for c in inspector.get_columns('users')]
        if 'password_hash' not in columns:
            op.add_column('users', sa.Column('password_hash', sa.String(), nullable=True))
            # If there are existing users, we need to set a default before making it non-nullable
            # but since this is dev, we can just set a dummy hash for existing rows
            dummy_hash = bcrypt.hashpw(b'dummy', bcrypt.gensalt()).decode('utf-8')
            op.execute(f"UPDATE users SET password_hash = '{dummy_hash}' WHERE password_hash IS NULL")
            op.alter_column('users', 'password_hash', nullable=False)
            
    # Grant permissions so app can query
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON roles TO scribe_app;")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON users TO scribe_app;")

    # Seed Roles
    op.execute("""
        INSERT INTO roles (id, name)
        SELECT 'clinician', 'Clinician'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 'clinician');
    """)
    op.execute("""
        INSERT INTO roles (id, name)
        SELECT 'admin', 'Administrator'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 'admin');
    """)
    op.execute("""
        INSERT INTO roles (id, name)
        SELECT 'auditor', 'Auditor'
        WHERE NOT EXISTS (SELECT 1 FROM roles WHERE id = 'auditor');
    """)
    
    # Seed Users
    clinician_pass = os.environ.get('SEED_CLINICIAN_PASSWORD', 'dev_clinician_pass')
    admin_pass = os.environ.get('SEED_ADMIN_PASSWORD', 'dev_admin_pass')
    
    if clinician_pass == 'dev_clinician_pass' or admin_pass == 'dev_admin_pass':
        print("WARNING: Seeding users with default local dev passwords. Do not use in production!")
        
    clinician_hash = bcrypt.hashpw(clinician_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    admin_hash = bcrypt.hashpw(admin_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    auditor_hash = bcrypt.hashpw(admin_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    # We use explicit UUIDs to ensure reproducible rows if needed, or just random
    clinician_id = str(uuid.uuid4())
    admin_id = str(uuid.uuid4())
    auditor_id = str(uuid.uuid4())
    
    op.execute(sa.text("""
        INSERT INTO users (id, username, password_hash, role_id)
        SELECT CAST(:cid AS UUID), 'dr-martinez', :chash, 'clinician'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'dr-martinez');
    """).bindparams(cid=clinician_id, chash=clinician_hash))
    
    op.execute(sa.text("""
        INSERT INTO users (id, username, password_hash, role_id)
        SELECT CAST(:aid AS UUID), 'admin', :ahash, 'admin'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin');
    """).bindparams(aid=admin_id, ahash=admin_hash))
    
    op.execute(sa.text("""
        INSERT INTO users (id, username, password_hash, role_id)
        SELECT CAST(:aud AS UUID), 'auditor', :audhash, 'auditor'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'auditor');
    """).bindparams(aud=auditor_id, audhash=auditor_hash))

    # And seed a second clinician to test RLS!
    clinician2_id = str(uuid.uuid4())
    clinician2_hash = bcrypt.hashpw(clinician_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    op.execute(sa.text("""
        INSERT INTO users (id, username, password_hash, role_id)
        SELECT CAST(:cid2 AS UUID), 'dr-jones', :chash2, 'clinician'
        WHERE NOT EXISTS (SELECT 1 FROM users WHERE username = 'dr-jones');
    """).bindparams(cid2=clinician2_id, chash2=clinician2_hash))


def downgrade() -> None:
    pass
