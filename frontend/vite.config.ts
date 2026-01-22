import { fileURLToPath, URL } from "node:url";
import { readFileSync } from "node:fs";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { visualizer } from "rollup-plugin-visualizer";

// Read version from VERSION file at build time
const getVersion = (): string => {
  try {
    return readFileSync("../VERSION", "utf-8").trim();
  } catch {
    return "0.0.0-dev";
  }
};

const appVersion = getVersion();
const buildTime = new Date().toISOString();

export default defineConfig({
  plugins: [
    vue(),
    // Bundle analyzer - generates stats.html after build
    // Run: npm run build && open stats.html
    visualizer({
      filename: "stats.html",
      open: false,
      gzipSize: true,
      brotliSize: true,
    }),
  ],
  // Inject version info at build time
  define: {
    __APP_VERSION__: JSON.stringify(appVersion),
    __BUILD_TIME__: JSON.stringify(buildTime),
    // Vue compile-time flags for smaller bundles
    __VUE_OPTIONS_API__: "true",
    __VUE_PROD_DEVTOOLS__: "false",
    __VUE_PROD_HYDRATION_MISMATCH_DETAILS__: "false",
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    // Generate source maps for debugging (but don't expose in production)
    sourcemap: false,
    // Chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks: (id) => {
          // Vendor chunk for Vue core
          if (
            id.includes("node_modules/vue") ||
            id.includes("node_modules/vue-router") ||
            id.includes("node_modules/pinia")
          ) {
            return "vue-vendor";
          }
          // AWS Amplify in separate chunk (large dependency)
          if (id.includes("node_modules/aws-amplify") || id.includes("node_modules/@aws-amplify")) {
            return "aws-auth";
          }
          // Chart.js in separate chunk for better caching
          if (id.includes("node_modules/chart.js") || id.includes("vue-chartjs")) {
            return "charts";
          }
        },
      },
    },
    // Target modern browsers for smaller bundles
    target: "es2020",
    // Vite 7 defaults to Oxc minifier (30-90x faster than esbuild)
    // Warn if chunk exceeds 500kb
    chunkSizeWarningLimit: 500,
  },
});
