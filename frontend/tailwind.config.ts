import type { Config } from "tailwindcss";

// Design tokens from the approved design system. Tailwind is used only for
// structured styling; the visual language lives in globals.css.
const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#ffffff",
        page: "#f5f5f3",
        wash: "#f6f6f4",
        hover: "#f5f5f2",
        ink: "#2b2b2b",
        muted: "#6b6b66",
        line: "#d6d6d1",
        success: "#2e6b34",
        warning: "#96690f",
        alert: "#a33327",
      },
      fontFamily: {
        sans: [
          "-apple-system",
          "BlinkMacSystemFont",
          '"Segoe UI"',
          "Roboto",
          '"Helvetica Neue"',
          "Arial",
          "sans-serif",
        ],
        serif: ["Georgia", '"Times New Roman"', "serif"],
      },
    },
  },
  plugins: [],
};

export default config;
