# Acceptance Criteria

**Document Version**: 1.0.0 (Phase 0 Freeze)  
**Specification Format**: Behavioral Driven Development (BDD / Gherkin)  

These acceptance criteria define the non-negotiable verification gates required for feature sign-off and deployment.

---

## Scenario 1: Successful Extraction and Deterministic Normalization of Clear Prescription

```gherkin
Feature: Prescription Extraction and Normalization
  As a patient with a legible handwritten prescription
  I want the system to extract my medications and provide a spoken explanation
  So that I know when and how to take my medicine safely

  Scenario: Extract clear prescription with 1-0-1 notation in Hindi
    Given a user has selected "hi-IN" as their preferred language
    And an image containing "Tab Metformin 500mg 1-0-1 after food for 10 days" is uploaded
    When the backend triggers multimodal extraction via Amazon Bedrock
    Then the raw extraction payload contains:
      | field        | value        |
      | drug_name    | Metformin    |
      | strength     | 500mg        |
      | dosage_form  | Tab          |
      | raw_schedule | 1-0-1        |
      | food_relation| after food   |
      | duration     | 10 days      |
    And the deterministic validator normalizes the schedule to:
      | morning | afternoon | evening | night | before_meal | after_meal |
      | 1       | 0         | 0       | 1     | false       | true       |
    And the verification status is "VERIFIED" with "requires_review = false"
    And a localized Hindi audio summary is synthesized and returned with HTTP 200
```

---

## Scenario 2: Refusal on Illegible Handwriting or Missing Dosage (Fail-Closed)

```gherkin
Feature: Fail-Closed Safety Gate on Illegible Posology
  As a patient with an unreadable prescription
  I want the system to refuse to guess dosages
  So that I do not suffer a medication error from AI hallucination

  Scenario: Unreadable dosage number triggers safe refusal
    Given a user submits a prescription image where the dosage numeral is smudged
    When the AI extraction model encounters the illegible token
    Then the field "dose_value" is returned as null
    And "is_legible" is set to false
    And "requires_review" is set to true
    When the deterministic safety gate evaluates the payload
    Then the prescription state transitions to "REQUIRES_HUMAN_REVIEW"
    And the HTTP response code is 422 Unprocessable Entity
    And the response body contains:
      | field            | value                                                       |
      | error_code       | UNCERTAIN_POSOLOGY_DETECTED                                 |
      | user_message_hi  | खुराक स्पष्ट नहीं है। कृपया डॉक्टर या फार्मासिस्ट से संपर्क करें। |
      | can_proceed_voice| false                                                       |
    And no guessed or default dosage is returned in the API or audio
```

---

## Scenario 3: Ambiguous Schedule Notation Refusal

```gherkin
Feature: Rejection of Non-Standard or Ambiguous Abbreviations
  As a healthcare safety auditor
  I want non-standard abbreviations rejected
  So that incorrect dosing frequencies are never assumed

  Scenario: Non-standard notation "1-?-1" or illegible scribble
    Given an extracted schedule string is "1-?-1"
    When the deterministic normalizer attempts pattern matching
    Then no standard intake pattern matches
    And the field "timing_uncertain" is set to true
    And the medication record is marked "requires_review = true"
    And the system refuses to authorize a spoken schedule for this medication
```

---

## Scenario 4: Voice Query Answering Strictly From Verified Data

```gherkin
Feature: Verified Voice Query Answering
  As a patient speaking Kannada
  I want to ask if my medicine should be taken before or after meals
  So that I can listen to verified instructions

  Scenario: User queries meal timing for active verified prescription
    Given an active prescription session exists with verified medication:
      | drug_name | after_meal | morning | night |
      | Metformin | true       | 1       | 1     |
    When the user speaks: "ಈ ಮಾತ್ರೆಯನ್ನು ಊಟಕ್ಕೆ ಮುಂಚೆ ಅಥವಾ ನಂತರ ತೆಗೆದುಕೊಳ್ಳಬೇಕೇ?"
    And Amazon Transcribe converts the audio to text with confidence > 0.85
    And the intent is classified as "QUERY_MEAL_TIMING"
    Then the response generator looks up only the verified "after_meal" property
    And synthesizes a Kannada audio response stating it must be taken after food
    And does not provide any general clinical advice or external Web knowledge
```

---

## Scenario 5: Safe Refusal on Out-of-Scope Clinical Queries

```gherkin
Feature: Out-of-Scope Clinical Query Disclaimer
  As a patient asking a medical advice question
  I want the system to tell me it is not a doctor
  So that I seek proper medical care

  Scenario: User asks about disease diagnosis or altering dosage
    Given an active prescription session exists
    When the user asks: "क्या मैं डॉक्टर की पर्ची से ज्यादा दवा ले सकता हूँ?"
    When the intent engine classifies the query as "CLINICAL_ADVICE_REQUEST"
    Then the system returns a safe clinical disclaimer:
      | error_code | CLINICAL_ADVICE_DISALLOWED |
    And the system speaks in Hindi:
      "मैं केवल डॉक्टर द्वारा लिखे गए पर्चे को पढ़कर सुना सकता हूँ। खुराक बदलने के लिए अपने डॉक्टर से बात करें।"
    And the system does not advise increasing or decreasing medication
```
