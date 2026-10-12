import os
import csv

def load_onc_interactions():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    onc_file = os.path.join(base_dir, 'eval', 'datasets', 'drugs', 'public-PDDI-analysis', 'PDDI-Datasets', 'ONC-High-Priority', 'ONC_High_Priority_Mapped.csv')
    
    unique_pairs = set()
    out_rows = []
    
    raw_lines = 0
    skipped_lines = 0
    
    with open(onc_file, 'r', encoding='utf-8-sig') as f:
        for idx, line in enumerate(f):
            raw_lines += 1
            parts = line.strip().split('$')
            if len(parts) >= 3 and parts[0] and parts[2]:
                drug_a = parts[0].strip().lower()
                drug_b = parts[2].strip().lower()
                
                pair = tuple(sorted([drug_a, drug_b]))
                if pair not in unique_pairs:
                    unique_pairs.add(pair)
                    out_rows.append({
                        'id': f"ONC-MAPPED:{idx+1}",
                        'drug_a': drug_a,
                        'drug_b': drug_b,
                        'severity': 'high',
                        'source_ref': f"ONC_High_Priority_Mapped.csv:{idx+1}"
                    })
                else:
                    skipped_lines += 1
            else:
                skipped_lines += 1
                
    out_csv = os.path.join(base_dir, 'services', 'safety', 'data', 'drug_interactions.csv')
    
    fieldnames = ['id', 'drug_a', 'drug_b', 'severity', 'source_ref']
        
    with open(out_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)
        
    print(f"Raw lines: {raw_lines}")
    print(f"Skipped/Malformed/Duplicate lines: {skipped_lines}")
    print(f"Unique pairs: {len(unique_pairs)}")
    print(f"Written rows: {len(out_rows)}")
    
if __name__ == '__main__':
    load_onc_interactions()
