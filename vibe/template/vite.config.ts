import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Vibe: Die Vorschau erreicht den Dev-Server über die Durchreiche des Servers, mit deren Host-Namen.
export default defineConfig({
  plugins: [react()],
  server: { host: '0.0.0.0', port: 5173, strictPort: true, allowedHosts: true },
})
