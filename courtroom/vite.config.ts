import { resolve } from "node:path";
import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: {
    target: "es2022",
    outDir: "dist",
    emptyOutDir: true,
    rollupOptions: {
      input: {
        landing: resolve(__dirname, "index.html"),
        courtroom: resolve(__dirname, "courtroom.html"),
        findings: resolve(__dirname, "findings.html"),
      },
    },
  },
});
