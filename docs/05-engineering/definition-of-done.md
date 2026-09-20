# Definition of Ready (DoR) and Definition of Done (DoD)

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Standard**: Agile Quality Gates for Engineering & AI Safety  

---

## 1. Definition of Ready (DoR)

Before an engineering ticket or backlog issue can be moved into an active sprint (`In Progress`), it must satisfy the following criteria:

- [ ] **Functional Requirement Mapped**: Issue links to a specific `FR-XXX` or `NFR-XXX` identifier.
- [ ] **Acceptance Criteria Defined**: Specific, unambiguous BDD/Gherkin acceptance scenarios exist.
- [ ] **API / Data Contract Defined**: If the ticket alters API routes or schemas, the JSON/Pydantic contract is reviewed and documented in `docs/02-architecture/api-contract.md`.
- [ ] **Safety Implications Evaluated**: Ticket explicitly documents whether it touches posology, extraction, normalization, or voice intent. If safety-critical, the "Fail-Closed" behavior is explicitly specified.
- [ ] **Dependencies Identified**: Database migrations, external AWS API dependencies, or provider adapters are listed.
- [ ] **Testing Strategy Documented**: Test fixtures (including negative/ambiguous test vectors) are planned.

---

## 2. Definition of Done (DoD)

A task or pull request is considered `Done` and ready for merge to `main` only when all of the following requirements are satisfied:

### 2.1 Code Quality & Architecture
- [ ] **Code Implementation Complete**: Implementation adheres to Clean/Hexagonal Architecture guidelines in `docs/05-engineering/coding-standards.md`.
- [ ] **No Route Handler Logic**: API route handlers only parse parameters, invoke domain services, and return responses.
- [ ] **Dependency Inversion Enforced**: AWS SDK calls reside strictly in `infrastructure/` adapters behind domain ports.
- [ ] **Strict Typing**: Python code passes `uv run mypy --strict .` with zero errors. TypeScript code passes `npm run typecheck` with zero `any` types.
- [ ] **Linting & Formatting**: Passes `uv run ruff check .` and `uv run ruff format --check .` without warnings.

### 2.2 Testing & Verification
- [ ] **Unit Tests Passing**: All unit tests pass; line coverage is ≥ 85% for domain services and 100% for safety gates.
- [ ] **Integration Tests Passing**: LocalStack / Docker testcontainers pass for database and S3 interactions.
- [ ] **Negative / Failure Tests**: All error codes, timeouts, and unparseable inputs have automated tests verifying correct HTTP status codes.

### 2.3 Observability & Security
- [ ] **Correlation Tracing**: `request_id` and `trace_id` are propagated through all service calls.
- [ ] **Zero PHI in Logs**: Verified that no patient names, raw prescription images, or raw voice streams appear in stdout.
- [ ] **No Hardcoded Secrets**: Scanned with automated secret detector (e.g. `gitleaks` or Ruff).

### 2.4 Documentation & Review
- [ ] **Docs Updated**: If an API contract or schema changed, relevant files in `docs/` are updated.
- [ ] **Architectural Record**: An ADR is authored for any significant architectural shift.
- [ ] **Peer Review**: At least one senior peer review approval obtained.
- [ ] **CI Pipeline Green**: All GitHub Actions workflows pass cleanly.

---

## 3. Mandatory Addendum for Safety-Critical Features

If a ticket touches **Prescription Extraction, Posology Normalization, Safety Gates, or Clinical Voice Intent Classification**, it MUST additionally fulfill:

- [ ] **Zero Unsafe Inference Verification**: Tested against the adversarial test suite in `docs/04-safety/unsafe-input-catalog.md` with 0.0% guessed data on ambiguous inputs.
- [ ] **Uncertainty Propagation**: Confirmed that when an input token is ambiguous, `null` is persisted and `requires_review = true` is set.
- [ ] **Safe Spoken Refusal Verification**: Verified that the TTS generator emits a safe, non-actionable refusal phrase rather than a partial or speculative schedule.
- [ ] **Benchmark Evaluation**: `PrescriptionBench-v1` regression test run completed with zero safety regressions.
