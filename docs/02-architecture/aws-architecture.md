# AWS Architecture & Cloud Infrastructure Specification

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Target AWS Region**: `ap-south-1` (Asia Pacific - Mumbai)  

Every AWS service is mapped to exactly one justified responsibility. No speculative services are included.

---

## 1. AWS Service Responsibility Matrix

```
+-----------------------------------------------------------------------------------------------------+
|                                          AWS CLOUD (ap-south-1)                                     |
|                                                                                                     |
|  +---------------------------+   +----------------------------+   +------------------------------+  |
|  |       Amazon S3           |   |       Amazon Bedrock       |   |       Amazon Transcribe      |  |
|  | Encrypted object storage  |   | Claude 3.5 Sonnet Vision   |   | Speech-to-Text for regional  |  |
|  | Prescriptions & Audio     |   | JSON-constrained inference |   | Hindi & Kannada queries      |  |
|  +---------------------------+   +----------------------------+   +------------------------------+  |
|                ^                               ^                                 ^                  |
|                |                               |                                 |                  |
|  +-------------+-------------------------------+---------------------------------+---------------+  |
|  |                       Compute: Amazon ECS with AWS Fargate (or AWS App Runner)                 |  |
|  |                       FastAPI Python 3.12 Containerized Stateless Backend                      |  |
|  +---------------------------------------------+-------------------------------------------------+  |
|                |                               |                                 |                  |
|                v                               v                                 v                  |
|  +---------------------------+   +----------------------------+   +------------------------------+  |
|  |   Amazon RDS PostgreSQL   |   |        Amazon Polly        |   |       AWS Secrets Manager    |  |
|  | Structured metadata, raw  |   | Neural Hindi TTS (Kajal)   |   | Database credentials and     |  |
|  | JSON & audit history      |   | Regional fallback adapter  |   | application encryption keys  |  |
|  +---------------------------+   +----------------------------+   +------------------------------+  |
|                                                                                                     |
|  +---------------------------+   +----------------------------+   +------------------------------+  |
|  |        AWS KMS            |   |          AWS IAM           |   |      Amazon CloudWatch       |  |
|  | Encryption at rest for    |   | Least-privilege roles for  |   | Operational metrics, alerts  |  |
|  | S3, RDS, and Secrets      |   | Task execution & S3 scopes |   | and sanitised audit logs     |  |
|  +---------------------------+   +----------------------------+   +------------------------------+  |
+-----------------------------------------------------------------------------------------------------+
```

---

## 2. Detailed Service Specifications

### 2.1 Amazon S3 (Simple Storage Service)
* **Why it exists**: Provides durable, scalable object storage for binary artifacts (prescription photos, generated MP3 audio clips).
* **What it stores/processes**: Binary images (`image/jpeg`, `image/png`) in `s3://medication-access-artifacts-dev/prescriptions/` and synthesized audio files in `/audio/`.
* **Security considerations**: Server-Side Encryption with AWS KMS (SSE-KMS). Bucket access blocked from public internet (`BlockPublicAccess: true`). Access granted strictly through short-lived pre-signed URLs (max 15 mins). S3 Lifecycle policy expires transient raw images after 24 hours.
* **Failure mode**: Network timeout, S3 503 SlowDown, or bucket permission error. Backend returns HTTP 503 and logs error with correlation ID.
* **Alternative considered**: Storing image blobs directly in PostgreSQL (`BYTEA`). Rejected due to database bloat, backup bottlenecks, and poor streaming performance.

### 2.2 Amazon Bedrock (Foundation Model Service)
* **Why it exists**: Serves state-of-the-art vision-language multimodal foundation models (`anthropic.claude-3-5-sonnet-20241022-v2:0`) via managed, serverless API endpoints within the Mumbai region (`ap-south-1`).
* **What it stores/processes**: Ingests base64/binary image bytes and system prompt instructions; outputs raw JSON extraction payloads constrained by JSON schema. Does not store prompt or response data (Zero Data Retention on Amazon Bedrock default API).
* **Security considerations**: TLS 1.3 in-transit; IAM role authentication via AWS SigV4; AWS PrivateLink VPC endpoint support.
* **Failure mode**: Bedrock model throttling (`ThrottlingException`), inference timeout (exceeding 12s), or content filter rejection. Handled by circuit breaker; triggers fail-closed error with HTTP 502/504.
* **Alternative considered**: Self-hosted open-weights vision model (e.g. Llama-Vision on EC2 G5 GPU instances). Rejected due to high static infrastructure costs, GPU provisioning latency, and operational overhead for hackathon MVP.

### 2.3 Amazon Transcribe (Speech-to-Text)
* **Why it exists**: Provides managed acoustic and language modeling for Indian English, Hindi (`hi-IN`), and regional speech recognition.
* **What it stores/processes**: Ingests user voice query audio bytes (16kHz WAV/MP3) and outputs text transcripts with word-level confidence scores.
* **Security considerations**: Data processed ephemerally; encrypted using KMS; IAM role access only.
* **Failure mode**: Audio unclear (`stt_confidence < 0.70`) or Transcribe API failure. System generates a localized spoken response asking the user to repeat their question.
* **Alternative considered**: Whisper self-hosted on FastAPI container. Rejected due to CPU inference latency (3-5 seconds on standard containers) and increased Docker container footprint.

### 2.4 Amazon RDS PostgreSQL
* **Why it exists**: Provides ACID-compliant relational storage for application state, medication records, session lifecycles, and append-only audit events.
* **What it stores/processes**: Relational tables (`prescriptions`, `normalized_medications`, `validated_medications`, `audit_events`, `voice_sessions`).
* **Security considerations**: Encryption at rest via KMS; private VPC subnet deployment (no public IP); SSL connection enforced (`sslmode=require`); IAM database authentication or rotating credentials managed via Secrets Manager.
* **Failure mode**: Database connection pool exhaustion or failover. Handled via asyncpg connection pool health checks and automatic retry on transient disconnects.
* **Alternative considered**: Amazon DynamoDB. Rejected because relational foreign-key integrity between extractions, normalizations, and audit events is critical for safety-gated verification.

### 2.5 Compute: Amazon ECS with AWS Fargate (or AWS App Runner)
* **Why it exists**: Runs the containerized Python 3.12 / FastAPI application in a serverless, managed container runtime without EC2 node management.
* **What it stores/processes**: Stateless business logic, deterministic parsing, Pydantic validation, and API routing.
* **Security considerations**: Read-only root filesystem; non-root container user (`UID 10001`); no inbound SSH access; security groups restrict ingress to port 8000 from Application Load Balancer (ALB).
* **Failure mode**: Task crash or Out-Of-Memory (OOM). ECS service auto-replaces failed tasks; ALB health check stops routing traffic until `/health` returns 200.
* **Alternative considered**: AWS Lambda. Considered, but cold starts with large Python libraries (Pydantic, SQLAlchemy, Pillow/OpenCV) can introduce 3-5 second latency spikes, violating our voice responsiveness targets.

### 2.6 Amazon Polly (Text-to-Speech)
* **Why it exists**: Provides high-quality neural speech synthesis for Hindi (`hi-IN`) using voice `Kajal`.
* **What it stores/processes**: Ingests plain text strings of validated medication instructions; returns MP3 audio streams.
* **Security considerations**: Transient processing; no storage of medical text on Polly servers.
* **Failure mode**: Polly service outage or language incompatibility. Handled by `TTSProvider` abstraction fallback.
* **Alternative considered / Kannada Note**: Amazon Polly does not currently support native Neural voices for Kannada (`kn-IN`). A provider abstraction is mandatory: Polly serves Hindi, while Kannada is delegated to a regional TTS provider adapter or mock engine during Phase 0/1.

### 2.7 AWS Secrets Manager & AWS KMS
* **Why it exists**: Secure storage and rotation of database passwords, API keys, and cryptographic encryption keys.
* **What it stores/processes**: Database connection strings, signing secrets. KMS manages customer master keys for S3, RDS, and CloudWatch.
* **Security considerations**: KMS key policies restrict decryption strictly to the ECS task execution role.
* **Failure mode**: Secrets retrieval timeout on startup. Container initialization halts immediately (fail-fast).

### 2.8 Amazon CloudWatch
* **Why it exists**: Centralized aggregation of container metrics (CPU, RAM, latency), access logs, and health alarms.
* **What it stores/processes**: Structured JSON application logs (with all PII scrubbed), latency metrics, and API error counts.
* **Security considerations**: CloudWatch Logs Data Protection policy configured to detect and mask potential PII/PHI patterns.

---

## 3. Verified Capabilities vs. Architecture Assumptions

| Service / Capability | Status | Evidence / Verification Notes |
| :--- | :--- | :--- |
| **Bedrock Claude 3.5 Sonnet in ap-south-1** | **Confirmed** | Claude 3.5 Sonnet v2 is generally available in AWS Mumbai (`ap-south-1`). |
| **Amazon Transcribe for Hindi (hi-IN)** | **Confirmed** | Fully supported with streaming and batch transcription. |
| **Amazon Transcribe for Kannada (kn-IN)** | **Confirmed** | Batch transcription is supported in `ap-south-1`. |
| **Amazon Polly Neural Voice for Hindi (hi-IN)** | **Confirmed** | Voice `Kajal` (Neural engine) is available and verified. |
| **Amazon Polly Neural Voice for Kannada (kn-IN)** | **Unsupported** | Polly does NOT offer a native Kannada voice. Architecture MUST use a provider abstraction port. |
| **Sub-4s Bedrock Multimodal Latency** | **Assumption** | In testing, multimodal calls typically range 2.5s to 5.5s depending on payload and token count. Requires empirical benchmarking. |
