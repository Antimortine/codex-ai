/*
 * Copyright 2025 Antimortine
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

/// <reference types="vitest" />
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path'; // Import path module for resolving alias

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true, // Use Vitest global APIs (describe, it, expect, etc.)
    environment: 'jsdom', // Simulate DOM environment
    setupFiles: './src/setupTests.js', // Setup file for jest-dom matchers
    testTimeout: 15000, // Increase default timeout to 15 seconds for flaky tests
    // Optional: Enable CSS processing if your components rely on CSS modules/imports
    // css: true,
    coverage: {
      provider: 'v8',
    },
    // --- ADDED: Server dependency optimization ---
    // Explicitly tell Vitest/Vite not to try and pre-bundle file-saver for SSR/tests
    // as we are aliasing it anyway. This can sometimes help with resolution issues.
    // server: {
    //   deps: {
    //     inline: [/^(?!file-saver$).*/], // Inline everything EXCEPT file-saver (or adjust regex)
    //     // Alternatively, explicitly exclude:
    //     // exclude: ['file-saver'],
    //   }
    // },
  },
  // --- ADDED: Resolve Alias for file-saver ---
  resolve: {
    alias: {
      // Alias 'file-saver' to our dummy mock implementation during tests
      // Ensure the path is resolved correctly relative to the config file location
      'file-saver': path.resolve(__dirname, 'src/__mocks__/file-saver.js'),
    },
  },
  // --- END ADDED ---
});