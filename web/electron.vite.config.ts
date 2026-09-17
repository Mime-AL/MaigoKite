import { defineConfig } from 'vite'
import { resolve } from 'node:path'

export default defineConfig({
  build: {
    outDir: 'dist-electron', emptyOutDir: true, sourcemap: true,
    rollupOptions: {
      external: ['electron', 'node:child_process', 'node:fs', 'node:path'],
      input: { main: resolve(__dirname, 'src/electron/main.ts'), preload: resolve(__dirname, 'src/electron/preload.ts') },
      output: { format: 'cjs', entryFileNames: '[name].cjs' }
    }
  }
})
