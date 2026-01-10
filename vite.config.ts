import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  define: {
    __VUE_OPTIONS_API__: true,
    __VUE_PROD_DEVTOOLS__: false,
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, 'front_vue')
    }
  },
  base: './', // 使用相对路径，增加嵌入灵活性
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:3001',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
    assetsInlineLimit: 0, // 禁用内联，防止大 data URI 导致卡死
    rollupOptions: {
      output: {
        manualChunks: undefined
      }
    }
  }
})
