import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => ({
  plugins: [react()],
  server: {
    port: 5175,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Hidden sourcemaps in prod: emitted next to assets but no //# comment in JS,
    // so they can be uploaded to Sentry without leaking source to browsers.
    sourcemap: mode === 'production' ? 'hidden' : true,
    rollupOptions: {
      output: {
        // Function form (object form was dropped by Vite 8's Rolldown bundler).
        manualChunks(id) {
          if (/node_modules\/(react|react-dom|react-router|react-router-dom)\//.test(id)) {
            return 'react'
          }
        },
      },
    },
    chunkSizeWarningLimit: 1500,
  },
  esbuild: {
    drop: mode === 'production' ? ['console', 'debugger'] : [],
  },
}))
