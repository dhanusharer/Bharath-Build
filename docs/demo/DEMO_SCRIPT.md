# MedTwin AI: 20-Minute Demonstration Script

**Video Walkthrough Guide for Happiest Health 2026 Submission**  
*Title*: MedTwin AI: A Medication-Aware Digital Twin for Personalized Adverse Health Event Forecasting

---

## Video Timeline & Stage Directions

### [00:00 – 02:00] Act 1: The Clinical Problem in Metabolic Care
* **Visual**: Presenter on camera with title slide, followed by clinical statistics overlay (101M diabetes patients in India; microvascular and macrovascular complications).
* **Script / Spoken Narrative**:
  > *"Welcome to our demonstration of MedTwin AI for the Happiest Health 2026 Summit. Today, more than 101 million people in India are living with Type 2 Diabetes. In current clinical practice, care is almost entirely reactive. A patient visits their physician every 3 to 6 months, gets an HbA1c test, and leaves with an adjusted prescription. But what happens in between?
  >
  > While wearable sensors like Continuous Glucose Monitors and smartwatches exist, their alerts are reactive: they buzz only after blood sugar has already spiked past 180 or 250 mg/dL. Furthermore, they are blind to the patient's verified medication regimen and compare everyone to generic population averages. Our objective is to transition from reactive monitoring to a proactive, personalized Digital Twin that forecasts adverse glycemic excursions two hours before they occur."*

---

### [02:00 – 05:00] Act 2: The Healthcare Digital Twin Concept
* **Visual**: Architectural diagram (from `docs/architecture/ARCHITECTURE.md`) highlighting the fusion of Static EHR, Verified Medication Profiles, and Dynamic Wearable Streams.
* **Script / Spoken Narrative**:
  > *"What turns a collection of health numbers into a genuine Digital Twin? In conventional machine learning, you pass a single row of sensor readings and get an isolated classification. 
  >
  > In MedTwin AI, the patient is represented as a stateful, evolving computational twin—the `PatientTwinState`. The twin maintains an understanding of the patient's biological history: their diabetes duration, baseline HbA1c, and critically, their personal physiological baselines—resting heart rate, circadian HRV, and typical sleep recovery.
  >
  > As dynamic wearable telemetry arrives every five minutes, the twin doesn't simply evaluate raw values; it calculates temporal velocities, rolling moving averages, and deviations relative to the individual's baseline. Most importantly, it integrates verified medication status to provide pharmacological context to physiological drift."*

---

### [05:00 – 08:00] Act 3: Synthetic EHR Generation & Reproducibility
* **Visual**: Screen capture of terminal executing `python scripts/generate_synthetic_ehr.py`, followed by inspection of `data/synthetic/ehr/patients_ehr.json` and patient selection in the dashboard.
* **Script / Spoken Narrative**:
  > *"To ensure technical rigor, clinical validity, and zero exposure of confidential patient identifiers, we developed a reproducible synthetic EHR generator calibrated to Synthea metabolic distributions.
  >
  > Let's look at the generated cohort in `data/synthetic/ehr/`. Here is patient PT-101, Rajesh Kumar, age 54, with a 6.5-year history of Type 2 Diabetes, baseline HbA1c of 7.8%, resting heart rate of 72 bpm, and personal baseline glucose of 132 mg/dL.
  >
  > Notice that we store personal baseline metrics for each patient. When we look at our clinician dashboard, we can switch across our synthetic cohort seamlessly. Everything is seeded and completely reproducible using our provided generation scripts."*

---

### [08:00 – 11:00] Act 4: The Medication Verification Layer
* **Visual**: Dashboard "Medication Verification Layer" tab. Live upload of a handwritten prescription image. Display extraction, deterministic validation, posology table, and a test demonstrating fail-closed `REQUIRES_REVIEW` gating.
* **Script / Spoken Narrative**:
  > *"Now let's examine one of our core architectural pillars: the Medication Verification Layer. We preserve our proven safety invariant: 'AI observes. Deterministic code validates. The system fails closed.'
  >
  > When a doctor uploads a handwritten prescription, multimodal vision extracts candidate tokens: drug name, strength, dosage, frequency, and meal instructions. However, foundation models are never treated as clinical arbiters.
  >
  > Deterministic Python code validates the tokens against strict clinical bounds. If strength is missing or handwriting is ambiguous, the system never guesses or interpolates. It marks the medication as `REQUIRES_REVIEW`. The Digital Twin will NEVER ingest an unverified dosage as ground truth. Notice that when all fields are verified, our table displays `VERIFIED SAFE` with validated strengths like '500 mg' and confirmed intake schedules."*

---

### [11:00 – 14:00] Act 5: Dynamic Wearable Telemetry & Simulation Scenarios
* **Visual**: Terminal showing `python scripts/generate_wearable_stream.py`. Dashboard simulator control bar showing Scenarios A through F.
* **Script / Spoken Narrative**:
  > *"Next, we examine Stream B: continuous wearable time-series telemetry. In `scripts/generate_wearable_stream.py`, we model realistic physiological signals: interstitial glucose, heart rate, autonomic HRV, sleep duration, steps, and activity intensity.
  >
  > We implemented six distinct clinical scenarios:
  > - Scenario A: Stable metabolic regulation with normal circadian rhythms.
  > - Scenario B: Sleep deficit (3.8 hours), elevating resting heart rate and depressing HRV, impairing next-day insulin sensitivity.
  > - Scenario C: An unbuffered postprandial glucose surge.
  > - Scenario D: A compounding adverse crisis.
  > - Scenario E: Wearable sensor packet loss testing missing-data resilience.
  > - Scenario F: An adherence lapse where a scheduled dose is skipped.
  >
  > Each scenario is deterministic and reproducible with fixed random seeds."*

---

### [14:00 – 17:00] Act 6: The Digital Twin Evolving in Real Time
* **Visual**: Clinician Dashboard running live playback of Scenario C (Post-Meal Excursion) and Scenario E (Sensor Dropout).
* **Script / Spoken Narrative**:
  > *"Let's watch the Patient Digital Twin update in real time. We select Scenario C and click 'Play Real-Time'. Every interval streams live into our FastAPI backend.
  >
  > Notice how the dashboard responds:
  > First, glucose begins to rise at step 25. The twin tracks the rolling 30-minute mean and detects a sharp acceleration in glucose slope: +2.8 mg/dL per hour.
  >
  > Concurrently, heart rate elevates and HRV drops. The twin's internal state score updates continuously. Watch the risk forecast tile: it transitions from LOW (18%) to ELEVATED (74%) a full 45 minutes before the glucose curve actually breaches the 180 mg/dL clinical threshold line!
  >
  > Now, let's switch to Scenario E with sensor dropouts. Notice what happens: when glucose packets drop, the twin does not hallucinate a zero or guess a value. It flags `MISSING`, applies a confidence penalty, and warns the clinician: 'Insufficient wearable stream data for reliable prediction'."*

---

### [17:00 – 19:00] Act 7: Explainable Risk Forecast & Benchmark Suite
* **Visual**: Close-up of the "What Changed?" panel, the Feature Contributions bar chart, and clicking "Benchmark Suite" to display the 10-scenario verification table.
* **Script / Spoken Narrative**:
  > *"Black-box predictions are unacceptable in healthcare. Why did the twin forecast elevated risk?
  > Look at our 'What Changed?' causation audit: it explains in clear medical language: 'Risk categorized as ELEVATED (74%) because glucose is +38 mg/dL above personal baseline, glucose slope accelerated (+22.4 mg/dL/hr), and sleep deficit reduced autonomic recovery.'
  >
  > Directly beneath, our decomposed feature attributions show exact mathematical contributions: Rolling 30m Glucose Mean (28%), Glucose Rate of Change (24%), Baseline Deviation (18%), and HbA1c (12%).
  >
  > Now let's execute our automated 10-Scenario Benchmark Suite. We click the button, and in real time, the backend runs all 10 clinical edge cases against our trained gradient boosted model. All 10 scenarios pass with 100% evaluation match!"*

---

### [19:00 – 20:00] Act 8: Safety, Clinical Limitations & Future Impact
* **Visual**: Presenter concluding with clinical disclaimer, roadmap slide, and GitHub repository overview.
* **Script / Spoken Narrative**:
  > *"To conclude, we emphasize that MedTwin AI is a research proof-of-concept for the Happiest Health 2026 Summit. It is designed to provide proactive decision-support signals, not autonomous diagnoses or therapy changes.
  >
  > Our roadmap includes prospective validation with clinical metabolic centers in India and secure ABDM FHIR gateway synchronization.
  >
  > By unifying static clinical history, verified pharmacology, and real-time autonomic signals into a living Digital Twin, MedTwin AI demonstrates how chronic disease management can shift from reactive emergency room visits to proactive, personalized care. Thank you."*
