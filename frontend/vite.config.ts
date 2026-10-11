import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
const target = process.env.MADAR_DEV_API_URL || "http://127.0.0.1:8000";
const developmentApi = new URL(target);
if (
  !["http:", "https:"].includes(developmentApi.protocol) ||
  !["localhost", "127.0.0.1", "[::1]"].includes(developmentApi.hostname) ||
  developmentApi.username ||
  developmentApi.password
) {
  throw new Error(
    "MADAR_DEV_API_URL must point to a loopback development API without credentials",
  );
}
const previewHosts = (process.env.MADAR_PREVIEW_HOSTS || "")
  .split(",")
  .map((h) => h.trim())
  .filter(Boolean);
const apiProxy = {
  target,
  changeOrigin: true,
  configure: (proxy: any) =>
    proxy.on("proxyReq", (proxyReq: any, req: any) => {
      // Forward same-origin browser mutations through the trusted development proxy.
      // Cross-origin requests keep their original Origin and are rejected by the API.
      const origin = req.headers.origin;
      try {
        if (origin && new URL(origin).host === req.headers.host)
          proxyReq.setHeader("Origin", target);
      } catch {
        /* The API rejects malformed origins. */
      }
    }),
};
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.endsWith("/workflowCatalog.ts"))
            return "workflow-architecture";
        },
      },
    },
  },
  server: {
    host: "0.0.0.0",
    port: 3000,
    strictPort: true,
    allowedHosts: previewHosts,
    proxy: { "/api": apiProxy, "/webhooks": { target, changeOrigin: true } },
  },
});
