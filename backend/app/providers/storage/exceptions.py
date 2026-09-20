"""Storage Provider Exceptions.

Safe application exceptions for object storage operations.
"""


class StorageError(Exception):
    """Base exception for all storage provider failures."""

    def __init__(
        self,
        message: str,
        error_code: str = "STORAGE_ERROR",
        key: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.key = key

    def __str__(self) -> str:
        key_suffix = f" (Key: {self.key})" if self.key else ""
        return f"[{self.error_code}] {self.message}{key_suffix}"


class StorageNotFoundError(StorageError):
    """Raised when an object is not found in storage."""

    def __init__(self, key: str) -> None:
        super().__init__(
            message=f"Object not found in storage: '{key}'.",
            error_code="STORAGE_OBJECT_NOT_FOUND",
            key=key,
        )


class StorageUploadError(StorageError):
    """Raised when an upload to storage fails."""

    def __init__(self, key: str, details: str) -> None:
        super().__init__(
            message=f"Failed to upload object: {details}",
            error_code="STORAGE_UPLOAD_FAILED",
            key=key,
        )


class StorageAuthError(StorageError):
    """Raised when storage credentials or permissions are invalid."""

    def __init__(self, message: str = "Storage authentication failure.") -> None:
        super().__init__(
            message=message,
            error_code="STORAGE_AUTH_FAILURE",
        )
