"""Prescription Ingestion and Retrieval Endpoints.

Routes:
- POST /api/v1/prescriptions: Upload image, store in S3, extract, safety-gate, persist.
- GET  /api/v1/prescriptions/{prescription_id}: Retrieve latest processing state and medications.
"""

import logging
import uuid
from typing import Annotated

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    UploadFile,
    status,
)

from app.api.dependencies import get_ingestion_service
from app.providers.bedrock.exceptions import BedrockExtractionError
from app.providers.storage.exceptions import StorageError
from app.schemas.error import ErrorBody, ErrorDetail, ErrorResponse
from app.schemas.ingestion import PrescriptionIngestionResponse
from app.services.prescription_ingestion import (
    IngestionValidationError,
    PrescriptionIngestionService,
)

logger = logging.getLogger("medication_accessibility.endpoints.prescriptions")

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.post(
    "",
    response_model=PrescriptionIngestionResponse,
    status_code=status.HTTP_201_CREATED,
    responses={
        400: {"model": ErrorResponse, "description": "Invalid image payload or empty file"},
        413: {"model": ErrorResponse, "description": "File size limit exceeded"},
        422: {"model": ErrorResponse, "description": "Extraction or normalization unprocessable"},
        500: {"model": ErrorResponse, "description": "Internal storage or provider failure"},
    },
)
async def upload_and_process_prescription(
    request: Request,
    file: UploadFile,
    ingestion_service: Annotated[PrescriptionIngestionService, Depends(get_ingestion_service)],
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> PrescriptionIngestionResponse:
    """Accept multipart prescription image upload, execute end-to-end ingestion and persistence."""
    req_id = x_request_id or request.headers.get("X-Request-ID") or str(uuid.uuid4())

    try:
        # Read file contents safely
        file_bytes = await file.read()
        file_name = file.filename or "prescription_upload.jpg"
        content_type = file.content_type or "application/octet-stream"

        return await ingestion_service.ingest_prescription(
            image_bytes=file_bytes,
            file_name=file_name,
            mime_type=content_type,
            request_id=req_id,
            idempotency_key=idempotency_key,
        )

    except IngestionValidationError as exc:
        if exc.code == "FILE_SIZE_EXCEEDED":
            status_code = status.HTTP_413_CONTENT_TOO_LARGE
        elif exc.code == "UNSUPPORTED_MEDIA_TYPE":
            status_code = status.HTTP_415_UNSUPPORTED_MEDIA_TYPE
        else:
            status_code = status.HTTP_400_BAD_REQUEST
        raise HTTPException(
            status_code=status_code,
            detail=ErrorResponse(
                error=ErrorBody(
                    code=exc.code,
                    message=exc.message,
                    details=[ErrorDetail(field="file", reason=exc.message)],
                    request_id=req_id,
                    safe_action_required="CONSULT_PHARMACIST",
                )
            ).model_dump(mode="json"),
        ) from exc

    except StorageError as exc:
        # Sanitized error response - never leak raw AWS S3 error
        logger.error(
            "Storage failure during prescription upload: %s",
            str(exc),
            extra={"request_id": req_id},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="STORAGE_UNAVAILABLE",
                    message="An error occurred while securely storing the image. Please retry.",
                    details=[],
                    request_id=req_id,
                    safe_action_required="CONSULT_PHARMACIST",
                )
            ).model_dump(mode="json"),
        ) from exc

    except BedrockExtractionError as exc:
        # Sanitized extraction error - never leak provider internals
        logger.error("Provider extraction failure: %s", str(exc), extra={"request_id": req_id})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="EXTRACTION_FAILED",
                    message="Failed to extract text. Please try again with a clearer image.",
                    details=[],
                    request_id=req_id,
                    safe_action_required="CONSULT_PHARMACIST",
                )
            ).model_dump(mode="json"),
        ) from exc


@router.get(
    "/{prescription_id}",
    response_model=PrescriptionIngestionResponse,
    status_code=status.HTTP_200_OK,
    responses={
        404: {"model": ErrorResponse, "description": "Prescription record not found"},
    },
)
async def get_prescription(
    request: Request,
    prescription_id: str,
    ingestion_service: Annotated[PrescriptionIngestionService, Depends(get_ingestion_service)],
    x_request_id: Annotated[str | None, Header(alias="X-Request-ID")] = None,
) -> PrescriptionIngestionResponse:
    """Retrieve the latest persisted processing state and normalized result for a prescription."""
    req_id = x_request_id or request.headers.get("X-Request-ID") or str(uuid.uuid4())

    result = await ingestion_service.get_prescription(
        prescription_id=prescription_id,
        request_id=req_id,
    )
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=ErrorResponse(
                error=ErrorBody(
                    code="PRESCRIPTION_NOT_FOUND",
                    message=f"Prescription with ID '{prescription_id}' was not found.",
                    details=[ErrorDetail(field="prescription_id", reason="Not found")],
                    request_id=req_id,
                    safe_action_required="CONSULT_PHARMACIST",
                )
            ).model_dump(mode="json"),
        )
    return result
