import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "../../packages/ui/src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-sans)"],
      },
      colors: {
        ink: "#07111f",
        cyan: "#67e8f9",
        emerald: "#34d399",
      },
      backgroundImage: {
        "grid-fade":
          "radial-gradient(circle at top, rgba(103, 232, 249, 0.12), transparent 40%), linear-gradient(rgba(148, 163, 184, 0.08) 1px, transparent 1px), linear-gradient(90deg, rgba(148, 163, 184, 0.08) 1px, transparent 1px)",
      },
      backgroundSize: {
        "grid-fade": "auto, 44px 44px, 44px 44px",
      },
    },
  },
  plugins: [],
};

export default config;
