import { fileURLToPath, URL } from 'node:url'

import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import pkg from './package.json'

export default defineConfig({
  plugins: [vue()],

  define: {
    __APP_VERSION__: JSON.stringify(pkg.version),
  },

  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  },

  server: {
    proxy: {
      '/spa/api': {
        target: 'http://gateway:8000/',
        changeOrigin: false,
      },
      '/spa/docs': {
        target: 'http://gateway:8000/',
        changeOrigin: false,
      },
      '/spa/test': {
        target: 'http://gateway:8000/',
        changeOrigin: false,
      },
      '/spa/auth/redirect': {
        target: 'http://gateway:8000/',
        changeOrigin: false,
      },
      '/self-service': {
        target: 'http://kratos:4433/',
        changeOrigin: false,
      },
      '/oauth2': {
        target: 'http://hydra:4444/',
        changeOrigin: false,
      }
    }
  }
})
