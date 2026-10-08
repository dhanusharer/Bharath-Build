/**
 * Typed API client for MedTwin AI: A Medication-Aware Digital Twin for Personalized Adverse Health Event Forecasting.
 * Designed for Happiest Health 2026 PoC Submission.
 */

export interface MedicationItem {
  medication_id: string;
  drug_name: string | null;
  is_verified_safe: boolean;
  requires_review: boolean;
  strength: {
    value: number | null;
    unit: string | null;
    raw_text: string | null;
  };
  dose: {
    value: number | null;
    unit: string | null;
    raw_text: string | null;
  };
  schedule: {
    morning: boolean | null;
    afternoon: boolean | null;
    evening: boolean | null;
    night: boolean | null;
    is_as_needed_sos: boolean;
    raw_text: string | null;
  };
  meal_instruction: {
    before_meal: boolean | null;
    after_meal: boolean | null;
    raw_text: string | null;
  };
  duration: {
    value: number | null;
    unit: string | null;
    raw_text: string | null;
  };
}

export interface PrescriptionResponse {
  success: boolean;
  request_id: string;
  prescription_id: string;
  status: "UPLOADED" | "PROCESSING" | "COMPLETED" | "REQUIRES_REVIEW" | "FAILED";
  requires_review: boolean;
  safety_reasons: string[];
  medications: MedicationItem[];
  created_at: string;
}

export interface VoiceQueryResponse {
  success: boolean;
  request_id: string;
  prescription_id: string;
  transcript: string;
  intent: string;
  target_drug: string | null;
  response_text: string;
  audio_base64: string | null;
  audio_content_type: string;
  language: string;
  requires_review: boolean;
  result_state?: "CONFIRMED_MATCH" | "PARTIAL_CONFIRMED_MATCH" | "NO_CONFIRMED_MATCH" | "PRESCRIPTION_REQUIRES_REVIEW";
  safety_reasons: string[];
  created_at: string;
}

export interface FeatureContribution {
  feature: string;
  display_name: string;
  value: number | null;
  contribution_percentage: number;
  direction: "RISK_INCREASING" | "PROTECTIVE_OR_NEUTRAL";
}

export interface PatientTwinState {
  patient_id: string;
  timestamp: string;
  name: string;
  age: number;
  sex: string;
  bmi: number;
  diabetes_duration_years: number;
  hba1c: number;
  fasting_glucose: number;
  baseline_glucose: number;
  baseline_hr: number;
  baseline_hrv: number;
  baseline_sleep_hours: number;
  baseline_steps: number;
  current_glucose: number | null;
  current_hr: number | null;
  current_hrv: number | null;
  current_sleep_hours: number | null;
  current_steps: number | null;
  current_activity_intensity: number | null;
  spo2?: number | null;
  blood_pressure_systolic?: number | null;
  blood_pressure_diastolic?: number | null;
  rolling_glucose_trend: number;
  rolling_hr_trend: number;
  rolling_hrv_trend: number;
  rolling_glucose_mean_15m: number;
  rolling_glucose_mean_30m: number;
  rolling_glucose_mean_60m: number;
  rolling_glucose_std_60m: number;
  deviation_glucose_from_baseline: number;
  deviation_hr_from_baseline: number;
  deviation_hrv_from_baseline: number;
  deviation_sleep_from_baseline: number;
  medication_profile: any[];
  medication_active_count: number;
  time_since_last_medication_hours: number | null;
  medication_adherence_status: "VERIFIED_ADHERENT" | "MISSED_DOSE" | "UNVERIFIED_REVIEW_REQUIRED" | "UNKNOWN";
  risk_score: number;
  risk_category: "LOW" | "MODERATE" | "ELEVATED" | "CRITICAL" | "INSUFFICIENT_DATA";
  prediction_horizon: string;
  model_version: string;
  state_confidence: number;
  feature_contributions: FeatureContribution[];
  what_changed_summary: string;
  missing_features: string[];
  requires_clinical_review: boolean;
  last_updated: string;
  clinical_disclaimer: string;
}

export interface TimelineEntry {
  timestamp: string;
  glucose: number | null;
  heart_rate: number | null;
  hrv: number | null;
  activity_intensity: number | null;
  risk_score: number | null;
  risk_category: string;
  glucose_deviation: number | null;
  event_flag: boolean;
}

export interface ScenarioInfo {
  scenario_id: string;
  scenario_type: string;
  title: string;
  clinical_narrative: string;
  expected_outcome: string;
}

export interface BenchmarkScenarioReport {
  scenario_index: number;
  scenario_name: string;
  description: string;
  prediction_risk_score: number;
  risk_category: string;
  state_confidence: number;
  missing_data_handled: boolean;
  medication_safety_checked: boolean;
  expected_status_matched: boolean;
  summary: string;
}

export interface BenchmarkSuiteResponse {
  timestamp: string;
  total_scenarios_evaluated: number;
  passed_scenarios: number;
  model_version: string;
  clinical_use_case: string;
  reports: BenchmarkScenarioReport[];
}

const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export async function uploadPrescription(file: File): Promise<PrescriptionResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`${API_BASE}/api/v1/prescriptions`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.detail?.error?.message || `Upload failed with status ${res.status}`;
    throw new Error(message);
  }

  return res.json();
}

export async function getPrescription(prescriptionId: string): Promise<PrescriptionResponse> {
  const res = await fetch(`${API_BASE}/api/v1/prescriptions/${prescriptionId}`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve prescription (${res.status})`);
  }
  return res.json();
}

export async function queryVoice(
  prescriptionId: string,
  audioBlob: Blob,
  language: string = "en-IN"
): Promise<VoiceQueryResponse> {
  const formData = new FormData();
  formData.append("file", audioBlob, "query.wav");
  formData.append("prescription_id", prescriptionId);
  formData.append("language", language);

  const res = await fetch(`${API_BASE}/api/v1/voice/query`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    const message = errorData?.detail?.error?.message || `Voice query failed with status ${res.status}`;
    throw new Error(message);
  }

  return res.json();
}

export async function getPatientTwin(patientId: string): Promise<PatientTwinState> {
  const res = await fetch(`${API_BASE}/api/v1/digital-twin/state/${patientId}`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve digital twin state (${res.status})`);
  }
  return res.json();
}

export async function listPatients(): Promise<any[]> {
  const res = await fetch(`${API_BASE}/api/v1/digital-twin/patients`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve patients (${res.status})`);
  }
  return res.json();
}

export async function getPatientTimeline(patientId: string): Promise<TimelineEntry[]> {
  const res = await fetch(`${API_BASE}/api/v1/digital-twin/timeline/${patientId}`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve timeline (${res.status})`);
  }
  return res.json();
}

export async function listScenarios(): Promise<ScenarioInfo[]> {
  const res = await fetch(`${API_BASE}/api/v1/digital-twin/scenarios`);
  if (!res.ok) {
    throw new Error(`Failed to retrieve scenarios (${res.status})`);
  }
  return res.json();
}

export async function simulateScenario(
  scenarioKey: string,
  patientId: string = "PT-101",
  steps: number = 12
): Promise<PatientTwinState> {
  const res = await fetch(
    `${API_BASE}/api/v1/digital-twin/simulate/${scenarioKey}?patient_id=${patientId}&steps=${steps}`,
    { method: "POST" }
  );
  if (!res.ok) {
    throw new Error(`Failed to run simulation (${res.status})`);
  }
  return res.json();
}

export async function runBenchmarkSuite(): Promise<BenchmarkSuiteResponse> {
  const res = await fetch(`${API_BASE}/api/v1/digital-twin/benchmarks`);
  if (!res.ok) {
    throw new Error(`Failed to execute benchmarks (${res.status})`);
  }
  return res.json();
}
