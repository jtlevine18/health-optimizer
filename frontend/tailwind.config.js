/** @type {import('tailwindcss').Config} */
export default {
  content: [
    './index.html',
    './src/**/*.{js,ts,jsx,tsx}',
  ],
  theme: {
    extend: {
      colors: {
        cream: '#f8fafa',
        gold: {
          DEFAULT: '#0d7377',
          hover: '#095c5f',
          light: '#5cc4c8',
          dark: '#074f52',
        },
        warm: {
          border: '#e0dcd5',
          muted: '#888888',
          'muted-light': '#999999',
          body: '#555555',
          'body-light': '#666666',
          'header-bg': '#f5f3ef',
        },
        sidebar: {
          DEFAULT: '#1a1a1a',
          end: '#0f1a1a',
          hover: '#2a2a3e',
        },
        success: '#2a9d8f',
        warning: '#0d7377',
        error: '#e63946',
        info: '#1565C0',
      },
      fontFamily: {
        serif: ['"Source Serif 4"', 'Georgia', 'serif'],
        sans: ['"DM Sans"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      },
      borderRadius: {
        DEFAULT: '10px',
      },
      letterSpacing: {
        'section': '1.5px',
        'label': '1.2px',
        'btn': '0.5px',
      },
    },
  },
  plugins: [],
}
