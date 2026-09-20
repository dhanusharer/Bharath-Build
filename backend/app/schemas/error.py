from datetime import UTC, datetime

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed validation or processing failure for a specific field."""

    field: str = Field(..., description="Target payload field or parameter")
    reason: str = Field(..., description="Failure explanation")


class ErrorBody(BaseModel):
    """Uniform error envelope matching the API contract specification."""

    code: str = Field(..., description="Standardized error code identifier")
    message: str = Field(..., description="Human-readable error explanation")
    details: list[ErrorDetail] = Field(default_factory=list, description="Granular error breakdown")
    request_id: str = Field(..., description="UUIDv4 correlation identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(UTC),
        description="UTC timestamp of error event",
    )
    safe_action_required: str | None = Field(
        None, description="Prescribed fail-safe action (e.g., CONSULT_PHARMACIST)"
    )


class ErrorResponse(BaseModel):
    """Top-level error response wrapper."""

    error: ErrorBody
