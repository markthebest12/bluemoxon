/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        // BlueMoxon brand colors
        moxon: {
          50: "#eff6ff",
          100: "#dbeafe",
          200: "#bfdbfe",
          300: "#93c5fd",
          400: "#60a5fa",
          500: "#3b82f6",
          600: "#2563eb",
          700: "#1d4ed8",
          800: "#1e40af",
          900: "#1e3a8a",
        },
        victorian: {
          gold: "#c9a227",
          burgundy: "#722f37",
          forest: "#228b22",
          cream: "#fffdd0",
        },
        // Dark navy theme colors (matching landing site)
        navy: {
          900: "#0a0f1a",
          800: "#111827",
          700: "#1a2332",
          600: "#1e293b",
          500: "#334155",
        },
      },
    },
  },
  plugins: [],
};
