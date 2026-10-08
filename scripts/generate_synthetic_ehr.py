#!/usr/bin/env python3
"""
Synthetic EHR Data Generator for MedTwin AI
Generates clinically plausible, reproducible EHR records for Type 2 Diabetes patients.
Aligned with Synthea-style distributions for adult metabolic health cohorts.
"""

import json
import random
from pathlib import Path

# Paths
OUTPUT_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic" / "ehr"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

FIRST_NAMES = [
    "Rajesh", "Sunita", "Amit", "Priya", "Vikram", "Ananya", "Ramesh", "Kavita",
    "Suresh", "Meera", "Deepak", "Shalini", "Arun", "Pooja", "Manoj", "Sneha",
    "Kishore", "Divya", "Sanjay", "Ritu", "Mohan", "Asha", "Girish", "Swati",
]
LAST_NAMES = [
    "Kumar", "Sharma", "Patel", "Desai", "Verma", "Rao", "Nair", "Iyer",
    "Gupta", "Joshi", "Menon", "Reddy", "Singh", "Bose", "Kulkarni", "Hegde",
]

COMORBIDITY_POOL = [
    "Essential Hypertension",
    "Dyslipidemia",
    "Metabolic Syndrome",
    "Mild Diabetic Neuropathy",
    "Grade 1 Fatty Liver (NAFLD)",
    "Hypothyroidism",
]

MEDICATION_REGIMENS = [
    [
        {"drug_name": "Metformin", "strength": "500 mg", "frequency": "1-0-1", "meal": "after food", "verified": True},
    ],
    [
        {"drug_name": "Metformin", "strength": "850 mg", "frequency": "1-0-1", "meal": "after food", "verified": True},
        {"drug_name": "Glimepiride", "strength": "1 mg", "frequency": "1-0-0", "meal": "before breakfast", "verified": True},
    ],
    [
        {"drug_name": "Metformin", "strength": "500 mg", "frequency": "1-0-1", "meal": "after food", "verified": True},
        {"drug_name": "Telmisartan", "strength": "40 mg", "frequency": "0-1-0", "meal": "after food", "verified": True},
        {"drug_name": "Atorvastatin", "strength": "10 mg", "frequency": "0-0-1", "meal": "at bedtime", "verified": True},
    ],
    [
        {"drug_name": "Sitagliptin", "strength": "100 mg", "frequency": "1-0-0", "meal": "with breakfast", "verified": True},
        {"drug_name": "Metformin", "strength": "1000 mg", "frequency": "1-0-1", "meal": "after food", "verified": True},
    ],
    [
        {"drug_name": "Dapagliflozin", "strength": "10 mg", "frequency": "1-0-0", "meal": "morning", "verified": True},
        {"drug_name": "Metformin", "strength": "500 mg", "frequency": "1-0-1", "meal": "after food", "verified": True},
    ],
]


def generate_patient_ehr(patient_idx: int, rng: random.Random) -> dict:
    """Generate a single clinically consistent synthetic EHR record."""
    patient_id = f"PT-{100 + patient_idx:03d}"
    first_name = rng.choice(FIRST_NAMES)
    last_name = rng.choice(LAST_NAMES)
    sex = rng.choice(["Male", "Female"])
    age = rng.randint(40, 72)
    bmi = round(rng.uniform(22.8, 34.5), 1)
    diabetes_duration = round(rng.uniform(1.5, 16.0), 1)

    # Correlate baseline HbA1c and glucose with duration and BMI
    base_hba1c = 6.2 + (diabetes_duration * 0.12) + ((bmi - 24.0) * 0.08) + rng.uniform(-0.5, 0.7)
    hba1c = round(max(5.8, min(11.2, base_hba1c)), 1)

    fasting_glucose = round(85 + (hba1c - 5.5) * 22 + rng.uniform(-10, 15), 1)
    baseline_glucose = round(fasting_glucose + rng.uniform(8, 22), 1)
    baseline_hr = round(rng.uniform(64, 82), 1)
    baseline_hrv = round(max(24.0, 68.0 - (age * 0.35) - ((bmi - 24) * 0.6) + rng.uniform(-5, 6)), 1)
    baseline_sleep_hours = round(rng.uniform(6.2, 7.8), 1)
    baseline_steps = int(rng.uniform(4500, 10500))

    has_hypertension = rng.random() < 0.62
    num_comorbidities = rng.randint(0, 3)
    comorbidities = rng.sample(COMORBIDITY_POOL, min(num_comorbidities, len(COMORBIDITY_POOL)))
    if has_hypertension and "Essential Hypertension" not in comorbidities:
        comorbidities.append("Essential Hypertension")

    meds = rng.choice(MEDICATION_REGIMENS)
    allergies = ["None"] if rng.random() > 0.15 else [rng.choice(["Penicillin", "Sulfa drugs", "Aspirin"])]

    return {
        "patient_id": patient_id,
        "name": f"{first_name} {last_name}",
        "age": age,
        "sex": sex,
        "bmi": bmi,
        "diabetes_duration_years": diabetes_duration,
        "hba1c": hba1c,
        "fasting_glucose": fasting_glucose,
        "baseline_glucose": baseline_glucose,
        "baseline_hr": baseline_hr,
        "baseline_hrv": baseline_hrv,
        "baseline_sleep_hours": baseline_sleep_hours,
        "baseline_steps": baseline_steps,
        "has_hypertension": has_hypertension,
        "comorbidities": comorbidities,
        "allergies": allergies,
        "medication_regimen": meds,
        "data_source": "Synthea-calibrated metabolic cohort generator",
        "synthetic": True,
    }


def main(n_patients: int = 100, seed: int = 42) -> None:
    rng = random.Random(seed)
    patients = [generate_patient_ehr(i, rng) for i in range(1, n_patients + 1)]

    json_path = OUTPUT_DIR / "patients_ehr.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(patients, f, indent=2)

    print(f"Generated {len(patients)} synthetic EHR records -> {json_path}")


if __name__ == "__main__":
    main()
