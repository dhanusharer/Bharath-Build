# ADR-006: Deterministic Normalization for Posology and Clinical Shorthand

## Status
Accepted (Phase 0 Freeze)

## Context
Prescriptions contain clinical abbreviations and shorthand notations that dictate life-critical timing (e.g. `1-0-1`, `0-0-1`, `OD`, `BD`, `TDS`, `QID`, `BBF`, `PC`, `AC`, `HS`). If we rely on the LLM to interpret these abbreviations into final medical instructions, we introduce probabilistic risks of interpretation hallucination, subtle semantic drift, or non-deterministic behavior across runs.

## Decision
We enforce a strict architectural boundary: **The LLM Extracts Raw Strings; Deterministic Code Normalizes**.
* The Multimodal Model is permitted only to extract the verbatim shorthand string (e.g., `"1-0-1"`, `"TDS"`) and mark its spatial confidence.
* A pure, deterministic normalization module (written in Python with 100% unit test coverage) maps the raw tokens to structured timing flags (`morning: 1`, `afternoon: 0`, `evening: 0`, `night: 1`).
* If a token does not match an approved, verified clinical regex pattern or normalization table, it is marked as `timing_uncertain: true` and flagged for human review. The system refuses to guess what the doctor intended.

## Alternatives Considered
1. **LLM-Based End-to-End Interpretation**: Letting the prompt instruct Claude to directly output morning, noon, and night integer counts. Rejected because probabilistic models can miscalculate or conflate ambiguous abbreviations without leaving an auditable rule trace.

## Consequences
* **Positive**: 100% predictable, auditable, and testable posology logic; changes to abbreviation mappings can be unit tested without running expensive foundation model inferences; complete separation of extraction from clinical rule enforcement.
* **Negative**: Requires maintaining a comprehensive dictionary and regular expression catalog of Indian clinical prescription shorthand patterns.
