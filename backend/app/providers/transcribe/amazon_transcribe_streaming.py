"""Amazon Transcribe Streaming Speech-to-Text Provider Adapter.

Implements SpeechToTextPort using Amazon Transcribe Streaming (HTTP/2 bidirectional stream).
Transcribes audio directly in memory without S3 staging or asynchronous polling.
Sub-second real-time latency for interactive patient posology inquiries.
"""

import asyncio
import io
import logging
from typing import Any

import boto3
import boto3.session
from botocore.exceptions import NoCredentialsError

from app.ports.stt import SpeechToTextPort, TranscriptResult
from app.ports.voice_exceptions import (
    EmptyAudioError,
    TranscribeError,
    UnsupportedLanguageError,
)

logger = logging.getLogger("medication_accessibility.transcribe_streaming")

SUPPORTED_STREAMING_LANGUAGES = {
    "en-IN": "en-IN",
    "hi-IN": "hi-IN",
    "kn-IN": "kn-IN",
    "en": "en-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
}


def _extract_pcm_or_wav_data(audio_bytes: bytes) -> tuple[bytes, int, str]:
    """Inspect audio header to detect encoding (wav/pcm vs mp3/ogg).

    Amazon Transcribe Streaming supports 'pcm', 'ogg-opus', 'flac'.
    Standard uncompressed 16kHz 16-bit mono WAV payload can be sent as raw PCM
    by stripping the 44-byte RIFF header, or directly if already raw PCM.
    """
    if audio_bytes.startswith(b"RIFF") and len(audio_bytes) > 44:
        # Standard WAV header: bytes 24-27 contain sample rate
        sample_rate = int.from_bytes(audio_bytes[24:28], byteorder="little")
        pcm_data = audio_bytes[44:]
        return pcm_data, sample_rate, "pcm"

    # Default assumed raw 16kHz PCM
    return audio_bytes, 16000, "pcm"


class AmazonTranscribeStreamingProvider(SpeechToTextPort):
    """Real-time streaming speech-to-text provider using amazon-transcribe."""

    def __init__(
        self,
        region_name: str = "ap-south-1",
        session: boto3.session.Session | None = None,
        fallback_batch_provider: SpeechToTextPort | None = None,
    ) -> None:
        self.region_name = region_name
        self._session = session
        self.fallback_batch_provider = fallback_batch_provider

    def _get_credential_resolver(self) -> Any:
        """Create static credential resolver from active boto3 session."""
        from amazon_transcribe.auth import StaticCredentialResolver

        session = self._session or boto3.session.Session()
        creds = session.get_credentials()
        if not creds:
            raise NoCredentialsError()
        frozen = creds.get_frozen_credentials()
        if not frozen.access_key or not frozen.secret_key:
            raise NoCredentialsError()
        return StaticCredentialResolver(
            access_key_id=frozen.access_key,
            secret_access_key=frozen.secret_key,
            session_token=frozen.token,
        )

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        language_code: str = "en-IN",
    ) -> TranscriptResult:
        """Execute real-time streaming speech transcription."""
        if not audio_bytes or len(audio_bytes) == 0:
            raise EmptyAudioError("Audio payload is empty.")

        norm_lang = SUPPORTED_STREAMING_LANGUAGES.get(language_code)
        if not norm_lang:
            raise UnsupportedLanguageError(
                f"Language '{language_code}' is not supported for streaming transcription."
            )

        # If audio is compressed MP3/WebM and ffmpeg is not available,
        # fallback seamlessly to the batch provider if configured
        is_wav_or_pcm = (
            audio_bytes.startswith(b"RIFF")
            or "wav" in mime_type.lower()
            or "pcm" in mime_type.lower()
        )

        if not is_wav_or_pcm:
            if self.fallback_batch_provider:
                logger.info(
                    "Non-PCM audio format '%s' received. Routing to batch provider.",
                    mime_type,
                )
                return await self.fallback_batch_provider.transcribe_audio(
                    audio_bytes=audio_bytes,
                    mime_type=mime_type,
                    language_code=language_code,
                )
            raise TranscribeError(
                f"Streaming transcription requires WAV or PCM audio; received '{mime_type}'."
            )

        pcm_data, sample_rate, encoding = _extract_pcm_or_wav_data(audio_bytes)

        try:
            from amazon_transcribe.client import TranscribeStreamingClient
            from amazon_transcribe.handlers import TranscriptResultStreamHandler
            from amazon_transcribe.model import TranscriptEvent

            resolver = self._get_credential_resolver()
            client = TranscribeStreamingClient(
                region=self.region_name,
                credential_resolver=resolver,
            )

            stream = await client.start_stream_transcription(
                language_code=norm_lang,
                media_sample_rate_hz=sample_rate,
                media_encoding=encoding,
            )

            collected_transcripts: list[str] = []

            class StreamingEventHandler(TranscriptResultStreamHandler):
                async def handle_transcript_event(self, transcript_event: TranscriptEvent) -> None:
                    results = transcript_event.transcript.results
                    for result in results:
                        if not result.is_partial and result.alternatives:
                            for alt in result.alternatives:
                                if alt.transcript:
                                    collected_transcripts.append(alt.transcript)

            handler = StreamingEventHandler(stream.output_stream)

            async def write_audio_chunks() -> None:
                chunk_size = 1024 * 4
                buffer = io.BytesIO(pcm_data)
                while True:
                    chunk = buffer.read(chunk_size)
                    if not chunk:
                        break
                    await stream.input_stream.send_audio_event(audio_chunk=chunk)
                    await asyncio.sleep(0.005)
                await stream.input_stream.end_stream()

            # Wait with bounded 10s timeout
            await asyncio.wait_for(
                asyncio.gather(
                    write_audio_chunks(),
                    handler.handle_events(),
                ),
                timeout=10.0,
            )

            final_text = " ".join(collected_transcripts).strip()
            if not final_text and self.fallback_batch_provider:
                logger.info("Streaming transcript was empty. Attempting batch fallback.")
                return await self.fallback_batch_provider.transcribe_audio(
                    audio_bytes=audio_bytes,
                    mime_type=mime_type,
                    language_code=language_code,
                )

            return TranscriptResult(
                text=final_text,
                language=norm_lang,
                confidence=0.95 if final_text else None,
            )

        except (NoCredentialsError, Exception) as e:
            logger.warning(
                "Streaming transcription failed or timed out: %s. Trying batch fallback.",
                str(e),
            )
            if self.fallback_batch_provider:
                return await self.fallback_batch_provider.transcribe_audio(
                    audio_bytes=audio_bytes,
                    mime_type=mime_type,
                    language_code=language_code,
                )
            raise TranscribeError("Streaming speech recognition failed.") from e
