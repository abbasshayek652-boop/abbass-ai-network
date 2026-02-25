/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ['class'],
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        mono: ['"JetBrains Mono"', 'monospace']
      },
      colors: {
        cyber: {
          bg: '#05060A',
          panel: '#0A0D14',
          panel2: '#0E121B',
          grid: '#0D1321',
          text: '#D5F2E3',
          dim: '#87A3A3',
          neon: '#00FFD1',
          neon2: '#A855F7',
          alert: '#00FF87',
          danger: '#FF3B81',
          warn: '#FFC857'
        }
      },
      boxShadow: {
        neon: '0 0 20px rgba(0, 255, 209, 0.4)'
      }
    }
  },
  plugins: []
};
