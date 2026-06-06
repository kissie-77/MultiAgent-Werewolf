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
      host: "127.0.0.1",
      port: 5173,
      // HMR is disabled in AI Studio via DISABLE_HMR env var.
      hmr: process.env.DISABLE_HMR !== 'true',
      watch: process.env.DISABLE_HMR === 'true' ? null : {},
      proxy: {
        // SSE-aware proxy for the engine-driven spectate stream — must come
        // before the generic '/api' rule so '/api/v1/.../stream' matches here.
        "/api/v1": {
          target: process.env.VITE_API_PROXY_TARGET || "http://127.0.0.1:8000",
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
        '/api': {
          target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/ready': {
          target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
        '/health': {
          target: process.env.VITE_API_PROXY_TARGET || 'http://127.0.0.1:8000',
          changeOrigin: true,
        },
      },
    },
  };
});
