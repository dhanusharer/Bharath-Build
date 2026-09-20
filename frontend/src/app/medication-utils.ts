import type { MedicationItem, PrescriptionResponse } from "./api-client";

export interface ResolvedMedicationDisplay {
  displayName: string;
  displayStrength: string;
  displayDuration: string;
  hasStrength: boolean;
  hasDuration: boolean;
}

/**
 * Deterministically resolves medication display strings.
 * Strict Safety Rule:
 * DO NOT infer strength, dosage, timing, meal relationship, or duration
 * from drug_name or presentation strings using regex or heuristic parsers.
 *
 * If structured/validated strength exists (med.strength.value):
 *   display the validated strength.
 * Otherwise:
 *   display "Strength not confirmed".
 */
export function resolveMedicationDisplay(med: MedicationItem): ResolvedMedicationDisplay {
  const rawName = (med.drug_name || "").trim();
  const strengthVal = med.strength?.value;
  const strengthUnit = (med.strength?.unit || "").trim();

  let displayStrength = "Strength unverified";
  let hasStrength = false;

  if (strengthVal !== null && strengthVal !== undefined) {
    displayStrength = `${strengthVal} ${strengthUnit}`.trim();
    hasStrength = true;
  }

  // Duration formatting - strictly from structured data, never inferred from strings
  const durationVal = med.duration?.value;
  const durationUnit = (med.duration?.unit || "").trim();

  let displayDuration = "Duration not confirmed";
  let hasDuration = false;

  if (durationVal !== null && durationVal !== undefined) {
    displayDuration = `${durationVal} ${durationUnit}`.trim();
    hasDuration = true;
  }

  return {
    displayName: rawName || "[Ambiguous Drug Name]",
    displayStrength,
    displayDuration,
    hasStrength,
    hasDuration,
  };
}

/**
 * Returns dynamic, safety-compliant section title.
 * Invariant: Never labels section as "Verified Posology Schedule" when status is REQUIRES_REVIEW or null.
 */
export function getScheduleSectionTitle(prescription: PrescriptionResponse | null): string {
  if (!prescription) {
    return "Medication Schedule";
  }
  const hasUnverifiedMed = prescription.medications?.some(
    (m) => !m.is_verified_safe || m.requires_review
  );
  if (
    prescription.status === "REQUIRES_REVIEW" ||
    prescription.requires_review ||
    hasUnverifiedMed
  ) {
    return "Unverified Medication Schedule (Requires Review)";
  }
  if (prescription.status === "COMPLETED") {
    return "Verified Posology Schedule";
  }
  if (prescription.status === "FAILED") {
    return "Prescription Processing Failed";
  }
  if (prescription.status === "PROCESSING" || prescription.status === "UPLOADED") {
    return "Extracting Medication Schedule...";
  }
  return "Medication Schedule";
}

/**
 * Returns dynamic, safety-compliant description.
 */
export function getScheduleSectionDescription(prescription: PrescriptionResponse | null): string {
  if (!prescription) {
    return "Upload a prescription image to extract and verify medication posology.";
  }
  const hasUnverifiedMed = prescription.medications?.some(
    (m) => !m.is_verified_safe || m.requires_review
  );
  if (
    prescription.status === "REQUIRES_REVIEW" ||
    prescription.requires_review ||
    hasUnverifiedMed
  ) {
    return "Caution: Posology fields contain ambiguities or low-confidence tokens. Do not administer without pharmacist confirmation.";
  }
  if (prescription.status === "COMPLETED") {
    return "Deterministic normalization output with safety confidence gating.";
  }
  if (prescription.status === "FAILED") {
    return "The document was illegible or rejected by the safety gate. Please consult a licensed professional.";
  }
  return "Processing prescription image...";
}
