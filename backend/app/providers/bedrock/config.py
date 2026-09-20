"""Bedrock Provider Configuration and Constants."""

from collections.abc import Mapping
from typing import Final

from pydantic import BaseModel, Field

SUPPORTED_MIME_TYPES: Final[Mapping[str, str]] = {
    "image/jpeg": "jpeg",
    "image/jpg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}


class BedrockProviderConfig(BaseModel):
    """Configuration settings for Bedrock Runtime extractor."""

    region_name: str = Field(default="ap-south-1", description="AWS Region")
    model_id: str = Field(
        default="placeholder-bedrock-multimodal-model-id",
        description="Configured multimodal foundation model ID in Bedrock (via BEDROCK_MODEL_ID)",
    )
    timeout_seconds: float = Field(
        default=30.0,
        ge=1.0,
        le=300.0,
        description="Conservative inference timeout in seconds",
    )
    max_retries: int = Field(
        default=2,
        ge=0,
        le=5,
        description="Maximum retries for transient/throttling errors",
    )
    temperature: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Model sampling temperature (0.0 for deterministic extraction)",
    )
    max_tokens: int = Field(
        default=2048,
        ge=256,
        le=8192,
        description="Maximum generation tokens",
    )
