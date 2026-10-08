import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_digital_twin_patients_list(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/digital-twin/patients")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "patient_id" in data[0]


@pytest.mark.asyncio
async def test_digital_twin_get_patient_state(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/digital-twin/state/PT-101")
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "PT-101"
    assert "risk_score" in data
    assert "prediction_horizon" in data
    assert "feature_contributions" in data
    assert "clinical_disclaimer" in data


@pytest.mark.asyncio
async def test_digital_twin_stream_observation(async_client: AsyncClient) -> None:
    payload = {
        "patient_id": "PT-101",
        "glucose": 138.0,
        "heart_rate": 74.0,
        "hrv": 44.0,
        "sleep_duration_hours": 7.0,
        "activity_intensity": 25.0,
    }
    response = await async_client.post("/api/v1/digital-twin/stream-observation", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["patient_id"] == "PT-101"
    assert data["current_glucose"] == 138.0
    assert 0.0 <= data["risk_score"] <= 1.0


@pytest.mark.asyncio
async def test_digital_twin_timeline(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/digital-twin/timeline/PT-101")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_digital_twin_scenarios_list(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/digital-twin/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 6
    assert any(s["scenario_type"] == "A" for s in data)


@pytest.mark.asyncio
async def test_digital_twin_benchmarks_endpoint(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/v1/digital-twin/benchmarks")
    assert response.status_code == 200
    data = response.json()
    assert data["total_scenarios_evaluated"] == 10
    assert data["passed_scenarios"] >= 8
    assert len(data["reports"]) == 10
