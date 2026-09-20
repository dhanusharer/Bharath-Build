# ADR-002: PostgreSQL for Structured Application and Audit Data

## Status
Accepted (Phase 0 Freeze)

## Context
The system processes prescriptions through a pipeline of extraction, validation, and user querying. We must persist:
1. Session metadata and user preferences.
2. Raw, unedited AI model JSON outputs for auditability.
3. Normalized and verified medication records.
4. Tamper-evident audit events and safety refusal logs.

We need strong relational integrity (foreign keys between prescriptions, medications, and audit logs) combined with the flexibility to store semi-structured raw AI responses.

## Decision
We select **Amazon RDS PostgreSQL (version 16+) with SQLAlchemy 2.0 (Async) and Alembic**.
* PostgreSQL provides robust relational guarantees (ACID transactions, foreign key constraints) critical for medical record integrity.
* The `JSONB` data type allows us to store raw, unmodified AI extraction outputs and audit payloads alongside indexed relational columns without data distortion.
* Async connectivity is managed via `asyncpg` for non-blocking database queries.

## Alternatives Considered
1. **Amazon DynamoDB**: Exceptional horizontal scalability, but poor support for complex relational queries, schema migrations, and relational integrity constraints across extraction stages.
2. **MongoDB / DocumentDB**: Excellent for JSON documents, but weaker transaction semantics and lack of strict foreign-key integrity between normalized medications and validation gates.

## Consequences
* **Positive**: Enforces relational consistency; raw extraction payloads remain immutable in JSONB; seamless schema evolution using Alembic migrations; strong tooling support.
* **Negative**: Requires VPC subnet provisioning and connection pooling management compared to fully serverless DynamoDB.
