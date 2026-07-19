import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',
  // Dev only: the SPA calls relative URLs (/api, /cache). Proxy them to the
  // FastAPI backend during `npm run dev`. In production the SPA is served by
  // FastAPI on the same origin, so these relative URLs resolve with no proxy.
  server: {
    proxy: {
      '/api': 'http://localhost:8095',
      '/cache': 'http://localhost:8095',
    },
  },
})
