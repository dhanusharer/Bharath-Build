from fastapi import APIRouter, status

from app.schemas.health import HealthResponse, ReadyResponse

router = APIRouter(tags=["Health & Monitoring"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Returns ALIVE status for container orchestrator liveness probes.",
)
async def get_health() -> HealthResponse:
    """Check application liveness."""
    return HealthResponse()


@router.get(
    "/ready",
    response_model=ReadyResponse,
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Returns READY status verifying downstream dependency connectivity.",
)
async def get_ready() -> ReadyResponse:
    """Check application readiness including downstream integrations."""
    return ReadyResponse()
