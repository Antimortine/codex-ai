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