/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#1f2933",
        panel: "#f7f8fa",
        accent: "#2563eb",
        success: "#0f766e",
        warning: "#b45309"
      }
    }
  },
  plugins: []
};

