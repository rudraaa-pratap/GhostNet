import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:8000',
      '/ws': {
        target: 'ws://127.0.0.1:8000',
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            if (err.code === 'EPIPE' || err.code === 'ECONNRESET') return
            console.error('[vite] ws proxy error:', err)
          })
          proxy.on('proxySocket', (socket) => {
            socket.on('error', (err) => {
              if (err.code === 'EPIPE' || err.code === 'ECONNRESET') return
              console.error('[vite] ws proxy socket error:', err)
            })
          })
        },
      },
    },
  },
})
