import json
import os
import csv

cond_path = "eval/datasets/ddxplus/release_conditions.json"
csv_path = "services/safety/data/diagnosis_risk_tiers.csv"

with open(cond_path, "r", encoding="utf-8") as f:
    conditions = json.load(f)

# Cut-off for MOST severe: severity <= 2 (17 conditions)
# Cut-off for LEAST severe: severity >= 4 (15 conditions)

with open(csv_path, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["condition_name", "severity"])
    for cond_id, data in conditions.items():
        cond_name = data.get("cond-name-eng", data.get("condition_name"))
        severity = data.get("severity")
        writer.writerow([cond_name, severity])
