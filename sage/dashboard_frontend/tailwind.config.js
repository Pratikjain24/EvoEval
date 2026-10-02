/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        background: "#090d16",
        surface: "#111827",
        "surface-card": "#161f33",
        "surface-border": "#1e293b",
        primary: {
          DEFAULT: "#6366f1",
          hover: "#4f46e5",
        },
        group: {
          G1: "#94a3b8", // Slate
          G2: "#3b82f6", // Blue
          G3: "#10b981", // Emerald
          G4: "#f59e0b", // Amber
          G5: "#8b5cf6", // Purple
          G6: "#ec4899", // Rose
        },
      },
    },
  },
  plugins: [],
};
