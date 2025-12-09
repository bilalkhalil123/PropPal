/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./app/**/*.{js,jsx,ts,tsx}",
    "./components/**/*.{js,jsx,ts,tsx}",
  ],
  presets: [require("nativewind/preset")],
  theme: {
    extend: {
      colors: {
        primary: '#0a7ea4',
        'accent-gold': '#f59e0b',
        'accent-amber': '#f59e0b',
        background: '#ffffff',
        foreground: '#0f172a',
        surface: '#f8fafc',
        'surface-secondary': '#e2e8f0',
        border: '#cbd5e1',
        'text-muted': '#64748b',
        'accent-success': '#10b981',
        'accent-warning': '#f59e0b',
        'accent-error': '#ef4444',
        slate: {
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          300: '#cbd5e1',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b',
          900: '#0f172a',
        },
        teal: {
          600: '#0d9488',
        },
      },
    },
  },
  plugins: [],
};

