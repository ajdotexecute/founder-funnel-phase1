/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // rgb(var(--x) / <alpha-value>) so opacity modifiers (bg-steel/10 etc.)
        // keep working even though the actual value is set at runtime from the
        // fetched theme, not fixed at build time — see lib/theme.ts.
        background: "rgb(var(--color-background) / <alpha-value>)",
        steel: "rgb(var(--color-accent) / <alpha-value>)",
      },
      fontFamily: {
        sans: ["var(--font-family)", "system-ui", "sans-serif"],
        serif: ["var(--font-family-display)", "Georgia", "serif"],
        mono: ["var(--font-family-mono)", "ui-monospace", "monospace"],
      },
    },
  },
  plugins: [],
};
