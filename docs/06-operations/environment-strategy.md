# Environment & Configuration Strategy

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Tiers**: Local, Development, Production  

---

## 1. Environment Topology

| Dimension | Local (`local`) | Development (`dev`) | Production (`prod`) |
| :--- | :--- | :--- | :--- |
| **Compute** | Local Docker / `uv run` | AWS ECS Fargate (Single Task) | AWS ECS Fargate (Auto-scaled Multi-AZ) |
| **Database** | Docker Compose PostgreSQL 16 | AWS RDS PostgreSQL (db.t4g.micro) | AWS RDS PostgreSQL Multi-AZ (db.t4g.small) |
| **Object Storage** | LocalStack / Dev S3 Bucket | Dedicated S3 Dev Bucket | Dedicated S3 Production Bucket (KMS CMK) |
| **Bedrock Models** | Mock / Live Claude 3.5 Sonnet | Live Claude 3.5 Sonnet (`ap-south-1`) | Live Claude 3.5 Sonnet (`ap-south-1`) |
| **Speech-to-Text** | Mock STT / Live Transcribe | Live Amazon Transcribe | Live Amazon Transcribe |
| **Text-to-Speech** | Mock TTS Engine | Amazon Polly (Hindi) / Mock Kannada | Amazon Polly (Hindi) / Dedicated Kannada Provider |
| **Secrets Management** | `.env` file (git-ignored) | AWS Secrets Manager (Dev Secret) | AWS Secrets Manager (Prod Secret + KMS) |
| **Logging Level** | `DEBUG` (Console Pretty) | `INFO` (Structured JSON) | `INFO` (Structured JSON + CloudWatch) |

---

## 2. Configuration Management via Pydantic BaseSettings

Configuration is managed strictly through typed environment variables:

```python
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    APP_ENV: str = Field(default="local")
    DEBUG: bool = Field(default=False)
    PORT: int = Field(default=8000)
    HOST: str = Field(default="0.0.0.0")
    
    # Security
    SECRET_KEY: str
    ALLOWED_ORIGINS: list[str] = ["http://localhost:3000"]
    
    # Database
    DATABASE_URL: str
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    
    # AWS Infrastructure
    AWS_REGION: str = "ap-south-1"
    S3_BUCKET_NAME: str
    S3_PRESIGNED_EXPIRATION_SECONDS: int = 900
    
    # Amazon Bedrock
    BEDROCK_MODEL_ID: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    BEDROCK_MAX_TOKENS: int = 2048
    BEDROCK_TEMPERATURE: float = 0.0
    
    # TTS & Voice
    TTS_DEFAULT_PROVIDER: str = "polly"
    POLLY_VOICE_ID_HINDI: str = "Kajal"
    TRANSCRIBE_LANGUAGE_CODE: str = "hi-IN"
```

---

## 3. Secret Isolation Rules
1. **Zero Secret Hardcoding**: Secrets are never checked into version control. Pre-commit hooks verify no `.env` or API tokens exist in commits.
2. **KMS Key Separation**: Production database credentials and encryption keys use dedicated KMS keys inaccessible to development IAM roles.
3. **IAM Role Assumption**: In ECS Fargate, the container retrieves credentials automatically via the Task Role metadata service; no static `AWS_ACCESS_KEY_ID` is used in production.
