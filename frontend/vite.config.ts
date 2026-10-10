import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
const target = 'http://127.0.0.1:8000';
const previewHosts = (process.env.MADAR_PREVIEW_HOSTS || '').split(',').map(h => h.trim()).filter(Boolean);
const apiProxy = {
  target, changeOrigin: true,
  configure: (proxy: any) => proxy.on('proxyReq', (proxyReq: any, req: any) => {
    // Forward same-origin browser mutations through the trusted development proxy.
    // Cross-origin requests keep their original Origin and are rejected by the API.
    const origin = req.headers.origin;
    try {
      if (origin && new URL(origin).host === req.headers.host) proxyReq.setHeader('Origin', target);
    } catch { /* The API rejects malformed origins. */ }
  }),
};
export default defineConfig({ plugins: [react()], server: { host: '0.0.0.0', port: 3000, strictPort: true, allowedHosts: previewHosts, proxy: { '/api': apiProxy, '/webhooks': { target, changeOrigin: true } } } });
