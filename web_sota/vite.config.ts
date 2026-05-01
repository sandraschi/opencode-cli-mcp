import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BACKEND_PORT = 10951;

export default defineConfig({
  plugins: [react()],
  server: {
    port: 10950,
    proxy: {
      "/api": {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      "/README.md": {
        target: "http://127.0.0.1:10950",
        changeOrigin: true,
      },
      "/docs": {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      "/openapi.json": {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
      "/redoc": {
        target: `http://127.0.0.1:${BACKEND_PORT}`,
        changeOrigin: true,
      },
    },
  },
});
