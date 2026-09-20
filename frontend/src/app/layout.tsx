import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Superpower — Bioluminescent Health Command Center | Bharat Builds",
  description:
    "Multimodal clinical prescription intelligence. Instant handwritten digitization, real-time vernacular voice AI in Hindi and Kannada, with deterministic clinical fail-closed safety.",
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
