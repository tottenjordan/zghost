import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      // Memory API must come before /api to avoid being caught by the broader rule
      '/api/memories': {
        target: 'http://localhost:8082',
        changeOrigin: true,
      },
      // All /api/* requests go to the api_server
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      // Voice WebSocket server
      '/ws': {
        target: 'ws://localhost:8081',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
