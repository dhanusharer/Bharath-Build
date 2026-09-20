"""Object Storage Port Interface.

Defines the abstract contract for binary object storage operations (such as Amazon S3),
isolating the domain and application layers from specific cloud storage SDKs.
"""

from abc import ABC, abstractmethod


class ObjectStoragePort(ABC):
    """Abstract port for storing, retrieving, and managing binary artifacts."""

    @abstractmethod
    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload a binary object and return its canonical storage reference key.

        Args:
            key: Target object key/path in storage.
            data: Raw binary content to store.
            content_type: MIME type of the payload.
            metadata: Optional user metadata key-value pairs.

        Returns:
            str: Persisted object key.

        Raises:
            StorageError: On storage failure.
        """
        ...

    @abstractmethod
    def get_object(self, key: str) -> bytes:
        """Retrieve raw binary content for a given object key.

        Args:
            key: Object key to retrieve.

        Returns:
            bytes: Binary content of the object.

        Raises:
            StorageNotFoundError: When the object does not exist.
            StorageError: On read failure.
        """
        ...

    @abstractmethod
    def delete_object(self, key: str) -> bool:
        """Delete an object by key.

        Args:
            key: Target object key.

        Returns:
            bool: True if deletion succeeded.

        Raises:
            StorageError: On deletion failure.
        """
        ...

    @abstractmethod
    def generate_presigned_url(
        self,
        key: str,
        expiration_seconds: int = 900,
    ) -> str:
        """Generate a time-limited secure read URL without exposing bucket credentials.

        Args:
            key: Target object key.
            expiration_seconds: Lifetime of URL in seconds.

        Returns:
            str: Secure pre-signed URL.

        Raises:
            StorageError: On URL generation failure.
        """
        ...
