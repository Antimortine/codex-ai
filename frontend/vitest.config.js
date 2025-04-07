/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true, // Use Vitest global APIs (describe, it, expect, etc.)
    environment: 'jsdom', // Simulate DOM environment
    setupFiles: './src/setupTests.js', // Setup file for jest-dom matchers
    // Optional: Enable CSS processing if your components rely on CSS modules/imports
    // css: true,
  },
});