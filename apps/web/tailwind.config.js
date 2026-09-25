/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      colors: {
        clinical: {
          50: '#f0f4ff',
          100: '#dbe4ff',
          200: '#bac8ff',
          300: '#91a7ff',
          400: '#748ffc',
          500: '#5c7cfa',
          600: '#4c6ef5',
          700: '#4263eb',
          800: '#3b5bdb',
          900: '#364fc7',
          950: '#1e3a5f',
        },
        surface: {
          0: '#0a0e1a',
          1: '#111827',
          2: '#1a2234',
          3: '#1f2b3f',
          4: '#253349',
        },
        paper: {
          DEFAULT: '#F5F5F3',
          2: '#EAEAE8',
          3: '#DFDFDC'
        },
        speaker: {
          clinician: '#3E5C6B',
          patient: '#5E6B3E',
        },
        safety: {
          'flag-red': '#ef4444',
          'flag-amber': '#f59e0b',
          'flag-yellow': '#eab308',
          'success': '#22c55e',
          'ungrounded': '#f97316',
        },
      },
      animation: {
        'pulse-recording': 'pulse-recording 2s ease-in-out infinite',
        'fade-in-up': 'fade-in-up 0.4s ease-out',
        'slide-down': 'slide-down 0.3s ease-out',
        'glow': 'glow 2s ease-in-out infinite alternate',
        'waveform': 'waveform 1.2s ease-in-out infinite',
      },
      keyframes: {
        'pulse-recording': {
          '0%, 100%': { opacity: '1', transform: 'scale(1)' },
          '50%': { opacity: '0.5', transform: 'scale(1.05)' },
        },
        'fade-in-up': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slide-down': {
          '0%': { opacity: '0', maxHeight: '0' },
          '100%': { opacity: '1', maxHeight: '500px' },
        },
        'glow': {
          '0%': { boxShadow: '0 0 5px rgba(92, 124, 250, 0.2)' },
          '100%': { boxShadow: '0 0 20px rgba(92, 124, 250, 0.4)' },
        },
        'waveform': {
          '0%, 100%': { height: '4px' },
          '50%': { height: '24px' },
        },
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glass': '0 8px 32px rgba(0, 0, 0, 0.12)',
        'glass-lg': '0 16px 48px rgba(0, 0, 0, 0.2)',
        'inner-glow': 'inset 0 1px 0 rgba(255, 255, 255, 0.05)',
      },
    },
  },
  plugins: [],
};
