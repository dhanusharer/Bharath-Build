# ADR-003: Amazon S3 for Prescription Images and Audio Artifacts

## Status
Accepted (Phase 0 Freeze)

## Context
The application handles binary assets: prescription photographs (1 MB to 10 MB) and synthesized speech audio files (MP3/WAV, 100 KB to 2 MB). Streaming binary blobs through application API servers causes memory bloat, high network bandwidth consumption, and thread pool exhaustion.

## Decision
We adopt **Amazon S3 with Client-Side Direct Uploads via Pre-Signed URLs**.
* The API server never buffers image upload streams directly from the client. Instead, it issues a cryptographically signed, short-lived (15-minute expiration) S3 pre-signed `PUT` URL.
* The client uploads the binary directly to S3.
* S3 Lifecycle policies automatically transition or expire transient prescription images after 24 hours, adhering to data minimization best practices.
* Synthesized TTS audio files are cached in S3 under `/audio/{prescription_id}/` and served via pre-signed GET URLs.

## Alternatives Considered
1. **Direct API Multipart Upload**: Client uploads image binary to the FastAPI backend, which then writes to disk or S3. Rejected due to severe memory overhead and vulnerability to Denial of Service (DoS) attacks on the container runtime.
2. **Local Disk Storage on ECS Container**: Ephemeral, non-durable across container restarts, and cannot scale horizontally across multiple instances.

## Consequences
* **Positive**: Minimal memory footprint on API nodes; high durability (99.999999999%); offloads bandwidth; native AWS KMS encryption at rest.
* **Negative**: Requires two client-server roundtrips (1: Get Presigned URL, 2: Notify Backend of Upload Completion).
