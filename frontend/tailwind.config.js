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
        // BlueMoxon brand colors - updated to Victorian hunter green palette
        moxon: {
          50: "#f0f5f3",
          100: "#dae8e2",
          200: "#b8d4c9",
          300: "#8dbaa8",
          400: "#5e9a82",
          500: "#3a6b5c",
          600: "#2f5a4b", // Primary brand green
          700: "#254a3d",
          800: "#1a3a2f",
          900: "#0f2318",
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
