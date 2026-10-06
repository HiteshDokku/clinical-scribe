import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

def get_db_url() -> str:
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "postgres_admin_secret")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "clinical_scribe")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

engine = create_async_engine(get_db_url(), echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

from starlette.requests import HTTPConnection
from sqlalchemy import text

async def get_db(conn: HTTPConnection):
    async with AsyncSessionLocal() as session:
        mock_role = conn.headers.get("X-Mock-Role")
        if mock_role == "admin":
            user_id = "admin123"
            role_id = "admin"
        else:
            user_id = conn.headers.get("X-User-Id", "dr-martinez")
            role_id = conn.headers.get("X-Role-Id", "clinician")
            
        await session.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": user_id})
        await session.execute(text("SELECT set_config('app.current_role_id', :rid, false)"), {"rid": role_id})
        await session.execute(text("SET ROLE scribe_app"))
        yield session
