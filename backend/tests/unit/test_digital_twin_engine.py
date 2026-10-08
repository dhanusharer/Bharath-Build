"""Unit tests for MedTwin AI Digital Twin Engine, stateful updates, and safety logic."""

import pytest
from app.schemas.digital_twin import WearableObservationInput
from app.services.digital_twin_engine import DigitalTwinEngine, get_digital_twin_engine
from app.services.voice_intent import VoiceIntentService, VoiceIntentType


@pytest.fixture
def twin_engine() -> DigitalTwinEngine:
    return DigitalTwinEngine()


def test_engine_initializes_with_patient_cohort(twin_engine: DigitalTwinEngine) -> None:
    patients = twin_engine.list_patients()
    assert len(patients) >= 1
    pt = patients[0]
    assert "patient_id" in pt
    assert "current_risk" in pt
    assert "risk_category" in pt


def test_get_initial_twin_state(twin_engine: DigitalTwinEngine) -> None:
    state = twin_engine.get_twin_state("PT-101")
    assert state is not None
    assert state.patient_id == "PT-101"
    assert state.prediction_horizon == "Next 2 hours"
    assert state.model_version == "MedTwin-GBM-v1.0"
    assert 0.0 <= state.risk_score <= 1.0
    assert state.state_confidence > 0.5


def test_ingest_stable_observation_maintains_low_risk(twin_engine: DigitalTwinEngine) -> None:
    obs = WearableObservationInput(
        patient_id="PT-101",
        glucose=124.0,
        heart_rate=70.0,
        hrv=48.0,
        sleep_duration_hours=7.2,
        activity_intensity=20.0,
    )
    state = twin_engine.ingest_observation(obs)
    assert state.current_glucose == 124.0
    assert state.risk_category in ["LOW", "MODERATE"]
    assert state.state_confidence >= 0.8
    assert len(state.missing_features) == 0


def test_ingest_escalating_glucose_elevates_risk(twin_engine: DigitalTwinEngine) -> None:
    # Ingest consecutive rising ticks to establish slope
    for g in [140.0, 150.0, 160.0, 172.0, 185.0, 198.0]:
        obs = WearableObservationInput(
            patient_id="PT-101",
            glucose=g,
            heart_rate=88.0,
            hrv=28.0,
            sleep_duration_hours=4.0,
            activity_intensity=12.0,
        )
        state = twin_engine.ingest_observation(obs)

    assert state.current_glucose == 198.0
    assert state.deviation_glucose_from_baseline > 50.0
    assert state.rolling_glucose_trend > 0.0
    assert state.risk_category in ["ELEVATED", "CRITICAL"]
    assert state.risk_score > 0.50
    assert "glucose" in state.what_changed_summary.lower()


def test_missing_data_triggers_confidence_penalty_and_fail_closed(
    twin_engine: DigitalTwinEngine,
) -> None:
    obs = WearableObservationInput(
        patient_id="PT-NEW-DROPOUT",
        glucose=None,  # Missing glucose telemetry
        heart_rate=72.0,
        hrv=None,  # Missing HRV telemetry
        sleep_duration_hours=None,
    )
    state = twin_engine.ingest_observation(obs)
    assert "current_glucose" in state.missing_features
    assert "hrv" in state.missing_features
    assert state.state_confidence < 0.60
    assert state.risk_category == "INSUFFICIENT_DATA"
    assert "Insufficient" in state.what_changed_summary


def test_unverified_medication_flags_review_in_digital_twin(twin_engine: DigitalTwinEngine) -> None:
    obs = WearableObservationInput(
        patient_id="PT-101",
        glucose=130.0,
        heart_rate=72.0,
        hrv=45.0,
        sleep_duration_hours=7.0,
    )
    unverified_meds = [
        {"drug_name": "Lisinopril 5mg", "verified": False, "requires_review": True}
    ]
    state = twin_engine.ingest_observation(obs, verified_med_profile=unverified_meds)
    assert state.medication_adherence_status == "UNVERIFIED_REVIEW_REQUIRED"
    assert state.requires_clinical_review is True


def test_feature_contributions_decomposition(twin_engine: DigitalTwinEngine) -> None:
    obs = WearableObservationInput(
        patient_id="PT-101",
        glucose=175.0,
        heart_rate=84.0,
        hrv=30.0,
        sleep_duration_hours=4.5,
    )
    state = twin_engine.ingest_observation(obs)
    assert len(state.feature_contributions) >= 4
    total_pct = sum(c.contribution_percentage for c in state.feature_contributions)
    assert 98.0 <= total_pct <= 102.0  # Normalized to ~100%


def test_benchmark_suite_runs_all_10_scenarios(twin_engine: DigitalTwinEngine) -> None:
    res = twin_engine.run_benchmark_suite()
    assert res.total_scenarios_evaluated == 10
    assert res.passed_scenarios >= 8
    assert len(res.reports) == 10
    assert any(r.scenario_name == "Stable Patient Baseline" for r in res.reports)
    assert any("Missing Wearable Data" in r.scenario_name for r in res.reports)


def test_voice_intent_classification_for_digital_twin() -> None:
    svc = VoiceIntentService()

    res1 = svc.classify_intent("Show my glucose trend")
    assert res1.intent == VoiceIntentType.GLUCOSE_TREND

    res2 = svc.classify_intent("ನನ್ನ glucose trend ತೋರಿಸಿ")
    assert res2.intent == VoiceIntentType.GLUCOSE_TREND

    res3 = svc.classify_intent("मेरा ग्लूकोज ट्रेंड क्या है?")
    assert res3.intent == VoiceIntentType.GLUCOSE_TREND

    res4 = svc.classify_intent("Risk yestu ide?")
    assert res4.intent == VoiceIntentType.RISK_SCORE

    res5 = svc.classify_intent("जोखिम कितना है?")
    assert res5.intent == VoiceIntentType.RISK_SCORE
