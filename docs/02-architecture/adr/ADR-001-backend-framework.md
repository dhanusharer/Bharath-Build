# ADR-001: Backend Framework Selection (FastAPI with Python 3.12)

## Status
Accepted (Phase 0 Freeze)

## Context
The system requires a backend framework capable of high-concurrency asynchronous I/O (handling image uploads, Bedrock invocations, Transcribe jobs, and audio streaming), native integration with modern data validation libraries, strict static typing, and first-class SDK support for AWS services (via `boto3` / `aioboto3`). The system is safety-critical: schema serialization and validation must be uncompromising.

## Decision
We select **Python 3.12 with FastAPI and Pydantic v2**.
* FastAPI provides asynchronous ASGI routing, automatic OpenAPI 3.1 documentation generation, and native integration with Pydantic v2.
* Pydantic v2 (compiled in Rust) provides high-performance runtime type checking, schema enforcement, and structured JSON parsing.
* Python 3.12 provides improved execution speed and modern typing syntax (PEP 695).

## Alternatives Considered
1. **Node.js / Express with TypeScript**: Fast and type-safe, but lacks native scientific/audio processing libraries and has fragmented AWS AI SDK ergonomics compared to Python.
2. **Go (Golang)**: Exceptional raw concurrency and binary size, but slower velocity for complex schema definitions and lack of rich AI evaluation/prompt testing ecosystem.
3. **Django Ninja**: Mature ORM, but heavier footprint and unnecessary overhead for our stateless microservice architecture.

## Consequences
* **Positive**: Rapid development velocity, native Pydantic v2 validation gates, deep compatibility with AWS Python SDKs, and clean type-hinting support with `mypy --strict`.
* **Negative**: Python requires careful async connection pool management (`asyncpg`) to avoid event-loop blocking during CPU-bound tasks (e.g. image hashing). CPU-intensive operations must run in thread pools (`run_in_threadpool`).
