"""Voice Accessibility API Endpoints.

Routes:
- POST /api/v1/voice/transcribe: Transcribe speech audio to text.
- POST /api/v1/voice/query: Spoken question answering on validated prescription data.
"""

import logging
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Form,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.api.dependencies import get_stt_port, get_voice_query_service
from app.ports.stt import SpeechToTextPort
from app.ports.voice_exceptions import (
    EmptyAudioError,
    TranscribeError,
    UnsupportedLanguageError,
)
from app.schemas.error import ErrorBody, ErrorDetail, ErrorResponse
from app.schemas.voice import TranscribeResponse, VoiceQueryResponse
from app.services.voice_query_service import (
    PrescriptionNotFoundError,
    VoiceQueryService,
)

logger = logging.getLogger("medication_accessibility.endpoints.voice")

router = APIRouter(prefix="/voice", tags=["voice"])


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid or empty audio"},
        415: {"model": ErrorResponse, "description": "Unsupported language"},
        500: {"model": ErrorResponse, "description": "Transcription service failure"},
    },
)
async def transcribe_speech(
    request: Request,
    file: UploadFile,
    language: Annotated[str, Form()] = "en-IN",
    stt_port: Annotated[SpeechToTextPort, Depends(get_stt_port)] = None,  # type: ignore[assignment]
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> TranscribeResponse:
    """Transcribe spoken audio bytes to text using SpeechToTextPort."""
    req_id = x_request_id or request.headers.get("X-Request-ID") or str(uuid.uuid4())

    try:
        audio_bytes = await file.read()
        mime_type = file.content_type or "audio/mpeg"

        result = await stt_port.transcribe_audio(
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            language_code=language,
        )

        return TranscribeResponse(
            success=True,
            transcript=result.text,
            language=result.language,
            confidence=result.confidence,
            request_id=req_id,
        )

    except EmptyAudioError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="EMPTY_AUDIO_PAYLOAD",
                    message="Uploaded audio file is empty.",
                    details=[ErrorDetail(field="file", reason=str(exc))],
                    request_id=req_id,
                    safe_action_required="RETRY_CAPTURE",
                )
            ).model_dump(mode="json"),
        ) from exc

    except UnsupportedLanguageError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="UNSUPPORTED_LANGUAGE",
                    message=str(exc),
                    details=[],
                    request_id=req_id,
                    safe_action_required="RETRY_CAPTURE",
                )
            ).model_dump(mode="json"),
        ) from exc

    except TranscribeError as exc:
        logger.error("Transcription error: %s", str(exc), extra={"request_id": req_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="TRANSCRIBE_UNAVAILABLE",
                    message="Speech recognition service is currently unavailable. Please retry.",
                    details=[],
                    request_id=req_id,
                    safe_action_required="CONSULT_PHARMACIST",
                )
            ).model_dump(mode="json"),
        ) from exc


@router.post(
    "/query",
    response_model=VoiceQueryResponse,
    status_code=status.HTTP_200_OK,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid audio input"},
        404: {"model": ErrorResponse, "description": "Prescription not found"},
        500: {"model": ErrorResponse, "description": "Processing failure"},
    },
)
async def query_prescription_voice(
    request: Request,
    file: UploadFile,
    prescription_id: Annotated[str, Form()],
    language: Annotated[str, Form()] = "en-IN",
    voice_service: Annotated[VoiceQueryService, Depends(get_voice_query_service)] = None,  # type: ignore[assignment]
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> VoiceQueryResponse:
    """End-to-end voice posology query against existing verified prescription data."""
    req_id = x_request_id or request.headers.get("X-Request-ID") or str(uuid.uuid4())

    try:
        audio_bytes = await file.read()
        mime_type = file.content_type or "audio/mpeg"

        return await voice_service.execute_voice_query(
            prescription_id=prescription_id,
            audio_bytes=audio_bytes,
            mime_type=mime_type,
            language=language,
            request_id=req_id,
        )

    except PrescriptionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="PRESCRIPTION_NOT_FOUND",
                    message=f"Prescription '{prescription_id}' was not found.",
                    details=[],
                    request_id=req_id,
                    safe_action_required="CONSULT_PHARMACIST",
                )
            ).model_dump(mode="json"),
        ) from exc

    except EmptyAudioError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="EMPTY_AUDIO_PAYLOAD",
                    message="Uploaded voice audio is empty.",
                    details=[],
                    request_id=req_id,
                    safe_action_required="RETRY_CAPTURE",
                )
            ).model_dump(mode="json"),
        ) from exc

    except UnsupportedLanguageError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="UNSUPPORTED_LANGUAGE",
                    message=str(exc),
                    details=[],
                    request_id=req_id,
                    safe_action_required="RETRY_CAPTURE",
                )
            ).model_dump(mode="json"),
        ) from exc

    except Exception as exc:
        logger.error("Voice query failed: %s", str(exc), extra={"request_id": req_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="VOICE_QUERY_ERROR",
                    message="An error occurred while answering your voice query. Please retry.",
                    details=[],
                    request_id=req_id,
                    safe_action_required="CONSULT_PHARMACIST",
                )
            ).model_dump(mode="json"),
        ) from exc
