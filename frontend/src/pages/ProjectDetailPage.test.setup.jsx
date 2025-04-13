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

// Common test setup for ProjectDetailPage tests
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi } from 'vitest';

// Mock the API module
vi.mock('../api/codexApi');

// Define mock functions directly
export const getProject = vi.fn();
export const updateProject = vi.fn();
export const listChapters = vi.fn();
export const createChapter = vi.fn();
export const deleteChapter = vi.fn();
export const listCharacters = vi.fn();
export const createCharacter = vi.fn();
export const deleteCharacter = vi.fn();
export const rebuildProjectIndex = vi.fn();
export const compileChapterContent = vi.fn();
export const listScenes = vi.fn();

// Test constants
export const TEST_PROJECT_ID = 'proj-detail-123';
export const TEST_PROJECT_NAME = 'Detailed Project';
export const UPDATED_PROJECT_NAME = 'Updated Name';
export const TEST_CHAPTER_ID = 'ch-1';
export const TEST_CHAPTER_TITLE = 'The First Chapter (Mocked)';
export const TEST_CHARACTER_ID = 'char-1';
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
    // Return additional helper methods here if needed
  };
}

// Helper to wait for promises to resolve
export const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0));

// Reset all mocks before each test
export function setupMocks() {
  vi.resetAllMocks();
  
  // Setup basic mocks for most tests
  getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
  listChapters.mockResolvedValue({ data: { chapters: [] } });
  listCharacters.mockResolvedValue({ data: { characters: [] } });
  
  // Mock window.confirm (used in delete operations)
  window.confirm = vi.fn(() => true);
}
