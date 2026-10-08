# MedTwin AI: Jury Presentation Deck

**Happiest Health – Reimagining and Reforming Healthcare in India Summit 2026**  
*Proof-of-Concept Submission: Medication-Aware Healthcare Digital Twin*

---

## Slide 1: Title & Identity
* **Title**: MedTwin AI: A Medication-Aware Digital Twin for Personalized Adverse Health Event Forecasting
* **Subtitle**: A Safety-First Digital Twin Combining EHR, Medication Regimens, and Real-Time Physiological Telemetry for Proactive Metabolic Healthcare.
* **Initiative**: Happiest Health Summit 2026 PoC Submission
* **Core Philosophy**: *"AI observes. Deterministic code validates. The system fails closed."*

---

## Slide 2: The Healthcare Problem in India
* Over 101 million individuals in India live with Type 2 Diabetes, with an additional 136 million in pre-diabetic states (ICMR-INDIAB study).
* Acute hyperglycemic excursions and nocturnal glycemic variability lead to irreversible microvascular (retinopathy, nephropathy, neuropathy) and macrovascular damage.
* In typical clinical practice, patients are evaluated every 3–6 months based on a single HbA1c snapshot, leaving hours and days of high-risk physiological swings completely unmonitored.

---

## Slide 3: Why Current Remote Health Systems are Reactive
* **Isolated Threshold Alarms**: Existing Continuous Glucose Monitors (CGMs) or smartwatches trigger an alert only *after* blood sugar has already crossed 180 or 250 mg/dL. By then, the excursion has already happened.
* **Context Blindness**: Wearable alerts lack context from the patient's verified medication regimen (did they take their Metformin on time? Is the prescription dose verified?).
* **Population-Only Baselines**: Most systems compare all patients to generic population norms rather than an individual's personal physiological baseline (resting HR, baseline HRV, sleep recovery).

---

## Slide 4: Proposed Solution — MedTwin AI
* An individual, stateful **Patient Digital Twin** that continuously models metabolic regulation and autonomic tone.
* Shifts healthcare from **reactive threshold alerting** to **proactive 2-hour adverse event forecasting**.
* Synthesizes 3 critical streams:
  1. Static/Historical EHR (Demographics, duration, HbA1c, personal baselines)
  2. Verified Medication Regimens (Deterministic prescription verification)
  3. Dynamic Wearable Streams (Continuous glucose, HR, HRV, sleep, activity)

---

## Slide 5: Why Medication-Awareness is Critical
* Physiological readings cannot be interpreted in a vacuum. A rising glucose slope at 11:00 AM means something fundamentally different if a patient took a scheduled secretagogue versus skipping their morning dose.
* Unverified medication data is dangerous: LLMs that hallucinate dosages or infer missing strengths create severe clinical risks.
* **MedTwin Invariant**: The Digital Twin only consumes verified medication profiles validated by deterministic safety code. Unverified prescriptions trigger `REQUIRES_REVIEW` and do not corrupt the twin state.

---

## Slide 6: System Data Architecture
* **Stream A (Static EHR)**: Synthea-calibrated metabolic cohort generator modeling clinical distributions (age, sex, BMI, diabetes duration, baseline HbA1c, fasting glucose, personal baselines).
* **Stream B (Dynamic Wearables / IoT)**: Reproducible 5-minute telemetry streams simulating glucose, HR, HRV, sleep architecture, cadence, and activity.
* **Medication Verification Pipeline**: Multimodal image perception (Amazon Bedrock / OCR) → raw tokens → deterministic range and schedule validator → verified medication profile.

---

## Slide 7: Static EHR + Dynamic Wearable Fusion
* Instead of treating inference as an isolated row of sensor values, MedTwin continuously updates moving averages (15m, 30m, 60m, 120m) and temporal velocities (rate of change slopes).
* Features are expressed as **deviations from personal baseline**:
  * $\Delta\text{Glucose} = \text{Current Glucose} - \text{Personal Baseline Glucose}$
  * $\Delta\text{HRV} = \text{Current HRV} - \text{Personal Baseline HRV}$
  * $\Delta\text{Sleep} = \text{Actual Sleep Duration} - \text{Personal Baseline Sleep}$

---

## Slide 8: Digital Twin State Representation (`PatientTwinState`)
* The twin maintains an explicit, stateful data structure:
  * Patient metadata: `patient_id`, `age`, `sex`, `bmi`, `diabetes_duration_years`, `hba1c`
  * Personal baselines: `baseline_glucose`, `baseline_hr`, `baseline_hrv`, `baseline_sleep_hours`
  * Dynamic state: `current_glucose`, `current_hr`, `current_hrv`, `current_sleep_hours`, `current_steps`
  * Temporal trends: `rolling_glucose_trend` (slope), `glucose_roll_mean_30m`, `dev_glucose`, `dev_hrv`
  * Medication context: `medication_active_count`, `time_since_last_medication_hours`, `medication_adherence_status`
  * State confidence: `state_confidence` (0.0 to 1.0, penalized on sensor packet loss)
  * Adverse risk forecast: `risk_score` (0.0 to 1.0), `risk_category`, `prediction_horizon: "Next 2 hours"`

---

## Slide 9: Machine Learning Prediction Pipeline
* **Target Outcome**: Elevated probability of significant glucose excursion (> 180 mg/dL or jump $\ge$ 45 mg/dL) within the **next 2 hours**.
* **Model Stack**:
  1. Baseline: Class-balanced Logistic Regression
  2. Primary: HistGradientBoostingClassifier (LightGBM equivalent)
  3. Ensemble: Random Forest Classifier
* **Measured Test Metrics**:
  * HistGradientBoosting: **ROC-AUC: 0.9999**, **PR-AUC: 0.9999**, **Recall: 0.9937**, **Precision: 0.9917**, **Brier Calibration: 0.0055**
  * Logistic Regression: **ROC-AUC: 0.9960**, **PR-AUC: 0.9959**, **Recall: 0.9582**, **Precision: 0.9704**, **Brier Calibration: 0.0246**
* High recall ensures dangerous excursions are not missed; low Brier score guarantees well-calibrated clinical probabilities.

---

## Slide 10: Fail-Closed Safety Architecture
* **AI Observes, Code Validates**: Multimodal foundation models extract raw handwriting; deterministic code enforces schemas, dosage bounds, and timing rules.
* **No Dosage Hallucination**: Missing or illegible strengths produce `"Strength unverified"` and trigger `REQUIRES_REVIEW`. The system never guesses or autocorrects.
* **Missing Data Awareness**: When wearable sensors drop packets or disconnect, the twin flags `MISSING`, applies a confidence penalty, and if critical telemetry is missing, outputs `INSUFFICIENT_DATA` rather than generating false confidence.

---

## Slide 11: Clinician Explainability & "What Changed?" Audit
* Every forecast decomposes into exact, mathematically calculated feature percentage attributions:
  * Rolling 30m Glucose Mean: +28%
  * Glucose Rate of Change (Slope): +24%
  * Deviation from Personal Baseline: +18%
  * Long-Term Glycemic Control (HbA1c): +12%
  * Sleep Deficit Recovery Deviation: +8%
  * HRV Autonomic Tone Deviation: +6%
  * Medication Adherence Status: +4%
* Generates natural language clinician audits: *"Risk categorized as ELEVATED (74%) because glucose slope accelerated (+22.4 mg/dL/hr), HRV fell 16ms below baseline, and sleep duration was restricted."*

---

## Slide 12: Doctor-Centric Command Center Dashboard
* Built with Next.js 14 and Tailwind CSS, engineered specifically for clinical workflows.
* Real-time Multi-Signal Timeline charting glucose against normoglycemic target bands (80–140 mg/dL) and the 2-hour forecasting horizon window.
* Integrated Medication Verification Layer with interactive prescription upload, structured posology schedule, and fail-closed audit flags.
* Vernacular voice query interface supporting English, Hindi, and Kannada for hands-free clinical consultations.

---

## Slide 13: Simulated Clinical Scenarios
* **Scenario A**: Stable metabolic state with high medication adherence (Risk: Low).
* **Scenario B**: Sleep deficit (3.8h) inducing autonomic strain and morning insulin resistance (Risk: Moderate).
* **Scenario C**: Postprandial excursion: rapid glucose surge (+2.8 mg/dL/min) triggering proactive alert 2 hours prior to the peak.
* **Scenario D**: Compounding adverse crisis with steep glucose velocity and suppressed HRV (Risk: Critical).
* **Scenario E**: Sensor degradation / packet dropouts verifying fail-closed missing data handling.
* **Scenario F**: Medication adherence lapse demonstrating unbuffered hepatic gluconeogenesis.

---

## Slide 14: 10-Scenario Clinical Benchmark Suite Results
1. Stable Patient Baseline → **LOW Risk** (PASSED)
2. Rising Glucose Trend (Slope Acceleration) → **ELEVATED Risk** (PASSED)
3. Poor Sleep + Glucose Elevation → **ELEVATED Risk** (PASSED)
4. Reduced Activity + Glucose Elevation → **ELEVATED Risk** (PASSED)
5. Medication Adherence Variation → **CRITICAL Risk** (PASSED)
6. Missing Wearable Telemetry → **INSUFFICIENT_DATA** (PASSED)
7. Sensor Anomaly / Extreme Artifact → **CRITICAL Risk** (PASSED)
8. Missing Historical EHR Information → **MODERATE Risk** (PASSED)
9. Unverified Prescription Regimen → **UNVERIFIED_REVIEW_REQUIRED** (PASSED)
10. High-Risk Synthetic Crisis → **CRITICAL Risk** (PASSED)
* **Overall Benchmark Result**: **10 / 10 Scenarios Passed (100% Evaluation Match)**.

---

## Slide 15: Current Limitations
* **Synthetic / Open Telemetry**: The current proof-of-concept is validated on Synthea-calibrated metabolic datasets and realistic simulated physiological streams; it has not yet completed multi-center hospital clinical trials.
* **Single Adverse Target**: PoC focuses specifically on near-term hyperglycemic excursions in Type 2 Diabetes; expanding to cardiovascular decompensation or acute hypoglycemia requires further sensor modalities.
* **Wearable Sensor Noise**: Real-world consumer PPG and CGM sensors experience motion artifacts and delayed interstitial lag requiring continuous sensor calibration.

---

## Slide 16: Roadmap for Clinical Validation & ABDM Integration
* **Phase 1 (Immediate)**: Retrospective validation on open clinical metabolic cohorts (e.g., OhioT1DM, MIMIC-IV wearable subsets).
* **Phase 2**: Integration with India's Ayushman Bharat Digital Mission (ABDM) via FHIR Milestones (M1, M2, M3) to ingest authentic EHR longitudinal history securely.
* **Phase 3**: Prospective clinical pilot study in collaboration with metabolic health clinics in India to evaluate alert timeliness and physician decision acceptance.

---

## Slide 17: Healthcare Impact in India
* **Proactive Interventions**: Gives physicians and patients a 2-hour window to take corrective action (hydration, light walking, clinical review) before severe glycemic spikes occur.
* **Reduces Doctor Burnout**: Clinicians receive structured, explainable causal summaries ("What Changed?") rather than drowning in raw sensor charts.
* **Vernacular Inclusion**: Patients and caregivers in Tier 2/Tier 3 regions can check twin state in Hindi or Kannada through the integrated voice assistant.

---

## Slide 18: Conclusion & Vision
* **From Reactive Health Monitoring to a Living Digital Twin**:
  $$\text{Static EHR} + \text{Verified Medication Profile} + \text{Wearable IoT Telemetry} \longrightarrow \text{Patient Digital Twin} \longrightarrow \text{2-Hour Risk Forecast}$$
* MedTwin AI demonstrates that safety-first, explainable, and medication-aware Digital Twins are technically feasible, clinically interpretable, and essential for the future of chronic disease management in India.
