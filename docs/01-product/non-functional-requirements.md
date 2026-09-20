# Non-Functional Requirements (NFR)

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Verification Status**: Targets & Engineering Baselines (Empirical Benchmarking Required in Phase 1)  

All performance requirements in this document represent measurable engineering targets under defined baseline conditions. Speculative claims (e.g. "instant execution") are strictly avoided; all targets must be validated through load and benchmark testing.

---

## 1. Latency & Performance

| ID | Metric / Area | Target Specification | Measurement Protocol / Benchmark Workload | Status |
| :--- | :--- | :--- | :--- | :--- |
| **NFR-001** | End-to-End Extraction Latency | **Target p95 ≤ 6.0s**, Target p50 ≤ 3.5s | Single page image (≤ 2 MB), standard resolution (1920x1080), measured from `POST /extract` initiation to complete validated JSON persistence. | **Engineering Target (Assumption)** |
| **NFR-002** | Voice Query Roundtrip Latency | **Target p95 ≤ 3.5s**, Target p50 ≤ 2.0s | Audio query (≤ 5s duration, 16kHz WAV) from microphone upload, Amazon Transcribe processing, intent matching, to initial TTS audio byte playback. | **Engineering Target (Assumption)** |
| **NFR-003** | TTS Synthesis Latency | **Target p95 ≤ 1.2s** | Synthesis of regional text script (≤ 150 characters) to first chunk audio delivery via Amazon Polly / regional adapter. | **Engineering Target (Assumption)** |
| **NFR-004** | API Gateway / Route Overhead | **p99 ≤ 50ms** | Internal framework execution time (FastAPI + Pydantic validation) excluding external AWS API network calls. | **Engineering Target** |

> [!NOTE]
> Foundation Model inference latencies via Amazon Bedrock (Claude 3.5 Sonnet) and speech processing via Amazon Transcribe depend heavily on AWS regional infrastructure (`ap-south-1`). These targets are provisional baselines to be verified during Phase 1 load testing.

---

## 2. Reliability & Availability

| ID | Parameter | Requirement Specification |
| :--- | :--- | :--- |
| **NFR-005** | Service Availability | Target 99.5% uptime during hackathon demonstration and pilot evaluation periods. |
| **NFR-006** | Fault Isolation & Graceful Degradation | An outage or degradation of the TTS audio service must not block visual rendering of the validated prescription data. The system must render the text card and display an audio playback retry button. |
| **NFR-007** | Circuit Breaking & Timeouts | Outgoing calls to AWS Bedrock and AWS Transcribe must enforce strict timeouts (Bedrock: 12.0s; Transcribe: 8.0s; Polly: 4.0s) with exponential backoff (max 2 retries) to prevent request pool exhaustion. |
| **NFR-008** | Idempotency | Extraction and voice query submission endpoints must support an `Idempotency-Key` header to prevent duplicate charge and processing on mobile network reconnects. |

---

## 3. Security, Privacy & Data Protection

| ID | Area | Requirement Specification |
| :--- | :--- | :--- |
| **NFR-009** | Encryption in Transit | All communications (client-to-server, server-to-AWS) must enforce TLS 1.3 (minimum TLS 1.2). Unencrypted HTTP traffic must be rejected. |
| **NFR-010** | Encryption at Rest | All Amazon S3 buckets storing prescription artifacts and RDS PostgreSQL volumes must be encrypted at rest using AWS KMS Customer Managed Keys (CMKs) or AWS-managed KMS keys (`aws/s3`, `aws/rds`). |
| **NFR-011** | Zero PHI in Application Logs | Application stdout/stderr logs, Datadog/CloudWatch metrics, and distributed traces must never contain raw prescription text, patient names, doctor identities, or voice audio streams. |
| **NFR-012** | IAM Least Privilege | Microservices and backend tasks must run under dedicated AWS IAM execution roles granting access strictly to specified S3 prefixes and Bedrock/Transcribe/Polly API actions. |
| **NFR-013** | Transient Storage Retention | Prescription image binaries stored in S3 bucket staging prefixes must be governed by S3 Lifecycle policies expiring objects after 24 hours unless explicitly preserved in an anonymized benchmark bucket. |

---

## 4. Accessibility & Vernacular Usability

| ID | Dimension | Requirement Specification |
| :--- | :--- | :--- |
| **NFR-014** | Visual Accessibility | Web UI must comply with WCAG 2.1 Level AA standards: minimum contrast ratio of 4.5:1 for standard text, 3:1 for large text, and support for 200% browser font scaling without loss of functionality. |
| **NFR-015** | Spoken Feedback First | Every visual state (loading, extraction success, validation error, safe refusal) must have an associated regional audio cue or spoken explanation. |
| **NFR-016** | Vernacular Script Fidelity | Localized text output in Devanagari (Hindi) and Kannada scripts must use correct Unicode normalization (NFC) and standard orthographic fonts (e.g., Noto Sans Devanagari / Noto Sans Kannada). |
| **NFR-017** | Single-Tap Interaction | Voice input triggers must be large, high-visibility touch targets (minimum 64x64 px) operable with a single tap or hold gesture suitable for tremor or motor-impaired elderly users. |

---

## 5. Observability & Maintainability

| ID | Capability | Requirement Specification |
| :--- | :--- | :--- |
| **NFR-018** | Distributed Tracing | Every user operation must be correlated using OpenTelemetry W3C `traceparent` headers, propagating the trace across API endpoints, S3 ingestion, and AI model invocations. |
| **NFR-019** | Structured JSON Logging | All application logs must be output in structured JSON format including `timestamp`, `level`, `request_id`, `trace_id`, `service`, `module`, and `error_code`. |
| **NFR-020** | Code Maintainability | Strict type safety enforced across the stack: Python backend must pass `mypy --strict`; Frontend must pass TypeScript strict checks with zero `any` types. Code coverage target: ≥ 85% for business logic and safety gates. |
