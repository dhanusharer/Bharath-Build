# Safety Specification & Fail-Closed Protocols

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Safety Classification**: High-Risk Assistive Healthcare System  
**Mandate**: Deterministic Backend Safety Precedes All Model Invocations  

---

## 1. The Twelve Non-Negotiable Safety Invariants

1. **LLM Output is Untrusted**: All model completions are treated as untrusted external inputs requiring strict deserialization, schema validation, and boundary verification.
2. **Unknown is Not Equivalent to False**: If `before_meal` is unstated, it is `null`. It must NEVER be defaulted to `false` or assumed to mean `after_meal`.
3. **Unknown is Not Equivalent to Inferred**: The system shall never fill in missing data points based on population averages or clinical conventions.
4. **Low Confidence Cannot Become Actionable**: A confidence score below `0.85` for any critical posology field immediately disqualifies the entity from automated voice playback.
5. **Drug Names Must Never Be Guessed**: Autocorrect, fuzzy-string completion, or phonetic guessing of ambiguous drug names is strictly banned.
6. **Dosage Must Never Be Guessed**: Missing numerals or smeared units must remain `null`. The system shall never assume standard commercial sizes (e.g. 500mg).
7. **Timing Must Never Be Invented**: If an abbreviation is unverified, all daily slots default to `0` with `timing_uncertain = true`.
8. **Prescription Facts Separated From Presentation**: Verified clinical entities are immutable. Translation and TTS layers only format vernacular presentation wrappers around verified entities.
9. **Voice Responses Rely Strictly on Validated Data**: The conversational engine can answer queries only by querying the active session's verified PostgreSQL table.
10. **Deterministic Backend Rules are Authoritative**: Algorithmic rules, range validators, and safety gates unconditionally override foundation model reasoning.
11. **Unsafe or Ambiguous Cases Fail Closed**: Any condition of ambiguity, corruption, or doubt transitions the system into a safe refusal state.
12. **Safety-Critical Behavior Must Have Automated Tests**: Every safety rule and failure scenario must be accompanied by non-flaky, automated regression tests in CI.

---

## 2. Environmental & Input Anomaly Action Protocol

| Anomaly Condition | Detection Mechanism | Immediate System Action | User-Facing Action (Screen & Audio) |
| :--- | :--- | :--- | :--- |
| **Image Blurry / Defocused** | Laplacian variance edge-density check (< 100.0) + Bedrock `is_legible=false`. | Transition status to `IMAGE_BLURRY`; halt extraction. | Spoken warning: *"फोटो धुंधली है। कृपया फोन को स्थिर रखकर दोबारा फोटो लें।"* (Photo is blurry. Please hold steady and retake.) |
| **Image Too Dark / Underexposed** | Average pixel luminance check (< 40 / 255). | Reject upload prior to Bedrock invocation; save API cost. | Spoken warning: *"कमरे में रोशनी कम है। कृपया पर्याप्त रोशनी में फोटो खींचें।"* (Lighting is low. Please capture in bright light.) |
| **Prescription Cropped / Clipped** | Model flags `doctor_notes_raw: "clipped_margins"`. | Mark prescription as `PARTIAL_DOCUMENT`. | Visual alert & audio: *"पर्चे का कुछ हिस्सा कट गया है। कृपया पूरा पर्चा फ्रेम में लें।"* |
| **Drug Name Uncertain** | Model confidence < 0.85 or `is_legible = false`. | Set `requires_review = true`; isolate entity from verified read layer. | Spoken warning: *"एक दवा का नाम स्पष्ट नहीं है। इसके लिए फार्मासिस्ट से मिलें।"* |
| **Dosage Numeral Uncertain** | Smudged digit; `strength_value = null`. | Fail safety gate; refuse to synthesize spoken quantity. | Screen displays amber badge; voice explicitly states dosage could not be verified. |
| **Timing Shorthand Uncertain** | Shorthand does not match regex dictionary (e.g. `1-?-1`). | Set `timing_uncertain = true`; refuse schedule synthesis. | Voice states: *"दवा लेने का समय स्पष्ट नहीं लिखा है।"* |
| **Multiple Interpretations Possible** | Model notes ambiguity (e.g. `OD or BD`). | Reject both interpretations; fail closed to `REQUIRES_HUMAN_REVIEW`. | Prompts human pharmacist consultation. No probabilistic coin-flip. |
| **Transcription Uncertain (Voice)** | Amazon Transcribe audio confidence < 0.70. | Invalidate intent resolution; trigger retry loop. | Spoken query: *"माफ़ कीजिये, आपकी आवाज़ साफ़ नहीं सुनाई दी। कृपया दोबारा बोलें।"* |
| **Query for Uncontained Data** | User asks: *"Can I eat mango with this medicine?"* | Intent engine detects fact absent from verified DB record. | Standard refusal: *"इस बारे में पर्चे में कोई निर्देश नहीं है। अपने डॉक्टर से सलाह लें।"* |
| **TTS Provider Unavailable** | Circuit breaker trips on Polly/regional engine timeout. | Fallback to secondary adapter or render high-contrast visual cards. | Visual notification: *"Audio currently unavailable. Please read verified card below."* |
| **AI Provider Timeout (Bedrock)** | Request duration > 12.0s or HTTP 504. | Abort transaction; log timeout; return HTTP 504. | Spoken alert: *"सर्वर से संपर्क नहीं हो पा रहा है। कृपया कुछ देर बाद प्रयास करें।"* |
