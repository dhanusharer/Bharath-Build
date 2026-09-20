from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class HealthStatus(StrEnum):
    ALIVE = "ALIVE"
    READY = "READY"
    DEGRADED = "DEGRADED"
    DOWN = "DOWN"


class DependencyStatus(StrEnum):
    UP = "UP"
    DOWN = "DOWN"
    DEGRADED = "DEGRADED"


class HealthResponse(BaseModel):
    """Liveness probe response model."""

    status: HealthStatus = Field(default=HealthStatus.ALIVE, description="Liveness state")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of probe check",
    )


class ReadyResponse(BaseModel):
    """Readiness probe response model checking service dependencies."""

    status: HealthStatus = Field(default=HealthStatus.READY, description="Readiness state")
    dependencies: dict[str, DependencyStatus] = Field(
        default_factory=lambda: {
            "database": DependencyStatus.UP,
            "s3_bucket": DependencyStatus.UP,
            "bedrock_endpoint": DependencyStatus.UP,
        },
        description="Health states of downstream dependencies",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of probe check",
    )
