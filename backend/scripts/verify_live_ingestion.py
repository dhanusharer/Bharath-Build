"""Live Phase 3 Verification Script.

Tests complete flow:
1. Health check
2. POST /api/v1/prescriptions with real Bedrock & S3
3. GET /api/v1/prescriptions/{id}
4. Failure test cases (MIME, empty, oversized)
5. Security checks
"""

import asyncio
import json
import sqlite3
import time
from pathlib import Path

import boto3
import httpx

from app.core.config import get_settings
from app.main import app


async def run_live_verification() -> None:
    print("=" * 60)
    print("PHASE 3 LIVE VERIFICATION")
    print("=" * 60)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # 1. Health check
        print("\n[1/5] Checking Health Endpoint...")
        r_health = await client.get("/api/v1/health")
        print(f"Health status: {r_health.status_code}")
        print(f"Health response: {r_health.json()}")
        assert r_health.status_code == 200, f"Expected 200, got {r_health.status_code}"

        # 2. Upload synthetic prescription
        print("\n[2/5] Performing Real POST /api/v1/prescriptions...")
        image_path = Path("backend/tests/fixtures/synthetic_prescription.png")
        image_bytes = image_path.read_bytes()
        print(f"Loaded test image: {len(image_bytes)} bytes")

        t0 = time.perf_counter()
        files = {"file": ("synthetic_prescription.png", image_bytes, "image/png")}
        headers = {"X-Request-ID": "live-test-req-001"}

        r_post = await client.post(
            "/api/v1/prescriptions", files=files, headers=headers, timeout=60.0
        )
        t_elapsed = time.perf_counter() - t0

        print(f"POST status: {r_post.status_code}")
        print(f"Total End-to-End Latency: {t_elapsed:.2f}s")
        assert r_post.status_code == 201, f"POST failed: {r_post.text}"

        post_data = r_post.json()
        print("\nAPI Response:")
        print(json.dumps(post_data, indent=2))

        prescription_id = post_data["prescription_id"]
        assert post_data["success"] is True
        assert post_data["status"] in ("COMPLETED", "REQUIRES_REVIEW")
        assert len(post_data["medications"]) >= 1

        # 3. GET /api/v1/prescriptions/{id}
        print(f"\n[3/5] Performing GET /api/v1/prescriptions/{prescription_id}...")
        r_get = await client.get(f"/api/v1/prescriptions/{prescription_id}")
        print(f"GET status: {r_get.status_code}")
        assert r_get.status_code == 200, f"GET failed: {r_get.text}"
        get_data = r_get.json()
        print("GET Response:")
        print(json.dumps(get_data, indent=2))
        assert get_data["prescription_id"] == prescription_id
        assert len(get_data["medications"]) == len(post_data["medications"])

        # 4. Failure modes
        print("\n[4/5] Testing Failure Modes...")
        # 4a: Unsupported MIME
        r_mime = await client.post(
            "/api/v1/prescriptions",
            files={"file": ("test.pdf", b"%PDF-1.4", "application/pdf")},
        )
        print(f"Unsupported MIME -> status: {r_mime.status_code}")
        assert r_mime.status_code == 415

        # 4b: Empty file
        r_empty = await client.post(
            "/api/v1/prescriptions",
            files={"file": ("empty.png", b"", "image/png")},
        )
        print(f"Empty file -> status: {r_empty.status_code}")
        assert r_empty.status_code == 400

        # 4c: Oversized file (> 10MB)
        oversized = b"0" * (10 * 1024 * 1024 + 1024)
        r_oversized = await client.post(
            "/api/v1/prescriptions",
            files={"file": ("oversized.png", oversized, "image/png")},
        )
        print(f"Oversized file -> status: {r_oversized.status_code}")
        assert r_oversized.status_code == 413

        print("\n[5/5] Checking Database & S3 Records...")
        conn = sqlite3.connect("medassist.db")
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, status, schema_version FROM prescriptions WHERE id = ?",
            (prescription_id,),
        )
        p_row = cursor.fetchone()
        print(f"SQLite Prescription row: {p_row}")
        assert p_row is not None
        assert p_row[1] == "COMPLETED"

        cursor.execute(
            "SELECT s3_object_key, mime_type, file_size_bytes "
            "FROM prescription_images WHERE prescription_id = ?",
            (prescription_id,),
        )
        img_row = cursor.fetchone()
        print(f"SQLite Image metadata row: {img_row}")
        assert img_row is not None
        s3_key = img_row[0]

        cursor.execute(
            "SELECT drug_name, strength_value, strength_unit, is_verified_safe "
            "FROM medication_results WHERE prescription_id = ?",
            (prescription_id,),
        )
        med_rows = cursor.fetchall()
        print(f"SQLite Medications rows: {med_rows}")
        assert len(med_rows) >= 1

        # Verify S3 object exists
        bucket_name = get_settings().S3_BUCKET_NAME
        s3 = boto3.client("s3", region_name="ap-south-1")
        head = s3.head_object(Bucket=bucket_name, Key=s3_key)
        print(
            f"S3 Head Object verified: Bucket={bucket_name}, Key={s3_key}, "
            f"ContentLength={head['ContentLength']}, ContentType={head['ContentType']}"
        )
        assert head["ContentLength"] == len(image_bytes)

        print("\n" + "=" * 60)
        print("ALL LIVE VERIFICATION CHECKS COMPLETED SUCCESSFULLY!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(run_live_verification())
