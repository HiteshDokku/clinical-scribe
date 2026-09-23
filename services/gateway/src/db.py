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

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
