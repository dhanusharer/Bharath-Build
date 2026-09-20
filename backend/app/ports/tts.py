"""Text-to-Speech Port Abstraction.

Defines domain contracts for converting text to synthesized audio streams.
Decouples application logic from AWS Polly or regional TTS providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class AudioResponse:
    """Represents synthesized audio output."""

    audio_bytes: bytes
    content_type: str
    language: str
    duration_seconds: float | None = None


class TTSProvider(ABC):
    """Port interface for Text-to-Speech providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str = "en-IN",
    ) -> AudioResponse:
        """Synthesize text into speech audio.

        Args:
            text: Plain text content to synthesize.
            language: Target language code (e.g. en-IN, hi-IN, kn-IN).

        Returns:
            AudioResponse containing binary audio data.

        Raises:
            TTSError: If speech synthesis fails.
        """
        raise NotImplementedError
