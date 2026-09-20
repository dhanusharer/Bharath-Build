# Functional Requirements

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Standard**: Testable Requirement Specifications  

Each requirement is uniquely identified by `FR-XXX`, categorized, testable with clear acceptance conditions, and mapped to its safety impact.

---

## 1. Prescription Ingestion & Object Management

| ID | Requirement Statement | Test Verification Method | Safety Impact |
| :--- | :--- | :--- | :--- |
| **FR-001** | The system shall accept prescription images in JPEG, PNG, and WebP formats up to 10 MB in file size. | Automated integration test with valid and unsupported file MIME types. | Low |
| **FR-002** | The system shall generate time-bounded Amazon S3 pre-signed upload URLs with a maximum expiration of 15 minutes. | Unit test verifying URL structure, signature, and expiration timestamp. | Medium |
| **FR-003** | The system shall reject uploaded files that fail magic byte validation or exceed the 10 MB limit with an HTTP 400 response. | Test with corrupted headers, spoofed extensions, and oversized binaries. | Medium |
| **FR-004** | The system shall assign a unique UUIDv4 `prescription_id` to every uploaded document session. | Unit test verifying UUID RFC 4122 compliance and non-collision across 10k runs. | Low |

---

## 2. Multimodal Extraction & Schema Integrity

| ID | Requirement Statement | Test Verification Method | Safety Impact |
| :--- | :--- | :--- | :--- |
| **FR-005** | The system shall invoke Amazon Bedrock with a strict JSON Schema definition constraining output to the canonical `RawPrescriptionExtraction` schema. | Contract test asserting Bedrock output parses directly into Pydantic schema. | High |
| **FR-006** | The system shall preserve unreadable, missing, or smudged fields as `null` rather than guessing, interpolating, or substituting default values. | Benchmark evaluation test using blurred synthetic prescription test vectors. | **Critical** |
| **FR-007** | The system shall record a numerical confidence score (`0.00` to `1.00`) for each extracted drug name, dosage value, and timing parameter. | Schema test asserting `confidence` fields exist and are bounded between 0 and 1. | High |
| **FR-008** | The system shall flag any medication entity with `is_legible = false` and `requires_review = true` if model confidence is below the safety threshold (default: 0.85). | Automated unit test passing simulated low-confidence extraction payloads. | **Critical** |
| **FR-009** | The system shall preserve raw, unedited model outputs in the database for auditing and never overwrite them with normalized representations. | Database persistence test asserting raw payload remains unchanged post-normalization. | High |

---

## 3. Deterministic Normalization & Safety Gating

| ID | Requirement Statement | Test Verification Method | Safety Impact |
| :--- | :--- | :--- | :--- |
| **FR-010** | The system shall deterministically normalize recognized timing notation (e.g., `1-0-1`, `0-0-1`, `1-1-1`, `OD`, `BD`, `TDS`, `QID`, `HS`) into explicit intake flags (`morning`, `afternoon`, `evening`, `night`). | Table-driven unit test suite covering all standardized Indian prescription shorthand strings. | **Critical** |
| **FR-011** | The system shall reject ambiguous timing notations (e.g., `1-?-1`, unstandardized scribbles) and set `timing_uncertain = true` without guessing. | Unit test passing invalid timing string patterns. | **Critical** |
| **FR-012** | The system shall normalize dosage strengths into standardized metric units (`mg`, `mcg`, `g`, `ml`, `IU`) and reject unmapped units. | Unit test checking unit normalization dictionary and boundary failure states. | High |
| **FR-013** | The system shall enforce a deterministic safety gate that marks a prescription session as `FAILED_VALIDATION` if any extracted medication lacks both verified drug name and verified timing. | Integration test verifying state machine transitions when required fields are missing. | **Critical** |

---

## 4. Voice Processing & Speech-to-Text (STT)

| ID | Requirement Statement | Test Verification Method | Safety Impact |
| :--- | :--- | :--- | :--- |
| **FR-014** | The system shall accept user voice audio in WAV, MP3, and OGG formats sampled at 16 kHz or higher. | Audio ingestion integration test with varying container formats. | Low |
| **FR-015** | The system shall transcribe regional speech in Hindi (`hi-IN`) and Kannada (`kn-IN`) using Amazon Transcribe. | Audio fixture playback test asserting transcribed string matches ground truth phonetic transcript. | Medium |
| **FR-016** | The system shall reject audio transcriptions with an average confidence score below 0.70 with a request for repetition. | Unit test verifying low-confidence STT transcription triggers safe retry prompt. | Medium |

---

## 5. Voice Intent Processing & Question Answering

| ID | Requirement Statement | Test Verification Method | Safety Impact |
| :--- | :--- | :--- | :--- |
| **FR-017** | The system shall resolve voice intents strictly related to prescription information: `QUERY_SCHEDULE`, `QUERY_MEAL_TIMING`, `QUERY_DURATION`, and `QUERY_MEDICATION_LIST`. | Intent classification evaluation test on 100 benchmark regional language utterances. | High |
| **FR-018** | The system shall answer voice queries exclusively using the validated medication records associated with the user's active prescription session. | Security boundary test ensuring intent engine does not invoke general clinical web search or LLM common knowledge. | **Critical** |
| **FR-019** | The system shall safely refuse off-scope clinical questions (e.g., "What disease do I have?", "Can I double my dose?") with a standardized non-diagnostic disclaimer. | Adversarial intent prompt suite verifying refusal trigger and refusal message text. | **Critical** |
| **FR-020** | The system shall refuse to answer queries regarding any medication flagged with `requires_review = true` and instead direct the user to a pharmacist. | Unit test querying an unverified drug record in an active session. | **Critical** |

---

## 6. Text-to-Speech (TTS) & Regional Localization

| ID | Requirement Statement | Test Verification Method | Safety Impact |
| :--- | :--- | :--- | :--- |
| **FR-021** | The system shall implement a `TTSProvider` abstraction interface decoupling voice synthesis from specific vendor SDKs. | Architecture unit test ensuring business logic imports only abstract interface. | Low |
| **FR-022** | The system shall synthesize spoken output in Hindi (`hi-IN`) using Amazon Polly Neural voice (e.g., `Kajal`). | Integration test verifying synthesis produces playable MP3 audio stream for Hindi text. | Medium |
| **FR-023** | The system shall route Kannada (`kn-IN`) synthesis requests through a dedicated regional TTS provider adapter with fallback to mock/secondary engine. | Provider routing test asserting correct adapter execution based on language code. | Medium |
| **FR-024** | The system shall generate spoken medication schedules using strictly deterministic localized sentence templates rather than generative LLM translation. | Unit test verifying sentence templates substitute only validated entity values. | High |

---

## 7. Auditability & Observability

| ID | Requirement Statement | Test Verification Method | Safety Impact |
| :--- | :--- | :--- | :--- |
| **FR-025** | The system shall attach a unique `request_id` and OpenTelemetry-compliant `trace_id` to all incoming requests and propagate it through all services. | End-to-end trace propagation assertion test. | Medium |
| **FR-026** | The system shall record immutable audit logs for every extraction event containing `model_id`, `prompt_hash`, `raw_output_hash`, and validation state. | Audit table persistence verification test. | High |
| **FR-027** | The system shall scrub all raw patient PII, unmasked prescription images, and patient names from application stdout/stderr logs. | Log scrubber automated test verifying PII tokens are masked or omitted in logs. | High |
| **FR-028** | The system shall expose `/api/v1/health` and `/api/v1/ready` endpoints reporting the operational status of database connections, S3, and model endpoints. | HTTP probe test verifying 200 OK under healthy conditions and 503 upon dependency outage. | Medium |
