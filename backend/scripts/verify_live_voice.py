"""Live Phase 4 Voice Verification Script with Transcribe Streaming & Kannada TTS.

Demonstrates:
1. Synthesizes controlled voice query in 16kHz PCM WAV format.
2. Invokes POST /api/v1/voice/query with streaming Transcribe.
3. Measures distinct latency breakdowns:
   - STT Latency
   - Intent Classification Latency
   - DB Lookup Latency
   - TTS Latency (English/Hindi via Polly)
   - Real Kannada TTS Latency via Regional Kannada Provider
   - Total End-to-End Voice Roundtrip Latency
4. Verifies response fidelity and safety.
"""

import asyncio
import sqlite3
import time
from pathlib import Path

import boto3
import httpx

from app.core.config import get_settings
from app.main import app
from app.ports.localization import CanonicalMedicationFact
from app.ports.tts import TTSProvider
from app.providers.tts.kannada import RegionalKannadaTTSProvider
from app.services.localization import TemplateLocalizationService
from app.services.voice_intent import VoiceIntentService


def create_wav_from_pcm(pcm_bytes: bytes, sample_rate: int = 16000) -> bytes:
    """Pack raw 16-bit mono PCM into standard WAV container."""
    num_channels = 1
    bits_per_sample = 16
    byte_rate = sample_rate * num_channels * (bits_per_sample // 8)
    block_align = num_channels * (bits_per_sample // 8)
    data_size = len(pcm_bytes)
    chunk_size = 36 + data_size

    header = bytearray()
    header.extend(b"RIFF")
    header.extend(chunk_size.to_bytes(4, "little"))
    header.extend(b"WAVE")
    header.extend(b"fmt ")
    header.extend((16).to_bytes(4, "little"))  # Subchunk1Size (16 for PCM)
    header.extend((1).to_bytes(2, "little"))  # AudioFormat (1 for PCM)
    header.extend(num_channels.to_bytes(2, "little"))
    header.extend(sample_rate.to_bytes(4, "little"))
    header.extend(byte_rate.to_bytes(4, "little"))
    header.extend(block_align.to_bytes(2, "little"))
    header.extend(bits_per_sample.to_bytes(2, "little"))
    header.extend(b"data")
    header.extend(data_size.to_bytes(4, "little"))

    return bytes(header) + pcm_bytes


async def run_live_voice_verification() -> None:
    print("=" * 68)
    print("PHASE 4 HARDENING — STREAMING TRANSCRIBE + REAL KANNADA TTS")
    print("=" * 68)

    settings = get_settings()
    region = settings.AWS_REGION
    profile = settings.AWS_PROFILE

    # 1. Obtain existing persisted prescription from SQLite
    conn = sqlite3.connect("medassist.db")
    query = (
        "SELECT id, status FROM prescriptions "
        "WHERE status = 'COMPLETED' ORDER BY created_at DESC LIMIT 1"
    )
    row = conn.execute(query).fetchone()
    if not row:
        raise RuntimeError("No completed prescription found in medassist.db.")
    prescription_id = row[0]
    print(f"\n[1/5] Target Prescribed Session: {prescription_id} (Status: {row[1]})")

    # 2. Synthesize 16kHz PCM audio query: 'What should I take at night?'
    print(
        "\n[2/5] Synthesizing 16kHz PCM WAV Question via Polly: 'What should I take at night?'..."
    )
    session = boto3.Session(profile_name=profile, region_name=region)
    polly_client = session.client("polly")

    synth_t0 = time.perf_counter()
    polly_resp = polly_client.synthesize_speech(
        Text="What should I take at night?",
        OutputFormat="pcm",
        SampleRate="16000",
        VoiceId="Kajal",
        Engine="neural",
        LanguageCode="en-IN",
    )
    pcm_bytes = polly_resp["AudioStream"].read()
    wav_audio_bytes = create_wav_from_pcm(pcm_bytes, sample_rate=16000)
    synth_latency = time.perf_counter() - synth_t0
    print(f"Synthesized WAV audio: {len(wav_audio_bytes)} bytes in {synth_latency:.2f}s")

    Path("backend/tests/fixtures/live_voice_query.wav").write_bytes(wav_audio_bytes)

    # 3. Benchmark Individual Stages
    print("\n[3/5] Benchmarking Pipeline Component Latencies...")

    # A. STT Streaming Latency
    from app.providers.transcribe.amazon_transcribe_streaming import (
        AmazonTranscribeStreamingProvider,
    )

    stt_provider = AmazonTranscribeStreamingProvider(region_name=region, session=session)
    stt_t0 = time.perf_counter()
    stt_res = await stt_provider.transcribe_audio(
        audio_bytes=wav_audio_bytes,
        mime_type="audio/wav",
        language_code="en-IN",
    )
    stt_latency = time.perf_counter() - stt_t0
    print(f"-> Streaming STT Latency: {stt_latency:.2f}s (Transcript: '{stt_res.text}')")

    # B. Intent Classification Latency
    intent_service = VoiceIntentService()
    intent_t0 = time.perf_counter()
    intent_res = intent_service.classify_intent(
        query_text=stt_res.text,
        known_drug_names=["Metformin", "Pantocid"],
    )
    intent_latency = time.perf_counter() - intent_t0
    print(f"-> Intent Latency: {intent_latency * 1000:.2f}ms (Intent: {intent_res.intent})")

    # C. Database Query Latency
    db_t0 = time.perf_counter()
    db_query = (
        "SELECT drug_name, strength_value, strength_unit, dose_value, dose_unit, "
        "morning, afternoon, evening, night, after_meal, before_meal, "
        "duration_value, duration_unit "
        "FROM medication_results WHERE prescription_id = ?"
    )
    med_rows = conn.execute(db_query, (prescription_id,)).fetchall()
    db_latency = time.perf_counter() - db_t0
    print(f"-> DB Query Latency: {db_latency * 1000:.2f}ms ({len(med_rows)} medications retrieved)")

    # D. Localization Latency
    loc_service = TemplateLocalizationService()
    facts = [
        CanonicalMedicationFact(
            drug_name=r[0],
            strength_value=r[1],
            strength_unit=r[2],
            dose_value=r[3],
            dose_unit=r[4],
            morning=bool(r[5]),
            afternoon=bool(r[6]),
            evening=bool(r[7]),
            night=bool(r[8]),
            is_as_needed_sos=False,
            after_meal=bool(r[9]),
            before_meal=bool(r[10]),
            duration_value=r[11],
            duration_unit=r[12],
        )
        for r in med_rows
    ]
    loc_t0 = time.perf_counter()
    response_text_en = loc_service.format_intent_response(
        intent=intent_res.intent,
        facts=facts,
        language="en-IN",
    )
    response_text_kn = loc_service.format_intent_response(
        intent=intent_res.intent,
        facts=facts,
        language="kn-IN",
    )
    loc_latency = time.perf_counter() - loc_t0
    print(f"-> Localization Latency: {loc_latency * 1000:.2f}ms")
    print(f"   English: '{response_text_en}'")
    print(f"   Kannada (UTF-8 bytes): {response_text_kn.encode('utf-8')!r}")

    # E. TTS Latencies
    tts_t0 = time.perf_counter()
    polly_out = polly_client.synthesize_speech(
        Text=response_text_en,
        OutputFormat="mp3",
        VoiceId="Kajal",
        Engine="neural",
        LanguageCode="en-IN",
    )
    _ = polly_out["AudioStream"].read()
    tts_polly_latency = time.perf_counter() - tts_t0
    print(f"-> Amazon Polly TTS (en-IN) Latency: {tts_polly_latency:.2f}s")

    kannada_tts: TTSProvider = RegionalKannadaTTSProvider()
    kn_t0 = time.perf_counter()
    kn_audio = await kannada_tts.synthesize(text=response_text_kn, language="kn-IN")
    tts_kannada_latency = time.perf_counter() - kn_t0
    print(
        f"-> Real Kannada TTS Latency: {tts_kannada_latency:.2f}s "
        f"({len(kn_audio.audio_bytes)} bytes audio returned)"
    )

    # 4. Invoke Live HTTP Endpoint: POST /api/v1/voice/query
    print("\n[4/5] Executing Live HTTP Request to POST /api/v1/voice/query...")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        files = {"file": ("query.wav", wav_audio_bytes, "audio/wav")}
        data = {"prescription_id": prescription_id, "language": "en-IN"}
        headers = {"X-Request-ID": "live-stream-req-001"}

        e2e_t0 = time.perf_counter()
        http_resp = await client.post(
            "/api/v1/voice/query",
            files=files,
            data=data,
            headers=headers,
            timeout=30.0,
        )
        total_e2e_latency = time.perf_counter() - e2e_t0

    assert http_resp.status_code == 200, f"HTTP Error: {http_resp.text}"
    body = http_resp.json()

    print("\n" + "-" * 35 + " LIVE STREAMING QUERY RESPONSE " + "-" * 35)
    print(f"Status: {http_resp.status_code} OK")
    print(f"Total Interactive Roundtrip Latency: {total_e2e_latency:.2f}s (Old batch was 14.14s)")
    print(f"Transcript Recognized: '{body['transcript']}'")
    print(f"Clinical Intent: {body['intent']}")
    print(f"Spoken Answer: '{body['response_text']}'")
    print(f"Audio Base64: {len(body['audio_base64'] or '')} characters")
    print(f"Requires Review: {body['requires_review']}")
    print("-" * 102)

    # 5. Verification Gate
    print("\n[5/5] Verifying Correctness & Latency Target...")
    assert body["success"] is True
    assert body["intent"] == "NIGHT_MEDICINE"
    assert "Metformin" in body["response_text"]
    assert "Pantocid" not in body["response_text"]
    assert total_e2e_latency < 5.0, f"Latency {total_e2e_latency:.2f}s exceeds interactive target!"
    print(
        f"SUCCESS: Interactive latency reduced from 14.14s to {total_e2e_latency:.2f}s "
        f"({((14.14 - total_e2e_latency) / 14.14) * 100:.1f}% speedup)!"
    )

    print("\n" + "=" * 68)
    print("PHASE 4 HARDENING LIVE VERIFICATION COMPLETE!")
    print("=" * 68)


if __name__ == "__main__":
    asyncio.run(run_live_voice_verification())
