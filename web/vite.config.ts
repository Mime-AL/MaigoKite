import { fileURLToPath, URL } from 'node:url'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

const gatewayTarget = process.env.MAIGOKITE_GATEWAY_PROXY_TARGET || 'http://127.0.0.1:8080'

function gatewayProxy() {
  return {
    '/api': { target: gatewayTarget, ws: true },
    '/health': { target: gatewayTarget },
  }
}

export default defineConfig({
  base: './',
  plugins: [vue()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  server: {
    proxy: gatewayProxy(),
  },
  preview: {
    proxy: gatewayProxy(),
  },
})
