import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(({mode}) => {
  const isProd = mode === 'production';

  return {
    plugins: [react(), tailwindcss()],
    build: {
      // 生产环境优化
      target: 'es2020',
      cssTarget: 'chrome80',
      sourcemap: !isProd,
      minify: 'esbuild',
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (id.includes('node_modules/three')) return 'three';
            if (id.includes('node_modules/motion')) return 'motion';
            if (id.includes('node_modules/lucide-react')) return 'icons';
            if (id.includes('node_modules/gsap')) return 'gsap';
            if (id.includes('node_modules/recharts')) return 'charts';
            if (id.includes('node_modules/react-router')) return 'router';
          },
        },
      },
      // 压缩 CSS
      cssCodeSplit: true,
      // 资源内联限制（小于 4KB 内联）
      assetsInlineLimit: 4096,
    },
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      // Do not modify—file watching is disabled to prevent flickering during agent edits.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        '/api': {target: process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8010', changeOrigin: true},
        '/ready': {target: process.env.VITE_API_PROXY ?? 'http://127.0.0.1:8010', changeOrigin: true},
      },
    },
    // 生产环境优化
    esbuild: {
      // 生产环境移除 console.log 和 debugger
      drop: isProd ? ['console', 'debugger'] : [],
    },
  };
});
