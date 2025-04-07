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
  },
});