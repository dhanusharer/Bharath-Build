/**
 * Typed API client for Bharat Builds Multimodal Medication Accessibility Backend.
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
  safety_reasons: string[];
  created_at: string;
}

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

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
