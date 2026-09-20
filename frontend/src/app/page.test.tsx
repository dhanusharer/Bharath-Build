import { describe, it } from "node:test";
import assert from "node:assert/strict";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";
import HomePage, {
  getScheduleSectionTitle,
  getScheduleSectionDescription,
  resolveMedicationDisplay,
} from "./page";
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

  it("Requirement 3: Resolves inconsistent rendering for 'Lisinopril 5mg' without 'Strength unstated'", () => {
    // Scenario: drug_name has "Lisinopril 5mg", but structured strength object was unpopulated
    const inconsistentMed: MedicationItem = {
      medication_id: "med-001",
      drug_name: "Lisinopril 5mg",
      is_verified_safe: true,
      requires_review: false,
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

    const display = resolveMedicationDisplay(inconsistentMed);

    // Assert that strength is detected from name and never marked as "Strength unstated"
    assert.equal(display.displayStrength, "5mg");
    assert.equal(display.hasStrength, true);
    assert.notEqual(
      display.displayStrength,
      "Strength unstated",
      "Should not display 'Strength unstated' when '5mg' is present in drug name"
    );
  });

  it("Requirement 3b: Displays 'Strength unstated' only when truly absent from both name and strength field", () => {
    const unstatedMed: MedicationItem = {
      medication_id: "med-002",
      drug_name: "Unknown Elixir",
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

    const display = resolveMedicationDisplay(unstatedMed);
    assert.equal(display.displayStrength, "Strength unstated");
    assert.equal(display.hasStrength, false);
  });
});
