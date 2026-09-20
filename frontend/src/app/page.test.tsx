import { describe, it } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import HomePage from "./page";
import {
  getScheduleSectionTitle,
  getScheduleSectionDescription,
  resolveMedicationDisplay,
} from "./medication-utils";
import type { PrescriptionResponse, MedicationItem } from "./api-client";

describe("Frontend Initial State & Safety UX Tests", () => {
  it("Requirement 1: Fresh session does not render hardcoded or stale medication data", () => {
    const html = renderToStaticMarkup(React.createElement(HomePage));

    // Must show clear fresh session empty state
    assert.ok(
      html.includes("No Prescription Uploaded"),
      "Fresh session must explicitly display empty state heading"
    );
    assert.ok(
      html.includes("Session Status: Fresh (No Active Prescription)"),
      "Fresh session must show fresh session badge"
    );
    assert.ok(
      html.includes("Awaiting Upload"),
      "Fresh session must show Awaiting Upload badge"
    );

    // Must NOT contain any hardcoded or stale drug names
    assert.ok(!html.includes("Lisinopril"), "Must not display stale Lisinopril medication");
    assert.ok(!html.includes("Metformin"), "Must not display stale Metformin medication");
    assert.ok(!html.includes("Pantocid"), "Must not display stale Pantocid medication");
    assert.ok(!html.includes("Amoxicillin"), "Must not display stale Amoxicillin medication");

    // Table must not be rendered when no prescription is active
    assert.ok(
      !html.includes('data-testid="medications-table"'),
      "Medications table must not exist in fresh initial empty state"
    );

    // Voice button should indicate no active prescription
    assert.ok(
      html.includes("No active prescription. Upload a prescription above to enable voice queries."),
      "Voice query helper text must guide user to upload prescription first"
    );
  });

  it("Requirement 2: Does not label section 'Verified Posology Schedule' when REQUIRES_REVIEW or empty", () => {
    // 1. Empty / Fresh session
    const freshTitle = getScheduleSectionTitle(null);
    assert.equal(freshTitle, "Medication Schedule");
    assert.notEqual(freshTitle, "Verified Posology Schedule");

    // 2. Prescription in REQUIRES_REVIEW state
    const reviewPrescription: PrescriptionResponse = {
      success: true,
      request_id: "req-123",
      prescription_id: "rx-123",
      status: "REQUIRES_REVIEW",
      requires_review: true,
      safety_reasons: ["Low handwriting confidence"],
      medications: [],
      created_at: new Date().toISOString(),
    };

    const reviewTitle = getScheduleSectionTitle(reviewPrescription);
    assert.notEqual(
      reviewTitle,
      "Verified Posology Schedule",
      "Must NEVER label section as 'Verified Posology Schedule' when status is REQUIRES_REVIEW"
    );
    assert.equal(reviewTitle, "Unverified Medication Schedule (Requires Review)");

    const reviewDesc = getScheduleSectionDescription(reviewPrescription);
    assert.ok(
      reviewDesc.includes("Caution"),
      "Description must emphasize caution when reviewing unverified schedule"
    );

    // 3. Prescription in COMPLETED state
    const completedPrescription: PrescriptionResponse = {
      ...reviewPrescription,
      status: "COMPLETED",
      requires_review: false,
      safety_reasons: [],
    };
    const completedTitle = getScheduleSectionTitle(completedPrescription);
    assert.equal(completedTitle, "Verified Posology Schedule");
  });

  it("Requirement 3: Never infers strength from drug_name with regex; displays 'Strength unverified' when structured strength is null", () => {
    // Case: drug_name = "Lisinopril 5mg", strength.value = null, strength.raw_text = null
    // Expected: display "Strength unverified", NOT "Strength: 5 mg" or "5mg"
    const unvalidatedStrengthMed: MedicationItem = {
      medication_id: "med-001",
      drug_name: "Lisinopril 5mg",
      is_verified_safe: false,
      requires_review: true,
      strength: {
        value: null,
        unit: null,
        raw_text: null,
      },
      dose: {
        value: 1,
        unit: "tablet",
        raw_text: "1 tab",
      },
      schedule: {
        morning: true,
        afternoon: null,
        evening: null,
        night: null,
        is_as_needed_sos: false,
        raw_text: "1-0-0",
      },
      meal_instruction: {
        before_meal: null,
        after_meal: true,
        raw_text: "after food",
      },
      duration: {
        value: 30,
        unit: "days",
        raw_text: "30 days",
      },
    };

    const display = resolveMedicationDisplay(unvalidatedStrengthMed);

    // Assert that frontend does NOT infer strength from drug_name string
    assert.notEqual(display.displayStrength, "5 mg", "Must NOT infer '5 mg' from drug_name via regex");
    assert.notEqual(display.displayStrength, "5mg", "Must NOT infer '5mg' from drug_name via regex");
    assert.equal(
      display.displayStrength,
      "Strength unverified",
      "Must display 'Strength unverified' when structured strength is missing"
    );
    assert.equal(display.hasStrength, false);

    // Verify rendered badge string
    const renderedBadgeText = display.hasStrength
      ? `Strength: ${display.displayStrength}`
      : display.displayStrength;
    assert.equal(renderedBadgeText, "Strength unverified");
    assert.notEqual(renderedBadgeText, "Strength: 5 mg");
    assert.notEqual(renderedBadgeText, "Strength: 5mg");
  });

  it("Requirement 3b: Displays validated strength when med.strength.value exists", () => {
    const validatedMed: MedicationItem = {
      medication_id: "med-002",
      drug_name: "Metformin",
      is_verified_safe: true,
      requires_review: false,
      strength: {
        value: 500,
        unit: "mg",
        raw_text: "500mg",
      },
      dose: { value: 1, unit: "tablet", raw_text: "1 tab" },
      schedule: {
        morning: true,
        afternoon: false,
        evening: false,
        night: true,
        is_as_needed_sos: false,
        raw_text: "1-0-1",
      },
      meal_instruction: { before_meal: false, after_meal: true, raw_text: "after food" },
      duration: { value: 1, unit: "month", raw_text: "1 month" },
    };

    const display = resolveMedicationDisplay(validatedMed);
    assert.equal(display.displayStrength, "500 mg");
    assert.equal(display.hasStrength, true);
    assert.equal(display.displayDuration, "1 month");
    assert.equal(display.hasDuration, true);
  });

  it("Requirement 5: drug_name = 'Lisinopril 5mg' with strength.value = null and strength.raw_text = null displays 'Strength unverified' and NOT 'Strength: 5 mg'", () => {
    const med: MedicationItem = {
      medication_id: "test-lisinopril-001",
      drug_name: "Lisinopril 5mg",
      is_verified_safe: false,
      requires_review: true,
      strength: {
        value: null,
        unit: null,
        raw_text: null,
      },
      dose: { value: null, unit: null, raw_text: null },
      schedule: {
        morning: null,
        afternoon: null,
        evening: null,
        night: null,
        is_as_needed_sos: false,
        raw_text: null,
      },
      meal_instruction: { before_meal: null, after_meal: null, raw_text: null },
      duration: { value: null, unit: null, raw_text: null },
    };

    const resolved = resolveMedicationDisplay(med);
    assert.equal(resolved.displayName, "Lisinopril 5mg");
    assert.equal(resolved.displayStrength, "Strength unverified");
    assert.notEqual(resolved.displayStrength, "Strength: 5 mg");
    assert.notEqual(resolved.displayStrength, "5 mg");
    assert.notEqual(resolved.displayStrength, "5mg");
    assert.equal(resolved.hasStrength, false);
  });

  it("Requirement 6: Duration display strictly reflects validated structured data and never infers from strings", () => {
    // Validated 5 days
    const med5Days: MedicationItem = {
      medication_id: "med-aug",
      drug_name: "Tab. Augmentin 625",
      is_verified_safe: true,
      requires_review: false,
      strength: { value: 625, unit: "mg", raw_text: "625mg" },
      dose: { value: 1, unit: "tablet", raw_text: "1 tab" },
      schedule: { morning: true, afternoon: false, evening: true, night: false, is_as_needed_sos: false, raw_text: "1-0-1" },
      meal_instruction: { before_meal: false, after_meal: true, raw_text: "after food" },
      duration: { value: 5, unit: "days", raw_text: "x5days" },
    };
    const display5Days = resolveMedicationDisplay(med5Days);
    assert.equal(display5Days.displayDuration, "5 days");
    assert.equal(display5Days.hasDuration, true);

    // Validated 1 week (7 days)
    const med1Week: MedicationItem = {
      ...med5Days,
      drug_name: "Hexigel gum paint massage",
      duration: { value: 7, unit: "days", raw_text: "x1week" },
    };
    const display1Week = resolveMedicationDisplay(med1Week);
    assert.equal(display1Week.displayDuration, "7 days");
    assert.equal(display1Week.hasDuration, true);

    // Missing duration
    const medNoDuration: MedicationItem = {
      ...med5Days,
      duration: { value: null, unit: null, raw_text: null },
    };
    const displayNoDur = resolveMedicationDisplay(medNoDuration);
    assert.equal(displayNoDur.displayDuration, "Duration not confirmed");
    assert.equal(displayNoDur.hasDuration, false);
  });

  it("Requirement 7 & 8: Top-level section title reflects medication-level safety state and never shows Verified Posology Schedule when any med requires review", () => {
    const unverifiedPrescription: PrescriptionResponse = {
      success: true,
      request_id: "req-unverified",
      prescription_id: "rx-unverified",
      status: "COMPLETED", // Even if status was COMPLETED
      requires_review: false,
      safety_reasons: [],
      medications: [
        {
          medication_id: "med-1",
          drug_name: "Augmentin",
          is_verified_safe: false, // Medication requires review
          requires_review: true,
          strength: { value: null, unit: null, raw_text: null },
          dose: { value: null, unit: null, raw_text: null },
          schedule: { morning: null, afternoon: null, evening: null, night: null, is_as_needed_sos: false, raw_text: null },
          meal_instruction: { before_meal: null, after_meal: null, raw_text: null },
          duration: { value: null, unit: null, raw_text: null },
        },
      ],
      created_at: new Date().toISOString(),
    };

    const title = getScheduleSectionTitle(unverifiedPrescription);
    assert.notEqual(
      title,
      "Verified Posology Schedule",
      "Must NEVER show Verified Posology Schedule if any medication has requires_review=true or is_verified_safe=false"
    );
    assert.equal(title, "Unverified Medication Schedule (Requires Review)");

    const desc = getScheduleSectionDescription(unverifiedPrescription);
    assert.ok(desc.includes("Caution"));
  });
});
