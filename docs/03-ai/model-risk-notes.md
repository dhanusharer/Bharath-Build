# AI Model Risk & Clinical Hazard Notes

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Classification**: AI Safety & Clinical Risk Mitigation  

---

## 1. Identified Multimodal LLM Failure Modes in Healthcare Document Ingestion

Foundation models exhibit specific systemic failure modes when applied to handwritten clinical manuscripts. Understanding these failure modes informs our deterministic defenses.

### 1.1 The "Look-Alike / Sound-Alike" (LASA) Hallucination Risk
* **Phenomenon**: Medical cursive for certain drug pairs looks almost identical (e.g., *Metformin* vs *Metoprolol*, *Celebrex* vs *Celexa*, *Prednisone* vs *Prednisolone*).
* **Model Behavior**: When cursive strokes are ambiguous, multimodal LLMs tend to auto-complete the token to the most frequent word in their pre-training corpora.
* **Clinical Hazard**: Administering a beta-blocker (Metoprolol) instead of a biguanide anti-diabetic (Metformin) could trigger severe bradycardia or hypoglycemia.
* **Deterministic Guardrail**: Confidence thresholding. If the vision model's confidence for the character sequence falls below `0.90`, the drug is flagged with `requires_review = true` and spoken advice is withheld.

### 1.2 The "Trailing Zero / Decimal Point" Confusion
* **Phenomenon**: Physicians writing `5.0 mg` where the dot is faint, or `5 mg` where a speck of ink appears as `.5 mg` or `50 mg`.
* **Model Behavior**: Multimodal models may misread `5.0` as `50`, representing a 10x overdose hazard.
* **Deterministic Guardrail**: Range-checking validation in Pydantic. If a drug's extracted dosage is outside plausible pharmacological boundaries for that molecule (e.g., Metformin > 1000mg per unit dose, or Levothyroxine in `g` instead of `mcg`), the safety gate rejects the record.

### 1.3 Posology Re-Association / Spatial Drift
* **Phenomenon**: Prescriptions written on unlined paper where timing instructions for line 1 drift physically closer to line 2.
* **Model Behavior**: The model associates the timing `1-0-1` with the wrong drug.
* **Deterministic Guardrail**: The prompt demands line-by-line bounding decomposition (`raw_drug_line`), and the backend forces the user to visually review the mapped cards alongside the cropped visual snippet.

### 1.4 Over-Helpfulness / Confirmation Bias in Conversational Voice
* **Phenomenon**: A user asking *"Did the doctor say to take this with milk?"* when the prescription mentions nothing about milk.
* **Model Behavior**: Conversational LLMs often politely speculate: *"Usually it is good to take medicine with milk to prevent stomach upset."*
* **Clinical Hazard**: Calcium in milk binds to certain antibiotics (e.g., Ciprofloxacin, Tetracycline), completely nullifying bioavailability.
* **Deterministic Guardrail**: Pure template-based answer generation. The intent engine cannot generate freeform advice. If a fact is not in the verified record, the system outputs a fixed rejection: *"There are no instructions regarding milk on your prescription. Please follow the doctor's directions."*

---

## 2. Risk Mitigation Summary Matrix

| Failure Mode | Severity | Likelihood | Architectural Mitigation Layer |
| :--- | :--- | :--- | :--- |
| **LASA Drug Hallucination** | Catastrophic | High | Bedrock prompt constraints + High confidence gate (0.90) + Pharmacist review flag |
| **10x Overdose (Decimal Point)** | Catastrophic | Medium | Pydantic posology range validator + Pharmacist confirmation requirement |
| **Spatial Posology Drift** | High | Medium | Verbatim raw line parsing + Visual snippet mapping in UI |
| **Conversational Speculation** | High | High | Intent engine isolation from web knowledge + Deterministic answer templating |
| **Model Outage / 504 Timeout** | Medium | Low | Circuit breaker + Explicit retry prompt + Zero silent fallback |
