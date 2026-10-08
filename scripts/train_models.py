#!/usr/bin/env python3
"""
Model Training and Evaluation Pipeline for MedTwin AI
Trains and benchmarks:
1. Baseline Model: Logistic Regression
2. Gradient Boosting Model: HistGradientBoostingClassifier (LightGBM-equivalent)
3. Ensemble / Random Forest Model

Evaluates on clinical metrics: ROC-AUC, PR-AUC, F1, Precision, Recall, Calibration (Brier Score),
and extracts feature importance rankings for explainable Digital Twin inference.
"""

import json
from pathlib import Path
import joblib
import numpy as np
import pandas as pd
from sklearn.calibration import calibration_curve
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = PROJECT_ROOT / "data" / "synthetic" / "merged" / "digital_twin_features.csv"
MODELS_DIR = PROJECT_ROOT / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

FEATURE_COLS = [
    # Static EHR features
    "age",
    "bmi",
    "diabetes_duration_years",
    "hba1c",
    "has_hypertension",
    "base_glucose",
    "base_hr",
    "base_hrv",
    "base_sleep",
    # Dynamic wearable observations
    "current_glucose",
    "current_hr",
    "current_hrv",
    "current_activity",
    # Rolling features
    "glucose_roll_mean_15m",
    "glucose_roll_mean_30m",
    "glucose_roll_mean_60m",
    "glucose_roll_std_60m",
    # Temporal Trend slopes
    "glucose_slope_30m",
    "glucose_slope_60m",
    "hr_slope_30m",
    "hrv_slope_30m",
    # Deviations from personal baseline
    "dev_glucose",
    "dev_hr",
    "dev_hrv",
    "dev_sleep",
    # Circadian features
    "circadian_morning",
    "circadian_postprandial",
    "circadian_evening",
    "circadian_night",
    # Medication-aware features
    "med_count",
    "has_metformin",
    "has_sulfonylurea",
    "time_since_med_hours",
    "is_adherence_lapse",
    # Missingness flags
    "glucose_missing",
    "hrv_missing",
]

TARGET_COL = "adverse_event_2h_ahead"


def train_and_evaluate() -> dict:
    df = pd.read_csv(DATA_PATH)
    print(f"Loaded dataset: {df.shape[0]} rows, {df.shape[1]} columns")

    X = df[FEATURE_COLS]
    y = df[TARGET_COL]

    # Stratified train-test split (80/20)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=42, stratify=y
    )

    # Scaler for linear baseline
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    # 1. Baseline Model: Logistic Regression
    lr = LogisticRegression(max_iter=1000, class_weight="balanced", random_state=42)
    lr.fit(X_train_scaled, y_train)
    y_pred_lr = lr.predict(X_test_scaled)
    y_prob_lr = lr.predict_proba(X_test_scaled)[:, 1]

    # 2. Gradient Boosting Model: HistGradientBoostingClassifier
    gbm = HistGradientBoostingClassifier(
        max_iter=120,
        learning_rate=0.08,
        max_depth=6,
        random_state=42,
        class_weight="balanced",
    )
    gbm.fit(X_train, y_train)
    y_pred_gbm = gbm.predict(X_test)
    y_prob_gbm = gbm.predict_proba(X_test)[:, 1]

    # 3. Random Forest Model
    rf = RandomForestClassifier(n_estimators=100, max_depth=8, class_weight="balanced", random_state=42)
    rf.fit(X_train, y_train)
    y_pred_rf = rf.predict(X_test)
    y_prob_rf = rf.predict_proba(X_test)[:, 1]

    def evaluate_model(name: str, y_true: np.ndarray, y_pred: np.ndarray, y_prob: np.ndarray) -> dict:
        cm = confusion_matrix(y_true, y_pred).tolist()
        roc_auc = float(roc_auc_score(y_true, y_prob))
        pr_auc = float(average_precision_score(y_true, y_prob))
        f1 = float(f1_score(y_true, y_pred))
        precision = float(precision_score(y_true, y_pred))
        recall = float(recall_score(y_true, y_pred))
        brier = float(brier_score_loss(y_true, y_prob))

        # Calibration curve points
        prob_true, prob_pred = calibration_curve(y_true, y_prob, n_bins=5)

        return {
            "model_name": name,
            "roc_auc": round(roc_auc, 4),
            "pr_auc": round(pr_auc, 4),
            "f1_score": round(f1, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "brier_score_loss": round(brier, 4),
            "confusion_matrix": {
                "true_negative": cm[0][0],
                "false_positive": cm[0][1],
                "false_negative": cm[1][0],
                "true_positive": cm[1][1],
            },
            "calibration": {
                "prob_true": [round(float(p), 4) for p in prob_true],
                "prob_pred": [round(float(p), 4) for p in prob_pred],
            },
        }

    metrics = {
        "dataset_summary": {
            "total_samples": len(df),
            "training_samples": len(X_train),
            "test_samples": len(X_test),
            "feature_count": len(FEATURE_COLS),
            "target": TARGET_COL,
            "prediction_horizon": "2 hours ahead",
        },
        "models": {
            "logistic_regression_baseline": evaluate_model("Logistic Regression Baseline", y_test, y_pred_lr, y_prob_lr),
            "hist_gradient_boosting": evaluate_model("HistGradientBoosting (LightGBM equivalent)", y_test, y_pred_gbm, y_prob_gbm),
            "random_forest": evaluate_model("Random Forest Ensemble", y_test, y_pred_rf, y_prob_rf),
        },
    }

    # Feature Importance analysis (using Random Forest Gini + Logistic weights)
    rf_importances = rf.feature_importances_
    feat_imp = [
        {"feature": feat, "importance": round(float(imp), 4)}
        for feat, imp in zip(FEATURE_COLS, rf_importances)
    ]
    feat_imp.sort(key=lambda x: x["importance"], reverse=True)
    metrics["top_feature_importances"] = feat_imp

    # Save artifacts
    joblib.dump(gbm, MODELS_DIR / "digital_twin_gbm_model.joblib")
    joblib.dump(lr, MODELS_DIR / "digital_twin_lr_baseline.joblib")
    joblib.dump(rf, MODELS_DIR / "digital_twin_rf_model.joblib")
    joblib.dump(scaler, MODELS_DIR / "feature_scaler.joblib")
    with open(MODELS_DIR / "feature_names.json", "w", encoding="utf-8") as f:
        json.dump(FEATURE_COLS, f, indent=2)

    with open(MODELS_DIR / "evaluation_metrics.json", "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)

    print("\n--- Model Evaluation Results ---")
    for m_key, m_val in metrics["models"].items():
        print(f"[{m_val['model_name']}]")
        print(f"  ROC-AUC: {m_val['roc_auc']:.4f} | PR-AUC: {m_val['pr_auc']:.4f} | F1: {m_val['f1_score']:.4f}")
        print(f"  Recall:  {m_val['recall']:.4f} | Precision: {m_val['precision']:.4f} | Brier: {m_val['brier_score_loss']:.4f}")
        cm = m_val["confusion_matrix"]
        print(f"  Confusion Matrix: TP={cm['true_positive']}, FP={cm['false_positive']}, FN={cm['false_negative']}, TN={cm['true_negative']}")

    print("\n--- Top 10 Features Driving Prediction ---")
    for item in feat_imp[:10]:
        print(f"  {item['feature']:<25}: {item['importance']:.4f}")

    return metrics


def main() -> None:
    train_and_evaluate()


if __name__ == "__main__":
    main()
