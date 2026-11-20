import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',
  build: {
    // xlsx.min is an ~860 kB third-party library loaded lazily only on Excel export
    chunkSizeWarningLimit: 900,
    rolldownOptions: {
      output: {
        codeSplitting: {
          groups: [
            { name: 'vendor-react', test: /node_modules[\\/](react|react-dom|scheduler)[\\/]/ },
            { name: 'vendor-icons', test: /node_modules[\\/]lucide-react[\\/]/ },
          ],
        },
      },
    },
  },
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
