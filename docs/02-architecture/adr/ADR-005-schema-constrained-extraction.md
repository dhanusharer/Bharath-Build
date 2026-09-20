# ADR-005: Schema-Constrained Extraction via Pydantic v2

## Status
Accepted (Phase 0 Freeze)

## Context
Generative models natively produce unstructured text. In a healthcare accessibility domain, unstructured responses introduce unpredictable formatting, conversational chit-chat, unparseable sentences, and hallucinated medical facts. We require guaranteed structured JSON representations of extracted prescription entities.

## Decision
We enforce **Schema-Constrained Extraction with Strict Pydantic v2 Validation**.
* Model prompts are paired with an explicit JSON Schema definition defining fields, enums, confidence bounds, and nullability.
* Claude 3.5 Sonnet is instructed to output strictly valid JSON conforming to the schema and nothing else.
* The backend immediately deserializes the response using `RawPrescriptionExtraction.model_validate_json(response, strict=True)`.
* Any output failing JSON parsing or schema validation triggers an immediate `EXTRACTION_FAILED` state; no fuzzy repair or guessing is performed on malformed outputs.

## Alternatives Considered
1. **Freeform Text with Regex Parsing**: Extracting raw clinical summaries and using regex to extract drug entities. Rejected due to extreme fragility, high error rates, and inability to capture relational confidence metadata.
2. **Tool / Function Calling (Bedrock Converse API)**: Viable alternative, but direct JSON Schema enforcement with system prompt instructions provides greater transparency, portability, and easier offline evaluation on static benchmarks.

## Consequences
* **Positive**: Guarantees strongly typed contracts at system boundaries; prevents syntax leakage into domain logic; enforces explicit confidence fields.
* **Negative**: If the model outputs an unexpected key or missing bracket, the request fails closed. Requires robust prompt engineering and automated regression testing.
