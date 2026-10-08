#!/usr/bin/env python3
"""
Wearable / IoT Dynamic Physiological Stream Generator for MedTwin AI
Generates realistic multi-signal continuous time-series (Glucose, HR, HRV, Sleep, Activity, SpO2, BP)
covering 6 distinct clinical scenarios with reproducible seeds.
"""

import json
import math
import random
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"
WEARABLE_DIR = DATA_DIR / "wearable"
SCENARIO_DIR = DATA_DIR / "scenarios"
WEARABLE_DIR.mkdir(parents=True, exist_ok=True)
SCENARIO_DIR.mkdir(parents=True, exist_ok=True)


def generate_time_series(
    patient_ehr: dict,
    scenario_type: str = "A",
    duration_hours: int = 12,
    interval_minutes: int = 5,
    start_time: datetime | None = None,
    seed: int = 42,
) -> list[dict]:
    """Generate realistic 5-minute interval physiological observations for a given clinical scenario."""
    rng = random.Random(seed)
    if start_time is None:
        start_time = datetime(2026, 10, 8, 8, 0, 0)

    base_glucose = patient_ehr.get("baseline_glucose", 125.0)
    base_hr = patient_ehr.get("baseline_hr", 72.0)
    base_hrv = patient_ehr.get("baseline_hrv", 48.0)
    base_sleep = patient_ehr.get("baseline_sleep_hours", 7.0)

    total_steps = int(duration_hours * 60 / interval_minutes)
    records = []

    # Scenario parameters
    # A: Stable patient
    # B: Poor sleep -> reduced activity -> physiological deviation
    # C: Post-meal glucose rise
    # D: High glucose-risk episode
    # E: Sensor degradation / missing values
    # F: Medication adherence variation

    cur_glucose = base_glucose
    cur_hr = base_hr
    cur_hrv = base_hrv
    cum_steps = 0
    sleep_hours = base_sleep
    sleep_quality = 85.0

    if scenario_type == "B":
        sleep_hours = 3.8
        sleep_quality = 41.0
        cur_hr += 10.0
        cur_hrv -= 16.0
        cur_glucose += 12.0
    elif scenario_type == "D":
        cur_glucose += 25.0
        cur_hr += 14.0
        cur_hrv -= 18.0

    for step in range(total_steps):
        t = start_time + timedelta(minutes=step * interval_minutes)
        hour_fraction = t.hour + (t.minute / 60.0)

        # Baseline circadian oscillations
        circadian_hr = 4.0 * math.sin(2 * math.pi * (hour_fraction - 6) / 24)
        circadian_glucose = 8.0 * math.sin(2 * math.pi * (hour_fraction - 8) / 24)

        # Activity level
        if 8.5 <= hour_fraction <= 9.5 or 17.0 <= hour_fraction <= 18.0:
            activity_intensity = rng.uniform(45.0, 75.0)  # Walking / commute
            step_delta = rng.randint(80, 220)
        elif 13.0 <= hour_fraction <= 14.0:
            activity_intensity = rng.uniform(15.0, 35.0)
            step_delta = rng.randint(20, 60)
        else:
            activity_intensity = rng.uniform(5.0, 25.0)  # Sedentary/desk
            step_delta = rng.randint(0, 30)

        if scenario_type == "B":
            activity_intensity *= 0.4
            step_delta = int(step_delta * 0.4)

        cum_steps += step_delta

        # Scenario dynamic drift
        if scenario_type == "A":
            # Stable: small noise around base
            cur_glucose = base_glucose + circadian_glucose + rng.gauss(0, 3.5)
            cur_hr = base_hr + circadian_hr + (activity_intensity * 0.15) + rng.gauss(0, 2.0)
            cur_hrv = base_hrv - (activity_intensity * 0.12) + rng.gauss(0, 2.5)

        elif scenario_type == "B":
            # Poor sleep: sluggish activity, elevated HR, slow upward glucose creep
            cur_glucose += 0.4 + rng.gauss(0, 2.0)
            cur_hr = (base_hr + 12.0) + circadian_hr + rng.gauss(0, 2.2)
            cur_hrv = max(18.0, base_hrv - 15.0 + rng.gauss(0, 2.0))

        elif scenario_type == "C":
            # Post-meal spike starting at 10:30 (step ~30)
            if step < 25:
                cur_glucose = base_glucose + rng.gauss(0, 3.0)
            elif 25 <= step < 45:
                # Rapid rise post heavy lunch
                cur_glucose += rng.uniform(3.5, 6.0)
                cur_hr += rng.uniform(0.5, 1.2)
            else:
                # Peak and slow plateau
                cur_glucose = max(160.0, cur_glucose - rng.uniform(0.5, 1.5))
            cur_hr = base_hr + (cur_glucose - base_glucose) * 0.12 + rng.gauss(0, 2.0)
            cur_hrv = max(20.0, base_hrv - (cur_glucose - base_glucose) * 0.18 + rng.gauss(0, 2.0))

        elif scenario_type == "D":
            # Severe adverse event: continuous rapid escalation
            cur_glucose += rng.uniform(1.8, 3.8)
            cur_hr = min(120.0, cur_hr + rng.uniform(0.2, 0.7))
            cur_hrv = max(15.0, cur_hrv - rng.uniform(0.2, 0.6))

        elif scenario_type == "E":
            # Sensor degradation: normal baseline but intermittent packet loss
            cur_glucose = base_glucose + circadian_glucose + rng.gauss(0, 3.0)
            cur_hr = base_hr + circadian_hr + rng.gauss(0, 2.0)
            cur_hrv = base_hrv + rng.gauss(0, 2.5)

        elif scenario_type == "F":
            # Medication adherence variation: morning dose skipped -> uncurbed gradual glucose climb
            if step < 20:
                cur_glucose = base_glucose + rng.gauss(0, 2.5)
            else:
                # Missed dose impact accumulating
                cur_glucose += rng.uniform(0.8, 2.0)
            cur_hr = base_hr + rng.gauss(0, 2.5)
            cur_hrv = max(22.0, base_hrv - 6.0 + rng.gauss(0, 2.0))

        # Clamp vitals to physiological limits
        clamped_glucose = round(max(65.0, min(380.0, cur_glucose)), 1)
        clamped_hr = round(max(48.0, min(145.0, cur_hr)), 1)
        clamped_hrv = round(max(12.0, min(95.0, cur_hrv)), 1)
        spo2 = round(max(92.0, min(100.0, 98.2 - (0.01 * (clamped_hr - 70)) + rng.gauss(0, 0.4))), 1)
        systolic_bp = round(118.0 + (clamped_hr - 70) * 0.35 + rng.gauss(0, 2.0), 1)
        diastolic_bp = round(76.0 + (clamped_hr - 70) * 0.2 + rng.gauss(0, 1.5), 1)

        record = {
            "patient_id": patient_ehr.get("patient_id", "PT-101"),
            "timestamp": t.isoformat(),
            "glucose": clamped_glucose,
            "heart_rate": clamped_hr,
            "hrv": clamped_hrv,
            "sleep_duration_hours": round(sleep_hours, 1),
            "sleep_quality_score": round(sleep_quality, 1),
            "steps_interval": step_delta,
            "steps_cumulative": cum_steps,
            "activity_intensity": round(activity_intensity, 1),
            "spo2": spo2,
            "blood_pressure_systolic": systolic_bp,
            "blood_pressure_diastolic": diastolic_bp,
            "scenario": scenario_type,
            "sensor_status": "NORMAL",
        }

        # If Scenario E: inject realistic sensor dropouts/missing packets
        if scenario_type == "E" and (15 <= step <= 25 or 50 <= step <= 56):
            record["glucose"] = None if step % 2 == 0 else record["glucose"]
            record["hrv"] = None
            record["activity_intensity"] = None
            record["sensor_status"] = "DEGRADED_PACKET_LOSS"

        records.append(record)

    return records


def generate_all_scenarios(patient_ehr: dict) -> dict[str, list[dict]]:
    """Generate all 6 standard benchmark scenarios for a patient."""
    scenarios = {
        "A_stable": ("A", 42, "Scenario A: Stable metabolic state with high medication adherence"),
        "B_sleep_deficit": ("B", 43, "Scenario B: Severe sleep deficit, reduced physical activity & autonomic drift"),
        "C_postprandial_rise": ("C", 44, "Scenario C: Postprandial high-glycemic excursion requiring proactive decision support"),
        "D_hyperglycemic_spike": ("D", 45, "Scenario D: Compounding adverse metabolic risk event (>180 mg/dL forecasted within 2h)"),
        "E_sensor_dropout": ("E", 46, "Scenario E: Wearable sensor packet degradation & missing physiological streams"),
        "F_adherence_lapse": ("F", 47, "Scenario F: Medication schedule adherence lapse triggering unbuffered glucose drift"),
    }

    results = {}
    for key, (sc_type, seed, desc) in scenarios.items():
        stream = generate_time_series(patient_ehr, scenario_type=sc_type, duration_hours=12, seed=seed)
        results[key] = {
            "scenario_key": key,
            "scenario_type": sc_type,
            "description": desc,
            "patient_id": patient_ehr["patient_id"],
            "stream": stream,
        }
    return results


def main() -> None:
    ehr_path = DATA_DIR / "ehr" / "patients_ehr.json"
    if not ehr_path.exists():
        print("EHR dataset not found. Generating EHR dataset first...")
        from generate_synthetic_ehr import main as gen_ehr
        gen_ehr()

    with open(ehr_path, "r", encoding="utf-8") as f:
        patients = json.load(f)

    # Generate streams for first 5 primary patients and all scenarios
    primary_patient = patients[0]
    scenarios = generate_all_scenarios(primary_patient)

    for sc_key, sc_data in scenarios.items():
        sc_file = SCENARIO_DIR / f"{sc_key}.json"
        with open(sc_file, "w", encoding="utf-8") as f:
            json.dump(sc_data, f, indent=2)
        print(f"Generated {sc_key} ({len(sc_data['stream'])} ticks) -> {sc_file}")

    # Generate a full wearable cohort for ML dataset building
    all_wearable_records = []
    for idx, p in enumerate(patients[:30]):
        # Distribute scenario types to create realistic training variance
        sc_choice = ["A", "A", "B", "C", "D", "E", "F"][idx % 7]
        stream = generate_time_series(p, scenario_type=sc_choice, duration_hours=16, seed=100 + idx)
        all_wearable_records.extend(stream)

    wearable_all_file = WEARABLE_DIR / "cohort_wearable_stream.json"
    with open(wearable_all_file, "w", encoding="utf-8") as f:
        json.dump(all_wearable_records, f, indent=2)

    print(f"Generated cohort wearable stream ({len(all_wearable_records)} observations) -> {wearable_all_file}")


if __name__ == "__main__":
    main()
