import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/apps': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/run': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/run_sse': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/list-apps': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
      '/ws': {
        target: 'ws://localhost:8081',
        ws: true,
        changeOrigin: true,
      },
    },
  },
})
