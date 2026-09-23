from typing import Tuple, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from rapidfuzz import process, fuzz

async def fetch_all_known_names(session: AsyncSession) -> List[Tuple[str, str]]:
    """Fetch all brand names and ingredients from brand_map and drug_interactions to use for fuzzy matching."""
    # We want a set of all valid ingredient strings and brand strings.
    # Since we can't use an ingredient dictionary, we derive known ingredients from brand_map and drug_interactions.
    query = """
    SELECT brand_name as name, ingredient as target_ingredient FROM brand_map
    UNION
    SELECT ingredient as name, ingredient as target_ingredient FROM brand_map
    UNION
    SELECT ingredient_a as name, ingredient_a as target_ingredient FROM drug_interactions
    UNION
    SELECT ingredient_b as name, ingredient_b as target_ingredient FROM drug_interactions
    """
    result = await session.execute(text(query))
    return [(row.name, row.target_ingredient) for row in result]

async def resolve_medication_mention(text_mention: str, session: AsyncSession) -> Tuple[Optional[str], bool]:
    """
    Resolves a text mention to an ingredient.
    Returns (ingredient_string, needs_manual_confirmation).
    """
    text_mention = text_mention.strip().lower()
    
    # 1. Exact match against brand_map (brand_name or ingredient)
    exact_query = """
    SELECT ingredient FROM brand_map WHERE LOWER(brand_name) = :m OR LOWER(ingredient) = :m LIMIT 1
    """
    exact_result = await session.execute(text(exact_query), {"m": text_mention})
    exact = exact_result.scalar()
    if exact:
        return exact, False
        
    # 2. Exact match against drug_interactions (ingredient_a or ingredient_b)
    exact_int_query = """
    SELECT ingredient_a as ingredient FROM drug_interactions WHERE LOWER(ingredient_a) = :m
    UNION
    SELECT ingredient_b as ingredient FROM drug_interactions WHERE LOWER(ingredient_b) = :m
    LIMIT 1
    """
    exact_int_result = await session.execute(text(exact_int_query), {"m": text_mention})
    exact_int = exact_int_result.scalar()
    if exact_int:
        return exact_int, False
        
    # 3. Fuzzy match
    all_names = await fetch_all_known_names(session)
    if not all_names:
        return None, True
        
    choices = [n[0] for n in all_names]
    match = process.extractOne(text_mention, choices, scorer=fuzz.WRatio)
    if not match:
        return None, True
        
    best_name, score, idx = match
    target_ingredient = all_names[idx][1]
    
    if score < 85.0:
        return target_ingredient, True
        
    return target_ingredient, False

async def check_pair(ingredient_a: str, ingredient_b: str, session: AsyncSession) -> List[dict]:
    """
    Deterministic table lookup for interactions between two ingredients.
    """
    query = """
    SELECT severity, source_ref, note 
    FROM drug_interactions 
    WHERE (LOWER(ingredient_a) = LOWER(:a) AND LOWER(ingredient_b) = LOWER(:b))
       OR (LOWER(ingredient_a) = LOWER(:b) AND LOWER(ingredient_b) = LOWER(:a))
    """
    result = await session.execute(text(query), {"a": ingredient_a, "b": ingredient_b})
    interactions = []
    for row in result:
        interactions.append({
            "severity": row.severity,
            "source": row.source_ref,
            "description": row.note
        })
    return interactions
