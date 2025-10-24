import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Get backend URL from environment or default to localhost:8080
const apiUrl = process.env.VITE_API_URL || 'http://localhost:8080';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: apiUrl,
        changeOrigin: true,
      },
      '/ws': {
        target: apiUrl.replace('http', 'ws'),
        ws: true,
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: '../swecli/web/static',
    emptyOutDir: true,
  },
})
