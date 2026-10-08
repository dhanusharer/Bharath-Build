from typing import Any
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.digital_twin import (
    BenchmarkSuiteResponse,
    PatientTwinState,
    ScenarioInfo,
    TimelineEntry,
    WearableObservationInput,
)
from app.services.digital_twin_engine import get_digital_twin_engine

router = APIRouter(prefix="/digital-twin", tags=["Digital Twin"])


@router.get("/patients", summary="List synthetic patient cohort")
async def list_patients() -> list[dict[str, Any]]:
    engine = get_digital_twin_engine()
    return engine.list_patients()


@router.get("/state/{patient_id}", response_model=PatientTwinState, summary="Get active Patient Digital Twin state")
async def get_patient_state(patient_id: str) -> PatientTwinState:
    engine = get_digital_twin_engine()
    state = engine.get_twin_state(patient_id)
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Digital Twin for patient '{patient_id}' not found.",
        )
    return state


@router.post(
    "/stream-observation",
    response_model=PatientTwinState,
    summary="Ingest dynamic wearable observation tick and update twin state",
)
async def ingest_observation(obs: WearableObservationInput) -> PatientTwinState:
    engine = get_digital_twin_engine()
    return engine.ingest_observation(obs)


@router.get(
    "/timeline/{patient_id}",
    response_model=list[TimelineEntry],
    summary="Get multi-signal time-series timeline for a patient",
)
async def get_patient_timeline(patient_id: str) -> list[TimelineEntry]:
    engine = get_digital_twin_engine()
    return engine.get_timeline(patient_id)


@router.get("/scenarios", response_model=list[ScenarioInfo], summary="List available physiological simulation scenarios")
async def list_scenarios() -> list[ScenarioInfo]:
    engine = get_digital_twin_engine()
    return engine.list_scenarios()


@router.post(
    "/simulate/{scenario_key}",
    response_model=PatientTwinState,
    summary="Replay simulated scenario observations into patient digital twin",
)
async def simulate_scenario(
    scenario_key: str,
    patient_id: str = Query("PT-101", description="Patient ID to simulate"),
    steps: int = Query(12, ge=1, le=144, description="Number of 5-minute ticks to ingest"),
) -> PatientTwinState:
    engine = get_digital_twin_engine()
    stream = engine.load_scenario_stream(scenario_key)
    if not stream:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Scenario stream for key '{scenario_key}' not found on server.",
        )

    last_state = None
    for item in stream[:steps]:
        obs = WearableObservationInput(
            patient_id=patient_id,
            timestamp=item.get("timestamp"),
            glucose=item.get("glucose"),
            heart_rate=item.get("heart_rate"),
            hrv=item.get("hrv"),
            sleep_duration_hours=item.get("sleep_duration_hours"),
            sleep_quality_score=item.get("sleep_quality_score"),
            steps_interval=item.get("steps_interval"),
            steps_cumulative=item.get("steps_cumulative"),
            activity_intensity=item.get("activity_intensity"),
            spo2=item.get("spo2"),
            blood_pressure_systolic=item.get("blood_pressure_systolic"),
            blood_pressure_diastolic=item.get("blood_pressure_diastolic"),
            sensor_status=item.get("sensor_status", "NORMAL"),
        )
        last_state = engine.ingest_observation(obs)

    if not last_state:
        raise HTTPException(status_code=400, detail="Unable to replay scenario stream.")
    return last_state


@router.get(
    "/benchmarks",
    response_model=BenchmarkSuiteResponse,
    summary="Run full 10-scenario clinical Digital Twin benchmark suite",
)
async def run_benchmarks() -> BenchmarkSuiteResponse:
    engine = get_digital_twin_engine()
    return engine.run_benchmark_suite()
