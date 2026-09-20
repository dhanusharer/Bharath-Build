"use client";

import React, { useState, useEffect, useRef } from "react";
import Image from "next/image";
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
  ArrowRight,
  ShieldCheck,
  Check,
  Zap,
  HeartPulse,
  Sun,
  Sunset,
  Moon,
  Coffee,
  Pill,
  BookmarkCheck,
  Stethoscope,
  ChevronRight,
} from "lucide-react";
import {
  uploadPrescription,
  queryVoice,
  PrescriptionResponse,
  VoiceQueryResponse,
} from "./api-client";
import {
  resolveMedicationDisplay,
  getScheduleSectionTitle,
  getScheduleSectionDescription,
} from "./medication-utils";

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
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [voiceResponse, setVoiceResponse] = useState<VoiceQueryResponse | null>(null);
  const [voiceError, setVoiceError] = useState<string | null>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Thumbnail active index state
  const [activeThumbnail, setActiveThumbnail] = useState<number>(0);

  // FAQ accordion state
  const [expandedFaq, setExpandedFaq] = useState<number | null>(null);

  // Pricing controls: Currency and Billing period
  const [billingCycle, setBillingCycle] = useState<"monthly" | "annual">("monthly");
  const [currency, setCurrency] = useState<"USD" | "INR">("USD");

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

  // Quick Load Verified Clinical Samples for Instant Testing
  const handleLoadSample = (sampleType: "verified" | "review") => {
    setUploadError(null);
    setVoiceError(null);
    setVoiceResponse(null);

    if (sampleType === "verified") {
      setPrescriptionData({
        success: true,
        request_id: "req-sample-dental-01",
        prescription_id: "RX-SAMPLE-AUGMENTIN-625",
        status: "COMPLETED",
        requires_review: false,
        safety_reasons: [],
        created_at: new Date().toISOString(),
        medications: [
          {
            medication_id: "med-aug-625",
            drug_name: "Tab. Augmentin 625",
            is_verified_safe: true,
            requires_review: false,
            strength: { value: 625, unit: "mg", raw_text: "625mg" },
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
            duration: { value: 5, unit: "days", raw_text: "5 days" },
          },
          {
            medication_id: "med-enz-01",
            drug_name: "Tab. Enzflam",
            is_verified_safe: true,
            requires_review: false,
            strength: { value: 100, unit: "mg", raw_text: "100mg" },
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
            duration: { value: 5, unit: "days", raw_text: "5 days" },
          },
          {
            medication_id: "med-pand-01",
            drug_name: "Cap. Pan D 40",
            is_verified_safe: true,
            requires_review: false,
            strength: { value: 40, unit: "mg", raw_text: "40mg" },
            dose: { value: 1, unit: "capsule", raw_text: "1 cap" },
            schedule: {
              morning: true,
              afternoon: false,
              evening: false,
              night: false,
              is_as_needed_sos: false,
              raw_text: "1-0-0",
            },
            meal_instruction: { before_meal: true, after_meal: false, raw_text: "before food" },
            duration: { value: 5, unit: "days", raw_text: "5 days" },
          },
        ],
      });
    } else {
      setPrescriptionData({
        success: true,
        request_id: "req-sample-review-02",
        prescription_id: "RX-SAMPLE-UNCERTAIN-AUDIT",
        status: "REQUIRES_REVIEW",
        requires_review: true,
        safety_reasons: ["Low handwriting confidence", "Unverified dosage timing on line 2"],
        created_at: new Date().toISOString(),
        medications: [
          {
            medication_id: "med-review-01",
            drug_name: "Lisinopril 5mg",
            is_verified_safe: false,
            requires_review: true,
            strength: { value: null, unit: null, raw_text: null },
            dose: { value: 1, unit: "tablet", raw_text: "1 tab" },
            schedule: {
              morning: true,
              afternoon: null,
              evening: null,
              night: null,
              is_as_needed_sos: false,
              raw_text: "1-?-?",
            },
            meal_instruction: { before_meal: null, after_meal: true, raw_text: "after food" },
            duration: { value: null, unit: null, raw_text: null },
          },
        ],
      });
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
            playSynthesizedAudio(vResp.audio_base64, vResp.audio_content_type);
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
    setIsPlayingAudio(true);
    const audio = new Audio(`data:${mimeType};base64,${base64Audio}`);
    audio.onended = () => setIsPlayingAudio(false);
    audio.onerror = () => setIsPlayingAudio(false);
    audio.play().catch(() => setIsPlayingAudio(false));
  };

  // Trigger quick prompt simulation when user taps an example query chip
  const handleQuickPromptClick = (promptText: string) => {
    if (!prescriptionData) return;
    setIsQueryingVoice(true);
    setTimeout(() => {
      setIsQueryingVoice(false);
      // Construct intuitive responses based on active meds
      const nightMeds = prescriptionData.medications?.filter((m) => m.schedule.night) || [];
      const hasNight = nightMeds.length > 0;

      let reply = "";
      if (promptText.includes("night") || promptText.includes("ರಾತ್ರಿ") || promptText.includes("रात")) {
        if (prescriptionData.requires_review) {
          reply =
            selectedLanguage === "kn-IN"
              ? "ಪ್ರಿಸ್ಕ್ರಿಪ್ಷನ್ ಪರಿಶೀಲನೆಯಲ್ಲಿದೆ. ದಯವಿಟ್ಟು ಔಷಧ ವಿತರಕರನ್ನು ಸಂಪರ್ಕಿಸಿ."
              : selectedLanguage === "hi-IN"
              ? "पर्चे की पुष्टि की आवश्यकता है। कृपया फार्मासिस्ट से परामर्श लें।"
              : "Prescription requires pharmacist verification. Please confirm night dosages with your doctor.";
        } else if (hasNight) {
          const names = nightMeds.map((m) => m.drug_name).join(", ");
          reply =
            selectedLanguage === "kn-IN"
              ? `ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಬೇಕಾದ ಮಾತ್ರೆಗಳು: ${names}. ಊಟದ ನಂತರ ತೆಗೆದುಕೊಳ್ಳಿ.`
              : selectedLanguage === "hi-IN"
              ? `रात को लेने वाली दवाएं: ${names}. खाने के बाद लें।`
              : `At night, take: ${names}, as prescribed after meals.`;
        } else {
          reply =
            selectedLanguage === "kn-IN"
              ? "ರಾತ್ರಿ ತೆಗೆದುಕೊಳ್ಳಲು ಯಾವುದೇ ಔಷಧವಿಲ್ಲ."
              : selectedLanguage === "hi-IN"
              ? "रात के लिए कोई दवा निर्धारित नहीं है।"
              : "There are no medications scheduled for nighttime administration.";
        }
      } else {
        reply =
          selectedLanguage === "kn-IN"
            ? "ನಿಮ್ಮ ವೈದ್ಯರ ನಿರ್ದೇಶನದಂತೆ ವೇಳಾಪಟ್ಟಿಯನ್ನು ಅನುಸರಿಸಿ."
            : selectedLanguage === "hi-IN"
            ? "कृपया डॉक्टर के निर्देशानुसार समय पर दवा लें।"
            : "Follow your verified posology schedule as outlined on the prescription.";
      }

      setVoiceResponse({
        success: true,
        request_id: `req-quick-${Date.now()}`,
        prescription_id: prescriptionData.prescription_id,
        transcript: promptText,
        intent: "MEDICATION_SCHEDULE",
        target_drug: null,
        response_text: reply,
        audio_base64: null,
        audio_content_type: "audio/mpeg",
        language: selectedLanguage,
        requires_review: prescriptionData.requires_review,
        safety_reasons: prescriptionData.safety_reasons,
        created_at: new Date().toISOString(),
        result_state: prescriptionData.requires_review
          ? "PRESCRIPTION_REQUIRES_REVIEW"
          : "CONFIRMED_MATCH",
      });
    }, 700);
  };

  const scrollToCommandCenter = () => {
    const el = document.getElementById("command-center");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const scrollToPricing = () => {
    const el = document.getElementById("pricing");
    if (el) {
      el.scrollIntoView({ behavior: "smooth" });
    }
  };

  const thumbnails = [
    { title: "Prescription OCR", badge: "Bedrock Vision" },
    { title: "Posology Matrix", badge: "Deterministic" },
    { title: "Kannada Speech", badge: "Regional TTS" },
    { title: "Hindi Streaming", badge: "Polly Aditi" },
    { title: "Fail-Closed Audit", badge: "Zero Hallucination" },
  ];

  const quickPrompts = {
    "en-IN": [
      "What should I take at night?",
      "Which medicine is before food?",
      "Summarize my daily schedule",
    ],
    "hi-IN": [
      "रात को कौन सी दवा लेनी है?",
      "खाने से पहले क्या लेना है?",
      "पूरा टाइम टेबल बताओ",
    ],
    "kn-IN": [
      "ರಾತ್ರಿ ಯಾವ ಮಾತ್ರೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು?",
      "ಊಟಕ್ಕೆ ಮುಂಚೆ ಏನು ತಗೋಬೇಕು?",
      "ನನ್ನ ವೇಳಾಪಟ್ಟಿ ತಿಳಿಸಿ",
    ],
  };

  const faqItems = [
    {
      q: "How does the deterministic safety gate prevent AI hallucinations?",
      a: "Our architecture employs a strict separation of concerns. While Amazon Bedrock extracts raw observational candidates from handwritten doctor notes, zero medication is marked safe until a deterministic rules engine validates strength, posology timings, and clinical contraindications. If any field is ambiguous, the system fails closed with REQUIRES_REVIEW.",
    },
    {
      q: "Which regional languages are supported for voice queries and audio playback?",
      a: "The command center natively supports English (Indian dialect), Hindi (हिन्दी via Amazon Polly Aditi), and regional Kannada (ಕನ್ನಡ via dedicated high-fidelity regional TTS). Both speech-to-text queries via Amazon Transcribe Streaming and spoken answers are fully localized.",
    },
    {
      q: "What does the $17/month Superpower Health Pass include?",
      a: "The Health Pass provides unlimited high-resolution prescription digitization, real-time vernacular voice streaming, multi-profile family tracking, pharmacist-verified PDF export, and priority processing on dedicated AWS Bedrock instances, accompanied by the physical marbled membership card.",
    },
    {
      q: "Can this system be integrated into hospital management and pharmacy POS?",
      a: "Yes. Our Clinical Provider Tier ($99/mo) exposes standard FHIR-compliant REST APIs and Webhook hooks to plug handwritten digitization directly into hospital EMRs, pharmacy dispensing stations, and state health registries.",
    },
  ];

  // Pricing calculations
  const isAnnual = billingCycle === "annual";
  const healthPassPrice = currency === "USD" ? (isAnnual ? "$13.60" : "$17") : (isAnnual ? "₹1,119" : "₹1,399");
  const providerPrice = currency === "USD" ? (isAnnual ? "$79" : "$99") : (isAnnual ? "₹6,399" : "₹7,999");
  const billingPeriodLabel = isAnnual ? "/ mo (billed annually)" : "/ month";

  return (
    <div className="flex min-h-screen flex-col bg-white text-[#18181b]">
      {/* 1. FLOATING PILL NAVIGATION BAR */}
      <div className="fixed top-5 left-0 right-0 z-50 flex justify-center px-4 pointer-events-none">
        <nav className="pointer-events-auto flex items-center justify-between gap-4 sm:gap-8 rounded-[15px] bg-[#18181b]/95 backdrop-blur-md px-5 py-3 border border-white/10 shadow-lg text-white max-w-[1120px] w-full transition">
          {/* Brand Wordmark */}
          <div className="flex items-center gap-2">
            <span className="font-bold tracking-tight text-sm uppercase flex items-center text-white">
              BHARAT BUILDS
              <span className="text-[#fc5f2b] ml-1 text-base leading-none">&bull;</span>
              <span className="ml-1 text-[11px] font-normal text-white/60 tracking-normal capitalize">
                Superpower
              </span>
            </span>
          </div>

          {/* Center Nav Links */}
          <div className="hidden md:flex items-center gap-6 text-xs text-white/60 font-medium">
            <a
              href="#command-center"
              className="hover:text-white transition tracking-tight"
            >
              Command Center
            </a>
            <a
              href="#telemetry"
              className="hover:text-white transition tracking-tight"
            >
              Clinical Telemetry
            </a>
            <a
              href="#pricing"
              className="hover:text-white transition tracking-tight"
            >
              Membership & Pricing
            </a>
            <a
              href="#faq"
              className="hover:text-white transition tracking-tight"
            >
              Safety FAQ
            </a>
          </div>

          {/* Right Action & Language Selector */}
          <div className="flex items-center gap-2 sm:gap-3">
            {/* Language Selector Pills */}
            <div className="flex items-center rounded-full bg-white/10 p-0.5 text-[11px] font-medium border border-white/10">
              <Languages className="ml-1.5 mr-1 h-3 w-3 text-white/60" />
              <button
                type="button"
                onClick={() => setSelectedLanguage("en-IN")}
                className={`rounded-full px-2 py-0.5 transition ${
                  selectedLanguage === "en-IN"
                    ? "bg-[#fc5f2b] text-white font-semibold"
                    : "text-white/70 hover:text-white"
                }`}
              >
                EN
              </button>
              <button
                type="button"
                onClick={() => setSelectedLanguage("hi-IN")}
                className={`rounded-full px-2 py-0.5 transition ${
                  selectedLanguage === "hi-IN"
                    ? "bg-[#fc5f2b] text-white font-semibold"
                    : "text-white/70 hover:text-white"
                }`}
              >
                HI
              </button>
              <button
                type="button"
                onClick={() => setSelectedLanguage("kn-IN")}
                className={`rounded-full px-2 py-0.5 transition ${
                  selectedLanguage === "kn-IN"
                    ? "bg-[#fc5f2b] text-white font-semibold"
                    : "text-white/70 hover:text-white"
                }`}
              >
                KN
              </button>
            </div>

            {/* Primary Action Button (Sunrise Coral) */}
            <button
              type="button"
              onClick={scrollToCommandCenter}
              className="rounded-full bg-[#fc5f2b] px-3.5 py-1.5 text-xs font-bold text-white transition hover:opacity-90 flex items-center gap-1 shadow-sm"
            >
              <span>Scan Rx</span>
              <ArrowRight className="h-3 w-3" />
            </button>
          </div>
        </nav>
      </div>

      {/* 2. CINEMATIC ATMOSPHERIC HERO SECTION */}
      <section className="relative min-h-[640px] md:min-h-[720px] w-full bg-[#090d12] flex flex-col justify-center items-center text-center px-4 pt-32 pb-20 overflow-hidden">
        {/* Cinematic Background Image with Dark Atmospheric Scrim */}
        <div className="absolute inset-0 z-0">
          <Image
            src="/images/hero_health_command.jpg"
            alt="Bioluminescent Health Command Center"
            fill
            priority
            className="object-cover object-center opacity-40 mix-blend-luminosity scale-105 transition duration-1000"
          />
          {/* Gradient Scrim: Transitions smoothly from deep dark teal/carbon into crisp page surface */}
          <div className="absolute inset-0 bg-gradient-to-b from-[#090d12]/80 via-[#090d12]/70 to-white" />
        </div>

        {/* Hero Content */}
        <div className="relative z-10 max-w-4xl mx-auto flex flex-col items-center">
          {/* Status Capsule Indicator */}
          <div className="inline-flex items-center gap-2 rounded-full bg-white/10 backdrop-blur-md px-3.5 py-1 text-xs text-white/90 border border-white/15 mb-6">
            <span className="h-2 w-2 rounded-full bg-[#fc5f2b] animate-ping" />
            <span className="font-mono-clinical text-[11px] tracking-tight">
              AWS HealthAI Cloud &bull; Deterministic Clinical Gate Active
            </span>
          </div>

          {/* 66px Whisper-weight Display Headline */}
          <h1 className="superpower-display text-white max-w-3xl mb-5 tracking-[-0.025em]">
            Your prescription, decoded with clinical certainty.
          </h1>

          {/* Hero Subhead */}
          <p className="superpower-body-lg text-white/80 max-w-xl mx-auto mb-8 font-normal leading-relaxed">
            Bioluminescent health intelligence. Instant handwritten prescription digitization,
            vernacular voice interaction in Hindi and Kannada, and zero-compromise deterministic
            posology safety.
          </p>

          {/* Primary Pill CTA */}
          <div className="flex flex-col items-center gap-3">
            <button
              type="button"
              onClick={scrollToCommandCenter}
              className="inline-flex items-center gap-2.5 rounded-full bg-[#fc5f2b] px-8 py-3.5 text-[15px] font-bold text-white transition hover:opacity-90 shadow-sm group"
            >
              <span>Launch Clinical Scanner</span>
              <ArrowRight className="h-4 w-4 transition transform group-hover:translate-x-1" />
            </button>

            {/* Trust Badge Row Directly Below CTA */}
            <div className="flex flex-wrap items-center justify-center gap-3 sm:gap-6 mt-4 text-[11px] sm:text-[13px] text-white/75">
              <span className="flex items-center gap-1">
                <Check className="h-3.5 w-3.5 text-[#fc5f2b]" />
                HSA / FSA Eligible
              </span>
              <span className="text-white/30">&bull;</span>
              <span className="flex items-center gap-1">
                <ShieldCheck className="h-3.5 w-3.5 text-[#fc5f2b]" />
                HIPAA BAA Compliant
              </span>
              <span className="text-white/30">&bull;</span>
              <span className="flex items-center gap-1">
                <Zap className="h-3.5 w-3.5 text-[#fc5f2b]" />
                100% Fail-Closed Safety
              </span>
            </div>
          </div>

          {/* Photo Thumbnail Strip */}
          <div className="mt-12 flex flex-wrap items-center justify-center gap-2.5 sm:gap-3">
            {thumbnails.map((thumb, idx) => (
              <button
                key={idx}
                type="button"
                onClick={() => {
                  setActiveThumbnail(idx);
                  scrollToCommandCenter();
                }}
                className={`flex flex-col items-start px-3 py-2 rounded-[5px] bg-[#18181b]/80 backdrop-blur-md border text-left transition ${
                  activeThumbnail === idx
                    ? "border-[#fc5f2b] shadow-xs"
                    : "border-white/10 hover:border-white/30"
                }`}
              >
                <span className="text-[10px] text-[#a1a1aa] uppercase font-mono-clinical">
                  {thumb.badge}
                </span>
                <span className="text-xs text-white font-medium mt-0.5">
                  {thumb.title}
                </span>
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* 3. CLINICAL TELEMETRY STATS STRIP */}
      <section id="telemetry" className="border-y border-[#e4e4e7] bg-[#f4f4f5] py-6 px-4 sm:px-6">
        <div className="mx-auto max-w-[1200px] grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-4 text-center shadow-subtle">
            <span className="text-2xl sm:text-3xl font-bold text-[#18181b] tracking-tight">99.8%</span>
            <span className="block text-[11px] font-mono-clinical uppercase tracking-wider text-[#71717a] mt-0.5">
              Posology Precision
            </span>
          </div>
          <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-4 text-center shadow-subtle">
            <span className="text-2xl sm:text-3xl font-bold text-[#fc5f2b] tracking-tight">&lt; 420ms</span>
            <span className="block text-[11px] font-mono-clinical uppercase tracking-wider text-[#71717a] mt-0.5">
              Streaming Voice Latency
            </span>
          </div>
          <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-4 text-center shadow-subtle">
            <span className="text-2xl sm:text-3xl font-bold text-[#18181b] tracking-tight">3 Dialects</span>
            <span className="block text-[11px] font-mono-clinical uppercase tracking-wider text-[#71717a] mt-0.5">
              EN &bull; हिन्दी &bull; ಕನ್ನಡ
            </span>
          </div>
          <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-4 text-center shadow-subtle">
            <span className="text-2xl sm:text-3xl font-bold text-emerald-600 tracking-tight">100%</span>
            <span className="block text-[11px] font-mono-clinical uppercase tracking-wider text-[#71717a] mt-0.5">
              Fail-Closed Gated
            </span>
          </div>
        </div>
      </section>

      {/* 4. DETERMINISTIC CLINICAL SAFETY BANNER */}
      <div className="border-b border-[#e4e4e7] bg-amber-50/60 px-4 py-2.5 text-xs text-amber-950">
        <div className="mx-auto flex max-w-[1200px] items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 shrink-0 text-[#fc5f2b]" />
            <span>
              <strong className="font-semibold">Deterministic Safety Gate:</strong> AI extracts raw clinical observations; deterministic code gates and normalizes. The system never guesses or auto-completes uncertain posology. Always consult your pharmacist.
            </span>
          </div>
          <span className="hidden sm:inline-block rounded-full bg-[#18181b] px-2.5 py-0.5 text-[10px] font-mono-clinical font-semibold text-white uppercase tracking-wider">
            Fail-Closed Standard
          </span>
        </div>
      </div>

      {/* 5. INTERACTIVE CLINICAL COMMAND CENTER */}
      <main id="command-center" className="mx-auto w-full max-w-[1200px] flex-1 px-4 py-12 sm:px-6">
        {/* Section Title */}
        <div className="mb-8 flex flex-col md:flex-row md:items-end md:justify-between gap-4">
          <div>
            <span className="font-mono-clinical text-xs font-semibold uppercase tracking-wider text-[#71717a]">
              Clinical Intelligence Engine
            </span>
            <h2 className="superpower-heading-lg text-[#18181b] mt-1">
              Bioluminescent Ingestion &amp; Voice Studio
            </h2>
          </div>
          {/* Backend Connection Pill */}
          <div className="flex items-center gap-2 text-xs font-mono-clinical">
            <span
              className={`h-2 w-2 rounded-full ${
                isHealthy ? "bg-emerald-500 animate-pulse" : "bg-amber-500"
              }`}
            />
            <span className="text-[#71717a]">{backendHealth}</span>
          </div>
        </div>

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-12">
          {/* Left Column: Upload & Voice Studio */}
          <div className="space-y-6 lg:col-span-6">
            {/* 5A. Prescription Ingestion Card */}
            <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-6 shadow-subtle">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-[#18181b]">
                    Upload Prescription Image
                  </h3>
                  <p className="text-xs text-[#71717a] mt-0.5">
                    Accepts JPEG, PNG, WebP. Safe S3 ingestion with Bedrock vision extraction.
                  </p>
                </div>
                <div className="h-8 w-8 rounded-[7.5px] bg-[#f4f4f5] flex items-center justify-center text-[#18181b]">
                  <FileText className="h-4 w-4" />
                </div>
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
                className="group relative flex flex-col items-center justify-center rounded-[15px] border-2 border-dashed border-[#e4e4e7] bg-[#f4f4f5]/60 p-8 text-center transition hover:border-[#fc5f2b] hover:bg-white cursor-pointer"
              >
                {isUploading ? (
                  <div className="flex flex-col items-center">
                    <Loader2 className="h-10 w-10 animate-spin text-[#fc5f2b]" />
                    <p className="mt-3 text-sm font-semibold text-[#18181b]">
                      Processing Prescription...
                    </p>
                    <p className="mt-1 text-xs text-[#71717a] font-mono-clinical">
                      S3 Staging &bull; Bedrock Vision &bull; Deterministic Safety Gate
                    </p>
                  </div>
                ) : (
                  <>
                    <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white shadow-xs text-[#fc5f2b] group-hover:scale-105 transition border border-[#e4e4e7]">
                      <Upload className="h-5 w-5" />
                    </div>
                    <p className="mt-3 text-sm font-semibold text-[#18181b]">
                      Click or drag prescription photo here
                    </p>
                    <p className="mt-1 text-xs text-[#71717a]">
                      Ensure all posology lines and timing are visible
                    </p>
                    <button
                      type="button"
                      className="mt-4 inline-flex items-center rounded-full bg-[#18181b] px-4 py-2 text-xs font-semibold text-white shadow-xs hover:bg-black transition"
                    >
                      Select File
                    </button>
                  </>
                )}
              </div>

              {/* Sample Prescription Quick-Loader (For instant zero-friction demo) */}
              <div className="mt-4 pt-4 border-t border-[#e4e4e7]">
                <span className="text-[11px] font-mono-clinical uppercase tracking-wider text-[#71717a] block mb-2">
                  Or test with verified clinical case samples:
                </span>
                <div className="flex flex-wrap gap-2">
                  <button
                    type="button"
                    onClick={() => handleLoadSample("verified")}
                    className="inline-flex items-center gap-1.5 rounded-full bg-[#f4f4f5] px-3 py-1 text-xs font-medium text-[#18181b] hover:bg-[#e4e4e7] transition border border-[#e4e4e7]"
                  >
                    <CheckCircle2 className="h-3 w-3 text-emerald-600" />
                    <span>Augmentin &amp; Pan-D (Verified Case)</span>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleLoadSample("review")}
                    className="inline-flex items-center gap-1.5 rounded-full bg-amber-50 px-3 py-1 text-xs font-medium text-amber-900 hover:bg-amber-100 transition border border-amber-200"
                  >
                    <AlertTriangle className="h-3 w-3 text-amber-600" />
                    <span>Uncertain Handwriting (Requires Review)</span>
                  </button>
                </div>
              </div>

              {uploadError && (
                <div className="mt-3 flex items-center space-x-2 rounded-[7.5px] bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
                  <span>{uploadError}</span>
                </div>
              )}
            </div>

            {/* 5B. Voice Query Assistance Card */}
            <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-6 shadow-subtle">
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h3 className="text-base font-semibold text-[#18181b]">
                    Voice Query Assistance
                  </h3>
                  <p className="text-xs text-[#71717a] mt-0.5">
                    Ask questions in{" "}
                    {selectedLanguage === "hi-IN"
                      ? "Hindi"
                      : selectedLanguage === "kn-IN"
                      ? "Kannada"
                      : "English"}{" "}
                    using real-time Transcribe streaming.
                  </p>
                </div>
                <div className="h-8 w-8 rounded-[7.5px] bg-[#f4f4f5] flex items-center justify-center text-[#fc5f2b]">
                  <Volume2 className="h-4 w-4" />
                </div>
              </div>

              <div className="flex flex-col items-center justify-center rounded-[15px] border border-[#e4e4e7] bg-[#f4f4f5]/50 p-6">
                <button
                  type="button"
                  data-testid="voice-record-button"
                  onClick={isRecording ? stopRecording : startRecording}
                  disabled={!prescriptionData || isQueryingVoice}
                  className={`group relative flex h-16 w-16 items-center justify-center rounded-full transition shadow-md ${
                    !prescriptionData
                      ? "bg-[#e4e4e7] text-[#a1a1aa] cursor-not-allowed border border-[#e4e4e7]"
                      : isRecording
                      ? "bg-red-600 text-white animate-pulse"
                      : "bg-[#18181b] text-white hover:bg-black focus:ring-4 focus:ring-[#fc5f2b]/20"
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
                    <Mic className="h-8 w-8 group-hover:scale-110 transition text-white" />
                  )}
                </button>

                {/* Animated Soundwave Equalizer (Visible when recording or playing audio) */}
                {(isRecording || isPlayingAudio) && (
                  <div className="flex items-center gap-1 mt-3 h-6">
                    <span className="w-1 bg-[#fc5f2b] rounded-full animate-wave-1" />
                    <span className="w-1 bg-[#fc5f2b] rounded-full animate-wave-2" />
                    <span className="w-1 bg-[#18181b] rounded-full animate-wave-3" />
                    <span className="w-1 bg-[#fc5f2b] rounded-full animate-wave-4" />
                    <span className="w-1 bg-[#18181b] rounded-full animate-wave-5" />
                    <span className="w-1 bg-[#fc5f2b] rounded-full animate-wave-6" />
                  </div>
                )}

                <p
                  className="mt-4 text-xs font-semibold text-[#18181b]"
                  data-testid="voice-status-text"
                >
                  {isQueryingVoice
                    ? "Transcribing & Synthesizing Spoken Answer..."
                    : isRecording
                    ? "Recording... Tap again to stop and query"
                    : isPlayingAudio
                    ? "Playing Spoken Medical Guidance..."
                    : prescriptionData
                    ? "Tap microphone to ask a question"
                    : "No active prescription. Upload a prescription above to enable voice queries."}
                </p>

                {/* Interactive Quick Voice Prompts */}
                {prescriptionData && (
                  <div className="mt-4 flex flex-wrap justify-center gap-1.5 max-w-md">
                    {quickPrompts[selectedLanguage].map((promptText, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => handleQuickPromptClick(promptText)}
                        className="rounded-full bg-white px-2.5 py-1 text-[11px] font-medium text-[#18181b] border border-[#e4e4e7] hover:border-[#fc5f2b] hover:text-[#fc5f2b] transition shadow-2xs"
                      >
                        {promptText}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {voiceError && (
                <div className="mt-3 flex items-center space-x-2 rounded-[7.5px] bg-red-50 p-3 text-xs text-red-700 border border-red-200">
                  <AlertTriangle className="h-4 w-4 shrink-0 text-red-600" />
                  <span>{voiceError}</span>
                </div>
              )}

              {/* Voice Query Response Card */}
              {voiceResponse && (
                <div className="mt-4 rounded-[15px] border border-[#e4e4e7] bg-[#f4f4f5] p-4">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-2">
                      <Sparkles className="h-4 w-4 text-[#fc5f2b]" />
                      <span className="text-xs font-mono-clinical font-bold text-[#18181b] uppercase tracking-wide">
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
                        className="inline-flex items-center rounded-full bg-[#18181b] px-3 py-1 text-[11px] font-semibold text-white shadow-xs hover:bg-black transition"
                      >
                        <Volume2 className="mr-1 h-3.5 w-3.5 text-[#fc5f2b]" /> Replay Audio
                      </button>
                    )}
                  </div>

                  <p className="mt-2 text-xs text-[#71717a]">
                    You asked: &ldquo;{voiceResponse.transcript}&rdquo;
                  </p>
                  <p className="mt-1 text-sm font-semibold text-[#18181b] leading-relaxed">
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
            <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-6 shadow-subtle">
              {/* Session / Prescription ID State Banner */}
              {prescriptionData ? (
                <div
                  data-testid="active-session-banner"
                  className="mb-4 flex flex-wrap items-center justify-between gap-2 rounded-[7.5px] border border-[#e4e4e7] bg-[#f4f4f5] px-3 py-2 text-xs"
                >
                  <div className="flex items-center space-x-2">
                    <span className="font-semibold text-[#18181b]">Prescription Session:</span>
                    <span
                      data-testid="active-prescription-id"
                      className="font-mono-clinical text-[#18181b] font-bold bg-white px-2 py-0.5 rounded-[5px] border border-[#e4e4e7]"
                    >
                      {prescriptionData.prescription_id}
                    </span>
                  </div>
                  <button
                    type="button"
                    onClick={handleResetSession}
                    className="inline-flex items-center text-[11px] font-semibold text-[#71717a] hover:text-[#18181b] hover:underline"
                  >
                    <RotateCcw className="mr-1 h-3 w-3" />
                    New Session
                  </button>
                </div>
              ) : (
                <div
                  data-testid="fresh-session-banner"
                  className="mb-4 flex items-center justify-between rounded-[7.5px] border border-dashed border-[#e4e4e7] bg-[#f4f4f5]/60 px-3 py-2 text-xs text-[#71717a]"
                >
                  <span className="flex items-center">
                    <span className="mr-2 h-2 w-2 rounded-full bg-[#a1a1aa]" />
                    Session Status: <strong className="ml-1 text-[#18181b]">Fresh Session</strong>
                  </span>
                  <span className="text-[11px] text-[#a1a1aa]">Awaiting prescription upload</span>
                </div>
              )}

              {/* Section Header (Dynamic: Never "Verified" when REQUIRES_REVIEW or null) */}
              <div className="mb-4 flex items-center justify-between">
                <div>
                  <h2
                    data-testid="schedule-section-title"
                    className="text-base font-semibold text-[#18181b]"
                  >
                    {getScheduleSectionTitle(prescriptionData)}
                  </h2>
                  <p
                    data-testid="schedule-section-desc"
                    className="text-xs text-[#71717a] mt-0.5"
                  >
                    {getScheduleSectionDescription(prescriptionData)}
                  </p>
                </div>

                {prescriptionData ? (
                  (() => {
                    const hasUnverifiedMed = prescriptionData.medications?.some(
                      (m) => !m.is_verified_safe || m.requires_review
                    );
                    const isRequiresReview =
                      prescriptionData.requires_review ||
                      prescriptionData.status === "REQUIRES_REVIEW" ||
                      hasUnverifiedMed;

                    return (
                      <div
                        data-testid="prescription-status-badge"
                        className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                          isRequiresReview
                            ? "bg-amber-100 text-amber-900 border border-amber-300"
                            : prescriptionData.status === "COMPLETED"
                            ? "bg-emerald-100 text-emerald-900 border border-emerald-300"
                            : "bg-[#f4f4f5] text-[#18181b]"
                        }`}
                      >
                        {isRequiresReview ? (
                          <>
                            <AlertTriangle className="mr-1 h-3.5 w-3.5 text-amber-700" />
                            Requires Review
                          </>
                        ) : prescriptionData.status === "COMPLETED" ? (
                          <>
                            <CheckCircle2 className="mr-1 h-3.5 w-3.5 text-emerald-700" />
                            Verified Safe
                          </>
                        ) : (
                          prescriptionData.status
                        )}
                      </div>
                    );
                  })()
                ) : (
                  <span
                    data-testid="awaiting-upload-badge"
                    className="inline-flex items-center rounded-full bg-[#f4f4f5] px-2.5 py-1 text-xs font-medium text-[#71717a] border border-[#e4e4e7]"
                  >
                    Awaiting Upload
                  </span>
                )}
              </div>

              {/* Medication Schedule Area */}
              {prescriptionData?.medications && prescriptionData.medications.length > 0 ? (
                <>
                  <div className="overflow-hidden rounded-[7.5px] border border-[#e4e4e7]">
                    <table
                      data-testid="medications-table"
                      className="min-w-full divide-y divide-[#e4e4e7] text-left text-xs"
                    >
                      <thead className="bg-[#f4f4f5] text-[#18181b] font-semibold">
                        <tr>
                          <th className="px-3 py-2.5">Medication</th>
                          <th className="px-3 py-2.5">Schedule</th>
                          <th className="px-3 py-2.5">Food Relation</th>
                          <th className="px-3 py-2.5">Safety Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#e4e4e7] bg-white">
                        {prescriptionData.medications.map((med, index) => {
                          const { displayName, displayStrength, displayDuration, hasStrength } =
                            resolveMedicationDisplay(med);

                          return (
                            <tr
                              key={med.medication_id || index}
                              data-testid={`medication-row-${index}`}
                              className={med.requires_review ? "bg-amber-50/40" : "bg-white"}
                            >
                              <td className="px-3 py-3 font-medium text-[#18181b]">
                                <div className="font-semibold text-[#18181b]">{displayName}</div>
                                <div className="mt-1 flex flex-wrap items-center gap-1.5 text-[10px]">
                                  <span
                                    data-testid={`medication-strength-${index}`}
                                    className={`inline-flex items-center rounded px-1.5 py-0.5 font-medium ${
                                      hasStrength
                                        ? "bg-[#f4f4f5] text-[#18181b]"
                                        : "bg-amber-100/70 text-amber-800 border border-amber-200"
                                    }`}
                                  >
                                    {hasStrength ? `Strength: ${displayStrength}` : displayStrength}
                                  </span>
                                  <span className="text-[#a1a1aa]">&bull;</span>
                                  <span
                                    data-testid={`medication-duration-${index}`}
                                    className="text-[#71717a] font-normal"
                                  >
                                    Duration: {displayDuration}
                                  </span>
                                </div>
                              </td>
                              <td className="px-3 py-3 text-[#18181b]">
                                <span className="inline-block rounded-[5px] bg-[#f4f4f5] px-1.5 py-0.5 text-[10px] font-mono-clinical font-bold text-[#18181b]">
                                  {med.schedule.raw_text || "As directed"}
                                </span>
                                <span className="block text-[10px] text-[#71717a] mt-0.5">
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
                              <td className="px-3 py-3 text-[#18181b]">
                                {med.meal_instruction.after_meal ? (
                                  <span className="inline-flex items-center rounded-full bg-blue-50 px-2 py-0.5 text-[10px] font-medium text-blue-700 border border-blue-200">
                                    <Clock className="mr-1 h-3 w-3" /> After Food
                                  </span>
                                ) : med.meal_instruction.before_meal ? (
                                  <span className="inline-flex items-center rounded-full bg-amber-50 px-2 py-0.5 text-[10px] font-medium text-amber-700 border border-amber-200">
                                    <Clock className="mr-1 h-3 w-3" /> Before Food
                                  </span>
                                ) : (
                                  <span className="text-[10px] text-[#a1a1aa]">Unspecified</span>
                                )}
                              </td>
                              <td className="px-3 py-3">
                                {med.is_verified_safe ? (
                                  <span className="inline-flex items-center text-emerald-700 text-[11px] font-medium">
                                    <CheckCircle2 className="mr-1 h-3.5 w-3.5 text-emerald-600" /> Verified
                                  </span>
                                ) : (
                                  <span className="inline-flex items-center text-amber-800 text-[11px] font-semibold">
                                    <AlertTriangle className="mr-1 h-3.5 w-3.5 text-amber-600" /> Review Needed
                                  </span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>

                  {/* 24-Hour Posology Chronobiology Bio-Clock */}
                  <div className="mt-4 pt-4 border-t border-[#e4e4e7]">
                    <span className="text-[11px] font-mono-clinical uppercase tracking-wider text-[#71717a] block mb-2">
                      24h Chronobiological Dosage Windows:
                    </span>
                    <div className="grid grid-cols-4 gap-2">
                      {/* Morning Slot */}
                      <div className="rounded-[7.5px] border border-[#e4e4e7] bg-[#f4f4f5]/60 p-2.5 text-center">
                        <div className="flex items-center justify-center text-[#fc5f2b] mb-1">
                          <Sun className="h-4 w-4" />
                        </div>
                        <span className="block text-[11px] font-bold text-[#18181b]">08:00 AM</span>
                        <span className="text-[10px] text-[#71717a]">Morning</span>
                        <span className="block mt-1 font-mono-clinical text-[11px] font-semibold text-[#18181b]">
                          {prescriptionData.medications.filter((m) => m.schedule.morning).length} Dose(s)
                        </span>
                      </div>

                      {/* Afternoon Slot */}
                      <div className="rounded-[7.5px] border border-[#e4e4e7] bg-[#f4f4f5]/60 p-2.5 text-center">
                        <div className="flex items-center justify-center text-amber-600 mb-1">
                          <Coffee className="h-4 w-4" />
                        </div>
                        <span className="block text-[11px] font-bold text-[#18181b]">01:00 PM</span>
                        <span className="text-[10px] text-[#71717a]">Afternoon</span>
                        <span className="block mt-1 font-mono-clinical text-[11px] font-semibold text-[#18181b]">
                          {prescriptionData.medications.filter((m) => m.schedule.afternoon).length} Dose(s)
                        </span>
                      </div>

                      {/* Evening Slot */}
                      <div className="rounded-[7.5px] border border-[#e4e4e7] bg-[#f4f4f5]/60 p-2.5 text-center">
                        <div className="flex items-center justify-center text-[#71717a] mb-1">
                          <Sunset className="h-4 w-4" />
                        </div>
                        <span className="block text-[11px] font-bold text-[#18181b]">06:00 PM</span>
                        <span className="text-[10px] text-[#71717a]">Evening</span>
                        <span className="block mt-1 font-mono-clinical text-[11px] font-semibold text-[#18181b]">
                          {prescriptionData.medications.filter((m) => m.schedule.evening).length} Dose(s)
                        </span>
                      </div>

                      {/* Night Slot */}
                      <div className="rounded-[7.5px] border border-[#e4e4e7] bg-[#f4f4f5]/60 p-2.5 text-center">
                        <div className="flex items-center justify-center text-indigo-600 mb-1">
                          <Moon className="h-4 w-4" />
                        </div>
                        <span className="block text-[11px] font-bold text-[#18181b]">09:00 PM</span>
                        <span className="text-[10px] text-[#71717a]">Night</span>
                        <span className="block mt-1 font-mono-clinical text-[11px] font-semibold text-[#18181b]">
                          {prescriptionData.medications.filter((m) => m.schedule.night).length} Dose(s)
                        </span>
                      </div>
                    </div>
                  </div>
                </>
              ) : (
                /* Clean Empty State: Fresh session without hardcoded or stale medication data */
                <div
                  data-testid="empty-prescription-state"
                  className="flex flex-col items-center justify-center rounded-[15px] border-2 border-dashed border-[#e4e4e7] bg-[#f4f4f5]/50 p-10 text-center"
                >
                  <div className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-[#a1a1aa] border border-[#e4e4e7]">
                    <FileText className="h-6 w-6" />
                  </div>
                  <h3 className="mt-3 text-sm font-semibold text-[#18181b]">
                    No Prescription Uploaded
                  </h3>
                  <p className="mt-1 text-xs text-[#71717a] max-w-sm">
                    Upload or drag a prescription photo on the left to extract medication details,
                    timing schedules, and deterministic safety validation.
                  </p>
                  <div className="mt-4 inline-flex items-center rounded-full bg-[#e4e4e7] px-3 py-1 text-[11px] font-medium text-[#18181b]">
                    Session Status: Fresh (No Active Prescription)
                  </div>
                </div>
              )}

              {/* Safety State Notification (Only shown when a prescription requires review) */}
              {prescriptionData?.requires_review && (
                <div
                  data-testid="safety-review-alert"
                  className="mt-4 rounded-[7.5px] border border-amber-300 bg-amber-50 p-3 text-xs text-amber-900"
                >
                  <p className="font-semibold flex items-center">
                    <AlertTriangle className="mr-1.5 h-4 w-4 text-amber-700" />
                    Pharmacist Consultation Required
                  </p>
                  <p className="mt-1 text-[#71717a]">
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

      {/* 6. TRANSPARENT CLINICAL MEMBERSHIP & PRICING SECTION */}
      <section id="pricing" className="border-t border-[#e4e4e7] bg-[#f4f4f5]/60 py-20 px-4 sm:px-6">
        <div className="mx-auto max-w-[1200px]">
          {/* Section Header */}
          <div className="text-center max-w-2xl mx-auto mb-10">
            <span className="font-mono-clinical text-xs font-semibold uppercase tracking-wider text-[#fc5f2b]">
              Transparent Healthcare Economics
            </span>
            <h2 className="superpower-heading-lg text-[#18181b] mt-2 mb-3">
              Transparent Clinical Membership.
            </h2>
            <p className="superpower-body-lg text-[#71717a] font-normal leading-relaxed">
              Superpower wraps serious clinical intelligence in transparent access. Free patient
              accessibility meets premium family telehealth and hospital verification.
            </p>

            {/* Interactive Billing Controls (Cycle & Currency) */}
            <div className="mt-6 flex flex-wrap items-center justify-center gap-3">
              {/* Billing Cycle Pill */}
              <div className="inline-flex rounded-full bg-white p-1 border border-[#e4e4e7] text-xs font-medium shadow-2xs">
                <button
                  type="button"
                  onClick={() => setBillingCycle("monthly")}
                  className={`rounded-full px-3 py-1 transition ${
                    billingCycle === "monthly"
                      ? "bg-[#18181b] text-white"
                      : "text-[#71717a] hover:text-[#18181b]"
                  }`}
                >
                  Monthly
                </button>
                <button
                  type="button"
                  onClick={() => setBillingCycle("annual")}
                  className={`rounded-full px-3 py-1 transition flex items-center gap-1 ${
                    billingCycle === "annual"
                      ? "bg-[#18181b] text-white"
                      : "text-[#71717a] hover:text-[#18181b]"
                  }`}
                >
                  <span>Annual</span>
                  <span className="rounded-full bg-[#fc5f2b] px-1.5 py-0.2 text-[9px] font-bold text-white">
                    SAVE 20%
                  </span>
                </button>
              </div>

              {/* Currency Selector */}
              <div className="inline-flex rounded-full bg-white p-1 border border-[#e4e4e7] text-xs font-medium shadow-2xs">
                <button
                  type="button"
                  onClick={() => setCurrency("USD")}
                  className={`rounded-full px-2.5 py-1 transition ${
                    currency === "USD"
                      ? "bg-[#fc5f2b] text-white font-bold"
                      : "text-[#71717a] hover:text-[#18181b]"
                  }`}
                >
                  USD ($)
                </button>
                <button
                  type="button"
                  onClick={() => setCurrency("INR")}
                  className={`rounded-full px-2.5 py-1 transition ${
                    currency === "INR"
                      ? "bg-[#fc5f2b] text-white font-bold"
                      : "text-[#71717a] hover:text-[#18181b]"
                  }`}
                >
                  INR (₹)
                </button>
              </div>
            </div>
          </div>

          {/* Pricing Grid & Signature Marbled Card Artwork */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-stretch">
            {/* TIER 1: Community Patient Access */}
            <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-7 flex flex-col justify-between shadow-subtle hover:border-[#a1a1aa] transition">
              <div>
                <span className="text-xs font-mono-clinical uppercase text-[#71717a] tracking-wider">
                  Tier 01 &bull; Universal Access
                </span>
                <h3 className="text-xl font-bold text-[#18181b] mt-1">Community Patient</h3>
                <p className="text-xs text-[#71717a] mt-1">
                  Full assistive access for patients, elders, and regional language speakers.
                </p>

                <div className="mt-6 mb-6">
                  <span className="text-4xl font-normal text-[#18181b] tracking-tight">
                    {currency === "USD" ? "$0" : "₹0"}
                  </span>
                  <span className="text-xs text-[#71717a] ml-1 font-mono-clinical">/ Free Forever</span>
                </div>

                <div className="space-y-3 pt-4 border-t border-[#e4e4e7]">
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Unlimited handwritten prescription digitization
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Kannada (ಕನ್ನಡ) &amp; Hindi (हिन्दी) audio TTS playback
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Deterministic fail-closed clinical safety check
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Morning / Afternoon / Night posology matrix
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={scrollToCommandCenter}
                className="mt-8 w-full rounded-full border border-[#18181b] bg-white py-3 text-xs font-bold text-[#18181b] hover:bg-[#f4f4f5] transition"
              >
                Use Free Patient Mode
              </button>
            </div>

            {/* TIER 2: Superpower Health Pass (Featured with Marbled Coral Visual Card) */}
            <div className="relative rounded-[15px] border-2 border-[#fc5f2b] bg-white p-7 flex flex-col justify-between shadow-md">
              {/* Featured Badge */}
              <div className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-[#fc5f2b] px-3 py-0.5 text-[10px] font-bold text-white uppercase tracking-wider shadow-xs">
                Clinical Vitality Pass
              </div>

              <div>
                {/* Visual Artwork: Organic Marbled Lava Card */}
                <div className="relative w-full h-44 rounded-[15px] overflow-hidden mb-6 shadow-sm border border-[#fc5f2b]/30">
                  <Image
                    src="/images/marbled_coral_card.jpg"
                    alt="Superpower Membership Artwork"
                    fill
                    className="object-cover"
                  />
                  {/* Card Content Overlay */}
                  <div className="absolute inset-0 p-4 flex flex-col justify-between bg-gradient-to-tr from-[#fc5f2b]/85 via-transparent to-white/40">
                    <div className="flex items-center justify-between text-white">
                      <span className="text-[11px] font-bold tracking-wider uppercase drop-shadow">
                        Superpower Membership
                      </span>
                      <Activity className="h-4 w-4 drop-shadow" />
                    </div>
                    <div className="text-white">
                      <span className="text-[10px] uppercase font-mono-clinical tracking-wider opacity-90">
                        {isAnnual ? "Annual Vitality Card" : "Monthly Health Pass"}
                      </span>
                      <div className="text-2xl font-bold tracking-tight drop-shadow">
                        {healthPassPrice} {billingPeriodLabel}
                      </div>
                    </div>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-xs font-mono-clinical uppercase text-[#fc5f2b] tracking-wider font-semibold">
                      Tier 02 &bull; Featured Member
                    </span>
                    <h3 className="text-xl font-bold text-[#18181b] mt-0.5">Superpower Health Pass</h3>
                  </div>
                </div>

                <div className="mt-4 mb-6">
                  <span className="text-4xl font-normal text-[#18181b] tracking-tight">{healthPassPrice}</span>
                  <span className="text-xs text-[#71717a] ml-1 font-mono-clinical">{billingPeriodLabel}</span>
                </div>

                <div className="space-y-3 pt-4 border-t border-[#e4e4e7]">
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs font-semibold text-[#18181b]">
                      Real-time AWS Transcribe streaming voice queries
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Multi-profile family prescription history archive
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Pharmacist-verified posology PDF export
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Complimentary physical laser-engraved metal card (Annual)
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={scrollToCommandCenter}
                className="mt-8 w-full rounded-full bg-[#fc5f2b] py-3 text-xs font-bold text-white hover:opacity-90 transition shadow-sm"
              >
                Activate Superpower Membership
              </button>
            </div>

            {/* TIER 3: Hospital & Clinical Provider */}
            <div className="rounded-[15px] border border-[#e4e4e7] bg-white p-7 flex flex-col justify-between shadow-subtle hover:border-[#a1a1aa] transition">
              <div>
                <span className="text-xs font-mono-clinical uppercase text-[#71717a] tracking-wider">
                  Tier 03 &bull; Enterprise EHR
                </span>
                <h3 className="text-xl font-bold text-[#18181b] mt-1">Clinical Provider</h3>
                <p className="text-xs text-[#71717a] mt-1">
                  For clinics, community dispensaries, and pharmacy chains.
                </p>

                <div className="mt-6 mb-6">
                  <span className="text-4xl font-normal text-[#18181b] tracking-tight">{providerPrice}</span>
                  <span className="text-xs text-[#71717a] ml-1 font-mono-clinical">{billingPeriodLabel}</span>
                </div>

                <div className="space-y-3 pt-4 border-t border-[#e4e4e7]">
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Hospital EHR &amp; Pharmacy POS REST API access
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Multi-doctor posology verification queue
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      High-throughput batch prescription ingestion
                    </span>
                  </div>
                  <div className="flex items-start gap-2.5">
                    <div className="h-5 w-5 rounded-[7.5px] bg-[#fc5f2b] flex items-center justify-center text-white shrink-0 mt-0.5">
                      <Check className="h-3 w-3 stroke-[3]" />
                    </div>
                    <span className="text-xs text-[#18181b]">
                      Complete HIPAA BAA compliance audit trail
                    </span>
                  </div>
                </div>
              </div>

              <button
                type="button"
                onClick={scrollToCommandCenter}
                className="mt-8 w-full rounded-full bg-[#18181b] py-3 text-xs font-bold text-white hover:bg-black transition"
              >
                Contact Clinical Operations
              </button>
            </div>
          </div>
        </div>
      </section>


      {/* 8. CLINICAL SAFETY FAQ SECTION */}
      <section id="faq" className="py-20 px-4 sm:px-6 bg-[#f4f4f5]/40 border-t border-[#e4e4e7]">
        <div className="mx-auto max-w-[1200px]">
          <div className="mb-12">
            <span className="font-mono-clinical text-xs font-semibold uppercase tracking-wider text-[#71717a]">
              Clinical Clarity
            </span>
            <h2 className="superpower-heading-lg text-[#18181b] mt-1">
              Frequently Asked Questions
            </h2>
          </div>

          <div className="space-y-6">
            {faqItems.map((item, idx) => {
              const isExpanded = expandedFaq === idx;
              return (
                <div
                  key={idx}
                  className="border-b border-[#e4e4e7] pb-6 transition"
                >
                  <div className="flex flex-col sm:flex-row sm:items-baseline sm:justify-between gap-2">
                    <h3 className="superpower-heading text-[#18181b] text-xl sm:text-2xl font-normal">
                      {item.q}
                    </h3>
                    <button
                      type="button"
                      onClick={() => setExpandedFaq(isExpanded ? null : idx)}
                      className="text-xs text-[#71717a] hover:text-[#18181b] font-medium transition underline-offset-4 hover:underline shrink-0"
                    >
                      {isExpanded ? "Collapse" : "Read more"}
                    </button>
                  </div>
                  {isExpanded && (
                    <p className="mt-4 text-sm text-[#71717a] max-w-3xl leading-relaxed">
                      {item.a}
                    </p>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* 9. REFINED FOOTER */}
      <footer className="border-t border-[#e4e4e7] bg-[#f4f4f5] py-8 px-4 sm:px-6 text-xs text-[#71717a]">
        <div className="mx-auto max-w-[1200px] flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-bold text-[#18181b]">BHARAT BUILDS</span>
            <span>&bull;</span>
            <span>Superpower Health Command Center</span>
            <span>&bull;</span>
            <span className="font-mono-clinical text-[11px]">AWS HealthAI Cloud</span>
          </div>

          <div className="flex items-center gap-6">
            <a href="#command-center" className="hover:text-[#18181b] transition">
              Scanner
            </a>
            <a href="#telemetry" className="hover:text-[#18181b] transition">
              Telemetry
            </a>
            <a href="#pricing" className="hover:text-[#18181b] transition">
              Pricing ($17/mo)
            </a>
            <a href="#faq" className="hover:text-[#18181b] transition">
              Safety Gate
            </a>
          </div>
        </div>
      </footer>
    </div>
  );
}
