# Infrastructure Directory - Multimodal Medication Accessibility System

This directory houses infrastructure specifications, container orchestration configurations, and local development service setups.

## Structure
* `docker-compose.yml` (root): Orchestrates local PostgreSQL, FastAPI backend, and Next.js frontend.
* `local/init-db.sql`: Database initialization script for local development.
* `terraform/` or `cloudformation/` (Phase 1+): AWS infrastructure definitions for Amazon ECS/Fargate, RDS PostgreSQL, S3, IAM, KMS, and CloudWatch as specified in `docs/02-architecture/aws-architecture.md`.

## Local Development
To launch the full local development stack:
```bash
docker compose up --build
```
This boots:
* Backend API: `http://localhost:8000` (Swagger UI: `http://localhost:8000/docs`)
* Frontend Web App: `http://localhost:3000`
* PostgreSQL Database: `localhost:5432`
