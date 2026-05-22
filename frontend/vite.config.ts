import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { fileURLToPath, URL } from 'node:url'

export default defineConfig(({ mode }) => ({
  plugins: [vue()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  // In prod the app is served at /admin/ by host nginx
  base: mode === 'production' ? '/admin/' : '/',
  server: {
    port: 5173,
    proxy: {
      // Forward /api/* → admin-api dev port (strips /api prefix)
      '/api': {
        target: 'http://localhost:13002',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
}))
