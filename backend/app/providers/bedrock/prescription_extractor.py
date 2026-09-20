"""Bedrock Multimodal Prescription Extractor Adapter.

Implements the VisionExtractionPort using Amazon Bedrock Runtime Converse API
with structured tool-use output constraints.
"""

import json
import logging
import time
from typing import Any

from botocore.exceptions import (
    ClientError,
    ConnectTimeoutError,
    NoCredentialsError,
    PartialCredentialsError,
    ReadTimeoutError,
)
from pydantic import ValidationError

from app.ports.prescription_extractor import VisionExtractionPort
from app.providers.bedrock.client import create_bedrock_runtime_client
from app.providers.bedrock.config import SUPPORTED_MIME_TYPES, BedrockProviderConfig
from app.providers.bedrock.exceptions import (
    BedrockAccessDeniedError,
    BedrockAuthError,
    BedrockExtractionError,
    BedrockModelUnavailableError,
    BedrockThrottlingError,
    BedrockTimeoutError,
    EmptyImageError,
    MalformedResponseError,
    SchemaValidationError,
    UnexpectedProviderError,
    UnsupportedImageTypeError,
)
from app.providers.bedrock.prompts import EXTRACTION_SYSTEM_PROMPT, EXTRACTION_USER_PROMPT
from app.schemas.prescription import RawPrescriptionExtraction

logger = logging.getLogger("medication_accessibility.bedrock")


class BedrockPrescriptionExtractor(VisionExtractionPort):
    """Concrete Bedrock Runtime adapter for prescription vision extraction."""

    def __init__(
        self,
        config: BedrockProviderConfig | None = None,
        client: Any = None,
    ) -> None:
        self.config = config or BedrockProviderConfig()
        self._client = client

    @property
    def client(self) -> Any:
        """Lazy-initialize Bedrock runtime client."""
        if self._client is None:
            self._client = create_bedrock_runtime_client(self.config)
        return self._client

    def _build_tool_spec(self) -> dict[str, Any]:
        """Construct the Converse API tool specification bound to the Pydantic schema."""
        schema = RawPrescriptionExtraction.model_json_schema()
        return {
            "toolSpec": {
                "name": "record_prescription_extraction",
                "description": (
                    "Record structured raw prescription extraction fields observed from the image."
                ),
                "inputSchema": {
                    "json": schema,
                },
            }
        }

    def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
        request_id: str | None = None,
    ) -> RawPrescriptionExtraction:
        """Extract structured raw prescription from image bytes via Bedrock Runtime."""
        start_time = time.perf_counter()

        # 1. Validate image payload
        if not image_bytes:
            logger.warning("Empty image payload received", extra={"request_id": request_id})
            raise EmptyImageError(request_id=request_id)

        clean_mime = mime_type.strip().lower()
        if clean_mime not in SUPPORTED_MIME_TYPES:
            logger.warning(
                "Unsupported MIME type: %s", clean_mime, extra={"request_id": request_id}
            )
            raise UnsupportedImageTypeError(mime_type=clean_mime, request_id=request_id)

        image_format = SUPPORTED_MIME_TYPES[clean_mime]
        tool_spec = self._build_tool_spec()

        try:
            # 2. Invoke Bedrock Converse API with structured tool schema
            response = self.client.converse(
                modelId=self.config.model_id,
                system=[{"text": EXTRACTION_SYSTEM_PROMPT}],
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "image": {
                                    "format": image_format,
                                    "source": {"bytes": image_bytes},
                                }
                            },
                            {"text": EXTRACTION_USER_PROMPT},
                        ],
                    }
                ],
                inferenceConfig={
                    "temperature": self.config.temperature,
                    "maxTokens": self.config.max_tokens,
                },
                toolConfig={
                    "tools": [tool_spec],
                    "toolChoice": {
                        "tool": {"name": "record_prescription_extraction"},
                    },
                },
            )

            # 3. Parse and extract structured payload
            raw_dict = self._extract_payload_from_response(response, request_id)

            # 4. Validate through canonical Pydantic model
            raw_extraction = RawPrescriptionExtraction.model_validate(raw_dict)

            latency_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Bedrock extraction succeeded",
                extra={
                    "request_id": request_id,
                    "provider": "bedrock",
                    "model_id": self.config.model_id,
                    "latency_ms": round(latency_ms, 2),
                    "medications_count": len(raw_extraction.medications),
                    "success": True,
                },
            )
            return raw_extraction

        except (NoCredentialsError, PartialCredentialsError) as e:
            self._log_failure(start_time, "BEDROCK_AUTH_FAILURE", request_id)
            raise BedrockAuthError(request_id=request_id) from e

        except (ConnectTimeoutError, ReadTimeoutError) as e:
            self._log_failure(start_time, "BEDROCK_TIMEOUT", request_id)
            raise BedrockTimeoutError(
                timeout_seconds=self.config.timeout_seconds,
                request_id=request_id,
            ) from e

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            self._log_failure(start_time, error_code, request_id)

            if error_code in ("AccessDeniedException", "UnauthorizedException"):
                raise BedrockAccessDeniedError(
                    model_id=self.config.model_id,
                    request_id=request_id,
                ) from e

            if error_code in (
                "ThrottlingException",
                "RequestLimitExceeded",
                "TooManyRequestsException",
            ):
                raise BedrockThrottlingError(request_id=request_id) from e

            if error_code in (
                "ResourceNotFoundException",
                "ModelNotReadyException",
                "ModelNotAvailableException",
            ):
                raise BedrockModelUnavailableError(
                    model_id=self.config.model_id,
                    request_id=request_id,
                ) from e

            if error_code == "ValidationException":
                # Check for model not supported in region or parameter issues
                err_msg = e.response.get("Error", {}).get("Message", "")
                if "model" in err_msg.lower() or "not supported" in err_msg.lower():
                    raise BedrockModelUnavailableError(
                        model_id=self.config.model_id,
                        request_id=request_id,
                    ) from e

            raise UnexpectedProviderError(
                details=f"AWS ClientError [{error_code}]",
                request_id=request_id,
            ) from e

        except ValidationError as e:
            self._log_failure(start_time, "SCHEMA_VALIDATION_FAILURE", request_id)
            raise SchemaValidationError(
                details=str(e),
                request_id=request_id,
            ) from e

        except BedrockExtractionError:
            raise

        except Exception as e:
            self._log_failure(start_time, "UNEXPECTED_ERROR", request_id)
            raise UnexpectedProviderError(
                details=f"Internal extraction error: {type(e).__name__}",
                request_id=request_id,
            ) from e

    def _extract_payload_from_response(
        self,
        response: dict[str, Any],
        request_id: str | None,
    ) -> dict[str, Any]:
        """Extract structured dictionary from Bedrock Converse response."""
        output_message = response.get("output", {}).get("message", {})
        content_blocks = output_message.get("content", [])

        # Priority 1: Check toolUse block (Structured output)
        for block in content_blocks:
            if "toolUse" in block:
                tool_input = block["toolUse"].get("input")
                if isinstance(tool_input, dict):
                    return tool_input
                if isinstance(tool_input, str):
                    try:
                        parsed = json.loads(tool_input)
                        if isinstance(parsed, dict):
                            return parsed
                    except json.JSONDecodeError as e:
                        raise MalformedResponseError(
                            details="Tool input string could not be decoded as JSON",
                            request_id=request_id,
                        ) from e

        # Priority 2: Fallback to text block JSON parsing
        for block in content_blocks:
            if "text" in block:
                text_content = block["text"].strip()
                try:
                    parsed = json.loads(text_content)
                    if isinstance(parsed, dict):
                        return parsed
                except json.JSONDecodeError:
                    continue

        raise MalformedResponseError(
            details="Response did not contain valid structured tool input or JSON text block",
            request_id=request_id,
        )

    def _log_failure(self, start_time: float, error_category: str, request_id: str | None) -> None:
        """Record structured observability log on failure without exposing sensitive data."""
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Bedrock extraction failed",
            extra={
                "request_id": request_id,
                "provider": "bedrock",
                "model_id": self.config.model_id,
                "latency_ms": round(latency_ms, 2),
                "error_category": error_category,
                "success": False,
            },
        )
