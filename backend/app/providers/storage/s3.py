"""Amazon S3 Object Storage Provider Adapter.

Implements the ObjectStoragePort interface for managing prescription images.
Never exposes raw bucket credentials or permanent bucket URLs to clients.
"""

import logging
import uuid
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError, PartialCredentialsError

from app.ports.storage import ObjectStoragePort
from app.providers.storage.exceptions import (
    StorageAuthError,
    StorageError,
    StorageNotFoundError,
    StorageUploadError,
)

logger = logging.getLogger("medication_accessibility.storage")

SUPPORTED_MIME_TYPES: tuple[str, ...] = (
    "image/jpeg",
    "image/png",
    "image/webp",
)


def generate_prescription_s3_key(prescription_id: str, file_extension: str) -> str:
    """Generate a safe, collision-resistant, non-user-controlled S3 object key.

    Guarantees no user-supplied directory traversal.
    Format: prescriptions/{prescription_id}/{random_uuid}.{clean_ext}
    """
    clean_id = prescription_id.replace("/", "").replace("\\", "").replace("..", "")
    clean_ext = file_extension.lstrip(".").lower().replace("/", "").replace("\\", "")
    unique_file_id = uuid.uuid4().hex
    return f"prescriptions/{clean_id}/{unique_file_id}.{clean_ext}"


class S3ObjectStorage(ObjectStoragePort):
    """Concrete Amazon S3 adapter implementing ObjectStoragePort."""

    def __init__(
        self,
        bucket_name: str,
        region_name: str = "ap-south-1",
        client: Any = None,
    ) -> None:
        self.bucket_name = bucket_name
        self.region_name = region_name
        self._client = client

    @property
    def client(self) -> Any:
        """Lazy-initialize boto3 S3 client."""
        if self._client is None:
            boto_config = Config(
                region_name=self.region_name,
                signature_version="s3v4",
                retries={"max_attempts": 2, "mode": "standard"},
            )
            self._client = boto3.client(
                "s3",
                region_name=self.region_name,
                config=boto_config,
            )
        return self._client

    def put_object(
        self,
        key: str,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> str:
        """Upload binary data to S3."""
        extra_args: dict[str, Any] = {"ContentType": content_type}
        if metadata:
            extra_args["Metadata"] = metadata

        try:
            self.client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=data,
                **extra_args,
            )
            logger.info(
                "Successfully stored object in S3",
                extra={"key": key, "bucket": self.bucket_name, "size_bytes": len(data)},
            )
            return key

        except (NoCredentialsError, PartialCredentialsError) as e:
            raise StorageAuthError("AWS credentials not found for S3.") from e

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("AccessDenied", "UnauthorizedOperation"):
                raise StorageAuthError(f"Access denied writing to bucket '{self.bucket_name}'.") from e
            raise StorageUploadError(key=key, details=f"S3 ClientError [{error_code}]") from e

        except Exception as e:
            raise StorageUploadError(key=key, details=str(e)) from e

    def get_object(self, key: str) -> bytes:
        """Fetch raw binary object from S3."""
        try:
            response = self.client.get_object(Bucket=self.bucket_name, Key=key)
            data: bytes = response["Body"].read()
            return data

        except (NoCredentialsError, PartialCredentialsError) as e:
            raise StorageAuthError("AWS credentials not found for S3.") from e

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise StorageNotFoundError(key=key) from e
            if error_code in ("AccessDenied", "UnauthorizedOperation"):
                raise StorageAuthError(f"Access denied reading from bucket '{self.bucket_name}'.") from e
            raise StorageError(f"S3 get_object failed: [{error_code}]", key=key) from e

        except Exception as e:
            raise StorageError(f"Failed to retrieve object: {e}", key=key) from e

    def delete_object(self, key: str) -> bool:
        """Delete an object from S3."""
        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            return True

        except (NoCredentialsError, PartialCredentialsError) as e:
            raise StorageAuthError("AWS credentials not found for S3.") from e

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            raise StorageError(f"S3 delete_object failed: [{error_code}]", key=key) from e

    def generate_presigned_url(
        self,
        key: str,
        expiration_seconds: int = 900,
    ) -> str:
        """Generate a secure, time-limited presigned GET URL."""
        try:
            url = self.client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket_name, "Key": key},
                ExpiresIn=expiration_seconds,
            )
            return str(url)

        except Exception as e:
            raise StorageError(f"Failed to generate presigned URL: {e}", key=key) from e
