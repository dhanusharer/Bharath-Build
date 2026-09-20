# API Contract Specification (OpenAPI 3.1 Compatible)

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Base URL**: `/api/v1`  
**Standard Headers**:
* `X-Request-ID`: UUIDv4 tracing identifier (required on all requests/responses)
* `X-Correlation-ID`: OpenTelemetry W3C distributed trace header
* `Idempotency-Key`: UUIDv4 preventing duplicate submission on write operations

---

## 1. Global Standard Error Response Shape

All error responses across all endpoints adhere to this uniform schema:

```json
{
  "error": {
    "code": "UNCERTAIN_POSOLOGY_DETECTED",
    "message": "The dosage information in the prescription could not be verified with certainty.",
    "details": [
      {
        "field": "medications[0].dose_value",
        "reason": "Token illegible or missing numerical dosage"
      }
    ],
    "request_id": "8f3e2b10-6c54-4a8b-9e2d-3f1a7b8c9d0e",
    "timestamp": "2026-09-19T09:15:00Z",
    "safe_action_required": "CONSULT_PHARMACIST"
  }
}
```

### Standard Error Code Registry
* `INVALID_IMAGE_PAYLOAD`: File not an accepted image format or corrupt headers.
* `FILE_SIZE_EXCEEDED`: Payload exceeds the 10 MB limit.
* `EXTRACTION_FAILED`: Bedrock inference error or upstream timeout.
* `UNCERTAIN_POSOLOGY_DETECTED`: Handwriting unreadable; safe refusal triggered.
* `TIMING_NORMALIZATION_FAILED`: Shorthand notation unrecognizable.
* `AUDIO_TRANSCRIPTION_FAILED`: Speech inaudible or low confidence score.
* `CLINICAL_ADVICE_DISALLOWED`: Query sought clinical diagnosis or medical modification.
* `PROVIDER_UNAVAILABLE`: Upstream AWS service (Transcribe/Polly/Bedrock) circuit open.

---

## 2. API Endpoints Contract

### 2.1 POST /api/v1/prescriptions
Initializes a prescription session and issues a secure pre-signed Amazon S3 upload URL.

#### Request Body
```json
{
  "file_name": "prescription_photo.jpg",
  "content_type": "image/jpeg",
  "file_size_bytes": 2451020,
  "language_preference": "hi-IN"
}
```

#### Response (HTTP 201 Created)
```json
{
  "prescription_id": "b9f7a83d-3c2e-4b61-9c8f-123456789abc",
  "status": "CREATED",
  "upload_url": "https://medication-access-artifacts-dev.s3.ap-south-1.amazonaws.com/prescriptions/b9f7a83d/image.jpg?AWSAccessKeyId=...&Signature=...&Expires=...",
  "upload_method": "PUT",
  "expires_in_seconds": 900,
  "created_at": "2026-09-19T09:14:00Z"
}
```

---

### 2.2 POST /api/v1/prescriptions/{id}/extract
Triggers multimodal Bedrock extraction, deterministic validation, normalization, and localized audio synthesis.

#### Request Headers
* `Idempotency-Key: 7b3a8c12-5f6e-4a9b-8c1d-0e1f2a3b4c5d`

#### Request Body
```json
{
  "language_preference": "hi-IN"
}
```

#### Response: Success (HTTP 200 OK)
```json
{
  "prescription_id": "b9f7a83d-3c2e-4b61-9c8f-123456789abc",
  "status": "VERIFIED",
  "requires_review": false,
  "language": "hi-IN",
  "medications": [
    {
      "medication_id": "med_01",
      "drug_name": "Metformin",
      "dosage_form": "TABLET",
      "strength": {
        "value": 500.0,
        "unit": "mg"
      },
      "schedule": {
        "morning": 1,
        "afternoon": 0,
        "evening": 0,
        "night": 1,
        "frequency_per_day": 2,
        "raw_shorthand": "1-0-1"
      },
      "meal_instruction": {
        "timing": "AFTER_MEAL",
        "raw_text": "after food"
      },
      "duration": {
        "value": 10,
        "unit": "DAYS",
        "raw_text": "10 days"
      },
      "is_legible": true,
      "requires_review": false
    }
  ],
  "audio_summary": {
    "audio_url": "https://medication-access-artifacts-dev.s3.ap-south-1.amazonaws.com/audio/b9f7a83d_hi.mp3?...",
    "duration_seconds": 14.2,
    "spoken_text": "डॉक्टर ने आपको मेटफॉर्मिन 500 मिलीग्राम की गोली दिन में दो बार, सुबह और रात को खाने के बाद, 10 दिनों तक लेने को लिखा है।"
  },
  "extracted_at": "2026-09-19T09:14:05Z"
}
```

#### Response: Safe Refusal / Ambiguity (HTTP 422 Unprocessable Entity)
```json
{
  "error": {
    "code": "UNCERTAIN_POSOLOGY_DETECTED",
    "message": "Doctor handwriting for dosage or medicine name is ambiguous or unreadable.",
    "prescription_id": "b9f7a83d-3c2e-4b61-9c8f-123456789abc",
    "status": "REQUIRES_HUMAN_REVIEW",
    "safe_spoken_message": {
      "language": "hi-IN",
      "text": "पर्चे में लिखी दवा की मात्रा स्पष्ट नहीं है। कृपया स्पष्ट फोटो लें या फार्मासिस्ट से पूछें।",
      "audio_url": "https://medication-access-artifacts-dev.s3.ap-south-1.amazonaws.com/audio/refusal_b9f7a83d_hi.mp3?..."
    }
  }
}
```

---

### 2.3 GET /api/v1/prescriptions/{id}
Fetches the current status and verified records of a prescription.

#### Response (HTTP 200 OK)
Returns the same body schema as Section 2.2.

---

### 2.4 POST /api/v1/voice/transcribe
Direct utility endpoint to convert raw speech audio into text via Amazon Transcribe.

#### Request (Multipart Form Data)
* `audio_file`: Binary audio data (WAV/MP3/OGG)
* `language_code`: `hi-IN` | `kn-IN`

#### Response (HTTP 200 OK)
```json
{
  "transcript": "दवा कब लेनी है",
  "confidence": 0.96,
  "language_code": "hi-IN",
  "duration_seconds": 2.4
}
```

---

### 2.5 POST /api/v1/voice/query
Processes a spoken or text question against an active verified prescription session.

#### Request Body
```json
{
  "prescription_id": "b9f7a83d-3c2e-4b61-9c8f-123456789abc",
  "query_text": "खाना खाने से पहले या बाद में?",
  "language_code": "hi-IN"
}
```

#### Response: Verified Answer (HTTP 200 OK)
```json
{
  "query_id": "q_789456",
  "intent": "QUERY_MEAL_TIMING",
  "is_safe": true,
  "spoken_answer": "मेटफॉर्मिन दवा खाने के बाद सुबह और रात को लेनी है।",
  "audio_url": "https://medication-access-artifacts-dev.s3.ap-south-1.amazonaws.com/audio/q_789456.mp3?...",
  "referenced_medications": ["Metformin"]
}
```

#### Response: Disallowed Clinical Query (HTTP 200 OK with Clinical Disclaimer)
```json
{
  "query_id": "q_789457",
  "intent": "CLINICAL_ADVICE_DISALLOWED",
  "is_safe": false,
  "spoken_answer": "मैं केवल आपके पर्चे की जानकारी पढ़ सकता हूँ। इस चिकित्सीय प्रश्न के लिए कृपया डॉक्टर से परामर्श लें।",
  "audio_url": "https://medication-access-artifacts-dev.s3.ap-south-1.amazonaws.com/audio/disclaimer_789457.mp3?...",
  "referenced_medications": []
}
```

---

### 2.6 POST /api/v1/audio/synthesize
On-demand text-to-speech rendering via the provider abstraction port.

#### Request Body
```json
{
  "text": "ನಮಸ್ಕಾರ, ನಿಮ್ಮ ಔಷಧಿ ವಿವರಗಳನ್ನು ಇಲ್ಲಿ ಕೇಳಬಹುದು.",
  "language_code": "kn-IN"
}
```

#### Response (HTTP 200 OK)
```json
{
  "audio_url": "https://medication-access-artifacts-dev.s3.ap-south-1.amazonaws.com/audio/synth_123.mp3?...",
  "provider_used": "mock",
  "duration_seconds": 3.1
}
```

---

### 2.7 GET /api/v1/health & GET /api/v1/ready
Liveness and readiness probes for container orchestration (ECS / Kubernetes / App Runner).

#### GET /health (Liveness)
```json
{
  "status": "ALIVE",
  "timestamp": "2026-09-19T09:14:00Z"
}
```

#### GET /ready (Readiness - Checks DB connection, S3 bucket access, and AWS credentials)
```json
{
  "status": "READY",
  "dependencies": {
    "database": "UP",
    "s3_bucket": "UP",
    "bedrock_endpoint": "UP"
  },
  "timestamp": "2026-09-19T09:14:00Z"
}
```
