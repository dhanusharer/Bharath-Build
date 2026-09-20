# AI Extraction Schema & Data Contract Specification

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Schema Standard**: JSON Schema Draft 2020-12 & Pydantic v2  

---

## 1. Schema Pipeline Architecture: Three Distinct Layers

To guarantee auditability, safety, and non-destructive data flow, the system strictly separates prescription data into three distinct representations:

```
+-----------------------------------+
|       1. RAW EXTRACTION           |  <- Pure model perception (Probabilistic)
|  Verbatim strings, confidence,    |     Stores what the vision model saw.
|  nulls for illegible tokens       |     IMMUTABLE AUDIT RECORD
+-----------------+-----------------+
                  |
                  v  (Deterministic Normalizer)
+-----------------+-----------------+
|     2. NORMALIZED MEDICATION      |  <- Deterministic canonical representation
|  Parsed intervals (1-0-1 -> M,N), |     Standardized metric units (mg, ml)
|  derived duration days            |     TRANSITIONAL LOGIC RECORD
+-----------------+-----------------+
                  |
                  v  (Deterministic Safety Gate)
+-----------------+-----------------+
|      3. VALIDATED MEDICATION      |  <- Certified safe for presentation/voice
|  is_safe == true, review == false |     Only 100% verified posology is exposed
|  High-contrast UI / Spoken Audio  |     READ-ONLY TO USER & VOICE ENGINE
+-----------------------------------+
```

Raw extraction payloads are **never overwritten** during normalization or validation.

---

## 2. Layer 1: Canonical Raw Extraction Schema (Pydantic v2 / JSON Schema)

This schema defines the payload contract passed to Amazon Bedrock and validated immediately upon receipt.

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "RawPrescriptionExtraction",
  "type": "object",
  "required": ["schema_version", "overall_legibility", "medications"],
  "properties": {
    "schema_version": {
      "type": "string",
      "enum": ["1.0.0"]
    },
    "overall_legibility": {
      "type": "boolean",
      "description": "True if the general prescription document is decipherable."
    },
    "doctor_notes_raw": {
      "type": ["string", "null"],
      "description": "Verbatim doctor advice or clinical notes if present."
    },
    "medications": {
      "type": "array",
      "items": {
        "$ref": "#/$defs/RawMedicationItem"
      }
    }
  },
  "$defs": {
    "RawMedicationItem": {
      "type": "object",
      "required": [
        "raw_drug_line",
        "drug_name",
        "drug_name_confidence",
        "is_legible",
        "requires_review"
      ],
      "properties": {
        "raw_drug_line": {
          "type": "string",
          "description": "Exact verbatim line of text transcribed from the image."
        },
        "drug_name": {
          "type": ["string", "null"],
          "description": "Extracted pharmaceutical name. Must be null if illegible."
        },
        "drug_name_confidence": {
          "type": "number",
          "minimum": 0.0,
          "maximum": 1.0,
          "description": "Confidence score for drug name recognition."
        },
        "dosage_form": {
          "type": ["string", "null"],
          "description": "Tablet, Syrup, Capsule, Ointment, Injection, etc."
        },
        "strength_value": {
          "type": ["number", "null"],
          "description": "Numerical strength e.g., 500, 250, 5."
        },
        "strength_unit": {
          "type": ["string", "null"],
          "description": "mg, mcg, g, ml, IU."
        },
        "dose_quantity": {
          "type": ["string", "null"],
          "description": "e.g., '1 tablet', '5 ml', '2 drops'."
        },
        "raw_timing_shorthand": {
          "type": ["string", "null"],
          "description": "Verbatim notation e.g., '1-0-1', 'OD', 'BD', 'TDS', 'SOS'."
        },
        "raw_meal_instruction": {
          "type": ["string", "null"],
          "description": "Verbatim meal text e.g., 'after food', 'empty stomach', 'AC'."
        },
        "duration_value": {
          "type": ["number", "null"],
          "description": "Duration number e.g., 5, 10, 30."
        },
        "duration_unit": {
          "type": ["string", "null"],
          "description": "days, weeks, months."
        },
        "is_legible": {
          "type": "boolean",
          "description": "False if handwriting is smudged, clipped, or ambiguous."
        },
        "requires_review": {
          "type": "boolean",
          "description": "True if confidence is low or any critical posology is missing."
        },
        "extraction_notes": {
          "type": ["string", "null"],
          "description": "Reasoning for uncertainty (e.g. 'dosage digit blurred by fold')."
        }
      }
    }
  }
}
```

---

## 3. Layer 2: Normalized Medication Model (Python / Pydantic v2)

```python
from enum import Enum
from pydantic import BaseModel, Field

class MealTiming(str, Enum):
    BEFORE_MEAL = "BEFORE_MEAL"
    AFTER_MEAL = "AFTER_MEAL"
    WITH_MEAL = "WITH_MEAL"
    UNSPECIFIED = "UNSPECIFIED"

class NormalizedSchedule(BaseModel):
    morning: int = Field(default=0, ge=0, le=5)
    afternoon: int = Field(default=0, ge=0, le=5)
    evening: int = Field(default=0, ge=0, le=5)
    night: int = Field(default=0, ge=0, le=5)
    frequency_per_day: int = Field(ge=0, le=10)
    is_as_needed_sos: bool = False
    timing_uncertain: bool = False

class NormalizedMedication(BaseModel):
    normalized_id: str
    drug_name: str | None
    drug_confidence: float
    strength_value: float | None
    strength_unit: str | None
    schedule: NormalizedSchedule
    meal_timing: MealTiming
    duration_days: int | None
    is_legible: bool
    requires_review: bool
    normalization_errors: list[str] = []
```

---

## 4. Layer 3: Validated Medication Model (Authoritative Presentation Record)

```python
class ValidatedMedication(BaseModel):
    """Authoritative, read-only verified medication record for voice/UI."""
    medication_id: str
    drug_name: str
    strength_display: str | None  # e.g., "500 mg"
    schedule_display_hi: str      # Localized schedule string
    schedule_display_kn: str
    morning: int
    afternoon: int
    evening: int
    night: int
    meal_instruction: MealTiming
    duration_days: int | None
    is_safe: bool = True
    requires_review: bool = False
```

---

## 5. Schema Versioning Strategy

* **Semantic Versioning (`MAJOR.MINOR.PATCH`)**:
  * `MAJOR`: Breaking changes to field types, deletion of fields, or restructuring of definitions. Requires simultaneous database migration and Bedrock prompt update.
  * `MINOR`: Backward-compatible additions (e.g., adding an optional `route_of_administration` field).
  * `PATCH`: Non-functional metadata updates or documentation clarification.
* **Payload Enclave**: Every extraction request and persisted DB row records the exact `schema_version`.
* **Deprecation Policy**: Minimum 2 minor versions supported simultaneously during rolling blue/green deployments.
