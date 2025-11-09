/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        umass: {
          maroon: '#881c1c',
          gold: '#fdb913',
        }
      }
    },
  },
  plugins: [
    require('@tailwindcss/typography'),
  ],
}

