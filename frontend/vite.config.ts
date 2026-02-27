import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

const CLOUD_RUN_URL = 'https://trends-and-insights-frontend-in2bk2mdwa-uc.a.run.app'
const useLocal = process.env.VITE_LOCAL_BACKEND === 'true'

const apiTarget = useLocal ? 'http://localhost:8000' : CLOUD_RUN_URL
const memoryTarget = useLocal ? 'http://localhost:8082' : CLOUD_RUN_URL
const voiceTarget = useLocal ? 'http://localhost:8081' : CLOUD_RUN_URL

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Memory API must come before /api to avoid being caught by the broader rule
      '/api/memories': {
        target: memoryTarget,
        changeOrigin: true,
        secure: true,
      },
      // All /api/* requests go to the api_server (or Cloud Run)
      '/api': {
        target: apiTarget,
        changeOrigin: true,
        secure: true,
      },
      // Voice WebSocket server
      '/ws': {
        target: voiceTarget,
        ws: true,
        changeOrigin: true,
        secure: true,
      },
    },
  },
})
