# syntax=docker/dockerfile:1.4
FROM python:3.12-slim AS builder

WORKDIR /app

# Install uv for fast dependency management
COPY --from=ghcr.io/astral-sh/uv:0.4.18 /uv /bin/uv

# Copy dependency specifications, project metadata, and app package
COPY pyproject.toml README.md ./
COPY app/ ./app/

# Install dependencies using uv into a virtual environment
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install --no-cache .

# ------------------------------------------------------------------------------
# Production Runner
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

WORKDIR /app

# Create non-privileged system user for container security
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /sbin/nologin -d /app appuser

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Copy application source code
COPY app/ /app/app/

# Set file ownership
RUN chown -R appuser:appgroup /app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/v1/health')" || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
