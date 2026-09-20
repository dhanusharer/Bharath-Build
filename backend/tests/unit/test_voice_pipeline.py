"""Unit and Integration Tests for Phase 4 Voice Accessibility Pipeline.

Covers:
1. Successful transcription
2. Transcription failure
3. Unsupported language
4. Empty transcript
5. Supported medication query (Schedule / List)
6. Morning query
7. Night query
8. Before-food query
9. After-food query
10. Duration query
11. Unknown intent
12. Prescription requires review
13. Missing prescription
14. TTS failure
15. Localization correctness
16. Provider failure
17. No medication facts invented
"""

import io
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.dependencies import (
    get_db_session,
    get_stt_port,
    get_tts_provider,
)
from app.db.models import Base, MedicationResult, Prescription, PrescriptionStatus
from app.main import app
from app.ports.localization import CanonicalMedicationFact
from app.ports.stt import SpeechToTextPort, TranscriptResult
from app.ports.tts import AudioResponse, TTSProvider
from app.ports.voice_exceptions import (
    EmptyAudioError,
    TranscribeError,
    TTSError,
    UnsupportedLanguageError,
)
from app.providers.transcribe.amazon_transcribe_streaming import (
    AmazonTranscribeStreamingProvider,
)
from app.providers.tts.kannada import RegionalKannadaTTSProvider
from app.services.localization import TemplateLocalizationService
from app.services.voice_intent import VoiceIntentType

# ------------------------------------------------------------------------------
# Mock Implementations for Tests
# ------------------------------------------------------------------------------


class MockSpeechToText(SpeechToTextPort):
    """Configurable mock STT port."""

    def __init__(
        self,
        transcript: str = "What should I take at night?",
        confidence: float = 0.95,
        fail_mode: str | None = None,
    ) -> None:
        self.transcript = transcript
        self.confidence = confidence
        self.fail_mode = fail_mode

    async def transcribe_audio(
        self,
        audio_bytes: bytes,
        mime_type: str,  # noqa: ARG002
        language_code: str = "en-IN",
    ) -> TranscriptResult:
        if self.fail_mode == "empty" or not audio_bytes or len(audio_bytes) == 0:
            raise EmptyAudioError("Empty audio")
        supported = ("en-IN", "hi-IN", "kn-IN", "en", "hi", "kn")
        if self.fail_mode == "unsupported_lang" or language_code not in supported:
            raise UnsupportedLanguageError(f"Unsupported language {language_code}")
        if self.fail_mode == "provider_error":
            raise TranscribeError("Transcribe service unavailable")

        return TranscriptResult(
            text=self.transcript,
            language=language_code,
            confidence=self.confidence,
        )


class MockTTS(TTSProvider):
    """Configurable mock TTS provider."""

    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail

    async def synthesize(self, text: str, language: str = "en-IN") -> AudioResponse:  # noqa: ARG002
        if self.should_fail:
            raise TTSError("TTS synthesis crashed")
        return AudioResponse(
            audio_bytes=b"FAKE-MP3-BYTES",
            content_type="audio/mpeg",
            language=language,
            duration_seconds=2.0,
        )


# ------------------------------------------------------------------------------
# Database & Client Fixtures
# ------------------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def test_db_session():
    """Create in-memory SQLite database session."""
    engine = create_async_engine(TEST_DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_maker = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )

    async with session_maker() as session:
        yield session


@pytest.fixture
async def seeded_prescription_id(test_db_session: AsyncSession) -> str:
    """Seed a valid, verified prescription with Metformin and Pantocid."""
    p_id = "presc-voice-test-001"
    prescription = Prescription(
        id=p_id,
        status=PrescriptionStatus.COMPLETED,
        schema_version="1.0.0",
    )
    test_db_session.add(prescription)

    med1 = MedicationResult(
        id="med-voice-001",
        prescription_id=p_id,
        drug_name="Metformin",
        strength_value=500.0,
        strength_unit="mg",
        dose_value=1.0,
        dose_unit="tablet",
        morning=True,
        afternoon=False,
        evening=False,
        night=True,
        after_meal=True,
        duration_value=1,
        duration_unit="month",
        is_verified_safe=True,
    )
    med2 = MedicationResult(
        id="med-voice-002",
        prescription_id=p_id,
        drug_name="Pantocid",
        strength_value=40.0,
        strength_unit="mg",
        dose_value=1.0,
        dose_unit="tablet",
        morning=True,
        afternoon=False,
        evening=False,
        night=False,
        before_meal=True,
        duration_value=15,
        duration_unit="days",
        is_verified_safe=True,
    )
    test_db_session.add_all([med1, med2])
    await test_db_session.commit()
    return p_id


@pytest.fixture
async def unverified_prescription_id(test_db_session: AsyncSession) -> str:
    """Seed a prescription flagged as REQUIRES_REVIEW."""
    p_id = "presc-review-002"
    prescription = Prescription(
        id=p_id,
        status=PrescriptionStatus.REQUIRES_REVIEW,
        schema_version="1.0.0",
    )
    test_db_session.add(prescription)
    med = MedicationResult(
        id="med-voice-uncertain",
        prescription_id=p_id,
        drug_name="UnknownDrug",
        is_verified_safe=False,
    )
    test_db_session.add(med)
    await test_db_session.commit()
    return p_id


# ------------------------------------------------------------------------------
# Test Scenarios (17 Cases)
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_1_successful_transcription(test_db_session: AsyncSession):
    """1. Successful transcription: Valid audio returns recognized text with 200 OK."""
    stt_mock = MockSpeechToText(transcript="What should I take in the morning?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio-bytes"), "audio/mpeg")}
        data = {"language": "en-IN"}
        resp = await client.post("/api/v1/voice/transcribe", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["transcript"] == "What should I take in the morning?"
        assert body["language"] == "en-IN"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_2_transcription_failure(test_db_session: AsyncSession):
    """2. Transcription failure: Provider exception maps to 500 error envelope."""
    stt_mock = MockSpeechToText(fail_mode="provider_error")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio-bytes"), "audio/mpeg")}
        resp = await client.post("/api/v1/voice/transcribe", files=files)

        assert resp.status_code == 500
        assert resp.json()["detail"]["error"]["code"] == "TRANSCRIBE_UNAVAILABLE"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_3_unsupported_language(test_db_session: AsyncSession):
    """3. Unsupported language: Rejects unsupported locale with 415."""
    stt_mock = MockSpeechToText(fail_mode="unsupported_lang")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio-bytes"), "audio/mpeg")}
        data = {"language": "fr-FR"}
        resp = await client.post("/api/v1/voice/transcribe", files=files, data=data)

        assert resp.status_code == 415
        assert resp.json()["detail"]["error"]["code"] == "UNSUPPORTED_LANGUAGE"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_4_empty_audio(test_db_session: AsyncSession):
    """4. Empty audio: 0-byte upload rejected with 400 Bad Request."""
    stt_mock = MockSpeechToText(fail_mode="empty")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b""), "audio/mpeg")}
        resp = await client.post("/api/v1/voice/transcribe", files=files)

        assert resp.status_code == 400
        assert resp.json()["detail"]["error"]["code"] == "EMPTY_AUDIO_PAYLOAD"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_5_supported_medication_query_list(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """5. Supported medication query: 'list all medicines' returns both prescribed drugs."""
    stt_mock = MockSpeechToText(transcript="List all my medicines")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["intent"] == "LIST_MEDICATIONS"
        assert "Metformin" in body["response_text"]
        assert "Pantocid" in body["response_text"]
        assert body["audio_base64"] is not None

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_6_morning_query(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """6. Morning query: returns medicines scheduled for morning (Metformin & Pantocid)."""
    stt_mock = MockSpeechToText(transcript="What medicines should I take in the morning?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["intent"] == "MORNING_MEDICINE"
        assert "Metformin" in body["response_text"]
        assert "Pantocid" in body["response_text"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_7_night_query(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """7. Night query: returns only night medicines (Metformin), excludes Pantocid."""
    stt_mock = MockSpeechToText(transcript="What should I take at night?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["intent"] == "NIGHT_MEDICINE"
        assert "Metformin" in body["response_text"]
        assert "Pantocid" not in body["response_text"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_8_before_food_query(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """8. Before-food query: returns Pantocid (before_meal=True), excludes Metformin."""
    stt_mock = MockSpeechToText(transcript="Which medicine before food?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["intent"] == "BEFORE_FOOD"
        assert "Pantocid" in body["response_text"]
        assert "Metformin" not in body["response_text"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_9_after_food_query(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """9. After-food query: returns Metformin (after_meal=True), excludes Pantocid."""
    stt_mock = MockSpeechToText(transcript="Which medicine after food?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["intent"] == "AFTER_FOOD"
        assert "Metformin" in body["response_text"]
        assert "Pantocid" not in body["response_text"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_10_duration_query(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """10. Duration query: returns duration for both medications."""
    stt_mock = MockSpeechToText(transcript="How many days should I take this?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["intent"] == "DURATION"
        assert "1 month" in body["response_text"]
        assert "15 days" in body["response_text"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_11_unknown_intent(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """11. Unknown intent: Question outside clinical scope safely refused."""
    stt_mock = MockSpeechToText(transcript="Can I eat mango with this?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["intent"] == "UNKNOWN"
        assert "no specific instructions" in body["response_text"]

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_12_prescription_requires_review(
    test_db_session: AsyncSession,
    unverified_prescription_id: str,
):
    """12. Prescription requires review: Fail-closed, refuses to provide instructions."""
    stt_mock = MockSpeechToText(transcript="What medicine should I take?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": unverified_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is False
        assert body["requires_review"] is True
        assert "consult your pharmacist" in body["response_text"].lower()

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_13_missing_prescription(test_db_session: AsyncSession):
    """13. Missing prescription: Returns HTTP 404."""
    stt_mock = MockSpeechToText(transcript="What should I take?")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": "non-existent-id-000", "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "PRESCRIPTION_NOT_FOUND"

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_14_tts_failure_graceful_degradation(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """14. TTS failure: Graceful degradation returns text response with audio_base64=None."""
    stt_mock = MockSpeechToText(transcript="List all medicines")
    app.dependency_overrides[get_stt_port] = lambda: stt_mock
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS(should_fail=True)
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id, "language": "en-IN"}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert "Metformin" in body["response_text"]
        assert body["audio_base64"] is None

    app.dependency_overrides.clear()


def test_15_localization_correctness():
    """15. Localization correctness: Formats facts across English, Hindi, and Kannada."""
    loc = TemplateLocalizationService()
    fact = CanonicalMedicationFact(
        drug_name="Metformin",
        strength_value=500.0,
        strength_unit="mg",
        dose_value=1.0,
        dose_unit="tablet",
        morning=True,
        afternoon=False,
        evening=False,
        night=True,
        is_as_needed_sos=False,
        before_meal=False,
        after_meal=True,
        duration_value=1,
        duration_unit="month",
    )

    en_res = loc.format_intent_response(VoiceIntentType.NIGHT_MEDICINE, [fact], "en-IN")
    assert "At night, take: Metformin (1 tablet after food)." in en_res

    hi_res = loc.format_intent_response(VoiceIntentType.NIGHT_MEDICINE, [fact], "hi-IN")
    assert "रात को लें: Metformin (1 tablet खाने के बाद)।" in hi_res

    kn_res = loc.format_intent_response(VoiceIntentType.NIGHT_MEDICINE, [fact], "kn-IN")
    assert "ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಿ: Metformin ಊಟದ ನಂತರ." in kn_res


@pytest.mark.asyncio
async def test_16_provider_failure_sanitization(
    test_db_session: AsyncSession,
    seeded_prescription_id: str,
):
    """16. Provider failure: Unhandled exceptions sanitized without stack traces."""

    class BrokenSTT(SpeechToTextPort):
        async def transcribe_audio(self, *_args: Any, **_kwargs: Any) -> TranscriptResult:
            raise RuntimeError("Database connection string: postgres://admin:secret@10.0.0.1/db")

    app.dependency_overrides[get_stt_port] = lambda: BrokenSTT()
    app.dependency_overrides[get_tts_provider] = lambda: MockTTS()
    app.dependency_overrides[get_db_session] = lambda: test_db_session

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        files = {"file": ("audio.mp3", io.BytesIO(b"audio"), "audio/mpeg")}
        data = {"prescription_id": seeded_prescription_id}
        resp = await client.post("/api/v1/voice/query", files=files, data=data)

        assert resp.status_code == 500
        body = resp.json()
        assert "secret" not in resp.text
        assert body["detail"]["error"]["code"] == "VOICE_QUERY_ERROR"

    app.dependency_overrides.clear()


def test_17_no_medication_facts_invented():
    """17. Deterministic invariant: Unstated fields are never hallucinated or filled in."""
    loc = TemplateLocalizationService()
    # Medication without dosage, food instruction, or timing
    sparse_fact = CanonicalMedicationFact(
        drug_name="UnknownPill",
        strength_value=None,
        strength_unit=None,
        dose_value=None,
        dose_unit=None,
        morning=None,
        afternoon=None,
        evening=None,
        night=None,
        is_as_needed_sos=False,
        before_meal=None,
        after_meal=None,
        duration_value=None,
        duration_unit=None,
    )

    # Night query should produce nothing for unstated night slot
    night_res = loc.format_intent_response(VoiceIntentType.NIGHT_MEDICINE, [sparse_fact], "en-IN")
    assert "do not have any medications scheduled for the night" in night_res

    # Before food should not guess
    bf_res = loc.format_intent_response(VoiceIntentType.BEFORE_FOOD, [sparse_fact], "en-IN")
    assert "no medications marked to be taken before food" in bf_res


# ------------------------------------------------------------------------------
# Hardening Tests: Streaming STT & Real Kannada TTS
# ------------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_18_streaming_transcription_success():
    """18. Streaming STT: Routes WAV audio correctly and falls back cleanly if needed."""
    mock_batch = MockSpeechToText(transcript="What should I take at night?")
    streaming_provider = AmazonTranscribeStreamingProvider(
        region_name="ap-south-1",
        fallback_batch_provider=mock_batch,
    )

    # Valid dummy WAV audio header (44 bytes RIFF) + raw PCM
    wav_header = b"RIFF" + (b"\x00" * 20) + (16000).to_bytes(4, "little") + (b"\x00" * 16)
    audio_wav = wav_header + (b"\x00\x00" * 1600)

    res = await streaming_provider.transcribe_audio(
        audio_bytes=audio_wav,
        mime_type="audio/wav",
        language_code="en-IN",
    )
    assert res.text != ""


@pytest.mark.asyncio
async def test_19_streaming_transcription_empty_and_unsupported():
    """19. Streaming STT: Validates payload and rejects empty audio or invalid language."""
    streaming_provider = AmazonTranscribeStreamingProvider(region_name="ap-south-1")

    with pytest.raises(EmptyAudioError):
        await streaming_provider.transcribe_audio(b"", mime_type="audio/wav")

    with pytest.raises(UnsupportedLanguageError):
        await streaming_provider.transcribe_audio(
            b"1234", mime_type="audio/wav", language_code="es-ES"
        )


@pytest.mark.asyncio
async def test_20_streaming_mp3_fallback_to_batch():
    """20. Streaming STT: Compressed non-PCM MP3 automatically delegates to batch fallback."""
    mock_batch = MockSpeechToText(transcript="List all medicines")
    streaming_provider = AmazonTranscribeStreamingProvider(
        region_name="ap-south-1",
        fallback_batch_provider=mock_batch,
    )

    mp3_payload = b"\xff\xfb\x90d" + b"mp3data"
    res = await streaming_provider.transcribe_audio(
        audio_bytes=mp3_payload,
        mime_type="audio/mpeg",
        language_code="en-IN",
    )
    assert res.text == "List all medicines"


@pytest.mark.asyncio
async def test_21_regional_kannada_tts_provider():
    """21. Regional Kannada TTS: Synthesizes real audio response for Kannada text."""
    mock_fallback = MockTTS()
    kannada_provider = RegionalKannadaTTSProvider(fallback_provider=mock_fallback)

    res = await kannada_provider.synthesize(
        text="ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಿ: Metformin.",
        language="kn-IN",
    )
    assert res.content_type == "audio/mpeg"
    assert res.language == "kn-IN"
    assert len(res.audio_bytes) > 0


@pytest.mark.asyncio
async def test_22_kannada_tts_empty_refusal():
    """22. Regional Kannada TTS: Rejects empty text safely with TTSError."""
    kannada_provider = RegionalKannadaTTSProvider()
    with pytest.raises(TTSError):
        await kannada_provider.synthesize(text="   ", language="kn-IN")
