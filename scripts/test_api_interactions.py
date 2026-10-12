import httpx
import uuid
import json
import jwt
import psycopg

base_url = "http://localhost:8000"
client = httpx.Client(base_url=base_url)

# 1. Login
res = client.post("/api/v1/auth/login", json={"username": "dr-martinez", "password": "dev_clinician_pass"})
if res.status_code != 200:
    print("Login failed!", res.status_code, res.text)
    exit(1)
token = res.json()["access_token"]
csrf = res.cookies.get("csrf_token")
headers = {"Authorization": f"Bearer {token}", "X-CSRF-Token": csrf}
cookies = {"csrf_token": csrf}

# Decode JWT for clinician_id
payload = jwt.decode(token, options={"verify_signature": False})
clinician_id = payload.get("sub")

conn = psycopg.connect("postgresql://scribe_app:changeme_in_local_env_only@postgres:5432/clinical_scribe")
cursor = conn.cursor()

# 2. Create Encounter via API
res_enc = client.post("/api/v1/encounters", json={
    "clinician_id": clinician_id,
    "patient_ref": "test_patient"
}, headers=headers, cookies=cookies)
if res_enc.status_code != 200:
    print("Encounter creation failed!", res_enc.status_code, res_enc.text)
    exit(1)
enc_id = res_enc.json()["id"]

# Set user id for Row Level Security
cursor.execute("SELECT set_config('app.current_user_id', %s, false)", (clinician_id,))

# 3. Add interacting pair via DB
stmt_id = str(uuid.uuid4())
cursor.execute("INSERT INTO statements (id, encounter_id, text, statement_type, risk_tier) VALUES (%s, %s, 'dexmethylphenidate and tranylcypromine', 'medication_prescribed', 'red_flag')", (stmt_id, enc_id))
conn.commit()

stmt_res = client.get(f"/api/v1/encounters/{enc_id}", headers=headers)
enc = stmt_res.json()
stmt = next(s for s in enc["statements"] if s["id"] == stmt_id)
print("\nINTERACTING PAIR STATEMENT:")
print(json.dumps(stmt, indent=2))
assert stmt["risk_tier"] == "red_flag"

# Show it blocks /sign
req_body_sign = {"edits": {}, "statement_determinations": {}}
res_sign = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body_sign, headers=headers, cookies=cookies)
print("\nSIGN BLOCKED RESPONSE:")
print(f"Status Code: {res_sign.status_code}")
print(json.dumps(res_sign.json(), indent=2))
assert res_sign.status_code == 400

# 4. Safe pair via DB
stmt_id2 = str(uuid.uuid4())
cursor.execute("INSERT INTO statements (id, encounter_id, text, statement_type, risk_tier) VALUES (%s, %s, 'ibuprofen and paracetamol', 'medication_prescribed', 'benign')", (stmt_id2, enc_id))
conn.commit()

stmt_res2 = client.get(f"/api/v1/encounters/{enc_id}", headers=headers)
enc2 = stmt_res2.json()
stmt2 = next(s for s in enc2["statements"] if s["id"] == stmt_id2)
print("\nSAFE PAIR STATEMENT:")
print(json.dumps(stmt2, indent=2))
assert stmt2["risk_tier"] == "benign"

# 5. Reclassification test from Part 5
stmt_id3 = str(uuid.uuid4())
cursor.execute("INSERT INTO statements (id, encounter_id, text, statement_type, risk_tier) VALUES (%s, %s, 'Hypertension', 'inferred_diagnosis', 'benign')", (stmt_id3, enc_id))
conn.commit()

req_body_sign2 = {"edits": {}, "statement_determinations": {stmt_id3: "Malignant Hypertension"}}
res_sign2 = client.post(f"/api/v1/encounters/{enc_id}/sign", json=req_body_sign2, headers=headers, cookies=cookies)
print("\nRECLASSIFICATION SIGN BLOCKED RESPONSE:")
print(f"Status Code: {res_sign2.status_code}")
print(json.dumps(res_sign2.json(), indent=2))
assert res_sign2.status_code == 400
