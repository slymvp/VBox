import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

export default defineConfig({
  plugins: [vue()],
  base: '/admin/',
  resolve: {
    alias: {
      '@': resolve(__dirname, 'src')
    }
  },
  server: {
    port: 3001,
    proxy: {
      '/admin-api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rolldownOptions: {
      onwarn(warning, warn) {
        // 忽略 @vueuse/core 的 PURE 注释警告
        if (warning.code === 'INVALID_ANNOTATION' && 
            warning.message.includes('@vueuse/core')) {
          return
        }
        warn(warning)
      }
    }
  }
})
