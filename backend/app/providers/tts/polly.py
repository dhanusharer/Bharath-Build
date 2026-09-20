"""Amazon Polly Text-to-Speech Provider Adapter.

Implements TTSProvider using Amazon Polly.
Supports Hindi (hi-IN) and Indian English (en-IN) via neural voice Kajal.
Delegates unsupported regional languages (e.g., Kannada) to configured regional fallback or mock.
"""

import asyncio
import logging
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from app.ports.tts import AudioResponse, TTSProvider
from app.ports.voice_exceptions import TTSError, UnsupportedLanguageError

logger = logging.getLogger("medication_accessibility.polly")

SUPPORTED_POLLY_LANGUAGES = {
    "hi-IN": {"voice_id": "Kajal", "engine": "neural", "lang_code": "hi-IN"},
    "hi": {"voice_id": "Kajal", "engine": "neural", "lang_code": "hi-IN"},
    "en-IN": {"voice_id": "Kajal", "engine": "neural", "lang_code": "en-IN"},
    "en": {"voice_id": "Kajal", "engine": "neural", "lang_code": "en-IN"},
}


class AmazonPollyTTSProvider(TTSProvider):
    """Amazon Polly implementation of TTSProvider."""

    def __init__(
        self,
        region_name: str = "ap-south-1",
        client: Any = None,
        fallback_provider: TTSProvider | None = None,
    ) -> None:
        self.region_name = region_name
        self._client = client
        self.fallback_provider = fallback_provider

    @property
    def client(self) -> Any:
        """Lazy-initialize boto3 Polly client."""
        if self._client is None:
            boto_config = Config(
                region_name=self.region_name,
                retries={"max_attempts": 2, "mode": "standard"},
            )
            self._client = boto3.client("polly", region_name=self.region_name, config=boto_config)
        return self._client

    async def synthesize(
        self,
        text: str,
        language: str = "en-IN",
    ) -> AudioResponse:
        """Synthesize text to speech audio via Amazon Polly."""
        if not text or not text.strip():
            raise TTSError("Text content for synthesis cannot be empty.")

        norm_lang = language.strip()
        voice_cfg = SUPPORTED_POLLY_LANGUAGES.get(norm_lang)

        # If Polly does not support the language directly (e.g. Kannada), check fallback
        if not voice_cfg:
            if self.fallback_provider:
                logger.info(
                    "Delegating language '%s' to fallback TTS provider.",
                    language,
                )
                return await self.fallback_provider.synthesize(text, language)
            raise UnsupportedLanguageError(
                f"Language '{language}' is not supported by Amazon Polly in {self.region_name}."
            )

        try:
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self.client.synthesize_speech(
                    Text=text,
                    OutputFormat="mp3",
                    VoiceId=voice_cfg["voice_id"],
                    Engine=voice_cfg["engine"],
                    LanguageCode=voice_cfg["lang_code"],
                ),
            )
            stream = response.get("AudioStream")
            if not stream:
                raise TTSError("Polly returned empty audio stream.")

            audio_bytes = stream.read()
            return AudioResponse(
                audio_bytes=audio_bytes,
                content_type="audio/mpeg",
                language=voice_cfg["lang_code"],
            )

        except (NoCredentialsError, ClientError) as e:
            logger.error("Polly speech synthesis failed: %s", str(e))
            raise TTSError("Failed to synthesize speech audio.") from e
