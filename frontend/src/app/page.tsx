"use client";

import React, { useState, useEffect } from "react";
import {
  ShieldAlert,
  CheckCircle2,
  Mic,
  Upload,
  Volume2,
  Activity,
  AlertTriangle,
  FileText,
  Clock,
  Languages,
} from "lucide-react";

export default function HomePage() {
  const [selectedLanguage, setSelectedLanguage] = useState<"hi-IN" | "kn-IN" | "en-IN">("hi-IN");
  const [backendHealth, setBackendHealth] = useState<string>("Checking...");
  const [isHealthy, setIsHealthy] = useState<boolean | null>(null);

  useEffect(() => {
    // Probe backend health endpoint
    const checkHealth = async () => {
      try {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
        const res = await fetch(`${apiUrl}/health`);
        if (res.ok) {
          const data = await res.json();
          setBackendHealth(`Connected (${data.status})`);
          setIsHealthy(true);
        } else {
          setBackendHealth("Service Degraded");
          setIsHealthy(false);
        }
      } catch {
        setBackendHealth("Offline (Local Development Mode)");
        setIsHealthy(false);
      }
    };
    checkHealth();
  }, []);

  return (
    <div className="flex min-h-screen flex-col bg-slate-50">
      {/* Top Header */}
      <header className="sticky top-0 z-50 border-b border-slate-200 bg-white/95 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-4 py-3 sm:px-6">
          <div className="flex items-center space-x-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-sm">
              <Activity className="h-6 w-6" />
            </div>
            <div>
              <h1 className="text-lg font-bold tracking-tight text-slate-900">
                Bharat Builds
              </h1>
              <p className="text-xs font-medium text-emerald-700">
                Multimodal Medication Accessibility
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Language Selector */}
            <div className="flex items-center rounded-lg border border-slate-200 bg-slate-50 p-1 text-xs font-medium">
              <Languages className="mr-1.5 h-3.5 w-3.5 text-slate-500 ml-1" />
              <button
                onClick={() => setSelectedLanguage("hi-IN")}
                className={`rounded px-2 py-1 transition ${
                  selectedLanguage === "hi-IN"
                    ? "bg-emerald-600 text-white shadow-xs"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                हिन्दी
              </button>
              <button
                onClick={() => setSelectedLanguage("kn-IN")}
                className={`rounded px-2 py-1 transition ${
                  selectedLanguage === "kn-IN"
                    ? "bg-emerald-600 text-white shadow-xs"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                ಕನ್ನಡ
              </button>
              <button
                onClick={() => setSelectedLanguage("en-IN")}
                className={`rounded px-2 py-1 transition ${
                  selectedLanguage === "en-IN"
                    ? "bg-emerald-600 text-white shadow-xs"
                    : "text-slate-700 hover:text-slate-900"
                }`}
              >
                English
              </button>
            </div>

            {/* Backend Connectivity Status */}
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

      {/* Safety Notice Banner */}
      <div className="border-b border-amber-200 bg-amber-50 px-4 py-2 text-xs text-amber-900 sm:px-6">
        <div className="mx-auto flex max-w-6xl items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShieldAlert className="h-4 w-4 shrink-0 text-amber-700" />
            <span>
              <strong>Safety Core Tenet:</strong> This system is strictly an assistive accessibility aid. AI extracts, deterministic code validates. The system never guesses. Always verify prescriptions with your licensed physician or pharmacist.
            </span>
          </div>
          <span className="hidden md:inline-block rounded bg-amber-200 px-2 py-0.5 text-[10px] font-bold text-amber-800 uppercase">
            Fail-Closed Standard
          </span>
        </div>
      </div>

      {/* Main Content Area */}
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Left Column: Upload & Voice Interaction */}
          <div className="space-y-6 lg:col-span-6">
            {/* Upload Card */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Upload Prescription Image
                  </h2>
                  <p className="text-xs text-slate-500">
                    Supported: JPEG, PNG, WEBP (Max 10 MB). Blur detection enforced.
                  </p>
                </div>
                <FileText className="h-5 w-5 text-slate-400" />
              </div>

              <div className="group relative flex flex-col items-center justify-center rounded-lg border-2 border-dashed border-slate-300 bg-slate-50 p-8 text-center transition hover:border-emerald-500 hover:bg-emerald-50/20 cursor-pointer">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-100 text-emerald-600 group-hover:scale-105 transition">
                  <Upload className="h-6 w-6" />
                </div>
                <p className="mt-3 text-sm font-semibold text-slate-800">
                  Click or drag photo of prescription here
                </p>
                <p className="mt-1 text-xs text-slate-500">
                  Ensure the image is sharp, well-lit, and uncropped
                </p>
                <button
                  type="button"
                  className="mt-4 inline-flex items-center rounded-md bg-emerald-600 px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-emerald-700 transition"
                >
                  Select File
                </button>
              </div>
            </div>

            {/* Voice Accessibility Interface */}
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Voice Query Assistance
                  </h2>
                  <p className="text-xs text-slate-500">
                    Ask questions in {selectedLanguage === "hi-IN" ? "Hindi" : selectedLanguage === "kn-IN" ? "Kannada" : "English"} regarding dosage schedules.
                  </p>
                </div>
                <Volume2 className="h-5 w-5 text-emerald-600" />
              </div>

              <div className="flex flex-col items-center justify-center rounded-lg border border-slate-200 bg-slate-50 p-6">
                <button
                  type="button"
                  aria-label="Start Voice Query"
                  className="group flex h-16 w-16 items-center justify-center rounded-full bg-emerald-600 text-white shadow-md hover:bg-emerald-700 focus:ring-4 focus:ring-emerald-200 transition"
                >
                  <Mic className="h-8 w-8 group-hover:scale-110 transition" />
                </button>
                <p className="mt-4 text-xs font-semibold text-slate-700">
                  Tap microphone to speak
                </p>
                <p className="mt-1 text-[11px] text-slate-500 italic text-center max-w-sm">
                  {selectedLanguage === "hi-IN"
                    ? 'उदाहरण: "दवा खाना खाने से पहले लेनी है या बाद में?"'
                    : selectedLanguage === "kn-IN"
                    ? 'ಉದಾಹರಣೆ: "ಊಟದ ನಂತರ ಯಾವ ಮಾತ್ರೆ ತಗೋಬೇಕು?"'
                    : 'Example: "Which tablet should I take after meals?"'}
                </p>
              </div>
            </div>
          </div>

          {/* Right Column: Verified Extracted Schedule Preview */}
          <div className="space-y-6 lg:col-span-6">
            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-xs">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2 className="text-base font-semibold text-slate-900">
                    Verified Dosage Schedule
                  </h2>
                  <p className="text-xs text-slate-500">
                    Deterministic normalization output with safety confidence status.
                  </p>
                </div>
                <div className="inline-flex items-center rounded-full bg-emerald-100 px-2.5 py-1 text-xs font-semibold text-emerald-800">
                  <CheckCircle2 className="mr-1 h-3.5 w-3.5" />
                  Gated & Verified
                </div>
              </div>

              {/* Sample Medication Breakdown Table */}
              <div className="overflow-hidden rounded-lg border border-slate-200">
                <table className="min-w-full divide-y divide-slate-200 text-left text-xs">
                  <thead className="bg-slate-50 text-slate-700 font-semibold">
                    <tr>
                      <th className="px-3 py-2.5">Medication</th>
                      <th className="px-3 py-2.5">Schedule</th>
                      <th className="px-3 py-2.5">Relation to Food</th>
                      <th className="px-3 py-2.5">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-200 bg-white">
                    <tr>
                      <td className="px-3 py-3 font-medium text-slate-900">
                        Paracetamol 650mg
                        <span className="block text-[10px] text-slate-500">Tab • 3 Days</span>
                      </td>
                      <td className="px-3 py-3 text-slate-700">
                        <span className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                          1 - 0 - 1
                        </span>
                        <span className="block text-[10px] text-slate-500">Morning & Night</span>
                      </td>
                      <td className="px-3 py-3 text-slate-700">
                        <span className="inline-flex items-center rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
                          <Clock className="mr-1 h-3 w-3" /> After Meals
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <span className="inline-flex items-center text-emerald-600 text-[11px] font-medium">
                          <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> 98% Confident
                        </span>
                      </td>
                    </tr>
                    <tr className="bg-slate-50/50">
                      <td className="px-3 py-3 font-medium text-slate-900">
                        Amoxicillin 500mg
                        <span className="block text-[10px] text-slate-500">Cap • 5 Days</span>
                      </td>
                      <td className="px-3 py-3 text-slate-700">
                        <span className="inline-block rounded bg-slate-100 px-1.5 py-0.5 text-[10px] font-bold text-slate-700">
                          1 - 1 - 1
                        </span>
                        <span className="block text-[10px] text-slate-500">TDS (Thrice daily)</span>
                      </td>
                      <td className="px-3 py-3 text-slate-700">
                        <span className="inline-flex items-center rounded bg-blue-50 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
                          <Clock className="mr-1 h-3 w-3" /> After Meals
                        </span>
                      </td>
                      <td className="px-3 py-3">
                        <span className="inline-flex items-center text-emerald-600 text-[11px] font-medium">
                          <CheckCircle2 className="mr-1 h-3.5 w-3.5" /> 95% Confident
                        </span>
                      </td>
                    </tr>
                    <tr className="bg-amber-50/40">
                      <td className="px-3 py-3 font-medium text-slate-900">
                        [Illegible Dosage Line]
                        <span className="block text-[10px] text-amber-700">Ambiguous handwriting</span>
                      </td>
                      <td className="px-3 py-3 text-slate-500 italic">
                        Uncertain notation
                      </td>
                      <td className="px-3 py-3 text-slate-500 italic">
                        Unspecified
                      </td>
                      <td className="px-3 py-3">
                        <span className="inline-flex items-center text-amber-700 text-[11px] font-semibold">
                          <AlertTriangle className="mr-1 h-3.5 w-3.5" /> Refused (Review)
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>

              {/* Spoken Narration Preview Box */}
              <div className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50/50 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2">
                    <Volume2 className="h-4 w-4 text-emerald-700" />
                    <span className="text-xs font-bold text-emerald-900">
                      Voice Narration Preview ({selectedLanguage === "hi-IN" ? "Hindi" : selectedLanguage === "kn-IN" ? "Kannada" : "English"})
                    </span>
                  </div>
                  <button
                    type="button"
                    className="inline-flex items-center rounded bg-emerald-600 px-2.5 py-1 text-[11px] font-semibold text-white shadow-2xs hover:bg-emerald-700 transition"
                  >
                    Play Audio
                  </button>
                </div>
                <p className="mt-2 text-xs text-slate-700 leading-relaxed">
                  {selectedLanguage === "hi-IN"
                    ? "पैरासिटामोल दवा खाने के बाद सुबह और रात को लेनी है। एमोक्सिसिलिन दवा खाने के बाद दिन में तीन बार लेनी है। एक दवा अस्पष्ट है, कृपया अपने फार्मासिस्ट से जांचें।"
                    : selectedLanguage === "kn-IN"
                    ? "ಪ್ಯಾರಸಿಟಮಾಲ್ ಔಷಧಿಯನ್ನು ಊಟದ ನಂತರ ಬೆಳಿಗ್ಗೆ ಮತ್ತು ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಿ. ಅಮೋಕ್ಸಿಸಿಲಿನ್ ಔಷಧಿಯನ್ನು ಊಟದ ನಂತರ ದಿನಕ್ಕೆ ಮೂರು ಬಾರಿ ತೆಗೆದುಕೊಳ್ಳಿ. ಒಂದು ಔಷಧಿಯ ಕೈಬರಹ ಅಸ್ಪಷ್ಟವಾಗಿದೆ, ದಯವಿಟ್ಟು ಔಷಧಿ ತಜ್ಞರನ್ನು ಸಂಪರ್ಕಿಸಿ."
                    : "Take Paracetamol morning and night after food. Take Amoxicillin thrice daily after food. One line is ambiguous; please consult your pharmacist."}
                </p>
              </div>
            </div>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-200 bg-white px-4 py-4 text-center text-xs text-slate-500 sm:px-6">
        <p>
          Multimodal Medication Accessibility System &bull; Bharat Builds &bull; Built in collaboration with AWS
        </p>
      </footer>
    </div>
  );
}
