import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const backendTarget = process.env.MAIGOKITE_BACKEND_PROXY_TARGET || 'http://127.0.0.1:8080'

function backendProxy() {
  return {
    '/api': { target: backendTarget, ws: true },
    '/health': { target: backendTarget },
  }
}

export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    proxy: backendProxy(),
  },
  preview: {
    proxy: backendProxy(),
  },
})
