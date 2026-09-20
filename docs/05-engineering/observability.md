# Observability, Telemetry & Privacy-Preserving Audit Specification

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Standard**: Structured JSON Logging, OpenTelemetry Tracing, CloudWatch Metrics  

---

## 1. Structured JSON Logging Contract

All application logs must output single-line JSON strings to stdout. Every log event must contain standard correlation metadata and strictly omit Protected Health Information (PHI).

### Standard JSON Log Event Schema
```json
{
  "timestamp": "2026-09-19T09:14:05.123Z",
  "level": "INFO",
  "service": "medication-accessibility-api",
  "environment": "dev",
  "request_id": "b9f7a83d-3c2e-4b61-9c8f-123456789abc",
  "trace_id": "4bf92f3577b34da6a3ce929d0e0e4736",
  "span_id": "00f067aa0ba902b7",
  "event_name": "BEDROCK_EXTRACTION_COMPLETED",
  "module": "infrastructure.adapters.bedrock",
  "payload": {
    "prescription_id": "b9f7a83d-3c2e-4b61-9c8f-123456789abc",
    "model_id": "anthropic.claude-3-5-sonnet-20241022-v2:0",
    "prompt_version": "v1.0.0",
    "schema_version": "1.0.0",
    "duration_ms": 3210,
    "medications_extracted_count": 2,
    "all_legible": true,
    "status": "SUCCESS"
  }
}
```

---

## 2. Privacy-Preserving Log Redaction Protocol

> [!CAUTION]
> Under NO circumstance may raw prescription image base64 bytes, patient names, mobile numbers, raw doctor notes, or raw speech audio streams be emitted to application logs or metrics.

### Automated Redaction Filter
A custom Python `logging.Filter` (`core.observability.PIIFilter`) executes before log serialization:
1. Regex pattern matching against Indian phone numbers (`(\+91[\-\s]?)?[0]?(91)?[6789]\d{9}`).
2. Stripping of `raw_drug_line`, `image_bytes`, and `audio_stream` fields from logging dictionaries.
3. Replacing unauthorized keys with `"[REDACTED_PHI]"`.

---

## 3. Operational CloudWatch Metrics

The application emits custom metrics via AWS CloudWatch Embedded Metric Format (EMF):

| Metric Name | Unit | Dimensions | Description |
| :--- | :--- | :--- | :--- |
| `PrescriptionExtractionLatency` | Milliseconds | `ModelId`, `Status` | Total time spent in Amazon Bedrock inference. |
| `SafetyGateRefusalCount` | Count | `Reason`, `Language` | Incremented every time an unreadable prescription is safely refused. |
| `VoiceQueryLatency` | Milliseconds | `Language`, `Intent` | Round-trip latency for speech transcription and query answering. |
| `TTSProviderLatency` | Milliseconds | `Provider`, `Language` | Latency of audio synthesis by provider. |
| `UnsafeInferenceDetected` | Count | `PromptVersion` | Incremented if a safety assertion trips during post-processing. |

---

## 4. CloudWatch Alarms & Operational Thresholds

1. **Safety Gate Spike Alarm**: Triggers if `SafetyGateRefusalCount` exceeds 20% of total extractions over a 15-minute rolling window (indicates camera app defect or regional handwriting drift).
2. **Bedrock Latency Degradation**: Triggers if p95 `PrescriptionExtractionLatency` > 8.0s for 3 consecutive data points.
3. **HTTP 5xx Error Rate**: Triggers if 5xx responses exceed 1% of total API volume over 5 minutes.
