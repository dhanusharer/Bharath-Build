"""Live Voice Query Semantics Verification Script.

Tests the exact user query: 'What should I take at night?'
under both semantic states:
1. REQUIRES_REVIEW: Verified prescription from the real handwritten test case.
2. COMPLETED: Fully validated prescription with nighttime medicines.
"""

import asyncio
import os
from pathlib import Path
import sqlite3
import sys
import time

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import boto3
import httpx

from app.core.config import get_settings
from app.main import app


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
    header.extend((16).to_bytes(4, "little"))
    header.extend((1).to_bytes(2, "little"))
    header.extend(num_channels.to_bytes(2, "little"))
    header.extend(sample_rate.to_bytes(4, "little"))
    header.extend(byte_rate.to_bytes(4, "little"))
    header.extend(block_align.to_bytes(2, "little"))
    header.extend(bits_per_sample.to_bytes(2, "little"))
    header.extend(b"data")
    header.extend(data_size.to_bytes(4, "little"))

    return bytes(header) + pcm_bytes


async def run_live_verification() -> None:
    settings = get_settings()
    if settings.AWS_PROFILE:
        os.environ["AWS_PROFILE"] = settings.AWS_PROFILE
        os.environ["AWS_DEFAULT_REGION"] = settings.AWS_REGION

    session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
    polly = session.client("polly")

    # 1. Synthesize question audio: "What should I take at night?"
    print("Synthesizing question audio via Amazon Polly: 'What should I take at night?'...")
    resp = polly.synthesize_speech(
        Text="What should I take at night?",
        OutputFormat="pcm",
        SampleRate="16000",
        VoiceId="Kajal",
        Engine="neural",
        LanguageCode="en-IN",
    )
    wav_bytes = create_wav_from_pcm(resp["AudioStream"].read(), sample_rate=16000)
    print(f"Generated WAV audio: {len(wav_bytes)} bytes")

    # 2. Identify the real handwritten prescription in REQUIRES_REVIEW state
    conn = sqlite3.connect("medassist.db")
    review_row = conn.execute(
        "SELECT id, status FROM prescriptions WHERE status = 'REQUIRES_REVIEW' ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    if not review_row:
        raise RuntimeError("No REQUIRES_REVIEW prescription found in DB.")
    review_rx_id = review_row[0]
    print(f"\nTarget Review Prescription ID: {review_rx_id} (Status: {review_row[1]})")

    # 3. Create/Seed a verified COMPLETED prescription for comparison
    completed_rx_id = "test-live-verified-completed-rx"
    conn.execute(
        "INSERT OR REPLACE INTO prescriptions (id, status, schema_version, created_at, updated_at) "
        "VALUES (?, 'COMPLETED', '1.0.0', datetime('now'), datetime('now'))",
        (completed_rx_id,),
    )
    conn.execute(
        "INSERT OR REPLACE INTO medication_results "
        "(id, prescription_id, drug_name, strength_value, strength_unit, dose_value, dose_unit, "
        "morning, afternoon, evening, night, after_meal, before_meal, duration_value, duration_unit, is_verified_safe, requires_review, is_legible, is_as_needed_sos) "
        "VALUES "
        "('m-comp-1', ?, 'Tab. Augmentin', 625.0, 'mg', 1.0, 'tablet', 1, 0, 0, 1, 1, 0, 5, 'days', 1, 0, 1, 0), "
        "('m-comp-2', ?, 'Tab. Enzflam', NULL, NULL, 1.0, 'tablet', 1, 0, 0, 1, 1, 0, 5, 'days', 1, 0, 1, 0), "
        "('m-comp-3', ?, 'Tab. PanD', 40.0, 'mg', 1.0, 'tablet', 1, 0, 0, 0, 0, 1, 5, 'days', 1, 0, 1, 0)",
        (completed_rx_id, completed_rx_id, completed_rx_id),
    )
    conn.commit()
    conn.close()

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # TEST CASE A: REQUIRES_REVIEW + NIGHT_MEDICINE
        print("\n" + "=" * 60)
        print("TEST CASE A: REQUIRES_REVIEW + NIGHT_MEDICINE")
        print("=" * 60)
        files = {"file": ("query.wav", wav_bytes, "audio/wav")}
        data = {"prescription_id": review_rx_id, "language": "en-IN"}
        r_review = await client.post("/api/v1/voice/query", files=files, data=data)
        assert r_review.status_code == 200, f"Failed: {r_review.text}"
        res_review = r_review.json()

        print(f"Status Code: {r_review.status_code}")
        print(f"Success: {res_review['success']}")
        print(f"Requires Review: {res_review['requires_review']}")
        print(f"Result State: {res_review['result_state']}")
        print(f"Transcript: '{res_review['transcript']}'")
        print(f"Intent: {res_review['intent']}")
        print(f"Spoken Voice Response Text:\n>> \"{res_review['response_text']}\"")
        print(f"Audio Synthesized: {bool(res_review['audio_base64'])} ({len(res_review['audio_base64'] or '')} b64 chars)")

        # Invariant checks for CASE A (Option 3 Granular Disclosure)
        assert res_review["result_state"] == "PRESCRIPTION_REQUIRES_REVIEW"
        assert res_review["requires_review"] is True
        assert res_review["success"] is False
        assert "no medicine" not in res_review["response_text"].lower()
        assert "no medications scheduled" not in res_review["response_text"].lower()
        assert "Tab. Augmentin" in res_review["response_text"]
        assert "Tab. Enzflam" in res_review["response_text"]
        assert "pharmacist" in res_review["response_text"].lower()

        # TEST CASE A2: REQUIRES_REVIEW in KANNADA
        print("\n" + "=" * 60)
        print("TEST CASE A2: REQUIRES_REVIEW + KANNADA NIGHT_MEDICINE")
        print("=" * 60)
        from app.providers.tts.kannada import RegionalKannadaTTSProvider
        kannada_tts = RegionalKannadaTTSProvider()
        kn_audio = await kannada_tts.synthesize("ರಾತ್ರಿ ಯಾವ ಮಾತ್ರೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು?")
        files_kn = {"file": ("query.mp3", kn_audio.audio_bytes, "audio/mpeg")}
        data_kn = {"prescription_id": review_rx_id, "language": "kn-IN"}
        r_kn = await client.post("/api/v1/voice/query", files=files_kn, data=data_kn)
        assert r_kn.status_code == 200
        res_kn = r_kn.json()
        print(f"Kannada Transcript: '{res_kn['transcript']}' (Intent: {res_kn['intent']})")
        print(f"Kannada Voice Response Text:\n>> \"{res_kn['response_text']}\"")
        assert "Tab. Augmentin" in res_kn["response_text"]
        assert "Tab. Enzflam" in res_kn["response_text"]
        assert "ಔಷಧಿಕಾರರೊಂದಿಗೆ" in res_kn["response_text"]

        # TEST CASE B: COMPLETED + NIGHT_MEDICINE
        print("\n" + "=" * 60)
        print("TEST CASE B: COMPLETED + NIGHT_MEDICINE")
        print("=" * 60)
        files = {"file": ("query.wav", wav_bytes, "audio/wav")}
        data = {"prescription_id": completed_rx_id, "language": "en-IN"}
        r_completed = await client.post("/api/v1/voice/query", files=files, data=data)
        assert r_completed.status_code == 200, f"Failed: {r_completed.text}"
        res_completed = r_completed.json()

        print(f"Status Code: {r_completed.status_code}")
        print(f"Success: {res_completed['success']}")
        print(f"Requires Review: {res_completed['requires_review']}")
        print(f"Result State: {res_completed['result_state']}")
        print(f"Transcript: '{res_completed['transcript']}'")
        print(f"Intent: {res_completed['intent']}")
        print(f"Spoken Voice Response Text:\n>> \"{res_completed['response_text']}\"")
        print(f"Audio Synthesized: {bool(res_completed['audio_base64'])} ({len(res_completed['audio_base64'] or '')} b64 chars)")

        # Invariant checks for CASE B
        assert res_completed["result_state"] == "CONFIRMED_MATCH"
        assert res_completed["requires_review"] is False
        assert res_completed["success"] is True
        assert "Tab. Augmentin" in res_completed["response_text"]
        assert "Tab. Enzflam" in res_completed["response_text"]
        assert "Tab. PanD" not in res_completed["response_text"]

        print("\n" + "=" * 60)
        print("ALL LIVE VERIFICATION INVARIANTS MET PERFECTLY!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_live_verification())
