import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import path from 'path';
import {defineConfig} from 'vite';

export default defineConfig(() => {
  return {
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, '.'),
      },
    },
    server: {
      port: 5173,
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      hmr: process.env.DISABLE_HMR !== 'true',
      // Disable file watching when DISABLE_HMR is true to save CPU during agent edits.
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        "/api/v1": {
          target: "http://127.0.0.1:8000",
          changeOrigin: true,
          // SSE: keep the upstream stream open and unbuffered.
          configure: (proxy) => {
            proxy.on("proxyReq", (proxyReq, req) => {
              if (req.url?.endsWith("/stream")) {
                proxyReq.setHeader("Accept", "text/event-stream");
                proxyReq.setHeader("Cache-Control", "no-cache");
              }
            });
            proxy.on("proxyRes", (proxyRes, req) => {
              if (req.url?.endsWith("/stream")) {
                proxyRes.headers["cache-control"] = "no-cache";
                delete proxyRes.headers["content-length"];
              }
            });
          },
        },
      },
    },
  };
});
