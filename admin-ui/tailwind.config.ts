import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./src/**/*.{ts,tsx}"],
  // dark: ใช้ class strategy → ThemeProvider toggle `dark` ที่ <html>
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // เลือก palette ที่เป็นกลาง — ใช้ slate/indigo
        brand: {
          50: "#eef2ff",
          100: "#e0e7ff",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
        },
      },
      fontFamily: {
        sans: ["system-ui", "-apple-system", "Segoe UI", "Sarabun", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
