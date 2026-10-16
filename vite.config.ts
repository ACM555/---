import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const rootDirectory = fileURLToPath(new URL('.', import.meta.url))

export default defineConfig({
  // Keep production assets relative so the app works from a GitHub Pages
  // project subdirectory (and continues to work if the repository is renamed).
  base: './',
  plugins: [react()],
  build: {
    target: 'es2018',
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: {
      '@': path.resolve(rootDirectory, 'src'),
    },
  },
})
