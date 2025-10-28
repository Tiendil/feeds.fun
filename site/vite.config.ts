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
      '/spa': {
        target: 'http://gateway:8000/',
        changeOrigin: false,
      },
      '/realms': {
        target: 'http://keycloak:8080/',
        changeOrigin: false,
      },
      '/resources': {
        target: 'http://keycloak:8080/',
        changeOrigin: false,
      }
    }
  }
})
