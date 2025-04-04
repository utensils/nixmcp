/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './app/**/*.{js,ts,jsx,tsx,mdx}',
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        'nix-primary': '#5277C3',     // NixOS primary blue
        'nix-secondary': '#7EBAE4',   // NixOS secondary blue
        'nix-dark': '#1C3E5A',         // Darker blue for contrast
        'nix-light': '#E6F0FA',       // Light blue background
      },
      fontFamily: {
        sans: ['Inter', 'ui-sans-serif', 'system-ui', 'sans-serif'],
        mono: ['Fira Code', 'ui-monospace', 'monospace'],
      },
    },
  },
  plugins: [],
}