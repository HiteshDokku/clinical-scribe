import os
import csv
from scripts.load_onc_interactions import load_onc_interactions

def test_load_interactions_idempotent():
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    out_csv = os.path.join(base_dir, 'services', 'safety', 'data', 'drug_interactions.csv')
    
    # Run once
    load_onc_interactions()
    with open(out_csv, 'r', encoding='utf-8') as f:
        rows_1 = list(csv.reader(f))
        
    # Run twice
    load_onc_interactions()
    with open(out_csv, 'r', encoding='utf-8') as f:
        rows_2 = list(csv.reader(f))
        
    assert len(rows_1) == len(rows_2), f"Expected row counts to match, but got {len(rows_1)} and {len(rows_2)}"
    assert len(rows_1) > 1, "Expected more than just header"
    print("Idempotency test passed!")
