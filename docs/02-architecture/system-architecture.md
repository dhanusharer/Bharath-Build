# System Architecture Document

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Architectural Style**: Hexagonal (Ports & Adapters) / Clean Architecture  
**Primary Language & Framework**: Python 3.12, FastAPI, Pydantic v2  

---

## 1. High-Level Architectural Decomposition

The system implements a decoupled, event-driven hexagonal architecture separating the core domain (prescription validation, posology normalization, safety rules) from infrastructure adapters (Amazon S3, Bedrock, Transcribe, Polly, and PostgreSQL).

```
+----------------------------------------------------------------------------------------------------+
|                                           PRESENTATION LAYER                                       |
|   +--------------------------------------------------------------------------------------------+   |
|   |                       Mobile-Responsive Web Application (Next.js / React)                  |   |
|   |   * Prescription Image Capture / Upload UI          * Audio Player & Voice Input Controls  |   |
|   |   * Vernacular High-Contrast Medication Cards        * Safe Refusal & Uncertainty Banners   |   |
|   +--------------------------------------------------------------------------------------------+   |
+--------------------------------------------------+-------------------------------------------------+
                                                   | HTTPS / W3C Traceparent
                                                   v
+--------------------------------------------------+-------------------------------------------------+
|                                          API GATEWAY & ROUTING                                     |
|   +--------------------------------------------------------------------------------------------+   |
|   |                              FastAPI REST Controller Layer                                 |   |
|   |   * POST /prescriptions     * POST /prescriptions/{id}/extract   * POST /voice/query       |   |
|   |   * GET /prescriptions/{id} * POST /audio/synthesize             * GET /health, /ready     |   |
|   +--------------------------------------------------------------------------------------------+   |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+-------------------------------------------------+
|                                        APPLICATION CORE (PORTS)                                    |
|   +---------------------------------------+   +------------------------------------------------+   |
|   |        Inbound Use Cases              |   |          Outbound Driven Ports (Interfaces)    |   |
|   |   - IngestPrescriptionUseCase         |   |   - IObjectStore (Upload/Download Presigned)   |   |
|   |   - ExtractPrescriptionUseCase        |   |   - IPrescriptionExtractor (Multimodal AI)     |   |
|   |   - ResolveVoiceQueryUseCase          |   |   - ISpeechToTextProvider (Audio -> Text)      |   |
|   |   - SynthesizePrescriptionAudioUseCase|   |   - ITTSProvider (Text -> Audio Synthesis)     |   |
|   |                                       |   |   - IPrescriptionRepository (PostgreSQL)       |   |
|   +---------------------------------------+   +------------------------------------------------+   |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+-------------------------------------------------+
|                                           DOMAIN LAYER                                             |
|   +--------------------------------------------------------------------------------------------+   |
|   |   * Entities: Prescription, MedicationExtraction, ValidatedMedication, VoiceSession        |   |
|   |   * Deterministic Normalizer: Indian Clinical Shorthand Parser (1-0-1, OD, BD, TDS)       |   |
|   |   * Deterministic Safety Gate: Fail-Closed Validator (Confidence & Legibility Tripwire)   |   |
|   |   * Vernacular Template Engine: Safe Deterministic Localizer (Hindi, Kannada)              |   |
|   +--------------------------------------------------------------------------------------------+   |
+--------------------------------------------------+-------------------------------------------------+
                                                   |
                                                   v
+--------------------------------------------------+-------------------------------------------------+
|                                        INFRASTRUCTURE ADAPTERS                                     |
|   +-------------------+  +-------------------+  +-------------------+  +-----------------------+   |
|   |   S3Adapter       |  |  BedrockAdapter   |  | TranscribeAdapter |  | PollyTTSAdapter       |   |
|   |   (boto3 S3 client|  |  (Claude 3.5      |  | (Streaming/batch  |  | (Neural Kajal - hi-IN)|   |
|   |    Presigned URLs)|  |   Structured JSON)|  |  hi-IN / kn-IN)   |  | RegionalTTSAdapter    |   |
|   +-------------------+  +-------------------+  +-------------------+  +-----------------------+   |
|   +--------------------------------------------------------------------------------------------+   |
|   |   PostgreSQL Repository Adapter (SQLAlchemy 2.0 Async + asyncpg + Alembic)                 |   |
|   +--------------------------------------------------------------------------------------------+   |
+----------------------------------------------------------------------------------------------------+
```

---

## 2. Core Pipelines & Responsibilities

### Pipeline 1: The Prescription Digitization Path
1. **Client**: Uploads image directly to Amazon S3 using a pre-signed PUT URL generated by the API.
2. **Bedrock Extraction Adapter**: Submits image binary to Amazon Bedrock (`anthropic.claude-3-5-sonnet`) with a rigid JSON Schema. Claude functions purely as a text and token recognizer.
3. **Pydantic Validation**: Deserializes the raw JSON into `RawPrescriptionExtraction`. If schema validation fails, rejects immediately.
4. **Deterministic Normalization Engine**: Inspects recognized tokens (e.g. `1-0-1`, `Tab`, `5 days`) and deterministically parses them into canonical schedule slots (`morning: 1`, `afternoon: 0`, `evening: 0`, `night: 1`).
5. **Deterministic Safety Gate**: Evaluates `is_legible`, confidence thresholds, and missing posology. If any field is ambiguous or missing, marks as `REQUIRES_HUMAN_REVIEW` and halts automatic guidance.
6. **Persistence**: Saves `RawPrescriptionExtraction`, `NormalizedMedication`, and `AuditEvent` to PostgreSQL in a single database transaction.
7. **Vernacular Translation & TTS Engine**: Generates a deterministic Hindi/Kannada spoken summary and synthesizes audio via the `TTSProvider`.

### Pipeline 2: The Voice Query Path
1. **Client**: Streams recorded question audio to API via `POST /api/v1/voice/query`.
2. **Transcribe Adapter**: Amazon Transcribe processes speech into raw text with confidence scores.
3. **Intent Matcher**: Classifies user query into safe intents (`QUERY_SCHEDULE`, `QUERY_MEAL_TIMING`, `QUERY_DURATION`, `DISALLOWED_CLINICAL`).
4. **Data-Bound Query Resolver**: If safe, pulls the pre-verified medication record from PostgreSQL and formats a precise, factual answer.
5. **TTS Synthesis**: Renders the answer into spoken vernacular audio via `TTSProvider` and returns both text and audio stream to client.

---

## 3. Component Responsibility Matrix

| Component | Layer | Primary Responsibility | Explicit Prohibitions |
| :--- | :--- | :--- | :--- |
| **Prescription Controller** | Presentation | HTTP request parsing, status codes, routing. | Must not execute business logic or call AWS directly. |
| **Deterministic Safety Gate** | Domain | Enforce fail-closed rules on confidence, legibility, and completeness. | Must never use probabilistic models to guess missing fields. |
| **Posology Normalizer** | Domain | Deterministically map shorthand (`1-0-1`, `OD`) to structured time slots. | Must not perform fuzzy autocorrect on unverified drug names. |
| **Bedrock Adapter** | Infrastructure | Interface with AWS Bedrock SDK, enforce JSON output constraints. | Must not make decisions on whether a drug is safe or verified. |
| **Transcribe Adapter** | Infrastructure | Execute speech-to-text with regional language parameters. | Must not infer missing speech tokens if audio is garbled. |
| **TTS Adapter** | Infrastructure | Provide clean audio synthesis across Polly and regional engines. | Must not modify or add words to the generated transcript script. |
| **Repository Adapter** | Infrastructure | Manage atomic transactions and schema persistence via SQLAlchemy. | Must not alter raw extraction logs during normalization updates. |

---

## 4. Provider Abstraction Architecture

To avoid vendor lock-in and address regional language disparities (e.g. Amazon Polly supporting Hindi Neural voices while Kannada requires custom or secondary regional TTS services), all external integrations use abstract base classes (Ports).

```python
# Conceptual Python Interface Definition (Domain Port)
from abc import ABC, abstractmethod
from typing import BinaryIO
from pydantic import BaseModel

class AudioSynthesisResult(BaseModel):
    audio_stream: bytes
    mime_type: str
    sample_rate_hz: int
    duration_seconds: float
    provider_name: str

class ITTSProvider(ABC):
    """Abstract Port for Text-to-Speech synthesis."""
    
    @abstractmethod
    async def synthesize(self, text: str, language_code: str) -> AudioSynthesisResult:
        """Synthesize text into speech for the target language."""
        pass

    @abstractmethod
    def supports_language(self, language_code: str) -> bool:
        """Check if this provider supports the requested language."""
        pass
```

### Factory and Provider Selection
* For `language_code == "hi-IN"`: Routed by default to `PollyTTSAdapter` (Engine: Neural, VoiceId: `Kajal`).
* For `language_code == "kn-IN"`: Routed to `RegionalKannadaTTSAdapter` (or `MockTTSAdapter` in local/CI environments).
* In all cases, domain services invoke only `ITTSProvider.synthesize()` without knowing the concrete vendor.
