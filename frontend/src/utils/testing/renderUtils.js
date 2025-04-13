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

// Common testing utility functions and constants for React components with routing
import React from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

/**
 * Renders a component wrapped in a Router with a specific route.
 * This is useful for testing components that rely on the React Router context.
 * 
 * @param {React.ReactElement} ui - The component to render
 * @param {string} route - The route to use for the MemoryRouter
 * @param {string} path - The path pattern to match (defaults to the route)
 * @param {Object} options - Additional render options
 * @returns {Object} The render result and wrapper element
 */
export function renderWithRouter(ui, route, path, options = {}) {
  // If no path is provided, use the route as the path pattern
  if (!path) {
    // Extract the path pattern from the route by removing query params
    path = route.split('?')[0];
    // Replace specific IDs with route params
    path = path.replace(/\/[^/]+$/, '/:id');
  }

  const wrapper = React.createElement(
    MemoryRouter,
    { initialEntries: [route] },
    React.createElement(
      Routes,
      null,
      React.createElement(Route, { path, element: ui }),
    )
  );

  const result = render(wrapper, options);
  
  return {
    ...result,
    // Add helper for navigating to a new route
    navigate: (newRoute) => {
      // This is a simplified version, actual navigation would require
      // a more complex setup with history
      console.warn('Navigation in tests is simplified, rerender with new route instead');
    },
    // Return the wrapper element for further manipulation if needed
    wrapper
  };
}

/**
 * Helper to wait for promises to resolve
 * Useful when testing components that make asynchronous calls
 * 
 * @param {number} ms - Milliseconds to wait 
 * @returns {Promise} Promise that resolves after the specified time
 */
export function flushPromises(ms = 50) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * Helper to safely unmount components and wait for cleanup
 * 
 * @param {HTMLElement} container - The container returned by render
 * @returns {Promise} Promise that resolves when cleanup is complete
 */
export function unmountSafely(container) {
  if (container) {
    try {
      // Attempt to unmount
      render(null, { container });
      // Wait for any cleanup effects
      return flushPromises(10);
    } catch (e) {
      console.error('Error during unmount:', e);
      return Promise.resolve();
    }
  }
  return Promise.resolve();
}
