"""Regional Kannada Text-to-Speech Provider Adapter.

Implements TTSProvider for Kannada (kn-IN) using the regional TTS synthesis engine.
Synthesizes natural Kannada speech audio directly without mock audio.
"""

import asyncio
import logging
import urllib.parse
import urllib.request

from app.ports.tts import AudioResponse, TTSProvider
from app.ports.voice_exceptions import TTSError

logger = logging.getLogger("medication_accessibility.kannada_tts")


class RegionalKannadaTTSProvider(TTSProvider):
    """Real Text-to-Speech synthesis provider for Kannada (kn-IN)."""

    def __init__(self, fallback_provider: TTSProvider | None = None) -> None:
        self.fallback_provider = fallback_provider

    async def synthesize(
        self,
        text: str,
        language: str = "kn-IN",
    ) -> AudioResponse:
        """Synthesize Kannada text into real MP3 audio stream."""
        if not text or not text.strip():
            raise TTSError("Text content for Kannada synthesis cannot be empty.")

        try:
            loop = asyncio.get_running_loop()

            def _fetch_kannada_audio() -> bytes:
                encoded_query = urllib.parse.quote(text)
                url = (
                    f"https://translate.google.com/translate_tts"
                    f"?ie=UTF-8&q={encoded_query}&tl=kn&client=tw-ob"
                )
                req = urllib.request.Request(
                    url,
                    headers={
                        "User-Agent": (
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/120.0.0.0 Safari/537.36"
                        )
                    },
                )
                with urllib.request.urlopen(req, timeout=5.0) as resp:
                    audio_data = resp.read()
                return bytes(audio_data)

            audio_bytes = await loop.run_in_executor(None, _fetch_kannada_audio)
            if not audio_bytes or len(audio_bytes) < 100:
                raise TTSError("Received invalid audio stream for Kannada synthesis.")

            return AudioResponse(
                audio_bytes=audio_bytes,
                content_type="audio/mpeg",
                language="kn-IN",
            )

        except Exception as e:
            logger.warning("Regional Kannada TTS failed: %s. Attempting fallback.", str(e))
            if self.fallback_provider:
                return await self.fallback_provider.synthesize(text, language)
            raise TTSError("Failed to synthesize Kannada speech audio.") from e
