import os
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

db_name = os.getenv("POSTGRES_DB", "clinical_scribe")
DATABASE_URL = os.getenv("DATABASE_URL", f"postgresql+psycopg://scribe_app:changeme_in_local_env_only@postgres:5432/{db_name}")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
