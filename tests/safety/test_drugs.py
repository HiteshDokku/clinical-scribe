import pytest
import pandas as pd
import os
import pytest_asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy import text
from services.safety.src.drugs import resolve_medication_mention, check_pair
from services.gateway.src.models import Base

# Setup in-memory sqlite for testing
engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
TestingSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    # Create tables manually because they might not be in Base.metadata
    async with engine.begin() as conn:
        await conn.execute(text('''
            CREATE TABLE IF NOT EXISTS brand_map (
                id TEXT PRIMARY KEY,
                brand_name TEXT NOT NULL,
                ingredient TEXT NOT NULL,
                country TEXT NOT NULL
            )
        '''))
        await conn.execute(text('''
            CREATE TABLE IF NOT EXISTS drug_interactions (
                id TEXT PRIMARY KEY,
                ingredient_a TEXT NOT NULL,
                ingredient_b TEXT NOT NULL,
                severity TEXT NOT NULL,
                source_ref TEXT NOT NULL,
                note TEXT
            )
        '''))
        
    # Seed with basic test data from CSVs
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    csv_path = os.path.join(fixtures_dir, "adversarial_pairs.csv")
    pairs = pd.read_csv(csv_path)
    
    async with TestingSessionLocal() as session:
        # We need some brands and interactions to match the adversarial pairs
        # Brand map
        await session.execute(text("INSERT INTO brand_map (id, brand_name, ingredient, country) VALUES ('1', 'Atorva', 'Atorvastatin', 'IN')"))
        await session.execute(text("INSERT INTO brand_map (id, brand_name, ingredient, country) VALUES ('2', 'Ecosprin', 'Acetylsalicylic Acid', 'IN')"))
        await session.execute(text("INSERT INTO brand_map (id, brand_name, ingredient, country) VALUES ('3', 'Crocin', 'Paracetamol', 'IN')"))
        await session.execute(text("INSERT INTO brand_map (id, brand_name, ingredient, country) VALUES ('4', 'Pan', 'Pantoprazole', 'IN')"))
        await session.execute(text("INSERT INTO brand_map (id, brand_name, ingredient, country) VALUES ('5', 'Lipitor', 'Atorvastatin', 'IN')"))
        
        # Interactions
        await session.execute(text("INSERT INTO drug_interactions (id, ingredient_a, ingredient_b, severity, source_ref) VALUES ('1', 'Atorvastatin', 'Amiodarone', 'Major', 'DDInter')"))
        await session.execute(text("INSERT INTO drug_interactions (id, ingredient_a, ingredient_b, severity, source_ref) VALUES ('2', 'Warfarin', 'Acetylsalicylic Acid', 'Major', 'DDInter')"))
        await session.execute(text("INSERT INTO drug_interactions (id, ingredient_a, ingredient_b, severity, source_ref) VALUES ('3', 'Paracetamol', 'Warfarin', 'Moderate', 'DDInter')"))
        await session.execute(text("INSERT INTO drug_interactions (id, ingredient_a, ingredient_b, severity, source_ref) VALUES ('4', 'Pantoprazole', 'Clopidogrel', 'Moderate', 'DDInter')"))
        await session.commit()
    
    yield
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.mark.asyncio
async def test_adversarial_pairs():
    fixtures_dir = os.path.join(os.path.dirname(__file__), "fixtures")
    csv_path = os.path.join(fixtures_dir, "adversarial_pairs.csv")
    pairs = pd.read_csv(csv_path)
    
    async with TestingSessionLocal() as session:
        for _, row in pairs.iterrows():
            a = row['input_a']
            b = row['input_b']
            expected_sev = row['expected_severity']
            
            # Resolve A
            ing_a, conf_a = await resolve_medication_mention(a, session)
            if a == 'UnknownHerb':
                assert conf_a is True
                continue
            
            # Resolve B
            ing_b, conf_b = await resolve_medication_mention(b, session)
            
            # Check pair
            interactions = await check_pair(ing_a, ing_b, session)
            
            if expected_sev == 'Unknown':
                assert len(interactions) == 0
            else:
                assert len(interactions) > 0
                assert interactions[0]['severity'] == expected_sev
