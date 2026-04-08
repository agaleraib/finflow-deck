import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Dev server runs on 5174 to avoid clashing with the archived web mockup at 5173.
// /poc/* is proxied to the api dev server (default port 3000) so the playground
// can call routes without CORS gymnastics.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5174,
    proxy: {
      "/poc": {
        target: "http://localhost:3000",
        changeOrigin: true,
      },
    },
  },
});
