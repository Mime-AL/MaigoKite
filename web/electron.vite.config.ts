import { defineConfig } from 'vite'
import { resolve } from 'node:path'

export default defineConfig(({ mode }) => ({
  build: {
    outDir: 'dist-electron',
    emptyOutDir: mode !== 'preload',
    sourcemap: true,
    rollupOptions: {
      external: ['electron', 'node:child_process', 'node:fs', 'node:path', 'node:url'],
      input: resolve(__dirname, `src/electron/${mode === 'preload' ? 'preload' : 'main'}.ts`),
      // Sandboxed preload cannot require shared local chunks. Bundle it alone.
      output: {
        format: 'cjs',
        inlineDynamicImports: true,
        entryFileNames: mode === 'preload' ? 'preload.cjs' : 'main.cjs',
      },
    },
  },
}))
