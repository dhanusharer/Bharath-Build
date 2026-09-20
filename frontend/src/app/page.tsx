"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  ShieldAlert,
  CheckCircle2,
  Mic,
  MicOff,
  Upload,
  Volume2,
  Activity,
  AlertTriangle,
  FileText,
  Clock,
  Languages,
  Loader2,
  Sparkles,
  RotateCcw,
} from "lucide-react";
import {
  uploadPrescription,
  queryVoice,
  PrescriptionResponse,
  VoiceQueryResponse,
  MedicationItem,
} from "./api-client";

export interface ResolvedMedicationDisplay {
  displayName: string;
  displayStrength: string;
  displayDuration: string;
  hasStrength: boolean;
  hasDuration: boolean;
}

/**
 * Deterministically resolves medication display strings.
 * Guarantees consistent rendering so drug names containing strengths (e.g. "Lisinopril 5mg")
 * do not simultaneously display contradictory "Strength unstated" tags.
 */
export function resolveMedicationDisplay(med: MedicationItem): ResolvedMedicationDisplay {
  const rawName = (med.drug_name || "").trim();
  const strengthVal = med.strength?.value;
  const strengthUnit = (med.strength?.unit || "").trim();
  const rawStrength = (med.strength?.raw_text || "").trim();

  // Metric strength pattern (e.g. 500mg, 5 mg, 10mcg, 2.5ml, 20iu, etc.)
  const strengthPattern = /\b(\d+(?:\.\d+)?)\s*(mg|mcg|g|gm|ml|iu|puffs?|drops?)\b/i;

  let displayStrength = "Strength unstated";
  let hasStrength = false;

  if (strengthVal !== null && strengthVal !== undefined) {
    displayStrength = `${strengthVal} ${strengthUnit}`.trim();
    hasStrength = true;
  } else if (
    rawStrength &&
    rawStrength.toLowerCase() !== "null" &&
    rawStrength.toLowerCase() !== "none"
  ) {
    displayStrength = rawStrength;
    hasStrength = true;
  } else {
    // If drug_name contains strength notation (e.g. "Lisinopril 5mg"), extract it
    const match = rawName.match(strengthPattern);
    if (match) {
      displayStrength = match[0];
      hasStrength = true;
    }
  }

  // Duration formatting
  const durationVal = med.duration?.value;
  const durationUnit = (med.duration?.unit || "").trim();
  const rawDuration = (med.duration?.raw_text || "").trim();

  let displayDuration = "Duration unstated";
  let hasDuration = false;

  if (durationVal !== null && durationVal !== undefined) {
    displayDuration = `${durationVal} ${durationUnit}`.trim();
    hasDuration = true;
  } else if (
    rawDuration &&
    rawDuration.toLowerCase() !== "null" &&
    rawDuration.toLowerCase() !== "none"
  ) {
    displayDuration = rawDuration;
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
  if (prescription.status === "REQUIRES_REVIEW" || prescription.requires_review) {
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
  if (prescription.status === "REQUIRES_REVIEW" || prescription.requires_review) {
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

export default function HomePage() {
  const [selectedLanguage, setSelectedLanguage] = useState<"hi-IN" | "kn-IN" | "en-IN">("en-IN");
  const [backendHealth, setBackendHealth] = useState<string>("Checking...");
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  // Prescription Ingestion State — Initial state strictly null (no stale/hardcoded data)
  const [isUploading, setIsUploading] = useState<boolean>(false);
  const [prescriptionData, setPrescriptionData] = useState<PrescriptionResponse | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Voice Interaction State
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isQueryingVoice, setIsQueryingVoice] = useState<boolean>(false);
  const [voiceResponse, setVoiceResponse] = useState<VoiceQueryResponse | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";
        const res = await fetch(`${apiUrl}/api/v1/health`);
        if (res.ok) {
          const data = await res.json();
          setBackendHealth(`Connected (${data.status})`);
          setIsHealthy(true);
        } else {
          setBackendHealth("Service Degraded");
          setIsHealthy(false);
        }
      } catch {
        setBackendHealth("Offline (Local Mode)");
        setIsHealthy(false);
      }
    };
    checkHealth();
  }, []);

  // Reset current session to fresh state
  const handleResetSession = () => {
    setPrescriptionData(null);
    setVoiceResponse(null);
    setUploadError(null);
    setVoiceError(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  // Handle File Upload
  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    // Reset previous session data before new upload
    setIsUploading(true);
    setUploadError(null);
    setPrescriptionData(null);
    setVoiceResponse(null);
    setVoiceError(null);

    try {
      const result = await uploadPrescription(file);
      setPrescriptionData(result);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Prescription ingestion failed.";
      setUploadError(msg);
    } finally {
      setIsUploading(false);
    }
  };

  // Handle Voice Recording
  const startRecording = async () => {
    setVoiceError(null);
    audioChunksRef.current = [];
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream);
      mediaRecorderRef.current = recorder;

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) {
          audioChunksRef.current.push(e.data);
        }
      };

      recorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: "audio/wav" });
        stream.getTracks().forEach((track) => track.stop());

        if (!prescriptionData?.prescription_id) {
          setVoiceError("Please upload and verify a prescription first.");
          return;
        }

        setIsQueryingVoice(true);
        try {
          const vResp = await queryVoice(
            prescriptionData.prescription_id,
            audioBlob,
            selectedLanguage
          );
          setVoiceResponse(vResp);

          // Auto-play audio response if present
          if (vResp.audio_base64) {
            const audioSrc = `data:${vResp.audio_content_type};base64,${vResp.audio_base64}`;
            const audio = new Audio(audioSrc);
            audio.play().catch(() => {});
          }
        } catch (err: unknown) {
          const msg = err instanceof Error ? err.message : "Voice query failed.";
          setVoiceError(msg);
        } finally {
          setIsQueryingVoice(false);
        }
      };

      recorder.start();
      setIsRecording(true);
    } catch {
      setVoiceError("Microphone access was denied or is unavailable.");
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const playSynthesizedAudio = (base64Audio: string, mimeType: string = "audio/mpeg") => {
    const audio = new Audio(`data:${mimeType};base64,${base64Audio}`);
    audio.play().catch(() => {});
  };

  return (
    <div className="flex min-h-screen flex-col bg-slate-50 font-sans antialiased">
      {/* Top Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-xs">
              <Activity className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-slate-900">Bharat Builds</h1>
              <p className="text-xs font-semibold text-emerald-700">
                Multimodal Medication Accessibility
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Language Selector */}
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-medium">
              <Languages className="mr-1.5 h-3.5 w-3.5 text-slate-500 ml-1" />
              <button
                onClick={() => setSelectedLanguage("en-IN")}
                className={`rounded px-2 py-1 transition ${
                  selectedLanguage === "en-IN"
                    ? "bg-emerald-600 text-white shadow-2xs"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                English
              </button>
              <button
                onClick={() => setSelectedLanguage("hi-IN")}
                className={`rounded px-2 py-1 transition ${
                  selectedLanguage === "hi-IN"
                    ? "bg-emerald-600 text-white shadow-2xs"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                हिन्दी
              </button>
              <button
                onClick={() => setSelectedLanguage("kn-IN")}
                className={`rounded px-2 py-1 transition ${
                  selectedLanguage === "kn-IN"
                    ? "bg-emerald-600 text-white shadow-2xs"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                ಕನ್ನಡ
              </button>
            </div>

            {/* Health Indicator */}
            <div className="hidden sm:flex items-center space-x-2 text-xs font-medium">
              <span
                className={`h-2.5 w-2.5 rounded-full ${
                  isHealthy ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
                }`}
              />
              <span className="text-slate-600">{backendHealth}</span>
            </div>
          </div>
        </div>
      </header>

      {/* Fail-Closed Safety Notice Banner */}
      <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900 sm:px-6">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="h-4 w-4 shrink-0 text-amber-700" />
            <span>
              <strong>Deterministic Safety Gate:</strong> AI extracts raw clinical observations;
              deterministic code gates and normalizes. The system never guesses or auto-completes
              uncertain posology. Always consult your pharmacist.
            </span>
          </div>
          <span className="hidden md:inline-block rounded bg-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-800 uppercase">
            Fail-Closed Standard
          </span>
        </div>
      </div>

      {/* Main Grid */}
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Left Column: Upload & Voice Query */}
          <div className="space-y-6 lg:col-span-6">
            {/* Upload Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Upload Prescription Image
                  </h2>
                  <p className="text-xs text-slate-500">
                    Accepts JPEG, PNG, WebP. Safe S3 ingestion with Bedrock vision extraction.
                  </p>
                </div>
                <FileText className="h-5 w-5 text-slate-400" />
              </div>

              <input
                type="file"
                ref={fileInputRef}
                onChange={handleFileUpload}
                accept="image/jpeg,image/png,image/webp"
                className="hidden"
                data-testid="prescription-file-input"
              />

              <div
                onClick={() => fileInputRef.current?.click()}
                className="group relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center transition hover:border-emerald-500 hover:bg-emerald-50/20 cursor-pointer"
              >
                {isUploading ? (
                  <div className="flex flex-col items-center">
                    <Loader2 className="h-10 w-10 animate-spin text-emerald-600" />
                    <p className="mt-3 text-sm font-semibold text-slate-800">
                      Processing Prescription...
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      S3 Staging &bull; Bedrock Vision &bull; Deterministic Safety Gate
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 group-hover:scale-105 transition">
                      <Upload className="h-6 w-6" />
                    </div>
                    <p className="mt-3 text-sm font-semibold text-slate-800">
                      Click or drag prescription photo here
                    </p>
                    <p className="mt-1 text-xs text-slate-500">
                      Ensure all posology lines and timing are visible
                    </p>
                    <button
                      type="button"
                      className="mt-4 inline-flex items-center rounded-md bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-2xs hover:bg-emerald-700 transition"
                    >
                      Select File
                    </button>
                  </>
                )}
              </div>

              {uploadError && (
                <div className="mt-3 flex items-center space-x-2 rounded-lg bg-red-50 p-3 text-xs text-red-700">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
                  <span>{uploadError}</span>
                </div>
              )}
            </div>

            {/* Voice Accessibility Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">Voice Query Assistance</h2>
                  <p className="text-xs text-slate-500">
                    Ask questions in{" "}
                    {selectedLanguage === "hi-IN"
                      ? "Hindi"
                      : selectedLanguage === "kn-IN"
                      ? "Kannada"
                      : "English"}{" "}
                    using real-time Transcribe streaming.
                  </p>
                </div>
                <Volume2 className="h-5 w-5 text-emerald-600" />
              </div>

              <div className="flex flex-col items-center justify-center rounded-lg border border-slate-200 bg-slate-50 p-6">
                <button
                  type="button"
                  data-testid="voice-record-button"
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={!prescriptionData || isQueryingVoice}
                  className={`group flex h-16 w-16 items-center justify-center rounded-full transition shadow-md ${
                    !prescriptionData
                      ? "bg-slate-200 text-slate-400 cursor-not-allowed border border-slate-300"
                      : isRecording
                      ? "bg-red-600 text-white animate-pulse"
                      : "bg-emerald-600 text-white hover:bg-emerald-700 focus:ring-4 focus:ring-emerald-200"
                  }`}
                  title={
                    !prescriptionData
                      ? "Upload a prescription above to enable voice queries"
                      : "Click to ask a voice question"
                  }
                >
                  {isQueryingVoice ? (
                    <Loader2 className="h-8 w-8 animate-spin" />
                  ) : isRecording ? (
                    <MicOff className="h-8 w-8" />
                  ) : (
                    <Mic className="h-8 w-8 group-hover:scale-110 transition" />
                  )}
                </button>

                <p
                  className="mt-4 text-xs font-semibold text-slate-700"
                  data-testid="voice-status-text"
                >
                  {isQueryingVoice
                    ? "Transcribing & Synthesizing Spoken Answer..."
                    : isRecording
                    ? "Recording... Tap again to stop and query"
                    : prescriptionData
                    ? "Tap microphone to ask a question"
                    : "No active prescription. Upload a prescription above to enable voice queries."}
                </p>

                <p className="mt-1 text-[11px] text-slate-500 italic text-center max-w-sm">
                  {selectedLanguage === "hi-IN"
                    ? 'उदाहरण: "रात को कौन सी दवा लेनी है?"'
                    : selectedLanguage === "kn-IN"
                    ? 'ಉದಾಹರಣೆ: "ರಾತ್ರಿ ಯಾವ ಮಾತ್ರೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು?"'
                    : 'Example: "What should I take at night?"'}
                </p>
              </div>

              {voiceError && (
                <div className="mt-3 flex items-center space-x-2 rounded-lg bg-red-50 p-3 text-xs text-red-700">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
                  <span>{voiceError}</span>
                </div>
              )}

              {/* Voice Query Response Card */}
              {voiceResponse && (
                <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/60 p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Sparkles className="h-4 w-4 text-emerald-700" />
                      <span className="text-xs font-bold text-emerald-950 uppercase tracking-wide">
                        Query Answer &bull; {voiceResponse.intent}
                      </span>
                    </div>
                    {voiceResponse.audio_base64 && (
                      <button
                        type="button"
                        onClick={() =>
                          playSynthesizedAudio(
                            voiceResponse.audio_base64!,
                            voiceResponse.audio_content_type
                          )
                        }
                        className="inline-flex items-center rounded bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xs hover:bg-emerald-700 transition"
                      >
                        <Volume2 className="mr-1 h-3.5 w-3.5" /> Replay Audio
                      </button>
                    )}
                  </div>

                  <p className="mt-2 text-xs text-slate-600 font-medium">
                    You asked: &ldquo;{voiceResponse.transcript}&rdquo;
                  </p>
                  <p className="mt-1 text-sm font-semibold text-slate-900 leading-relaxed">
                    {voiceResponse.response_text}
                  </p>

                  {voiceResponse.requires_review && (
                    <div className="mt-2 flex items-center space-x-1.5 text-xs font-medium text-amber-800">
                      <AlertTriangle className="h-3.5 w-3.5 text-amber-600" />
                      <span>
                        {voiceResponse.safety_reasons.join(", ") ||
                          "Prescription requires pharmacist verification."}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Medication Schedule (Explicitly Dynamic & Tied to Session) */}
          <div className="space-y-6 lg:col-span-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              {/* Session / Prescription ID State Banner */}
              {prescriptionData ? (
                <div
                  data-testid="active-session-banner"
                  className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-xs"
                >
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-slate-700">Prescription Session:</span>
                    <span
                      data-testid="active-prescription-id"
                      className="font-mono text-slate-900 font-bold bg-white px-2 py-0.5 rounded border border-slate-200"
                    >
                      {prescriptionData.prescription_id}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleResetSession}
                    className="inline-flex items-center text-[11px] font-semibold text-slate-600 hover:text-slate-900 hover:underline"
                  >
                    <RotateCcw className="mr-1 h-3 w-3" />
                    New Session
                  </button>
                </div>
              ) : (
                <div
                  data-testid="fresh-session-banner"
                  className="mb-4 flex items-center justify-between rounded-lg border border-dashed border-slate-200 bg-slate-50/60 px-3 py-2 text-xs text-slate-500"
                >
                  <span className="flex items-center">
                    <span className="mr-2 h-2 w-2 rounded-full bg-slate-400" />
                    Session Status: <strong className="ml-1 text-slate-700">Fresh Session</strong>
                  </span>
                  <span className="text-[11px] text-slate-400">Awaiting prescription upload</span>
                </div>
              )}

              {/* Section Header (Dynamic: Never "Verified" when REQUIRES_REVIEW or null) */}
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2
                    data-testid="schedule-section-title"
                    className="text-base font-semibold text-slate-900"
                  >
                    {getScheduleSectionTitle(prescriptionData)}
                  </h2>
                  <p
                    data-testid="schedule-section-desc"
                    className="text-xs text-slate-500 mt-0.5"
                  >
                    {getScheduleSectionDescription(prescriptionData)}
                  </p>
                </div>

                {prescriptionData ? (
                  <div
                    data-testid="prescription-status-badge"
                    className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                      prescriptionData.requires_review ||
                      prescriptionData.status === "REQUIRES_REVIEW"
                        ? "bg-amber-100 text-amber-800 border border-amber-300"
                        : prescriptionData.status === "COMPLETED"
                        ? "bg-emerald-100 text-emerald-800 border border-emerald-300"
                        : "bg-slate-100 text-slate-700"
                    }`}
                  >
                    {prescriptionData.requires_review ||
                    prescriptionData.status === "REQUIRES_REVIEW" ? (
                      <>
                        <AlertTriangle className="mr-1 h-3.5 w-3.5 text-amber-600" />
                        Requires Review
                      </>
                    ) : prescriptionData.status === "COMPLETED" ? (
                      <>
                        <CheckCircle2 className="mr-1 h-3.5 w-3.5 text-emerald-600" />
                        Verified Safe
                      </>
                    ) : (
                      prescriptionData.status
                    )}
                  </div>
                ) : (
                  <span
                    data-testid="awaiting-upload-badge"
                    className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-1 text-xs font-medium text-slate-500 border border-slate-200"
                  >
                    Awaiting Upload
                  </span>
                )}
              </div>

              {/* Medication Schedule Area */}
              {prescriptionData?.medications && prescriptionData.medications.length > 0 ? (
                <div className="overflow-hidden rounded-lg border border-slate-200">
                  <table
                    data-testid="medications-table"
                    className="min-w-full divide-y divide-slate-200 text-left text-xs"
                  >
                    <thead className="bg-slate-50 text-slate-700 font-semibold">
                      <tr>
                        <th className="px-3 py-2.5">Medication</th>
                        <th className="px-3 py-2.5">Schedule</th>
                        <th className="px-3 py-2.5">Food Relation</th>
                        <th className="px-3 py-2.5">Safety Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-200 bg-white">
                      {prescriptionData.medications.map((med, index) => {
                        const { displayName, displayStrength, displayDuration, hasStrength } =
                          resolveMedicationDisplay(med);

                        return (
                          <tr
                            key={med.medication_id || index}
                            data-testid={`medication-row-${index}`}
                            className={med.requires_review ? "bg-amber-50/40" : "bg-white"}
                          >
                            <td className="px-3 py-3 font-medium text-slate-900">
                              <div className="font-semibold text-slate-900">{displayName}</div>
                              <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px]">
                                <span
                                  data-testid={`medication-strength-${index}`}
                                  className={`inline-flex items-center rounded px-1.5 py-0.5 font-medium ${
                                    hasStrength
                                      ? "bg-slate-100 text-slate-700"
                                      : "bg-amber-100/70 text-amber-800 border border-amber-200"
                                  }`}
                                >
                                  Strength: {displayStrength}
                                </span>
                                <span className="text-slate-300">&bull;</span>
                                <span
                                  data-testid={`medication-duration-${index}`}
                                  className="text-slate-500 font-normal"
                                >
                                  Duration: {displayDuration}
                                </span>
                              </div>
                            </td>
                            <td className="px-3 py-3 text-slate-700">
                              <span className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                                {med.schedule.raw_text || "As directed"}
                              </span>
                              <span className="block text-[10px] text-slate-500 mt-0.5">
                                {[
                                  med.schedule.morning ? "Morning" : null,
                                  med.schedule.afternoon ? "Afternoon" : null,
                                  med.schedule.evening ? "Evening" : null,
                                  med.schedule.night ? "Night" : null,
                                ]
                                  .filter(Boolean)
                                  .join(" / ") || "Unspecified"}
                              </span>
                            </td>
                            <td className="px-3 py-3 text-slate-700">
                              {med.meal_instruction.after_meal ? (
                                <span className="inline-flex items-center rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
                                  <Clock className="mr-1 h-3 w-3" /> After Food
                                </span>
                              ) : med.meal_instruction.before_meal ? (
                                <span className="inline-flex items-center rounded bg-amber-50 px-1.5 py-0.5 text-[10px] font-medium text-amber-700">
                                  <Clock className="mr-1 h-3 w-3" /> Before Food
                                </span>
                              ) : (
                                <span className="text-[10px] text-slate-400">Unspecified</span>
                              )}
                            </td>
                            <td className="px-3 py-3">
                              {med.is_verified_safe ? (
                                <span className="inline-flex items-center text-emerald-600 text-[11px] font-medium">
                                  <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> Verified
                                </span>
                              ) : (
                                <span className="inline-flex items-center text-amber-700 text-[11px] font-semibold">
                                  <AlertTriangle className="mr-1 h-3.5 w-3.5" /> Review Needed
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              ) : (
                /* Clean Empty State: Fresh session without hardcoded or stale medication data */
                <div
                  data-testid="empty-prescription-state"
                  className="flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-200 bg-slate-50/50 p-10 text-center"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
                    <FileText className="h-6 w-6" />
                  </div>
                  <h3 className="mt-3 text-sm font-semibold text-slate-800">
                    No Prescription Uploaded
                  </h3>
                  <p className="mt-1 text-xs text-slate-500 max-w-sm">
                    Upload or drag a prescription photo on the left to extract medication details,
                    timing schedules, and deterministic safety validation.
                  </p>
                  <div className="mt-4 inline-flex items-center rounded-full bg-slate-200/80 px-2.5 py-1 text-[11px] font-medium text-slate-600">
                    Session Status: Fresh (No Active Prescription)
                  </div>
                </div>
              )}

              {/* Safety State Notification (Only shown when a prescription requires review) */}
              {prescriptionData?.requires_review && (
                <div
                  data-testid="safety-review-alert"
                  className="mt-4 rounded-lg border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900"
                >
                  <p className="font-semibold flex items-center">
                    <AlertTriangle className="mr-1.5 h-4 w-4 text-amber-700" />
                    Pharmacist Consultation Required
                  </p>
                  <p className="mt-1 text-slate-700">
                    One or more posology fields could not be deterministically verified with full
                    clinical certainty. Unverified fields must not be administered without
                    professional confirmation.
                  </p>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white px-4 py-4 text-center text-xs text-slate-500 sm:px-6">
        <p>
          Multimodal Medication Accessibility System &bull; Bharat Builds &bull; Built in
          collaboration with AWS
        </p>
      </footer>
    </div>
  );
}
