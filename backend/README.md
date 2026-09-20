# Backend Service - Multimodal Medication Accessibility System

Stateless FastAPI REST API engineered to digitize handwritten prescriptions with deterministic safety gates and voice accessibility.

## Tech Stack
* **Python**: 3.12+
* **Framework**: FastAPI (ASGI)
* **Validation**: Pydantic v2
* **Package Management**: `uv`
* **Static Analysis & Formatting**: Ruff, Mypy (`strict = true`)
* **Testing**: Pytest & pytest-asyncio

## Getting Started

### Local Setup with uv
```bash
# Create virtual environment
uv venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/macOS:
source .venv/bin/activate

# Install dependencies in editable mode with development tools
uv pip install -e ".[dev]"

# Run dev server
uvicorn app.main:app --reload --port 8000
```

### Running Tests and Linting
```bash
# Run tests
pytest

# Run Ruff linter and formatter check
ruff check .
ruff format --check .

# Run Mypy static type checking
mypy app/
```

### Docker
```bash
docker build -t medication-accessibility-backend .
docker run -p 8000:8000 medication-accessibility-backend
```
