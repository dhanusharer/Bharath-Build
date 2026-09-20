"""FastAPI Route Dependencies for Storage, Extractor, Service, and Session Injection."""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.db.session import get_db_session as get_db_session
from app.ports.localization import LocalizationPort
from app.ports.prescription_extractor import VisionExtractionPort
from app.ports.storage import ObjectStoragePort
from app.ports.stt import SpeechToTextPort
from app.ports.tts import TTSProvider
from app.providers.bedrock.config import BedrockProviderConfig
from app.providers.bedrock.prescription_extractor import BedrockPrescriptionExtractor
from app.providers.storage.s3 import S3ObjectStorage
from app.providers.transcribe.amazon_transcribe import AmazonTranscribeProvider
from app.providers.transcribe.amazon_transcribe_streaming import (
    AmazonTranscribeStreamingProvider,
)
from app.providers.tts.kannada import RegionalKannadaTTSProvider
from app.providers.tts.mock import MockTTSProvider
from app.providers.tts.polly import AmazonPollyTTSProvider
from app.repositories.prescription_repository import PrescriptionRepository
from app.services.localization import TemplateLocalizationService
from app.services.prescription_extraction import PrescriptionExtractionService
from app.services.prescription_ingestion import PrescriptionIngestionService
from app.services.voice_intent import VoiceIntentService
from app.services.voice_query_service import VoiceQueryService


def get_storage_port(
    settings: Annotated[Settings, Depends(get_settings)],
) -> ObjectStoragePort:
    """Dependency for S3 Object Storage Port."""
    return S3ObjectStorage(
        bucket_name=settings.S3_BUCKET_NAME,
        region_name=settings.AWS_REGION,
    )


def get_vision_extractor(
    settings: Annotated[Settings, Depends(get_settings)],
) -> VisionExtractionPort:
    """Dependency for Vision Extraction Port (Bedrock Adapter)."""
    bedrock_config = BedrockProviderConfig(
        model_id=settings.BEDROCK_MODEL_ID,
        region_name=settings.AWS_REGION,
        timeout_seconds=settings.BEDROCK_TIMEOUT_SECONDS,
        max_retries=settings.BEDROCK_MAX_RETRIES,
        temperature=settings.BEDROCK_TEMPERATURE,
        max_tokens=settings.BEDROCK_MAX_TOKENS,
    )
    return BedrockPrescriptionExtractor(config=bedrock_config)


def get_extraction_service(
    extractor: Annotated[VisionExtractionPort, Depends(get_vision_extractor)],
) -> PrescriptionExtractionService:
    """Dependency for PrescriptionExtractionService."""
    return PrescriptionExtractionService(extractor=extractor)


def get_prescription_repository(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> PrescriptionRepository:
    """Dependency for PrescriptionRepository with per-request session."""
    return PrescriptionRepository(session=session)


def get_ingestion_service(
    storage: Annotated[ObjectStoragePort, Depends(get_storage_port)],
    extraction_service: Annotated[PrescriptionExtractionService, Depends(get_extraction_service)],
    repo: Annotated[PrescriptionRepository, Depends(get_prescription_repository)],
) -> PrescriptionIngestionService:
    """Dependency for PrescriptionIngestionService."""
    return PrescriptionIngestionService(
        storage_port=storage,
        extraction_service=extraction_service,
        repository=repo,
    )


# ------------------------------------------------------------------------------
# Voice & Localization Dependencies (Phase 4)
# ------------------------------------------------------------------------------


def get_stt_port(
    storage: Annotated[ObjectStoragePort, Depends(get_storage_port)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> SpeechToTextPort:
    """Dependency for Amazon Transcribe streaming speech-to-text port with batch fallback."""
    batch_fallback = AmazonTranscribeProvider(
        storage_port=storage,
        region_name=settings.AWS_REGION,
        bucket_name=settings.S3_BUCKET_NAME,
    )
    return AmazonTranscribeStreamingProvider(
        region_name=settings.AWS_REGION,
        fallback_batch_provider=batch_fallback,
    )


def get_tts_provider(
    settings: Annotated[Settings, Depends(get_settings)],
) -> TTSProvider:
    """Dependency for Text-to-Speech provider with Polly (hi/en) and Regional Kannada TTS."""
    mock_fallback = MockTTSProvider()
    kannada_provider = RegionalKannadaTTSProvider(fallback_provider=mock_fallback)
    return AmazonPollyTTSProvider(
        region_name=settings.AWS_REGION,
        fallback_provider=kannada_provider,
    )


def get_voice_intent_service() -> VoiceIntentService:
    """Dependency for deterministic VoiceIntentService."""
    return VoiceIntentService()


def get_localization_port() -> LocalizationPort:
    """Dependency for deterministic TemplateLocalizationService."""
    return TemplateLocalizationService()


def get_voice_query_service(
    stt: Annotated[SpeechToTextPort, Depends(get_stt_port)],
    intent_service: Annotated[VoiceIntentService, Depends(get_voice_intent_service)],
    localization: Annotated[LocalizationPort, Depends(get_localization_port)],
    tts: Annotated[TTSProvider, Depends(get_tts_provider)],
    repo: Annotated[PrescriptionRepository, Depends(get_prescription_repository)],
) -> VoiceQueryService:
    """Dependency for VoiceQueryService coordinating the end-to-end inquiry."""
    return VoiceQueryService(
        stt_port=stt,
        intent_service=intent_service,
        localization_port=localization,
        tts_provider=tts,
        repository=repo,
    )
