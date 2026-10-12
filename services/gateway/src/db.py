import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

def get_db_url() -> str:
    user = os.getenv("POSTGRES_USER", "postgres")
    password = os.getenv("POSTGRES_PASSWORD", "")
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "5432")
    db = os.getenv("POSTGRES_DB", "clinical_scribe")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{db}"

engine = create_async_engine(get_db_url(), echo=False)
AsyncSessionLocal = async_sessionmaker(
    bind=engine, class_=AsyncSession, expire_on_commit=False
)

import os
import jwt
from starlette.requests import HTTPConnection, Request
from sqlalchemy import text
from fastapi import HTTPException

def validate_jwt_secret(secret: str | None) -> str:
    if not secret:
        raise RuntimeError("JWT_SECRET environment variable is missing or empty")
    secret_bytes = secret.encode("utf-8")
    if len(secret_bytes) < 32:
        raise RuntimeError(
            f"JWT_SECRET is shorter than 32 bytes ({len(secret_bytes)} bytes provided); refuse to run"
        )
    return secret

JWT_SECRET = validate_jwt_secret(os.getenv("JWT_SECRET"))
JWT_ALGORITHM = "HS256"

def get_identity(conn: HTTPConnection) -> tuple[str, str]:
    token = None
    auth_header = conn.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]
    elif "access_token" in conn.cookies:
        token = conn.cookies["access_token"]
        
    if token:
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            return payload.get("sub", "anonymous"), payload.get("role_id", "anonymous")
        except Exception:
            pass
    return "anonymous", "anonymous"

async def get_db(conn: HTTPConnection):
    async with AsyncSessionLocal() as session:
        user_id, role_id = get_identity(conn)
            
        await session.execute(text("SELECT set_config('app.current_user_id', :uid, false)"), {"uid": user_id})
        await session.execute(text("SELECT set_config('app.current_role_id', :rid, false)"), {"rid": role_id})
        await session.execute(text("SET ROLE scribe_app"))
        yield session

def require_auth(conn: Request):
    user_id, role_id = get_identity(conn)
    if user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Unauthorized")
        
    if conn.method in ["POST", "PATCH", "PUT", "DELETE"]:
        csrf_cookie = conn.cookies.get("csrf_token")
        csrf_header = conn.headers.get("x-csrf-token")
        if not csrf_cookie or not csrf_header or csrf_cookie != csrf_header:
            raise HTTPException(status_code=403, detail="CSRF token missing or mismatch")
            
    return user_id, role_id
