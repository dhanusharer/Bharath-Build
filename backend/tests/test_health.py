import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_root_health_liveness(async_client: AsyncClient) -> None:
    """Verify root /health returns ALIVE status with 200 OK."""
    response = await async_client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ALIVE"
    assert "timestamp" in data
    assert "X-Request-ID" in response.headers


@pytest.mark.asyncio
async def test_root_readiness_probe(async_client: AsyncClient) -> None:
    """Verify root /ready returns READY status with dependency states."""
    response = await async_client.get("/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
    assert "dependencies" in data
    assert data["dependencies"]["database"] == "UP"
    assert data["dependencies"]["s3_bucket"] == "UP"
    assert data["dependencies"]["bedrock_endpoint"] == "UP"
    assert "timestamp" in data


@pytest.mark.asyncio
async def test_api_v1_health_liveness(async_client: AsyncClient) -> None:
    """Verify /api/v1/health conforms to contract."""
    response = await async_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ALIVE"


@pytest.mark.asyncio
async def test_api_v1_readiness(async_client: AsyncClient) -> None:
    """Verify /api/v1/ready conforms to contract."""
    response = await async_client.get("/api/v1/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "READY"
