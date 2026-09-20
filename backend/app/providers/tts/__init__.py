"""TTS provider package."""

from app.providers.tts.mock import MockTTSProvider
from app.providers.tts.polly import AmazonPollyTTSProvider

__all__ = ["AmazonPollyTTSProvider", "MockTTSProvider"]
