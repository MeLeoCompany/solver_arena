import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendTarget = process.env.VITE_BACKEND_URL ?? 'http://localhost:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': backendTarget,
      '/solve': backendTarget,
      '/jobs': backendTarget,
      '/batches': backendTarget,
      '/solvers': backendTarget,
      '/tokens': backendTarget,
      '/compare': backendTarget,
      '/system': backendTarget,
      '/users': backendTarget,
    },
  },
})
