import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MedTwin AI — Medication-Aware Healthcare Digital Twin | Happiest Health 2026",
  description:
    "A Safety-First Digital Twin combining EHR, verified medication regimens and real-time physiological signals for proactive 2-hour adverse health event forecasting. Happiest Health 2026 Proof-of-Concept.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-white text-[#18181b] antialiased selection:bg-[#fc5f2b]/20 selection:text-[#18181b]">
        {children}
      </body>
    </html>
  );
}
