# Engineering Coding Standards & Quality Guidelines

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Applicability**: All Future Backend, Frontend, and Infrastructure Code  

---

## 1. Technology Stack Selection

### Backend Ecosystem
* **Runtime**: Python 3.12+ managed via `uv` (fast package resolution and virtual environment management).
* **Web Framework**: FastAPI (ASGI asynchronous REST architecture).
* **Validation & Schemas**: Pydantic v2 (compiled Rust core, strict mode enabled).
* **Database Access**: SQLAlchemy 2.0 (Async API with `asyncpg` driver).
* **Migrations**: Alembic (version-controlled migration scripts).
* **Testing**: `pytest`, `pytest-asyncio`, `pytest-cov`, `httpx`.
* **Linting & Formatting**: Ruff (enforcing PEP 8, import sorting, and flake8 rules).
* **Static Typing**: `mypy` running with `--strict`.

### Frontend Ecosystem
* **Framework**: Next.js 14+ (App Router, React 18/19).
* **Language**: TypeScript (strict mode enabled; `noImplicitAny: true`).
* **Styling**: Tailwind CSS with custom accessible high-contrast design tokens.
* **Client Validation**: Zod (for frontend form and API response deserialization).
* **Server State**: TanStack Query (React Query v5) for caching and optimistic updates.
* **Audio Playback**: Native Web Audio API / HTML5 Audio with fallback streaming handlers.

---

## 2. General Architectural & Code Hygiene Rules

### Rule 1: Zero Business Logic in API Route Handlers
API route handlers (controllers) are strictly responsible for:
1. Parsing HTTP request parameters and validating incoming payloads.
2. Invoking the appropriate application use case service via Dependency Injection.
3. Mapping domain results or exceptions to standard HTTP response shapes and status codes.
*Route handlers must never directly query the database or instantiate AWS clients.*

### Rule 2: Provider SDK Isolation (Dependency Inversion)
Direct calls to `boto3`, `botocore`, or third-party AI APIs are strictly banned from domain services.
* All external interactions must pass through abstract interface ports (e.g. `ITTSProvider`, `IPrescriptionExtractor`, `IObjectStore`).
* Concrete adapters reside exclusively in the `infrastructure/` package.

### Rule 3: Zero Secrets in Source Code
Hardcoding credentials, AWS access keys, database passwords, or JWT secrets in code or git commits is a zero-tolerance policy violation.
* All configuration must load from environment variables via Pydantic `BaseSettings`.
* Local development must use `.env` (git-ignored) copied from `.env.example`.

### Rule 4: Zero Sensitive Data (PII/PHI) in Logs
Application logs, metrics labels, and error traces must never output raw prescription images, patient names, unmasked mobile numbers, or raw voice transcripts.
* Use correlation identifiers (`request_id`, `prescription_id`) for tracing.
* Sensitive fields in domain objects must implement custom `__repr__` masking (e.g. `phone_number: '******1234'`).

### Rule 5: No Unexplained Magic Numbers
All numeric thresholds (e.g. confidence gate `0.85`, S3 pre-signed expiration `900`, Laplacian blur threshold `100.0`, maximum file size `10 * 1024 * 1024`) must be defined as named domain constants or loaded from typed settings.

### Rule 6: Mandatory Automated Tests for Safety Gating
Every change to normalization regexes, confidence evaluation gates, or prompt structures must be accompanied by unit tests covering:
1. Positive golden paths.
2. Boundary and edge conditions.
3. Negative and ambiguous fail-closed scenarios.
