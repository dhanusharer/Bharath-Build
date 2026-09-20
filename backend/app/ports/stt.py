"""Speech-to-Text Port Abstraction.

Defines domain contracts for converting user speech audio into normalized transcripts.
Decouples application logic from AWS Transcribe or third-party STT providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class TranscriptResult:
    """Represents the output of a speech-to-text operation."""

    text: str
    language: str
    confidence: float | None = None
    duration_seconds: float | None = None


class SpeechToTextPort(ABC):
    """Port interface for Speech-to-Text providers."""

    @abstractmethod
    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        language_code: str = "en-IN",
    ) -> TranscriptResult:
        """Transcribe speech audio bytes into text.

        Args:
            audio_bytes: Binary audio data.
            mime_type: MIME type of audio (e.g., audio/mpeg, audio/wav).
            language_code: Language code (e.g., en-IN, hi-IN, kn-IN).

        Returns:
            TranscriptResult with transcript text and metadata.

        Raises:
            TranscribeError: If transcription fails.
            UnsupportedLanguageError: If the requested language is unsupported.
            EmptyAudioError: If the audio payload is empty.
        """
        raise NotImplementedError
