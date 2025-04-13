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

// Testing utility functions and constants for ProjectDetailPage tests
import React from 'react';
import { render } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// Test constants
export const TEST_PROJECT_ID = 'proj-detail-123';
export const TEST_PROJECT_NAME = 'Detailed Project';
export const UPDATED_PROJECT_NAME = 'Updated Name';
export const TEST_CHAPTER_ID = 'ch-1';
export const TEST_CHAPTER_TITLE = 'The First Chapter (Mocked)';
export const TEST_CHARACTER_ID = 'char-1';
export const TEST_CHARACTER_NAME = 'Test Character';
export const NEW_CHAPTER_TITLE = 'New Chapter';
export const UPDATED_CHAPTER_TITLE = 'Updated Chapter';

// Helper function to create a router wrapper
export function renderWithRouter(ui, route = `/projects/${TEST_PROJECT_ID}`) {
  window.history.pushState({}, 'Test page', route);
  
  return {
    ...render(
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/projects/:projectId" element={ui} />
        </Routes>
      </MemoryRouter>
    ),
  };
}

// Helper to wait for promises to resolve
export const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0));
