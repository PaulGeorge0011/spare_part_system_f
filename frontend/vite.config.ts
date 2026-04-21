// vite.config.ts
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import AutoImport from 'unplugin-auto-import/vite'
import Components from 'unplugin-vue-components/vite'
import { ElementPlusResolver } from 'unplugin-vue-components/resolvers'

// 白码同域部署时设为 /spare/，否则为 /
const base = process.env.VITE_BASE_PATH || '/'

export default defineConfig({
  base,
  plugins: [
    vue({
      // 启用响应式语法糖（可选，提升开发体验）
      reactivityTransform: true,
    }),
    // Element Plus 按需导入
    AutoImport({
      resolvers: [ElementPlusResolver()],
      imports: ['vue', 'vue-router', 'pinia'],
      dts: 'src/auto-imports.d.ts',
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: 'src/components.d.ts',
    }),
  ],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  },
  server: {
    port: 5173,
    // 监听所有网卡，同网段设备可通过本机 IP:5173 访问
    host: '0.0.0.0',
    proxy: {
      // API代理到后端（Docker 内使用服务名 fastapi，本地开发可用 localhost）
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path,
        ws: true,
      },
      // 二级目录开发时：/zs2sbgl/api/xxx 也代理到后端，否则图片上传/删除等 API 会落到 SPA 返回 HTML
      '/zs2sbgl/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/zs2sbgl/, ''),
        ws: true,
      },
      // MinIO 代理：/minio/xxx -> minio:9000/xxx（与 Nginx 的 /minio/ 规则一致）
      '/minio': {
        target: process.env.VITE_MINIO_PROXY_TARGET || 'http://localhost:9000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/minio/, ''),
      },
      // 二级目录部署时：/zs2sbgl/minio/xxx 也代理到 MinIO，否则该路径会被 SPA 吞掉返回 index.html
      '/zs2sbgl/minio': {
        target: process.env.VITE_MINIO_PROXY_TARGET || 'http://localhost:9000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/zs2sbgl\/minio/, ''),
      },
    }
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    // 代码分割优化
    chunkSizeWarningLimit: 1000,
    // 启用 CSS 代码分割
    cssCodeSplit: true,
    // 压缩选项
    minify: 'esbuild',
    // 目标浏览器
    target: 'es2020',
    rollupOptions: {
      output: {
        chunkFileNames: 'assets/js/[name]-[hash].js',
        entryFileNames: 'assets/js/[name]-[hash].js',
        assetFileNames: 'assets/[ext]/[name]-[hash].[ext]',
        // 优化的手动分包策略
        manualChunks(id) {
          // Vue 核心库
          if (id.includes('node_modules/vue') || 
              id.includes('node_modules/@vue') ||
              id.includes('node_modules/vue-router') ||
              id.includes('node_modules/pinia')) {
            return 'vue-vendor'
          }
          // Element Plus
          if (id.includes('node_modules/element-plus')) {
            return 'element-plus'
          }
          // ECharts
          if (id.includes('node_modules/echarts') || id.includes('node_modules/zrender')) {
            return 'echarts'
          }
          // 工具库
          if (id.includes('node_modules/axios') || 
              id.includes('node_modules/dayjs') ||
              id.includes('node_modules/xlsx') ||
              id.includes('node_modules/jszip')) {
            return 'utils-vendor'
          }
          // 电气系统页面打包在一起
          if (id.includes('/views/SparePartList') ||
              id.includes('/views/SparePartRequisition') ||
              id.includes('/components/SparePartFormDialog') ||
              id.includes('/components/BatchImportDialog') ||
              id.includes('/components/BatchImageImportDialog')) {
            return 'electrical'
          }
          // 机械系统页面打包在一起
          if (id.includes('/views/MechanicalSparePartList') ||
              id.includes('/views/MechanicalSparePartRequisition') ||
              id.includes('/components/MechanicalSparePartFormDialog') ||
              id.includes('/components/MechanicalRequisitionDialog')) {
            return 'mechanical'
          }
          // 布局组件
          if (id.includes('/layout/')) {
            return 'layout'
          }
        }
      }
    }
  },
  // 优化依赖预构建
  optimizeDeps: {
    include: [
      'vue', 
      'vue-router', 
      'pinia', 
      'axios', 
      'dayjs', 
      'element-plus',
      '@element-plus/icons-vue'
    ],
    // 强制预构建，避免首次加载时的延迟
    force: false,
  },
  // 启用实验性功能
  esbuild: {
    // 移除 console 和 debugger（生产环境）
    drop: process.env.NODE_ENV === 'production' ? ['console', 'debugger'] : [],
  }
})