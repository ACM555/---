import path from 'node:path'
import { fileURLToPath } from 'node:url'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const rootDirectory = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(rootDirectory, 'src'),
    },
  },
  test: {
    exclude: ['tests/e2e/**', 'node_modules/**', 'dist/**', 'output/**'],
    fileParallelism: false,
    environment: 'jsdom',
    maxWorkers: 1,
    pool: 'forks',
    setupFiles: ['./src/test/setup.ts'],
    css: true,
  },
})
