# ADR-009: Fail-Closed Safety Behavior on Uncertainty

## Status
Accepted (Phase 0 Freeze)

## Context
When reading low-quality, blurry, torn, or highly cursive prescriptions, uncertainty is inevitable. Conventional user-facing applications frequently "fail open" or attempt "best-guess" defaults to maintain high completion rates and avoid frustrating the user. In medication management, a "best guess" is a critical clinical hazard.

## Decision
We enforce a strict **Fail-Closed Safety Policy across all system layers**.
* If any critical medication field (drug name, strength, dosage value, intake schedule) is missing, unreadable, smudged, or below the confidence threshold:
  1. The system explicitly records the field as `null`.
  2. The entity is flagged with `is_legible = false` and `requires_review = true`.
  3. The prescription state transitions to `REQUIRES_HUMAN_REVIEW`.
  4. The system safely refuses to generate actionable spoken dosage instructions.
  5. The system issues a localized verbal and visual warning instructing the user to retake the photo in better lighting or consult a licensed physician/pharmacist.
* Voice queries addressing an uncertain medication are immediately intercepted and safely refused.

## Alternatives Considered
1. **Best-Effort Guess with Disclaimer**: Outputting the most probable dosage while attaching a small disclaimer warning. Rejected because users (especially elderly or non-literate individuals listening to audio) will act upon the spoken number regardless of disclaimers.

## Consequences
* **Positive**: Patient safety is mathematically and architecturally prioritized above transaction volume; eliminates liability from hallucinated dosages.
* **Negative**: Higher refusal rate on poor-quality images; requires educating users to provide well-lit, steady photographs.
