/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{vue,js,ts,jsx,tsx}"],
  theme: {
    extend: {
      fontFamily: {
        display: ["Cormorant Garamond", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      colors: {
        // BlueMoxon brand colors (keep for backwards compatibility)
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
        // Victorian design system
        victorian: {
          // Primary - Deep Hunter Green
          hunter: {
            900: "#0f2318",
            800: "#1a3a2f",
            700: "#254a3d",
            600: "#2f5a4b",
            500: "#3a6b5c",
          },
          // Accent - Antiquarian Gold
          gold: {
            light: "#d4af37",
            DEFAULT: "#c9a227",
            dark: "#a67c00",
            muted: "#b8956e",
          },
          // Accent - Rich Burgundy
          burgundy: {
            light: "#8b3a42",
            DEFAULT: "#722f37",
            dark: "#5c262e",
          },
          // Backgrounds - Warm Paper Tones
          paper: {
            white: "#fdfcfa",
            cream: "#f8f5f0",
            aged: "#f0ebe3",
            antique: "#e8e1d5",
          },
          // Text
          ink: {
            black: "#1a1a18",
            dark: "#2d2d2a",
            muted: "#5c5c58",
          },
          // Legacy colors (keep for compatibility)
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
