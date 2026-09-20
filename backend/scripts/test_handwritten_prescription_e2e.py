"""End-to-end test for real handwritten prescription test case.

Fetches the test image from S3 and runs it through the full ingestion pipeline:
Bedrock extraction -> Pydantic -> Safety Gate -> Normalization -> Persistence -> API
"""

import asyncio
import json
import time

import boto3
import httpx

from app.core.config import get_settings
from app.main import app


async def test_handwritten_rx_e2e() -> None:
    settings = get_settings()
    if settings.AWS_PROFILE:
        import os
        os.environ["AWS_PROFILE"] = settings.AWS_PROFILE
        os.environ["AWS_DEFAULT_REGION"] = settings.AWS_REGION

    session = boto3.Session(profile_name=settings.AWS_PROFILE, region_name=settings.AWS_REGION)
    s3 = session.client("s3")

    s3_key = "prescriptions/f53c37ee-2f06-4226-b180-83ebfcb7de48/bb8504a93b984d46975bf38aa878b622.images (2).jpg"
    print(f"Fetching source prescription image from s3://{settings.S3_BUCKET_NAME}/{s3_key}...")
    s3_obj = s3.get_object(Bucket=settings.S3_BUCKET_NAME, Key=s3_key)
    image_bytes = s3_obj["Body"].read()
    print(f"Downloaded {len(image_bytes)} bytes.")

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        print("\nSending POST /api/v1/prescriptions...")
        t0 = time.perf_counter()
        files = {"file": ("handwritten_rx_test.jpg", image_bytes, "image/jpeg")}
        headers = {"X-Request-ID": "test-handwritten-duration-001"}

        resp = await client.post("/api/v1/prescriptions", files=files, headers=headers, timeout=60.0)
        elapsed = time.perf_counter() - t0
        print(f"POST response status: {resp.status_code} in {elapsed:.2f}s")
        assert resp.status_code == 201, f"Failed: {resp.text}"

        data = resp.json()
        print("\n--- Prescription Response Summary ---")
        print(f"Prescription ID: {data['prescription_id']}")
        print(f"Status: {data['status']}")
        print(f"Requires Review: {data['requires_review']}")
        print(f"Safety Reasons: {data['safety_reasons']}")
        print(f"Medication Count: {len(data['medications'])}")

        print("\n--- Extracted & Normalized Posology ---")
        for idx, med in enumerate(data["medications"], 1):
            dur = med["duration"]
            sch = med["schedule"]
            meal = med["meal_instruction"]
            st = med["strength"]
            print(f"\nMedication #{idx}: {med['drug_name']}")
            print(f"  - Verified Safe: {med['is_verified_safe']}")
            print(f"  - Requires Review: {med['requires_review']}")
            print(f"  - Strength: {st['value']} {st['unit']} (raw: '{st['raw_text']}')")
            print(f"  - Duration: {dur['value']} {dur['unit']} (raw: '{dur['raw_text']}')")
            print(f"  - Schedule: raw='{sch['raw_text']}' (M={sch['morning']}, A={sch['afternoon']}, E={sch['evening']}, N={sch['night']})")
            print(f"  - Food Relation: before={meal['before_meal']}, after={meal['after_meal']} (raw: '{meal['raw_text']}')")

        # 1. Verify durations are extracted and validated
        durations = {med["drug_name"].lower(): med["duration"] for med in data["medications"]}
        print("\n--- Validating Expected Durations ---")
        for name, dur in durations.items():
            print(f"Checking '{name}': value={dur['value']}, unit={dur['unit']}, raw='{dur['raw_text']}'")
            if "augmentin" in name or "enzflam" in name or "pan" in name:
                assert dur["value"] == 5, f"Expected 5 days for {name}, got {dur['value']}"
                assert dur["unit"] == "days", f"Expected 'days' for {name}, got {dur['unit']}"
            elif "hexigel" in name:
                assert dur["value"] == 7, f"Expected 7 days (1 week) for {name}, got {dur['value']}"
                assert dur["unit"] == "days", f"Expected 'days' for {name}, got {dur['unit']}"

        # 2. Verify Top-Level Status Consistency
        has_review = any(m["requires_review"] or not m["is_verified_safe"] for m in data["medications"])
        if has_review:
            assert data["status"] == "REQUIRES_REVIEW", f"Top-level status must be REQUIRES_REVIEW, got {data['status']}"
            assert data["requires_review"] is True
        else:
            assert data["status"] == "COMPLETED", f"Top-level status must be COMPLETED, got {data['status']}"
            assert data["requires_review"] is False

        print("\nALL INVARIANTS AND DURATIONS VERIFIED SUCCESSFULLY!")


if __name__ == "__main__":
    asyncio.run(test_handwritten_rx_e2e())
