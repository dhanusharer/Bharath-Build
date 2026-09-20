"""Vision Extraction Port Interface.

Defines the abstract contract for multimodal prescription extraction providers.
Domain and application layers depend exclusively on this port without any
dependency on AWS SDK or cloud provider specifics.
"""

from abc import ABC, abstractmethod

from app.schemas.prescription import RawPrescriptionExtraction


class VisionExtractionPort(ABC):
    """Abstract interface port for multimodal vision extraction."""

    @abstractmethod
    def extract(
        self,
        image_bytes: bytes,
        mime_type: str,
        request_id: str | None = None,
    ) -> RawPrescriptionExtraction:
        """Extract structured raw prescription data from raw image bytes.

        Args:
            image_bytes: Raw binary image payload.
            mime_type: MIME type of the image (image/jpeg, image/png, image/webp).
            request_id: Optional correlation tracking identifier.

        Returns:
            RawPrescriptionExtraction: Strongly-typed raw extraction payload.

        Raises:
            BedrockExtractionError: Safe application-level error on extraction failure.
        """
        ...
