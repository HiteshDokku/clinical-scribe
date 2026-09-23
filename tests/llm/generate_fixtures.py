import json
import os

fixtures = [
    {
        "filename": "01_normal_visit.json",
        "encounter_id": "enc_01",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 2000, "text": "Patient comes in for a routine checkup."},
            {"id": "seg_2", "start_ms": 2000, "end_ms": 4000, "text": "Blood pressure is 120 over 80."},
            {"id": "seg_3", "start_ms": 4000, "end_ms": 6000, "text": "Will continue lisinopril 10mg daily."}
        ]
    },
    {
        "filename": "02_denied_symptom.json",
        "encounter_id": "enc_02",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 2000, "text": "Patient denies any chest pain or shortness of breath."},
            {"id": "seg_2", "start_ms": 2000, "end_ms": 4000, "text": "No headache or dizziness reported."},
            {"id": "seg_3", "start_ms": 4000, "end_ms": 6000, "text": "Plan is to follow up in 6 months."}
        ]
    },
    {
        "filename": "03_ambiguous_dose.json",
        "encounter_id": "enc_03",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 3000, "text": "Patient says they are taking amoxicillin."},
            {"id": "seg_2", "start_ms": 3000, "end_ms": 6000, "text": "They don't remember the dose, just taking one pill twice a day."},
            {"id": "seg_3", "start_ms": 6000, "end_ms": 9000, "text": "Will hold on refilling until we check their records."}
        ]
    },
    {
        "filename": "04_complex_medications.json",
        "encounter_id": "enc_04",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 4000, "text": "Starting metformin 500mg twice daily with meals."},
            {"id": "seg_2", "start_ms": 4000, "end_ms": 8000, "text": "Also adding atorvastatin 20mg at bedtime for hyperlipidemia."},
            {"id": "seg_3", "start_ms": 8000, "end_ms": 12000, "text": "Patient will monitor blood sugar and return in 3 months."}
        ]
    },
    {
        "filename": "05_active_symptoms.json",
        "encounter_id": "enc_05",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 3000, "text": "Chief complaint is severe lower back pain."},
            {"id": "seg_2", "start_ms": 3000, "end_ms": 6000, "text": "Started 3 days ago after lifting heavy boxes."},
            {"id": "seg_3", "start_ms": 6000, "end_ms": 9000, "text": "Radiates down the left leg."}
        ]
    },
    {
        "filename": "06_vitals_only.json",
        "encounter_id": "enc_06",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 2500, "text": "Heart rate is 75 beats per minute."},
            {"id": "seg_2", "start_ms": 2500, "end_ms": 5000, "text": "Temperature 98.6 Fahrenheit, respiratory rate 16."},
            {"id": "seg_3", "start_ms": 5000, "end_ms": 7500, "text": "Weight is 70 kilograms."}
        ]
    },
    {
        "filename": "07_plan_heavy.json",
        "encounter_id": "enc_07",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 3000, "text": "We will order a CBC and CMP today."},
            {"id": "seg_2", "start_ms": 3000, "end_ms": 6000, "text": "Please get a chest X-ray at the imaging center."},
            {"id": "seg_3", "start_ms": 6000, "end_ms": 9000, "text": "Referral to physical therapy for shoulder pain placed."}
        ]
    },
    {
        "filename": "08_multiple_diagnoses.json",
        "encounter_id": "enc_08",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 4000, "text": "Assessment includes type 2 diabetes mellitus, uncomplicated."},
            {"id": "seg_2", "start_ms": 4000, "end_ms": 8000, "text": "Also essential hypertension and mild osteoarthritis."}
        ]
    },
    {
        "filename": "09_mixed_negation.json",
        "encounter_id": "enc_09",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 3000, "text": "Patient has a cough but denies any fever or chills."},
            {"id": "seg_2", "start_ms": 3000, "end_ms": 6000, "text": "Cough is productive of green sputum."}
        ]
    },
    {
        "filename": "10_short_consult.json",
        "encounter_id": "enc_10",
        "_human_reviewed": True,
        "segments": [
            {"id": "seg_1", "start_ms": 0, "end_ms": 2000, "text": "Quick telemedicine checkup."},
            {"id": "seg_2", "start_ms": 2000, "end_ms": 4000, "text": "Rash has completely resolved with hydrocortisone."}
        ]
    }
]

def main():
    os.makedirs(r"c:\Users\hites\Downloads\clinical-scribe-scaffold\clinical-scribe\tests\llm\fixtures", exist_ok=True)
    for fix in fixtures:
        filename = fix.pop("filename")
        path = os.path.join(r"c:\Users\hites\Downloads\clinical-scribe-scaffold\clinical-scribe\tests\llm\fixtures", filename)
        with open(path, "w") as f:
            json.dump(fix, f, indent=2)

if __name__ == "__main__":
    main()
