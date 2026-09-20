import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        coral: {
          DEFAULT: "#fc5f2b",
          sunrise: "#fc5f2b",
          glow: "#ff8b64",
        },
        carbon: {
          DEFAULT: "#18181b",
          black: "#18181b",
        },
        zinc: {
          gray: "#71717a",
          ash: "#a1a1aa",
          mist: "#e4e4e7",
          fog: "#f4f4f5",
        },
        paper: "#ffffff",
      },
      borderRadius: {
        cards: "15px",
        icons: "7.5px",
        pills: "9999px",
        smallcards: "5px",
      },
      boxShadow: {
        subtle: "rgba(0, 0, 0, 0.05) 0px 2px 2px 0px",
      },
      fontFamily: {
        sans: ["var(--font-nb-international-pro)", "sans-serif"],
        mono: ["var(--font-nb-international-mono-pro)", "monospace"],
      },
    },
  },
  plugins: [],
};

export default config;
