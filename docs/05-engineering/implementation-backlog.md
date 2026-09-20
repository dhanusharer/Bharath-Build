# Implementation Backlog & Engineering Roadmap

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Status**: Ready for Sprint Planning (Post-Phase 0 Sign-Off)  
**Priority Legend**:
* **P0**: Blocking Foundation (Architecture, contracts, safety core)
* **P1**: Core MVP Capabilities (Extraction, normalization, voice query, audio playback)
* **P2**: Enhancements & Regional Optimizations
* **P3**: Future Scale & Optional Capabilities

---

## 1. Backlog Summary Matrix

| Issue ID | Priority | Title | Estimated Complexity | Safety Impact |
| :--- | :---: | :--- | :---: | :---: |
| **ISSUE-001** | **P0** | Core Domain Models & Pydantic Validation Engine | M (3 pts) | **Critical** |
| **ISSUE-002** | **P0** | Deterministic Posology Normalization Engine | L (5 pts) | **Critical** |
| **ISSUE-003** | **P0** | Fail-Closed Safety Gate & Uncertainty Tripwire | M (3 pts) | **Critical** |
| **ISSUE-004** | **P0** | FastAPI Application Scaffold, Middleware & OpenAPI | M (3 pts) | Low |
| **ISSUE-005** | **P0** | PostgreSQL Persistence Layer & Alembic Migrations | M (3 pts) | Medium |
| **ISSUE-006** | **P1** | Amazon S3 Storage Adapter & Pre-Signed URL Pipeline | S (2 pts) | Low |
| **ISSUE-007** | **P1** | Amazon Bedrock Multimodal Extraction Adapter | L (5 pts) | **Critical** |
| **ISSUE-008** | **P1** | TTS Provider Abstraction Port & Polly Hindi Adapter | M (3 pts) | Medium |
| **ISSUE-009** | **P1** | Amazon Transcribe STT & Regional Audio Ingestion | M (3 pts) | Medium |
| **ISSUE-010** | **P1** | Voice Intent Resolver & Data-Bound Fact Querying | L (5 pts) | **Critical** |
| **ISSUE-011** | **P1** | Next.js Vernacular Web UI (Mobile-Responsive) | L (5 pts) | Medium |
| **ISSUE-012** | **P2** | Regional Kannada TTS Provider Adapter Integration | M (3 pts) | Medium |
| **ISSUE-013** | **P2** | PrescriptionBench-v1 Automated CI Regression Runner | L (5 pts) | High |
| **ISSUE-014** | **P3** | Pharmacist Verification & Manual Override Portal | XL (8 pts) | Medium |

---

## 2. Detailed GitHub-Ready Issue Specifications

### ISSUE-001: Core Domain Models & Pydantic Validation Engine
* **Priority**: P0 (Blocking Foundation)
* **Complexity**: Medium (3 points)
* **Safety Impact**: **Critical**
* **Dependencies**: None
* **Description**: Implement the strongly typed domain models in `core/domain/models.py` using Pydantic v2. Defines `RawPrescriptionExtraction`, `NormalizedMedication`, `ValidatedMedication`, and `AuditEvent` conforming to `docs/03-ai/extraction-schema.md`.
* **Acceptance Criteria**:
  1. All models enforce strict type validation and raise `ValidationError` on type mismatch.
  2. Bounded numeric constraints enforce `0.0 <= confidence <= 1.0` and `0 <= frequency_per_day <= 10`.
  3. Deserialization benchmarks confirm < 5ms validation overhead per 10 medications.
  4. 100% unit test coverage on model serialization/deserialization.

---

### ISSUE-002: Deterministic Posology Normalization Engine
* **Priority**: P0 (Blocking Foundation)
* **Complexity**: Large (5 points)
* **Safety Impact**: **Critical**
* **Dependencies**: ISSUE-001
* **Description**: Implement the deterministic clinical abbreviation and timing parser in `core/domain/normalizer.py`. Formulates compiled regex rules mapping Indian shorthand (`1-0-1`, `OD`, `BD`, `TDS`, `SOS`, `BBF`, `PC`) to standard morning/afternoon/evening/night intervals.
* **Acceptance Criteria**:
  1. All patterns specified in `docs/03-ai/normalization-rules.md` parse into exact integer slot values.
  2. Any non-standard pattern (e.g. `1-?-1`) sets `timing_uncertain = true` and `requires_review = true`.
  3. No probabilistic logic or external network calls are present.
  4. 100% unit test line and branch coverage across all shorthand variations.

---

### ISSUE-003: Fail-Closed Safety Gate & Uncertainty Tripwire
* **Priority**: P0 (Blocking Foundation)
* **Complexity**: Medium (3 points)
* **Safety Impact**: **Critical**
* **Dependencies**: ISSUE-001, ISSUE-002
* **Description**: Build the authoritative safety gate in `core/domain/safety_gate.py`. Evaluates medication items and transitions prescription status. If confidence is below threshold (`0.85`), or if dosage is missing/null, safely transitions record to `REQUIRES_HUMAN_REVIEW` and blocks insertion into the verified presentation view.
* **Acceptance Criteria**:
  1. If `drug_name` or `dose_value` is `null`, record is barred from `ValidatedMedication`.
  2. Passes all adversarial scenarios in `docs/04-safety/unsafe-input-catalog.md`.
  3. Emits explicit, auditable violation codes for every rejected field.
  4. Zero-guess invariant verified with 100% unit test coverage.

---

### ISSUE-004: FastAPI Application Scaffold, Middleware & OpenAPI
* **Priority**: P0 (Blocking Foundation)
* **Complexity**: Medium (3 points)
* **Safety Impact**: Low
* **Dependencies**: None
* **Description**: Establish the FastAPI ASGI service structure, dependency injection containers, correlation tracing middleware (`X-Request-ID`, `traceparent`), standard error handlers, and `/health` and `/ready` probes conforming to `docs/02-architecture/api-contract.md`.
* **Acceptance Criteria**:
  1. Requests without `X-Request-ID` are automatically assigned a UUIDv4.
  2. Global exception handlers catch unhandled errors and format uniform error JSON shapes.
  3. OpenAPI 3.1 documentation is auto-generated at `/docs`.
  4. Integration tests verify `/health` returns 200 OK.

---

### ISSUE-005: PostgreSQL Persistence Layer & Alembic Migrations
* **Priority**: P0 (Blocking Foundation)
* **Complexity**: Medium (3 points)
* **Safety Impact**: Medium
* **Dependencies**: ISSUE-001
* **Description**: Setup SQLAlchemy 2.0 Async declarative tables (`prescriptions`, `raw_extractions`, `normalized_medications`, `validated_medications`, `audit_events`), `asyncpg` engine connection pools, and initial Alembic migrations.
* **Acceptance Criteria**:
  1. Relational foreign-key cascade behaviors enforced.
  2. Raw extraction payloads preserved verbatim in JSONB columns.
  3. Alembic `upgrade head` and `downgrade -1` execute cleanly without schema drift.
  4. Integration tests verify transaction rollbacks on failure.

---

### ISSUE-006: Amazon S3 Storage Adapter & Pre-Signed URL Pipeline
* **Priority**: P1 (Core MVP)
* **Complexity**: Small (2 points)
* **Safety Impact**: Low
* **Dependencies**: ISSUE-004
* **Description**: Implement `IObjectStore` port and `S3StorageAdapter` in `infrastructure/adapters/s3.py`. Implements pre-signed URL generation for direct client uploads with 15-minute expiration and MIME type restrictions.
* **Acceptance Criteria**:
  1. Issues signed `PUT` URLs restricted to `image/jpeg`, `image/png`, and `image/webp`.
  2. Verifies object existence and calculates SHA-256 checksum upon upload completion.
  3. Integration tests verify operation against LocalStack S3 fixture.

---

### ISSUE-007: Amazon Bedrock Multimodal Extraction Adapter
* **Priority**: P1 (Core MVP)
* **Complexity**: Large (5 points)
* **Safety Impact**: **Critical**
* **Dependencies**: ISSUE-001, ISSUE-004, ISSUE-006
* **Description**: Implement `IPrescriptionExtractor` using `boto3` Bedrock Runtime client. Invokes Claude 3.5 Sonnet with rigid system prompt (`docs/03-ai/prompt-specification.md`) and JSON Schema. Deserializes raw responses into `RawPrescriptionExtraction`.
* **Acceptance Criteria**:
  1. Configures `temperature = 0.0` and enforcement of JSON Schema.
  2. Timeouts enforced at 12.0s with circuit breaker instrumentation.
  3. Captures model latency, prompt version, and token usage into audit log.
  4. Integration tests verify successful extraction on golden image fixtures.

---

### ISSUE-008: TTS Provider Abstraction Port & Polly Hindi Adapter
* **Priority**: P1 (Core MVP)
* **Complexity**: Medium (3 points)
* **Safety Impact**: Medium
* **Dependencies**: ISSUE-004
* **Description**: Implement `ITTSProvider` port and `PollyTTSAdapter` in `infrastructure/adapters/polly.py`. Implements Hindi synthesis using Amazon Polly Neural voice `Kajal`. Includes `MockTTSAdapter` for CI/local development.
* **Acceptance Criteria**:
  1. Hindi text is successfully synthesized to MP3 audio stream via Polly.
  2. Generated audio stream is stored in S3 and pre-signed GET URL is returned.
  3. Provider selection factory delegates to mock in test environment.
  4. Unit tests verify adapter error handling and circuit breaking.

---

### ISSUE-009: Amazon Transcribe STT & Regional Audio Ingestion
* **Priority**: P1 (Core MVP)
* **Complexity**: Medium (3 points)
* **Safety Impact**: Medium
* **Dependencies**: ISSUE-004
* **Description**: Implement `ISpeechToTextProvider` and `TranscribeAdapter` in `infrastructure/adapters/transcribe.py`. Transcribes incoming audio streams for `hi-IN` and `kn-IN` with word-level confidence evaluation.
* **Acceptance Criteria**:
  1. Transcribes 16kHz WAV/MP3 audio streams into text.
  2. Transcripts with confidence < 0.70 are flagged as inaudible.
  3. Integration tests verify transcription on benchmark audio fixtures.

---

### ISSUE-010: Voice Intent Resolver & Data-Bound Fact Querying
* **Priority**: P1 (Core MVP)
* **Complexity**: Large (5 points)
* **Safety Impact**: **Critical**
* **Dependencies**: ISSUE-003, ISSUE-005, ISSUE-008, ISSUE-009
* **Description**: Implement `ResolveVoiceQueryUseCase`. Matches user transcription against verified prescription data. Restricts allowed queries to meal timing, schedule times, and duration. Intercepts clinical/diagnostic questions and responds with standardized spoken disclaimers.
* **Acceptance Criteria**:
  1. Answers meal timing questions strictly using verified `after_meal` / `before_meal` flags.
  2. Zero external LLM web search or speculative clinical advice generated.
  3. Safely refuses diagnostic inquiries (e.g. "Will this cure my infection?") with fixed disclaimers.
  4. 100% test pass on voice adversarial vectors in `docs/04-safety/unsafe-input-catalog.md`.

---

### ISSUE-011: Next.js Vernacular Web UI (Mobile-Responsive)
* **Priority**: P1 (Core MVP)
* **Complexity**: Large (5 points)
* **Safety Impact**: Medium
* **Dependencies**: ISSUE-004, ISSUE-006, ISSUE-007, ISSUE-010
* **Description**: Build mobile-first responsive web client in Next.js. Features camera prescription photo capture, direct S3 upload, high-contrast vernacular medication cards, audio player with auto-play, and single-tap voice microphone interface.
* **Acceptance Criteria**:
  1. High-contrast, WCAG 2.1 AA compliant interface.
  2. Clear visual cues for verified (green) vs pharmacist-review-required (amber) medications.
  3. Audio playback controls with play/pause, scrub, and volume slider.
  4. Language toggle between Hindi and Kannada.

---

### ISSUE-012: Regional Kannada TTS Provider Adapter Integration
* **Priority**: P2 (Enhancement)
* **Complexity**: Medium (3 points)
* **Safety Impact**: Medium
* **Dependencies**: ISSUE-008
* **Description**: Implement dedicated regional Kannada TTS provider adapter behind `ITTSProvider` port to resolve Polly's lack of native Kannada neural synthesis.
* **Acceptance Criteria**:
  1. `ITTSProviderFactory` routes `kn-IN` synthesis to regional adapter.
  2. Synthesizes clear, audible Kannada speech for medication summary templates.
  3. Fallback to mock adapter if regional provider is unreachable.

---

### ISSUE-013: PrescriptionBench-v1 Automated CI Regression Runner
* **Priority**: P2 (Enhancement)
* **Complexity**: Large (5 points)
* **Safety Impact**: High
* **Dependencies**: ISSUE-003, ISSUE-007
* **Description**: Construct automated CI evaluation runner executing `PrescriptionBench-v1` on pull requests. Measures Unsafe Inference Rate (UIR), legibility recall, and latency.
* **Acceptance Criteria**:
  1. Automatically runs on changes to prompts or extraction schemas.
  2. Hard-fails CI build if UIR > 0.0%.
  3. Outputs summary markdown table in PR comment.
