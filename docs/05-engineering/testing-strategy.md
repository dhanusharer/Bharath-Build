# Comprehensive Testing Strategy & Quality Assurance Architecture

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Standard**: Multi-Layer Test Pyramid & Automated AI Evaluation  

---

## 1. The Multi-Layer Test Pyramid

```
                       / \
                      /   \
                     / E2E \       <-- Playwright browser tests, full audio-voice flows
                    /-------\
                   / Integr. \     <-- LocalStack AWS mocks, real PostgreSQL containers
                  /-----------\
                 /   Contract  \   <-- OpenAPI & Pydantic schema validation tests
                /---------------\
               /   AI Evaluation \ <-- Benchmark dataset (PrescriptionBench-v1), UIR tripwire
              /-------------------\
             /     Unit Tests      \ <-- Pure Python, posology normalizers, safety gates
            +-----------------------+
```

---

## 2. Test Layer Specifications

### 2.1 Unit Tests (Pure Domain & Safety Gates)
* **Scope**: Normalizer regex algorithms, Pydantic model serialization, safety gate state machines, and vernacular sentence template rendering.
* **Execution Environment**: Local CPU; execution time < 10 seconds for the entire suite.
* **Coverage Target**: Minimum 85% overall coverage; **100% mandatory coverage on `core/domain/safety_gate.py` and `core/domain/normalizer.py`**.
* **Mocking**: Pure Python mocks; zero network calls.

### 2.2 Contract Tests (API & Schema Boundaries)
* **Scope**: Verifies that FastAPI route definitions, OpenAPI 3.1 specifications, and Bedrock JSON Schemas remain strictly in sync.
* **Execution**: Schemathesis or pytest-contract testing against mock payloads.

### 2.3 Integration Tests (Infrastructure Adapters)
* **Scope**: Verifies interaction between infrastructure adapters and external services.
* **Execution Environment**: Uses `pytest-docker` or `testcontainers` for PostgreSQL and `moto` / `LocalStack` for S3 bucket interactions.
* **AWS Services Mocking**: Bedrock, Transcribe, and Polly are tested using recorded fixture cassettes (`vcrpy`) to prevent cloud costs and latency during CI.

### 2.4 End-to-End (E2E) Acceptance Tests
* **Scope**: Full browser flows: image upload -> extraction -> visual card render -> audio playback trigger -> voice query utterance -> spoken response.
* **Tooling**: Playwright headless browser testing with mock audio hardware devices.

### 2.5 Security & Vulnerability Tests
* **Static Application Security Testing (SAST)**: `bandit` scanning for insecure Python code patterns; `safety` and `pip-audit` scanning dependencies for CVEs.
* **Adversarial Input Fuzzing**: Feeding corrupted image payloads, huge binary streams, and prompt injection vectors to ensure fail-closed stability.

---

## 3. AI Evaluation Pipeline (PrescriptionBench-v1)

AI evaluation is integrated directly into the CI/CD pipeline as an automated regression suite.

### Evaluated Dimensions
1. **Unsafe Inference Rate (UIR)**: Evaluates whether the model hallucinates or guesses drug names/dosages on deliberately degraded images. **Tolerance: 0.0%**.
2. **Field-Level Exact Match**: Transcribed characters vs ground-truth clinical annotations.
3. **Legibility Recall**: Percentage of truly illegible tokens correctly marked with `is_legible = false`. Target ≥ 95%.
4. **Voice Intent Classification Accuracy**: Intent resolution on regional audio transcripts. Target ≥ 95%.
5. **Latency Profile**: End-to-end inference latency percentiles (p50, p90, p95).

*Note*: Benchmark datasets and empirical measurements will be executed in Phase 1; all targets above represent non-negotiable passing gates.
