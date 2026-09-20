"""Live Bedrock Verification Script.

Executes a live verification attempt of the VisionExtractionPort against Amazon Bedrock
using the standard AWS credential chain.
Measures latency, validates against Phase 1 safety gates and normalizer,
and diagnoses any AWS-side access/permission blockers.
"""

import os
import sys
import time
from pathlib import Path

# Add backend directory to sys.path so app modules can be imported
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.providers.bedrock.config import BedrockProviderConfig  # noqa: E402
from app.providers.bedrock.exceptions import BedrockExtractionError  # noqa: E402
from app.providers.bedrock.prescription_extractor import BedrockPrescriptionExtractor  # noqa: E402
from app.services.prescription_extraction import PrescriptionExtractionService  # noqa: E402


def run_live_verification() -> None:
    settings = get_settings()

    image_path = BACKEND_DIR / "tests" / "fixtures" / "synthetic_prescription.png"
    if not image_path.exists():
        print(f"ERROR: Synthetic prescription image not found at {image_path}")
        sys.exit(1)

    with image_path.open("rb") as f:
        image_bytes = f.read()

    # Determine target model ID and region
    model_id = os.environ.get("BEDROCK_MODEL_ID", settings.BEDROCK_MODEL_ID)
    region = os.environ.get("AWS_REGION", settings.AWS_REGION)

    print("=" * 70)
    print("PHASE 2 LIVE BEDROCK VERIFICATION RUNNER")
    print("=" * 70)
    print(f"Target Model ID: {model_id}")
    print(f"Target AWS Region: {region}")
    print(f"Test Fixture: {image_path.name} ({len(image_bytes)} bytes, image/png)")
    print("-" * 70)

    config = BedrockProviderConfig(
        region_name=region,
        model_id=model_id,
        timeout_seconds=settings.BEDROCK_TIMEOUT_SECONDS,
        max_retries=settings.BEDROCK_MAX_RETRIES,
        temperature=settings.BEDROCK_TEMPERATURE,
        max_tokens=settings.BEDROCK_MAX_TOKENS,
    )

    extractor = BedrockPrescriptionExtractor(config=config)
    service = PrescriptionExtractionService(extractor=extractor)

    start_time = time.perf_counter()
    try:
        validated = service.process_image(
            image_bytes=image_bytes,
            mime_type="image/png",
            request_id="live-verif-001",
        )
        latency = (time.perf_counter() - start_time) * 1000

        print("STATUS: SUCCESS")
        print(f"Latency: {latency:.2f} ms")
        print(f"Overall Safety Status: {validated.overall_safety.status.value}")
        print(f"Is Certified Safe: {validated.overall_safety.is_safe}")
        print(f"Medications Extracted: {len(validated.medications)}")
        print("\nSanitized Verified Posology:")
        for idx, med in enumerate(validated.medications):
            norm = med.normalized
            print(f"  [{idx + 1}] Drug: {norm.drug_name}")
            print(f"      Safe: {med.is_verified_safe}")
            print(f"      Schedule: M={norm.morning}, A={norm.afternoon}, N={norm.night}")
            print(f"      Food: before={norm.before_meal}, after={norm.after_meal}")
            print(f"      Duration: {norm.duration_value} {norm.duration_unit}")

    except BedrockExtractionError as e:
        latency = (time.perf_counter() - start_time) * 1000
        print("STATUS: FAILED (Provider Error)")
        print(f"Latency: {latency:.2f} ms")
        print(f"Error Code: {e.error_code}")
        print(f"Message: {e.message}")
        print(f"Retryable: {e.retryable}")

    except Exception as e:
        latency = (time.perf_counter() - start_time) * 1000
        print(f"STATUS: FAILED (Unexpected Exception: {type(e).__name__})")
        print(f"Latency: {latency:.2f} ms")
        print(f"Error: {e}")


if __name__ == "__main__":
    run_live_verification()
