/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./dashboard/templates/**/*.html",
        "./ethiostore/templates/**/*.html",
    ],
    theme: {
        extend: {
            colors: {
                brand: {
                    dark: '#090a0f', // Deep dark enterprise background
                    darker: '#06070a', // Even darker for contrast
                    card: '#12141d', // Slightly lighter for cards
                    green: '#a3e635', // Light green priority accent
                    cyan: '#22d3ee', // Cyan secondary accent
                    text: '#f8fafc',
                    muted: '#94a3b8',
                    border: '#1e293b'
                }
            },
            fontFamily: {
                sans: ['"Space Grotesk"', 'sans-serif'],
            }
        },
    },
    plugins: [],
}
