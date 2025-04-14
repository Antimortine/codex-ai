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

import React from 'react';
import { waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import ProjectDetailPage from './ProjectDetailPage';
import {
  renderWithRouter,
  flushPromises,
  TEST_PROJECT_ID,
  TEST_PROJECT_NAME,
  UPDATED_PROJECT_NAME
} from '../utils/testing';

// Mock API calls used by ProjectDetailPage
vi.mock('../api/codexApi', async () => {
  return {
    getProject: vi.fn(),
    updateProject: vi.fn(),
    listChapters: vi.fn(),
    listCharacters: vi.fn(),
    listScenes: vi.fn(),
  };
});

// Mock ChapterSection component to avoid prop validation issues
vi.mock('../components/ChapterSection', () => {
  return {
    default: ({ chapter }) => <div data-testid={`chapter-section-${chapter.id}`}>{chapter.title}</div>
  };
});

// Import the mocked API functions
import { 
  getProject, 
  updateProject,
  listChapters, 
  listCharacters,
  listScenes
} from '../api/codexApi';

describe('ProjectDetailPage Edit Error Handling Tests', () => {
  // Set up and tear down
  beforeEach(() => {
    vi.resetAllMocks();
    
    // Setup basic mocks for most tests
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('handles API error when saving project name', async () => {
    // Setup test data
    const user = userEvent.setup();
    const errorMsg = "Save failed";
    
    // Reset all mocks to ensure clean state
    getProject.mockReset();
    listChapters.mockReset();
    listCharacters.mockReset();
    listScenes.mockReset();
    updateProject.mockReset();
    
    // Configure API mocks
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });
    
    // Setup error response for update
    updateProject.mockRejectedValue(new Error(errorMsg));
    
    // Render with our router helper
    const { container, findByText, queryByText } = renderWithRouter(
      <ProjectDetailPage />, 
      `/projects/${TEST_PROJECT_ID}`
    );
    
    // Wait for initial data load and project name to be displayed
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Verify the project name is displayed
    await findByText(TEST_PROJECT_NAME);
    
    // Find the edit button
    let editButton;
    await waitFor(() => {
      const buttons = container.querySelectorAll('button');
      for (const button of buttons) {
        if (button.textContent.toLowerCase().includes('edit')) {
          editButton = button;
          break;
        }
      }
      expect(editButton).toBeTruthy();
    });
    
    // Click the edit button
    await user.click(editButton);
    
    // Find the input field for editing the project name
    let nameInput;
    await waitFor(() => {
      const inputs = container.querySelectorAll('input[type="text"]');
      for (const input of inputs) {
        if (input.value === TEST_PROJECT_NAME) {
          nameInput = input;
          break;
        }
      }
      expect(nameInput).toBeTruthy();
    });
    
    // Clear and type the new project name
    await user.clear(nameInput);
    await user.type(nameInput, UPDATED_PROJECT_NAME);
    
    // Find the save button
    let saveButton;
    await waitFor(() => {
      const buttons = container.querySelectorAll('button');
      for (const button of buttons) {
        if (button.textContent.toLowerCase().includes('save')) {
          saveButton = button;
          break;
        }
      }
      expect(saveButton).toBeTruthy();
    });
    
    // Click the save button which will trigger the API error
    await user.click(saveButton);
    
    // Verify the updateProject API was called
    await waitFor(() => {
      expect(updateProject).toHaveBeenCalledWith(
        TEST_PROJECT_ID,
        expect.objectContaining({ name: UPDATED_PROJECT_NAME })
      );
    });
    
    // After an error, either:
    // 1. The form remains in edit mode (input is still visible), or
    // 2. An error message is displayed
    await waitFor(() => {
      // Check if we're still in edit mode (input is still visible)
      const inputsAfterError = container.querySelectorAll('input[type="text"]');
      
      // Or check if there's an error message
      const hasErrorText = 
        container.textContent.toLowerCase().includes('error') || 
        container.textContent.toLowerCase().includes('fail');
      
      // Either condition indicates proper error handling
      expect(inputsAfterError.length > 0 || hasErrorText).toBe(true);
    });
  });

  it('shows error message when API fails during load', async () => {
    // Reset all mocks to ensure clean state
    getProject.mockReset();
    listChapters.mockReset();
    listCharacters.mockReset();
    listScenes.mockReset();
    updateProject.mockReset();
    
    // Setup API error for initial project load
    const errorMsg = "Failed to load project";
    getProject.mockRejectedValue(new Error(errorMsg));
    
    // Render with our router helper
    const { container } = renderWithRouter(
      <ProjectDetailPage />, 
      `/projects/${TEST_PROJECT_ID}`
    );
    
    // Wait for the error to be displayed
    await waitFor(() => {
      const content = container.textContent.toLowerCase();
      const hasErrorText = 
        content.includes('error') || 
        content.includes('fail') || 
        content.includes('unable to load') ||
        content.includes('could not load');
      
      expect(hasErrorText).toBe(true);
    });
    
    // Verify that updateProject was not called (since we failed earlier in the flow)
    expect(updateProject).not.toHaveBeenCalled();
    
    // Verify getProject was called with the correct ID
    expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
  });
});
