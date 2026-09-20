from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application Settings managed via Pydantic BaseSettings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Core Application Settings
    APP_NAME: str = "Multimodal Medication Accessibility API"
    APP_ENV: str = "local"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"
    LOG_LEVEL: str = "INFO"

    # Security & CORS
    SECRET_KEY: str = "development-secret-key-replace-in-production-min-32-chars"
    ALLOWED_ORIGINS: list[str] = Field(default=["http://localhost:3000", "http://127.0.0.1:3000"])

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/medication_access_db"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # AWS Configuration (Supports AWS_PROFILE or standard credential chain)
    AWS_REGION: str = "ap-south-1"
    AWS_PROFILE: str | None = None
    AWS_ACCESS_KEY_ID: str | None = None
    AWS_SECRET_ACCESS_KEY: str | None = None

    # Storage & AI Services
    S3_BUCKET_NAME: str = "medication-access-artifacts-dev"
    S3_PRESIGNED_EXPIRATION_SECONDS: int = 900
    BEDROCK_MODEL_ID: str = Field(
        default="placeholder-bedrock-multimodal-model-id",
        description="Bedrock multimodal model ID supplied through environment (BEDROCK_MODEL_ID)",
    )
    BEDROCK_FALLBACK_MODEL_ID: str | None = Field(
        default=None,
        description="Optional fallback multimodal model ID",
    )
    BEDROCK_TIMEOUT_SECONDS: float = 30.0
    BEDROCK_MAX_RETRIES: int = 2
    BEDROCK_TEMPERATURE: float = 0.0
    BEDROCK_MAX_TOKENS: int = 2048

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, (list, str)):
            return v  # type: ignore[return-value]
        raise ValueError("Invalid format for ALLOWED_ORIGINS")


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
