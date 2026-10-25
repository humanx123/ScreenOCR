import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Sitio de proyecto en GitHub Pages: https://humanx123.github.io/ScreenOCR/
export default defineConfig({
  base: "/ScreenOCR/",
  plugins: [react()],
});
