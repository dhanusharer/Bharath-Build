from typing import Any, Literal
from pydantic import BaseModel, Field


class FeatureContribution(BaseModel):
    feature: str = Field(description="Name of the physiological or temporal feature")
    display_name: str = Field(description="Doctor-friendly feature description")
    value: float | None = Field(description="Current observed or calculated value")
    contribution_percentage: float = Field(description="Exact percentage contribution to risk probability")
    direction: Literal["RISK_INCREASING", "PROTECTIVE_OR_NEUTRAL"] = Field(
        description="Whether this factor drives risk upward or exerts protective dampening"
    )


class WearableObservationInput(BaseModel):
    patient_id: str
    timestamp: str | None = None
    glucose: float | None = None
    heart_rate: float | None = None
    hrv: float | None = None
    sleep_duration_hours: float | None = None
    sleep_quality_score: float | None = None
    steps_interval: int | None = None
    steps_cumulative: int | None = None
    activity_intensity: float | None = None
    spo2: float | None = None
    blood_pressure_systolic: float | None = None
    blood_pressure_diastolic: float | None = None
    sensor_status: str = "NORMAL"


class PatientTwinState(BaseModel):
    patient_id: str
    timestamp: str
    name: str
    age: int
    sex: str
    bmi: float
    diabetes_duration_years: float
    hba1c: float
    fasting_glucose: float
    baseline_glucose: float
    baseline_hr: float
    baseline_hrv: float
    baseline_sleep_hours: float
    baseline_steps: int

    # Current dynamic state
    current_glucose: float | None
    current_hr: float | None
    current_hrv: float | None
    current_sleep_hours: float | None
    current_steps: int | None
    current_activity_intensity: float | None
    spo2: float | None = None
    blood_pressure_systolic: float | None = None
    blood_pressure_diastolic: float | None = None

    # Temporal Trends & Rolling metrics
    rolling_glucose_trend: float
    rolling_hr_trend: float
    rolling_hrv_trend: float
    rolling_glucose_mean_15m: float
    rolling_glucose_mean_30m: float
    rolling_glucose_mean_60m: float
    rolling_glucose_std_60m: float

    # Deviations from personal baseline
    deviation_glucose_from_baseline: float
    deviation_hr_from_baseline: float
    deviation_hrv_from_baseline: float
    deviation_sleep_from_baseline: float

    # Medication Verification Context
    medication_profile: list[dict[str, Any]]
    medication_active_count: int
    time_since_last_medication_hours: float | None
    medication_adherence_status: Literal[
        "VERIFIED_ADHERENT", "MISSED_DOSE", "UNVERIFIED_REVIEW_REQUIRED", "UNKNOWN"
    ]

    # Model Risk Forecast
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_category: Literal["LOW", "MODERATE", "ELEVATED", "CRITICAL", "INSUFFICIENT_DATA"]
    prediction_horizon: str = "Next 2 hours"
    model_version: str = "MedTwin-GBM-v1.0"
    state_confidence: float = Field(ge=0.0, le=1.0)
    feature_contributions: list[FeatureContribution]
    what_changed_summary: str

    # Safety Invariants
    missing_features: list[str]
    requires_clinical_review: bool
    last_updated: str
    clinical_disclaimer: str = (
        "MedTwin AI is a research proof-of-concept for adverse health event forecasting. "
        "It provides clinical decision support signals and does NOT provide diagnosis, treatment, "
        "or dosage modifications."
    )


class TimelineEntry(BaseModel):
    timestamp: str
    glucose: float | None
    heart_rate: float | None
    hrv: float | None
    activity_intensity: float | None
    risk_score: float | None
    risk_category: str
    glucose_deviation: float | None
    event_flag: bool = False


class ScenarioInfo(BaseModel):
    scenario_id: str
    scenario_type: str
    title: str
    clinical_narrative: str
    expected_outcome: str


class BenchmarkScenarioReport(BaseModel):
    scenario_index: int
    scenario_name: str
    description: str
    prediction_risk_score: float
    risk_category: str
    state_confidence: float
    missing_data_handled: bool
    medication_safety_checked: bool
    expected_status_matched: bool
    summary: str


class BenchmarkSuiteResponse(BaseModel):
    timestamp: str
    total_scenarios_evaluated: int
    passed_scenarios: int
    model_version: str
    clinical_use_case: str
    reports: list[BenchmarkScenarioReport]
