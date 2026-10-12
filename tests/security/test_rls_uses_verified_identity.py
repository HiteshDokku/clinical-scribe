import pytest
import os
from sqlalchemy import text
from src.db import get_db

class MockConn:
    def __init__(self, headers):
        self.headers = headers
        self.cookies = {}

@pytest.mark.asyncio
async def test_rls_anonymous_blocks_access():
    os.environ["ALLOW_MOCK_ROLE_HEADER"] = "false"
    
    # Simulate an anonymous request with a spoofed header
    conn = MockConn({"X-Mock-Role": "admin"})
    
    # get_db will set app.current_role_id to 'anonymous'
    async for session in get_db(conn):
        # We must explicitly set role to scribe_app as get_db does
        # Attempt to read from note_versions
        result = await session.execute(text("SELECT count(*) FROM note_versions"))
        count = result.scalar()
        
        # RLS should enforce that 'anonymous' cannot see any note_versions
        assert count == 0, "RLS failed to block access for anonymous identity"
