# Product Requirements Document (PRD)

**Project Name**: Multimodal Medication Accessibility System  
**Initiative**: Bharat Builds / First Commit in collaboration with AWS  
**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Status**: Approved for Architecture Baseline  

---

## 1. Product Overview
The Multimodal Medication Accessibility System is an assistive technology platform designed to bridge the healthcare literacy and language divide across India by converting handwritten prescription images into structured, verified medication summaries and providing intuitive, voice-driven interaction in regional languages (starting with Hindi and Kannada). By combining Amazon Bedrock multimodal inference with deterministic backend safety gates, strict normalization algorithms, Amazon Transcribe speech-to-text, and a provider-abstracted text-to-speech layer, the system enables users who cannot read cursive English handwriting or medical shorthand to understand their dosage schedules and timings safely, without ever guessing uncertain information.

---

## 2. Problem Statement
In India and emerging healthcare ecosystems, the vast majority of outpatient prescriptions remain handwritten by medical practitioners using complex cursive handwriting, non-standard clinical abbreviations (e.g., *OD*, *BD*, *TDS*, *1-0-1*, *SOS*), and English terminology. For elderly individuals, citizens with limited formal literacy, rural and semi-urban populations, and non-English speakers, deciphering these documents creates acute anxiety, missed doses, dosage timing errors, and reliance on overloaded local pharmacists. Existing digital OCR tools frequently fail when encountering cursive medical handwriting, and conventional generative AI models suffer from hallucinations—fabricating plausible-sounding medication names or dosages when text is illegible. Furthermore, text-centric smartphone interfaces fail to serve non-literate users who depend primarily on oral communication. A reliable, fail-closed solution is required that extracts prescription data without hallucination, strictly validates every medical token, and communicates instructions through spoken regional vernacular.

---

## 3. Target Users

### Primary Users
1. **Elderly Patients**: Individuals managing chronic conditions (e.g., hypertension, diabetes) with multiple daily medications who experience reduced visual acuity or cognitive strain when reading doctor handwriting.
2. **Rural and Semi-Urban Citizens**: Users with low English literacy or limited formal education who communicate natively in regional languages (Hindi, Kannada) and rely on oral explanations.
3. **Caregivers & Family Members**: Sons, daughters, or community health workers (e.g., ASHA workers) responsible for administering prescriptions to family elders, needing a quick, reliable verification of doctor instructions.

### Secondary Users
1. **Retail Pharmacists**: Dispensing chemists seeking a secondary digital readout to confirm ambiguous handwritten schedules before dispensing.
2. **Community Clinic Volunteers**: Healthcare triage workers assisting non-literate patients in navigating outpatient treatment plans.

---

## 4. Value Proposition
* **Accessible Vernacular Audio**: Delivers spoken, conversational explanations of medication timing in the user's native tongue (Hindi, Kannada) without requiring them to read complex typography.
* **Deterministic Safety Over Guesswork**: Unlike generic chatbots that guess illegible text, our system enforces a strict "Fail-Closed" architecture—if a dosage or drug name is smudged or ambiguous, it explicitly flags the uncertainty and directs the user to professional verification.
* **Hands-Free Interactive Clarification**: Empowers patients to ask natural voice queries ("When do I take the yellow tablet?", "Do I take this after dinner?") answered strictly from verified prescription records.
* **Zero Clinical Pretense**: Explicitly positions itself as an assistive reading aid rather than a diagnostic engine, maintaining ethical boundaries and regulatory compliance.

---

## 5. Core User Journeys

### Journey A: Successful Prescription Digitization & Audio Walkthrough
1. **Capture**: The user (or caregiver) snaps a photograph of their doctor's handwritten prescription using a mobile browser.
2. **Upload & Ingestion**: The image is uploaded over HTTPS to Amazon S3 via a secure pre-signed URL.
3. **Multimodal Extraction**: Amazon Bedrock processes the image, generating a candidate JSON payload bound to our typed extraction schema.
4. **Deterministic Validation & Normalization**: The backend validates extracted fields against strict Pydantic models. Shorthand notation (e.g., `1-0-1`, `Tab`, `5 days`) is parsed into structured morning/night intake intervals and day counts.
5. **Safety Gate Verification**: Every medication record passes confidence and legibility criteria (`is_legible == true`, `requires_review == false`).
6. **Localized Explanation Generation**: The system renders a clean, templated regional language script (Hindi/Kannada) summarizing each medication, dosage, and meal relationship.
7. **Speech Synthesis**: The text is synthesized into natural audio via the TTS provider adapter (e.g., Amazon Polly for Hindi) and streamed to the user's device for playback.

### Journey B: Voice-Driven Interactive Querying
1. **Voice Query**: The user taps the microphone button and asks a question in Kannada: *"ಊಟದ ನಂತರ ಯಾವ ಮಾತ್ರೆ ತಗೋಬೇಕು?"* ("Which tablet should I take after food?").
2. **Speech-to-Text**: Amazon Transcribe converts the audio stream into text with language identification.
3. **Intent Resolution**: The backend classifies the intent against the active, verified prescription session (e.g., `QUERY_MEAL_TIMING`).
4. **Data-Bound Response Formulation**: The system queries only the verified database record for medications where `after_meal == true`. No external medical knowledge or speculative advice is generated.
5. **Speech Synthesis & Playback**: A localized Kannada voice response is generated and played back: *"ಊಟದ ನಂತರ ನೀವು ಟ್ಯಾಬ್ಲೆಟ್ ಮೆಟ್‌ಫಾರ್ಮಿನ್ ತೆಗೆದುಕೊಳ್ಳಬೇಕು."*

### Journey C: Ambiguous / Low-Quality Prescription (Safe Refusal Flow)
1. **Capture**: The user submits a poorly lit, blurry, or partially cropped photo of an old prescription.
2. **Multimodal Extraction & Uncertainty Detection**: Bedrock detects low token legibility and flags ambiguous drug names or illegible dosage numerals (`is_legible = false`, `requires_review = true`).
3. **Safety Gate Intervention**: The deterministic safety validator identifies missing dosage numbers and low confidence scores on critical fields. The prescription state is transitioned to `REQUIRES_HUMAN_REVIEW`.
4. **Safe Refusal & User Guidance**: The system blocks automatic medical interpretation and generates a localized voice and screen alert:
   * *"डॉक्टर द्वारा लिखी गई दवा की मात्रा स्पष्ट नहीं है। कृपया पर्चे की स्पष्ट फोटो लें या फार्मासिस्ट से संपर्क करें।"*
   * ("The dosage written by the doctor is not clear. Please take a clearer photo or consult your pharmacist.")
5. **No Hallucination**: The system refuses to provide partial or guessed medication instructions.

---

## 6. MVP Scope Boundary

### In-Scope for MVP
* Processing single-page handwritten prescription images in JPEG, PNG, or WebP format.
* Multimodal information extraction via Amazon Bedrock (Claude 3.5 Sonnet) constrained to strict JSON schemas.
* Deterministic parsing of standard Indian prescription abbreviations (`1-0-0`, `0-1-0`, `0-0-1`, `1-0-1`, `1-1-1`, `OD`, `BD`, `TDS`, `QID`, `BBF`, `PC`, `AC`, `HS`).
* Explicit uncertainty representation (`null`, `is_legible`, `requires_review`).
* Spoken language support for **Hindi** and **Kannada** for voice input and synthesized audio playback.
* Speech-to-text integration via Amazon Transcribe.
* Provider-abstracted Text-to-Speech (TTS) architecture supporting Amazon Polly and pluggable regional adapters.
* Core voice queries restricted to: meal timing, schedule times (morning/afternoon/evening/night), and duration.
* Complete audit logging of model IDs, prompt versions, raw responses, and validation decisions.

### Out-of-Scope for MVP
* Multi-page prescription stitching or batch medical records analysis.
* Drug-drug interaction checking or contraindication clinical decision support.
* Clinical diagnosis or symptom verification.
* Direct integration with pharmacy e-commerce, ordering, or payment gateways.
* Real-time conversational medical consulting or autonomous medical advice.
* Optical Character Recognition (OCR) fallback for languages other than English medical handwriting.
* Mobile native apps (iOS/Android native binaries); MVP is a responsive mobile web application.
* Electronic Health Record (EHR) / ABDM (Ayushman Bharat Digital Mission) FHIR gateway synchronization (reserved for Phase 2).
