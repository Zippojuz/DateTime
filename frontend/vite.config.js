import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The frontend proxies /api to the Flask backend in dev, so client code can use
// relative URLs and there's no CORS friction during development.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': 'http://localhost:5000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
  },
})
