"""Mock and regional in-memory TTS Provider Adapter.

Useful for unit testing, offline development, and regional language fallback (e.g. Kannada).
"""

from app.ports.tts import AudioResponse, TTSProvider
from app.ports.voice_exceptions import TTSError


class MockTTSProvider(TTSProvider):
    """Generates synthetic valid audio payloads for tests and fallback."""

    def __init__(self, sample_bytes: bytes | None = None) -> None:
        # Minimal valid MP3 header bytes for tests
        self.sample_bytes = sample_bytes or (b"\xff\xfb\x90d\x00\x00\x00\x00\x00\x00\x00\x00" * 8)

    async def synthesize(
        self,
        text: str,
        language: str = "en-IN",
    ) -> AudioResponse:
        """Return synthetic audio response without network dependency."""
        if not text or not text.strip():
            raise TTSError("Text content for synthesis cannot be empty.")

        return AudioResponse(
            audio_bytes=self.sample_bytes,
            content_type="audio/mpeg",
            language=language,
            duration_seconds=1.5,
        )
