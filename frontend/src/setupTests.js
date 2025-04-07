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

// src/setupTests.js
import { afterEach } from 'vitest';
import { cleanup } from '@testing-library/react';
// Import functions to extend Vitest's expect
import '@testing-library/jest-dom'; // Import the library directly to extend expect

// NOTE: No need for explicit expect.extend(matchers) when importing '@testing-library/jest-dom'

// Runs a cleanup after each test case (e.g., clearing jsdom)
afterEach(() => {
  cleanup();
});