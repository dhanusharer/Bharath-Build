"""Amazon Transcribe Speech-to-Text Provider Adapter.

Implements SpeechToTextPort using Amazon Transcribe and S3 staging.
Does not leak raw AWS exceptions or internal stack traces to the caller.
"""

import asyncio
import json
import logging
import urllib.request
import uuid
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from app.ports.storage import ObjectStoragePort
from app.ports.stt import SpeechToTextPort, TranscriptResult
from app.ports.voice_exceptions import (
    EmptyAudioError,
    TranscribeError,
    UnsupportedLanguageError,
)

logger = logging.getLogger("medication_accessibility.transcribe")

SUPPORTED_LANGUAGES = {
    "en-IN": "en-IN",
    "hi-IN": "hi-IN",
    "kn-IN": "kn-IN",
    "en": "en-IN",
    "hi": "hi-IN",
    "kn": "kn-IN",
}

MIME_TO_FORMAT = {
    "audio/mpeg": "mp3",
    "audio/mp3": "mp3",
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
    "audio/webm": "webm",
}


class AmazonTranscribeProvider(SpeechToTextPort):
    """Amazon Transcribe implementation of SpeechToTextPort."""

    def __init__(
        self,
        storage_port: ObjectStoragePort,
        region_name: str = "ap-south-1",
        bucket_name: str | None = None,
        transcribe_client: Any = None,
    ) -> None:
        self.storage = storage_port
        self.region_name = region_name
        self.bucket_name = bucket_name or getattr(storage_port, "bucket_name", None)
        self._client = transcribe_client

    @property
    def client(self) -> Any:
        """Lazy-initialize boto3 Transcribe client."""
        if self._client is None:
            boto_config = Config(
                region_name=self.region_name,
                retries={"max_attempts": 2, "mode": "standard"},
            )
            self._client = boto3.client(
                "transcribe",
                region_name=self.region_name,
                config=boto_config,
            )
        return self._client

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,
        language_code: str = "en-IN",
    ) -> TranscriptResult:
        """Transcribe audio via Amazon Transcribe service."""
        # 1. Validate payload
        if not audio_bytes or len(audio_bytes) == 0:
            raise EmptyAudioError("Audio payload is empty.")

        norm_lang = SUPPORTED_LANGUAGES.get(language_code)
        if not norm_lang:
            raise UnsupportedLanguageError(
                f"Language '{language_code}' is not supported. Supported: en-IN, hi-IN, kn-IN."
            )

        media_format = MIME_TO_FORMAT.get(mime_type.lower().strip(), "mp3")

        # 2. Stage audio in S3
        job_id = uuid.uuid4().hex
        s3_key = f"transcribe-staging/{job_id}.{media_format}"
        try:
            self.storage.put_object(
                key=s3_key,
                data=audio_bytes,
                content_type=mime_type,
            )
        except Exception as e:
            logger.error("Failed to stage audio in S3 for transcription: %s", str(e))
            raise TranscribeError("Unable to stage audio for speech recognition.") from e

        if not self.bucket_name:
            raise TranscribeError("Storage bucket name is required for Transcribe.")

        media_uri = f"s3://{self.bucket_name}/{s3_key}"
        job_name = f"medassist-stt-{job_id}"

        # 3. Start Transcribe Job
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None,
                lambda: self.client.start_transcription_job(
                    TranscriptionJobName=job_name,
                    Media={"MediaFileUri": media_uri},
                    MediaFormat=media_format,
                    LanguageCode=norm_lang,
                ),
            )
        except NoCredentialsError as e:
            raise TranscribeError("AWS credentials not configured for Transcribe.") from e
        except ClientError as e:
            logger.error("Transcribe start job failed: %s", str(e))
            raise TranscribeError("Failed to initiate transcription job.") from e

        # 4. Poll for completion with bounded timeout (max 45s)
        try:
            transcript_text = ""
            confidence: float | None = None
            max_attempts = 30
            poll_interval = 1.5

            for _ in range(max_attempts):
                await asyncio.sleep(poll_interval)
                status_resp = await loop.run_in_executor(
                    None,
                    lambda: self.client.get_transcription_job(TranscriptionJobName=job_name),
                )
                job = status_resp.get("TranscriptionJob", {})
                job_status = job.get("TranscriptionJobStatus")

                if job_status == "COMPLETED":
                    transcript_uri = job.get("Transcript", {}).get("TranscriptFileUri")
                    if transcript_uri:
                        # Fetch transcript content
                        req = urllib.request.Request(transcript_uri)
                        with urllib.request.urlopen(req) as resp:
                            data = json.loads(resp.read().decode("utf-8"))
                            results = data.get("results", {})
                            transcripts = results.get("transcripts", [])
                            if transcripts:
                                transcript_text = transcripts[0].get("transcript", "").strip()

                            # Calculate average item confidence if available
                            items = results.get("items", [])
                            confidences = [
                                float(it["alternatives"][0]["confidence"])
                                for it in items
                                if it.get("alternatives") and "confidence" in it["alternatives"][0]
                            ]
                            if confidences:
                                confidence = sum(confidences) / len(confidences)
                    break

                if job_status == "FAILED":
                    reason = job.get("FailureReason", "Unknown transcription error")
                    logger.error("Transcribe job failed: %s", reason)
                    raise TranscribeError(f"Transcription failed: {reason}")

            if not transcript_text and job_status != "COMPLETED":
                raise TranscribeError("Transcription timed out.")

            return TranscriptResult(
                text=transcript_text,
                language=norm_lang,
                confidence=confidence,
            )

        finally:
            # 5. Cleanup temporary S3 staging object & Transcribe job asynchronously
            try:
                self.storage.delete_object(s3_key)
            except Exception:
                pass
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.client.delete_transcription_job(TranscriptionJobName=job_name),
                )
            except Exception:
                pass
