# ADR-008: Treating Foundation Models as Untrusted Advisory Components

## Status
Accepted (Phase 0 Freeze)

## Context
Generative AI models, including advanced multimodal LLMs, operate via probabilistic token prediction. They lack inherent clinical judgment, can experience hallucinations, and can be influenced by prompt injection attacks or ambiguous image artifacts. In medical domains, an unvalidated hallucination (e.g. reading 5mg as 50mg, or confusing Metformin with Metoprolol) can lead to patient harm.

## Decision
We enforce the foundational architecture rule: **The LLM is an untrusted, advisory component**.
* The LLM's role is restricted to perceptual recognition (identifying character candidates from images or text utterances).
* The LLM is strictly prohibited from:
  1. Authorizing medication schedules.
  2. Autocorrecting or inventing missing dosage values.
  3. Generating autonomous medical recommendations or diagnoses.
  4. Directly executing database writes or triggering external state changes.
* High model confidence (e.g. `0.99`) is never sufficient by itself to bypass deterministic safety validation.

## Alternatives Considered
1. **Autonomous Agentic LLM Workflow (ReAct / Function Calling to complete medical actions)**: Allowing an autonomous agent to decide when a prescription is valid and directly advise patients. Rejected as dangerous and clinically irresponsible for an uncertified medical assistive system.

## Consequences
* **Positive**: Minimizes catastrophic clinical risk; guarantees full auditability; complies with emerging AI safety regulations and healthcare ethics.
* **Negative**: Requires rigorous deterministic validation rules, defensive schema validation layers, and frequent safe refusals on ambiguous inputs.
