"""Safe Application-Level Bedrock Provider Exceptions.

Ensures raw AWS SDK exceptions, stack traces, and internal cloud details are never
leaked across the provider boundary.
"""


class BedrockExtractionError(Exception):
    """Base exception for all Bedrock provider errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "BEDROCK_EXTRACTION_FAILED",
        request_id: str | None = None,
        retryable: bool = False,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.request_id = request_id
        self.retryable = retryable

    def __str__(self) -> str:
        req_suffix = f" (Request ID: {self.request_id})" if self.request_id else ""
        return f"[{self.error_code}] {self.message}{req_suffix}"


class UnsupportedImageTypeError(BedrockExtractionError):
    """Raised when an unsupported image MIME type is submitted."""

    def __init__(self, mime_type: str, request_id: str | None = None) -> None:
        super().__init__(
            message=f"Unsupported image format '{mime_type}'. Supported formats: JPEG, PNG, WebP.",
            error_code="UNSUPPORTED_IMAGE_TYPE",
            request_id=request_id,
            retryable=False,
        )


class EmptyImageError(BedrockExtractionError):
    """Raised when image bytes payload is empty or zero-length."""

    def __init__(self, request_id: str | None = None) -> None:
        super().__init__(
            message="Image payload is empty. Expected non-empty binary image bytes.",
            error_code="EMPTY_IMAGE_PAYLOAD",
            request_id=request_id,
            retryable=False,
        )


class BedrockAuthError(BedrockExtractionError):
    """Raised on invalid or missing AWS credentials."""

    def __init__(self, request_id: str | None = None) -> None:
        super().__init__(
            message="Bedrock authentication failed. Verify cloud provider credentials.",
            error_code="BEDROCK_AUTH_FAILURE",
            request_id=request_id,
            retryable=False,
        )


class BedrockAccessDeniedError(BedrockExtractionError):
    """Raised when AWS account lacks IAM permissions or model access is not granted."""

    def __init__(self, model_id: str, request_id: str | None = None) -> None:
        super().__init__(
            message=(
                f"Access denied for Bedrock model '{model_id}'. "
                "Check IAM policy and model access permissions."
            ),
            error_code="BEDROCK_ACCESS_DENIED",
            request_id=request_id,
            retryable=False,
        )


class BedrockModelUnavailableError(BedrockExtractionError):
    """Raised when the specified model ID is unavailable or does not exist."""

    def __init__(self, model_id: str, request_id: str | None = None) -> None:
        super().__init__(
            message=f"Bedrock model '{model_id}' is unavailable or not supported in this region.",
            error_code="BEDROCK_MODEL_UNAVAILABLE",
            request_id=request_id,
            retryable=False,
        )


class BedrockThrottlingError(BedrockExtractionError):
    """Raised when API call is rate-limited or quota exceeded."""

    def __init__(self, request_id: str | None = None) -> None:
        super().__init__(
            message="Bedrock API request throttled. Quota exceeded or rate limit reached.",
            error_code="BEDROCK_THROTTLED",
            request_id=request_id,
            retryable=True,
        )


class BedrockTimeoutError(BedrockExtractionError):
    """Raised when Bedrock inference exceeds configured timeout."""

    def __init__(self, timeout_seconds: float, request_id: str | None = None) -> None:
        super().__init__(
            message=f"Bedrock request timed out after {timeout_seconds:.1f} seconds.",
            error_code="BEDROCK_TIMEOUT",
            request_id=request_id,
            retryable=True,
        )


class MalformedResponseError(BedrockExtractionError):
    """Raised when Bedrock returns invalid JSON or unexpected message shape."""

    def __init__(self, details: str, request_id: str | None = None) -> None:
        super().__init__(
            message=f"Malformed model response: {details}",
            error_code="MALFORMED_MODEL_RESPONSE",
            request_id=request_id,
            retryable=False,
        )


class SchemaValidationError(BedrockExtractionError):
    """Raised when model output fails validation against RawPrescriptionExtraction schema."""

    def __init__(self, details: str, request_id: str | None = None) -> None:
        super().__init__(
            message=f"Model output failed raw schema validation: {details}",
            error_code="SCHEMA_VALIDATION_FAILURE",
            request_id=request_id,
            retryable=False,
        )


class UnexpectedProviderError(BedrockExtractionError):
    """Raised on unexpected upstream provider failures."""

    def __init__(self, details: str, request_id: str | None = None) -> None:
        super().__init__(
            message=f"Unexpected Bedrock provider failure: {details}",
            error_code="UNEXPECTED_PROVIDER_ERROR",
            request_id=request_id,
            retryable=False,
        )
