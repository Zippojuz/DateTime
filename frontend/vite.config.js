import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The frontend proxies /api to the Flask backend in dev, so client code can use
// relative URLs and there's no CORS friction during development.
export default defineConfig({
  plugins: [react()],
  server: {
    // Listen on all interfaces so the mapped port is reachable from the host
    // when running inside Docker.
    host: true,
    port: 5173,
    // inotify events don't cross the bind mount on macOS/Windows Docker; the
    // container sets VITE_USE_POLLING so file changes are still detected.
    // Left off for native local dev to avoid the extra CPU cost.
    watch: {
      usePolling: !!process.env.VITE_USE_POLLING,
    },
    proxy: {
      // Both processes share localhost inside the single container, so this
      // target works unchanged in Docker and in local dev.
      '/api': 'http://localhost:5000',
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: './src/test/setup.js',
  },
})
