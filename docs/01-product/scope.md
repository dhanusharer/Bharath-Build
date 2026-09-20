# Product Scope & Boundary Specifications

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Boundary Definition**: MVP Baseline vs. Future Roadmap  

---

## 1. Scope Matrix

| Capability / Feature | Phase 0 (Freeze) | Phase 1 (MVP) | Phase 2 (Enhancements) | Out of Scope / Disallowed |
| :--- | :---: | :---: | :---: | :---: |
| **Handwritten Prescription Ingestion (JPEG/PNG/WebP)** | Specs & Schemas | **Included** | Enhanced Preprocessing | Excluded |
| **Amazon Bedrock Multimodal Extraction** | Specs & Schemas | **Included** | Fine-tuned Vision Adapters | Excluded |
| **Deterministic Timing Normalization (1-0-1, OD, BD, TDS)** | Spec Rules | **Included** | Expanded Regional Jargon | Excluded |
| **Fail-Closed Safety Gate (Refusal on Null/Uncertain)** | Gate Design | **Included** | Dynamic Confidence Tuning | Excluded |
| **Hindi Language Voice Synthesis (Amazon Polly)** | Port & Contract | **Included** | Emotional Voice Tuning | Excluded |
| **Kannada Language Voice Synthesis (Adapter Port)** | Port & Contract | **Included** | Custom Deep Learning Model | Excluded |
| **Voice Querying on Validated Prescription Data** | Intent Model | **Included** | Multi-turn Conversational AI | Excluded |
| **Pharmacist Reviewer UI / Override Portal** | Wireframe Specs | Excluded | **Included** | Excluded |
| **Multi-Page Prescription Stitching** | Excluded | Excluded | **Included** | Excluded |
| **FHIR / ABDM (Ayushman Bharat) Integration** | Excluded | Excluded | **Included** | Excluded |
| **Drug-Drug Interaction Analysis** | Excluded | Excluded | Excluded | **Strictly Disallowed** |
| **Autonomous Clinical Diagnosis / Symptom Check** | Excluded | Excluded | Excluded | **Strictly Disallowed** |
| **Dosage Modification / Medical Advice** | Excluded | Excluded | Excluded | **Strictly Disallowed** |
| **Pharmacy E-Commerce / Auto-Refill Ordering** | Excluded | Excluded | Excluded | **Strictly Disallowed** |

---

## 2. Rationales for Exclusions & Safety Boundaries

### 1. Prohibition of Clinical Diagnosis & Treatment Advice
* **Rationale**: Providing clinical advice or diagnosing illness requires regulatory certification as a Software as a Medical Device (SaMD) under CDSCO/FDA guidelines.
* **Architecture Impact**: The AI agent is isolated from external medical knowledge bases and cannot suggest medications, alter dosages, or evaluate symptoms.

### 2. Prohibition of Drug-Drug Interaction Checking in MVP
* **Rationale**: Drug-drug interactions require curated, clinically accredited pharmacology databases (e.g., Lexicomp, First Databank) with real-time patient history, renal function, and allergy profiles. An incomplete check creates a false sense of safety.
* **Architecture Impact**: Interaction checking is deferred until accredited third-party clinical data partnerships are formally integrated.

### 3. Deferral of Multi-Page Prescriptions
* **Rationale**: Multi-page documents introduce cross-page deduplication, continuation ambiguity, and complex spatial tracking that increase MVP risk without validating the core voice-accessibility hypothesis.
* **Architecture Impact**: Single-image ingestion is strictly enforced for MVP; multi-page support is scheduled for Phase 2.

### 4. Responsive Web Client vs. Native Mobile Binary
* **Rationale**: Mobile web eliminates installation barriers for rural users and family members, works across diverse Android devices, and accelerates iterative deployment during hackathon evaluation.
