# Multimodal Medication Accessibility System
## Bharat Builds / First Commit in Collaboration with AWS

An AI-powered, safety-first assistive system designed to digitize handwritten medical prescriptions and provide voice-enabled accessibility in Indian regional languages (Hindi and Kannada).

> [!IMPORTANT]
> **Safety Core Tenet**: AI recommends/extracts. Deterministic code validates. The system never guesses.  
> This system is strictly an accessibility and educational aid. It is **NOT** a clinical diagnosis system, a physician replacement, or a prescription modification engine.

---

## Repository Structure

```
.
├── backend/                  # FastAPI Python 3.12 Backend API
│   ├── app/
│   │   ├── api/v1/          # Versioned API routes & health probes
│   │   ├── core/            # Configuration & BaseSettings
│   │   └── schemas/         # Pydantic v2 domain & contract models
│   ├── tests/               # Pytest async test suite
│   ├── Dockerfile           # Multi-stage production container
│   └── pyproject.toml       # Dependencies, Ruff, Mypy & Pytest configuration
│
├── frontend/                 # Next.js 14 App Router UI
│   ├── src/app/             # Pages, layouts & global styling
│   ├── Dockerfile           # Multi-stage production container
│   ├── package.json         # React 18, Tailwind CSS, Lucide icons
│   └── tailwind.config.ts   # Accessibility high-contrast theme
│
├── infra/                    # Infrastructure & Local Development
│   ├── local/init-db.sql    # Local PostgreSQL bootstrap script
│   └── README.md            # Infrastructure specs & roadmap
│
├── docs/                     # Comprehensive Phase 0 Engineering Baseline
│   ├── 01-product/          # PRD, acceptance criteria, user journeys
│   ├── 02-architecture/     # System architecture, API contracts, AWS architecture
│   ├── 03-ai/               # Extraction schemas, normalization rules, prompt spec
│   ├── 04-safety/           # Safety specification, failure modes matrix
│   └── 05-engineering/      # Coding standards, testing strategy
│
├── docker-compose.yml        # Orchestrates Backend, Frontend, and PostgreSQL
└── .env.example              # Environment variable template
```

---

## Core Technologies
* **AI Extraction Port**: Amazon Bedrock (Claude 3.5 Sonnet Multimodal Vision)
* **Backend**: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy, `uv`, Ruff, Mypy
* **Frontend**: Next.js 14, React 18, TypeScript, Tailwind CSS
* **Persistence & Storage**: Amazon RDS PostgreSQL (local: PostgreSQL 16), Amazon S3
* **Voice & Audio**: Amazon Transcribe (Speech-to-Text), Provider-Agnostic TTS Adapter Port (Amazon Polly / regional engines)
* **Quality Assurance**: Pytest, Pytest-Asyncio, Ruff, Mypy (`strict = true`)

---

## Getting Started

### 1. Quick Start via Docker Compose
Run the entire stack locally with a single command:
```bash
# Clone and enter the repository
cd Bharath_Build

# Copy environment template
cp .env.example .env

# Launch database, backend API, and frontend
docker compose up --build
```

Services will be available at:
* **Frontend Web App**: [http://localhost:3000](http://localhost:3000)
* **Backend API**: [http://localhost:8000](http://localhost:8000)
* **Interactive API Docs (Swagger UI)**: [http://localhost:8000/docs](http://localhost:8000/docs)
* **Backend Health Probe**: [http://localhost:8000/health](http://localhost:8000/health)
* **PostgreSQL Database**: `localhost:5432`

---

### 2. Manual Local Setup

#### Backend Setup (Python 3.12 + `uv`)
```bash
cd backend

# Create virtual environment and activate
uv venv
# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

# Install dependencies with development tooling
uv pip install -e ".[dev]"

# Run tests
pytest

# Start development server
uvicorn app.main:app --reload --port 8000
```

#### Frontend Setup (Next.js 14 + Node 20)
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

---

## Phase 0 Documentation Deliverables

All Phase 0 design specifications are finalized in `docs/`:
1. [Product Requirements Document (PRD)](file:///docs/01-product/PRD.md)
2. [Acceptance Criteria (Gherkin Scenarios)](file:///docs/01-product/acceptance-criteria.md)
3. [System Architecture & Ports/Adapters](file:///docs/02-architecture/system-architecture.md)
4. [API Contract Specification (OpenAPI 3.1)](file:///docs/02-architecture/api-contract.md)
5. [AWS Cloud Architecture Specification](file:///docs/02-architecture/aws-architecture.md)
6. [Extraction Schema](file:///docs/03-ai/extraction-schema.md)
7. [Normalization Rules (Posology & Timing)](file:///docs/03-ai/normalization-rules.md)
8. [Clinical Safety Specification](file:///docs/04-safety/safety-specification.md)
9. [Failure Modes & Safe Refusal Matrix](file:///docs/04-safety/failure-modes.md)
10. [Engineering Coding Standards](file:///docs/05-engineering/coding-standards.md)

Refer to [CONTRIBUTING.md](CONTRIBUTING.md) and [ENGINEERING_PRINCIPLES.md](ENGINEERING_PRINCIPLES.md) for contribution rules and development philosophy.
