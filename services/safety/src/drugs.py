import os
import csv
from rapidfuzz import process, fuzz
import re
from typing import Tuple, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
import csv
from rapidfuzz import process, fuzz
import re

def load_interactions():
    interactions = []
    path = os.path.join(os.path.dirname(__file__), "..", "data", "drug_interactions.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                if row["source_ref"].strip(): # Keep only rows with real source
                    interactions.append({
                        "drug_a": row["drug_a"].lower().strip(),
                        "drug_b": row["drug_b"].lower().strip(),
                        "severity": row["severity"].lower().strip(),
                        "description": row.get("description", ""),
                        "source_ref": row["source_ref"]
                    })
    return interactions

INTERACTIONS = load_interactions()

def load_brands():
    brands = {}
    path = os.environ.get("BRAND_MAP_PATH")
    if not path or not os.path.exists(path):
        # fallback
        path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "eval", "datasets", "drugs", "indian_medicine_brands.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                brand = row.get("brand_name", row.get("brand", "")).lower().strip()
                ingredient = row.get("ingredient_name", row.get("composition", "")).lower().strip()
                if brand and ingredient:
                    brands[brand] = ingredient
    return brands

BRANDS = load_brands()

def load_common_allowlist():
    reviewed = set()
    all_ingredients = set()
    path = os.path.join(os.path.dirname(__file__), "..", "data", "common_medications_allowlist.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                parts = [p.strip() for p in line.split(",")]
                if parts and parts[0]:
                    ing = parts[0].lower()
                    if ing == "ingredient":
                        continue
                    all_ingredients.add(ing)
                    if len(parts) > 1 and parts[1]:
                        reviewed.add(ing)
    return reviewed, all_ingredients

def load_common_medications_allowlist():
    reviewed, _ = load_common_allowlist()
    return reviewed

REVIEWED_COMMON_MEDICATIONS, ALL_ALLOWLIST_INGREDIENTS = load_common_allowlist()

def load_high_risk_classes():
    classes = {}
    path = os.path.join(os.path.dirname(__file__), "..", "data", "high_risk_classes.csv")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                d = row.get("drug_name", "").lower().strip()
                c = row.get("risk_class", "").strip()
                if d:
                    classes[d] = c
    return classes

HIGH_RISK_CLASSES = load_high_risk_classes()

# Build dictionary from allow-list + high_risk_classes + brand_map (NOT from drug_interactions.csv)
GENERIC_DRUGS = set()
for ing in ALL_ALLOWLIST_INGREDIENTS:
    GENERIC_DRUGS.add(ing)
for d in HIGH_RISK_CLASSES.keys():
    GENERIC_DRUGS.add(d)
for b, ing in BRANDS.items():
    for i in re.split(r'[/+]', ing):
        item = i.strip()
        if item:
            GENERIC_DRUGS.add(item)

def load_dictionary():
    return GENERIC_DRUGS


ALIASES = {
    "lisdexamfetamine": "lisdexamefetamine"
}

def resolve_medication(name: str) -> list[str]:
    name = name.lower().strip()
    
    # Check alias first
    if name in ALIASES:
        name = ALIASES[name]
        
    # Strip common dosage info (e.g., '625', '650')
    base_name = re.sub(r'\s+\d+.*$', '', name)
    
    # 1. Exact match on generic
    if base_name in GENERIC_DRUGS:
        return [base_name]
        
    # 2. Brand lookup
    if base_name in BRANDS:
        comp = BRANDS[base_name]
        return [i.strip() for i in re.split(r'[/+]', comp)]
        
    # 3. Fuzzy match (>= 0.90) on generics
    choices = list(GENERIC_DRUGS)
    if choices:
        match = process.extractOne(base_name, choices, scorer=fuzz.WRatio)
        if match and match[1] >= 95.0:
            return [match[0]]
            
    # 4. Fuzzy match on brands
    b_choices = list(BRANDS.keys())
    if b_choices:
        match = process.extractOne(base_name, b_choices, scorer=fuzz.WRatio)
        if match and match[1] >= 95.0:
            comp = BRANDS[match[0]]
            return [i.strip() for i in re.split(r'[/+]', comp)]
            
    # Anything unresolved
    return ["UNRESOLVED:" + name]

def normalize_med_name(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r'\b\d+(\.\d+)?\s*(mg|g|mcg|ml|meq)\b', ' ', name)
    name = re.sub(r'\b(tablet|tablets|capsule|capsules|tab|tabs|cap|caps|oral|po|daily|bid|tid|qid|prn|od|hs|once|twice)\b', ' ', name)
    name = re.sub(r'\b\d+\b', ' ', name)
    name = re.sub(r'\s+', ' ', name).strip()
    return name

def check_interaction(meds: list[str]) -> list[dict]:
    results = []
    # Collect candidate names for each medication mention
    # Interaction detection must not depend on resolution
    med_candidates = []
    for m in meds:
        cands = set()
        norm = normalize_med_name(m)
        if norm:
            cands.add(norm)
        # Also include resolved ingredients if available
        resolved = resolve_medication(m)
        for r in resolved:
            if not r.startswith("UNRESOLVED:"):
                cands.add(r)
        med_candidates.append(list(cands))
        
    for i in range(len(med_candidates)):
        for j in range(i + 1, len(med_candidates)):
            for a in med_candidates[i]:
                for b in med_candidates[j]:
                    for inter in INTERACTIONS:
                        if (a == inter["drug_a"] and b == inter["drug_b"]) or (a == inter["drug_b"] and b == inter["drug_a"]):
                            if inter not in results:
                                results.append(inter)
    return results


def get_high_risk_class(med_name: str) -> str | None:
    norm_name = (med_name or "").lower().strip()
    if norm_name.startswith("insulin"):
        return "insulin"

    ingredients = resolve_medication(med_name)
    if any(i.startswith("UNRESOLVED:") for i in ingredients):
        return "UNKNOWN_MANUAL_CONFIRMATION_REQUIRED"

    for ing in ingredients:
        ing_lower = ing.lower().strip()
        if ing_lower.startswith("insulin"):
            return "insulin"
        if ing_lower in HIGH_RISK_CLASSES:
            return HIGH_RISK_CLASSES[ing_lower]
        choices = list(HIGH_RISK_CLASSES.keys())
        if choices:
            match = process.extractOne(ing_lower, choices, scorer=fuzz.WRatio)
            if match and match[1] >= 95.0:
                return HIGH_RISK_CLASSES[match[0]]
    return None

async def resolve_medication_mention(text_mention: str, session: AsyncSession) -> Tuple[Optional[str], bool]:
    ingredients = resolve_medication(text_mention)
    if not ingredients or any(i.startswith("UNRESOLVED:") for i in ingredients):
        return None, True
    
    ingredient_str = " + ".join(ingredients)

    # A medication is approvable without manual entry only if EVERY resolved
    # ingredient is in common_medications_allowlist.csv with a non-empty reviewed_by.
    all_approved = True
    for ing in ingredients:
        if ing.lower() not in REVIEWED_COMMON_MEDICATIONS:
            all_approved = False
            break

    needs_manual = not all_approved

    hr_class = get_high_risk_class(text_mention)
    if hr_class:
        needs_manual = True

    return ingredient_str, needs_manual


async def check_pair(ingredient_a: str, ingredient_b: str, session: AsyncSession) -> List[dict]:
    # Reuse check_interaction
    interactions = check_interaction([ingredient_a, ingredient_b])
    res = []
    for inter in interactions:
        res.append({
            "severity": inter["severity"],
            "source": inter["source_ref"],
            "source_ref": inter["source_ref"],
            "description": inter["description"]
        })
    return res
