# Engineering Principles

These twelve core engineering principles govern all architectural, design, algorithmic, and operational decisions for the multimodal medication accessibility system. Every pull request, design document, and automated test must comply with these tenets.

---

## 1. The LLM is Never an Authority
The Large Language Model / Multimodal Foundation Model is treated as an inherently untrusted, probabilistic transducer. It is an advisory extraction engine, not a clinical arbiter. Outputs from the model are hypotheses about what is written on a page or spoken in an audio clip. The model is never permitted to authorize medical decisions, validate medication safety, or bypass application-level gates.

## 2. Unknown Data Remains Unknown
Unknown is fundamentally distinct from `false`, `none`, `0`, or "inferred default". If an image feature, dosage notation, timing frequency, or duration is unreadable, smudged, cropped, or ambiguous, the field must be explicitly populated as `null` with uncertainty flags (`is_legible = false`, `requires_review = true`). The system must never hallucinate or invent defaults to complete a schema.

## 3. Never Guess Medication or Dosage
Drug names, strengths, dosage values, units, and intake frequencies have zero margin for probabilistic interpolation. If the model is 80% confident that an illegible cursive word is "Metformin", that is an unacceptable safety risk. The system strictly prohibits fuzzy guessing or autocorrecting unverified drug entities. Ambiguous tokens must fail closed and trigger human verification.

## 4. All AI Output is Schema Validated
Unstructured text responses from foundation models are strictly barred from entering internal service boundaries. Model invocations must produce structured output conforming to a versioned JSON schema. The payload is immediately parsed and verified using strict deterministic validators (Pydantic v2) with runtime type checking, range validation, and unknown field rejections before any downstream processing.

## 5. Deterministic Business Rules are Authoritative
All medical logic, interval normalization (e.g., mapping `1-0-1` to Morning and Night intake), safety gates, and eligibility checks reside exclusively in auditable, deterministic, unit-tested backend code. The LLM may extract raw strings, but deterministic parsers normalize them. If a conflict arises between model reasoning and deterministic safety checks, deterministic code unconditionally overrides.

## 6. Medical Facts are Separated from Presentation Language
Prescription facts (drug identity, numerical dosage, canonical timing schedules) are maintained in a structured, immutable domain model. Regional language presentation (Hindi, Kannada translation, conversational speech formatting) operates as a separate rendering layer. Localization logic translates only the presentation wrappers around verified domain facts, preventing semantic drift or translation hallucinations of medical entities.

## 7. Provider SDKs are Isolated Behind Adapters
Direct calls to third-party or cloud SDKs (Amazon Bedrock, Amazon Transcribe, Amazon Polly, alternative TTS providers) must not leak into core domain services or API route handlers. All external dependencies must implement versioned interface ports (e.g., `TTSProvider`, `SpeechToTextProvider`, `PrescriptionExtractor`). This enables automated unit testing with mock fixtures and frictionless provider substitution without rewriting domain logic.

## 8. Sensitive Data Must Not Appear in Logs
Protected Health Information (PHI) and Personally Identifiable Information (PII)—including raw prescription images, patient names, extracted medication lists, unmasked phone numbers, and voice audio payloads—are strictly prohibited from application logs, metrics labels, and telemetry traces. Logs record only correlation IDs (`request_id`, `trace_id`), status codes, error classifications, latency metrics, and sanitised operational metadata.

## 9. AI Results Must Be Traceable
Every AI-assisted operation must be fully auditable. System records must link the normalized extraction result to the exact `model_id`, `prompt_version`, `schema_version`, `raw_model_response_hash`, and invocation timestamp. Changes to prompts or models are treated with the same discipline as database schema migrations: versioned, tested, and tracked in version control.

## 10. Safety-Critical Behavior Must Be Automated and Tested
Safety rules are not aspirational guidelines; they are enforced by automated CI/CD test suites. Every identified failure mode, ambiguous handwriting pattern, dosage parsing edge-case, and safety refusal must be accompanied by regression tests. Test suites must include adversarial input catalogs, blurry image test vectors, and hallucination tripwires that break the build if safety checks fail.

## 11. Performance is Measured, Not Assumed
Performance claims (e.g., "fast response time") are unscientific without concrete metrics. Latencies for Bedrock multimodal inference, Transcribe streaming/batch jobs, and TTS synthesis must be instrumented, measured under benchmark workloads, and reported as percentiles (p50, p90, p95, p99). Latency targets are empirical goals verified by automated benchmarks, not speculative marketing statements.

## 12. The System Fails Closed When Critical Information is Uncertain
Whenever the system encounters illegible handwriting, contradictory dosage instructions, malformed AI responses, upstream service timeouts, or unhandled voice intents, it defaults to a safe, non-actionable state. It explicitly informs the user in their selected language that the prescription or audio could not be verified safely and instructs them to consult a qualified physician or pharmacist.
