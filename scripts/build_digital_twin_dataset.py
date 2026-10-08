#!/usr/bin/env python3
"""
Digital Twin Feature Engineering & Dataset Builder for MedTwin AI
Fuses Static EHR, Dynamic Wearable Streams, and Verified Medication Regimens
into a stateful feature matrix for 2-hour adverse glucose excursion forecasting.
"""

import json
from datetime import datetime
from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "synthetic"
EHR_PATH = DATA_DIR / "ehr" / "patients_ehr.json"
WEARABLE_PATH = DATA_DIR / "wearable" / "cohort_wearable_stream.json"
MERGED_DIR = DATA_DIR / "merged"
MERGED_DIR.mkdir(parents=True, exist_ok=True)


def calculate_slopes(series: pd.Series, window_steps: int = 6) -> pd.Series:
    """Compute rate of change (slope per hour) over sliding window."""
    # Assuming 5-minute intervals, 6 steps = 30 minutes, 12 steps = 60 minutes
    return series.diff(window_steps) / (window_steps * 5.0 / 60.0)


def build_dataset() -> pd.DataFrame:
    with open(EHR_PATH, "r", encoding="utf-8") as f:
        ehr_list = json.load(f)
    ehr_map = {p["patient_id"]: p for p in ehr_list}

    with open(WEARABLE_PATH, "r", encoding="utf-8") as f:
        wearables = json.load(f)

    df_wearable = pd.DataFrame(wearables)
    df_wearable["timestamp"] = pd.to_datetime(df_wearable["timestamp"])
    df_wearable = df_wearable.sort_values(by=["patient_id", "timestamp"]).reset_index(drop=True)

    rows = []
    # 2 hours ahead = 24 steps (5-minute intervals)
    HORIZON_STEPS = 24
    SPIKE_THRESHOLD = 180.0
    DELTA_SPIKE_THRESHOLD = 45.0

    grouped = df_wearable.groupby("patient_id")

    for patient_id, group in grouped:
        patient_ehr = ehr_map.get(patient_id)
        if not patient_ehr:
            continue

        base_glucose = patient_ehr["baseline_glucose"]
        base_hr = patient_ehr["baseline_hr"]
        base_hrv = patient_ehr["baseline_hrv"]
        base_sleep = patient_ehr["baseline_sleep_hours"]
        base_steps = patient_ehr["baseline_steps"]
        hba1c = patient_ehr["hba1c"]
        age = patient_ehr["age"]
        bmi = patient_ehr["bmi"]
        diabetes_duration = patient_ehr["diabetes_duration_years"]
        has_hypertension = 1 if patient_ehr["has_hypertension"] else 0

        # Medication features
        meds = patient_ehr.get("medication_regimen", [])
        med_count = len(meds)
        has_metformin = 1 if any("metformin" in m["drug_name"].lower() for m in meds) else 0
        has_sulfonylurea = 1 if any("glimepiride" in m["drug_name"].lower() for m in meds) else 0

        group = group.copy().reset_index(drop=True)

        # Impute missing values with personal baseline for feature extraction, but record missing flag
        group["glucose_missing"] = group["glucose"].isna().astype(int)
        group["hrv_missing"] = group["hrv"].isna().astype(int)
        group["clean_glucose"] = group["glucose"].fillna(base_glucose)
        group["clean_hr"] = group["heart_rate"].fillna(base_hr)
        group["clean_hrv"] = group["hrv"].fillna(base_hrv)
        group["clean_activity"] = group["activity_intensity"].fillna(20.0)

        # Temporal rolling statistics
        group["glucose_roll_mean_15m"] = group["clean_glucose"].rolling(3, min_periods=1).mean()
        group["glucose_roll_mean_30m"] = group["clean_glucose"].rolling(6, min_periods=1).mean()
        group["glucose_roll_mean_60m"] = group["clean_glucose"].rolling(12, min_periods=1).mean()
        group["glucose_roll_mean_120m"] = group["clean_glucose"].rolling(24, min_periods=1).mean()
        group["glucose_roll_std_60m"] = group["clean_glucose"].rolling(12, min_periods=2).std().fillna(0.0)

        group["glucose_slope_30m"] = calculate_slopes(group["clean_glucose"], window_steps=6).fillna(0.0)
        group["glucose_slope_60m"] = calculate_slopes(group["clean_glucose"], window_steps=12).fillna(0.0)
        group["hr_slope_30m"] = calculate_slopes(group["clean_hr"], window_steps=6).fillna(0.0)
        group["hrv_slope_30m"] = calculate_slopes(group["clean_hrv"], window_steps=6).fillna(0.0)

        n_records = len(group)
        for i in range(n_records):
            cur = group.iloc[i]

            # Labeling: target in [i + 1, i + HORIZON_STEPS]
            if i + HORIZON_STEPS < n_records:
                future_window = group.iloc[i + 1 : i + HORIZON_STEPS + 1]["clean_glucose"]
                max_future_glucose = future_window.max()
                delta_future_glucose = max_future_glucose - cur["clean_glucose"]
                # Adverse outcome event if future glucose > 180 or jump >= 45 mg/dL
                adverse_event_2h = 1 if (max_future_glucose >= SPIKE_THRESHOLD or delta_future_glucose >= DELTA_SPIKE_THRESHOLD) else 0
            else:
                # Last 2 hours of sequence - no future ground truth horizon
                continue

            t = cur["timestamp"]
            hour = t.hour
            circadian_morning = 1 if 6 <= hour <= 11 else 0
            circadian_postprandial = 1 if 12 <= hour <= 16 else 0
            circadian_evening = 1 if 17 <= hour <= 22 else 0
            circadian_night = 1 if hour >= 23 or hour < 6 else 0

            # Deviations from personal baseline
            dev_glucose = cur["clean_glucose"] - base_glucose
            dev_hr = cur["clean_hr"] - base_hr
            dev_hrv = cur["clean_hrv"] - base_hrv
            sleep_hours = cur["sleep_duration_hours"]
            dev_sleep = (sleep_hours - base_sleep) if pd.notna(sleep_hours) else 0.0

            # Medication schedule context (assuming standard doses at 8:00 AM and 8:00 PM)
            cur_time_hours = hour + (t.minute / 60.0)
            if cur_time_hours >= 20.0:
                time_since_med = cur_time_hours - 20.0
            elif cur_time_hours >= 8.0:
                time_since_med = cur_time_hours - 8.0
            else:
                time_since_med = cur_time_hours + 4.0  # since 8 PM previous night

            is_adherence_lapse = 1 if cur.get("scenario") == "F" and cur_time_hours > 9.0 else 0

            row = {
                "patient_id": patient_id,
                "timestamp": cur["timestamp"].isoformat(),
                "age": age,
                "bmi": bmi,
                "diabetes_duration_years": diabetes_duration,
                "hba1c": hba1c,
                "has_hypertension": has_hypertension,
                "base_glucose": base_glucose,
                "base_hr": base_hr,
                "base_hrv": base_hrv,
                "base_sleep": base_sleep,
                "base_steps": base_steps,
                "current_glucose": cur["clean_glucose"],
                "current_hr": cur["clean_hr"],
                "current_hrv": cur["clean_hrv"],
                "current_sleep": sleep_hours,
                "current_activity": cur["clean_activity"],
                "glucose_roll_mean_15m": round(cur["glucose_roll_mean_15m"], 2),
                "glucose_roll_mean_30m": round(cur["glucose_roll_mean_30m"], 2),
                "glucose_roll_mean_60m": round(cur["glucose_roll_mean_60m"], 2),
                "glucose_roll_mean_120m": round(cur["glucose_roll_mean_120m"], 2),
                "glucose_roll_std_60m": round(cur["glucose_roll_std_60m"], 2),
                "glucose_slope_30m": round(cur["glucose_slope_30m"], 2),
                "glucose_slope_60m": round(cur["glucose_slope_60m"], 2),
                "hr_slope_30m": round(cur["hr_slope_30m"], 2),
                "hrv_slope_30m": round(cur["hrv_slope_30m"], 2),
                "dev_glucose": round(dev_glucose, 2),
                "dev_hr": round(dev_hr, 2),
                "dev_hrv": round(dev_hrv, 2),
                "dev_sleep": round(dev_sleep, 2),
                "circadian_morning": circadian_morning,
                "circadian_postprandial": circadian_postprandial,
                "circadian_evening": circadian_evening,
                "circadian_night": circadian_night,
                "med_count": med_count,
                "has_metformin": has_metformin,
                "has_sulfonylurea": has_sulfonylurea,
                "time_since_med_hours": round(time_since_med, 2),
                "is_adherence_lapse": is_adherence_lapse,
                "glucose_missing": cur["glucose_missing"],
                "hrv_missing": cur["hrv_missing"],
                # Target
                "adverse_event_2h_ahead": adverse_event_2h,
            }
            rows.append(row)

    df = pd.DataFrame(rows)
    csv_path = MERGED_DIR / "digital_twin_features.csv"
    df.to_csv(csv_path, index=False)
    print(f"Built Digital Twin dataset: {df.shape[0]} samples, {df.shape[1]} features -> {csv_path}")
    print(f"Adverse event incidence rate: {df['adverse_event_2h_ahead'].mean():.2%}")
    return df


def main() -> None:
    build_dataset()


if __name__ == "__main__":
    main()
