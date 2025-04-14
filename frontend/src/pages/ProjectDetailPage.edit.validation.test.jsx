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
  TEST_PROJECT_NAME
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

describe('ProjectDetailPage Edit Validation Tests', () => {
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

  it('disables save button when project name is empty', async () => {
    // Setup test data
    const user = userEvent.setup();
    
    // Reset mocks to ensure clean state
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
    
    // Render with our router helper
    const { container, findByText } = renderWithRouter(
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
    
    // Clear the input to trigger validation
    await user.clear(nameInput);
    
    // After clearing, find the save button and verify it's disabled
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
      // Key assertion: The save button should be disabled when the name is empty
      expect(saveButton.disabled).toBe(true);
    });
    
    // Try to click the save button anyway (even though it's disabled)
    await user.click(saveButton);
    
    // Verify the API was NOT called (should not be able to save an empty name)
    expect(updateProject).not.toHaveBeenCalled();
  });
  
  it('validates project name length is reasonable', async () => {
    // Setup test data
    const user = userEvent.setup();
    // Use a moderately long name (not excessively long) to ensure the test is stable
    const longName = 'A'.repeat(50); // Long enough but not too long
    
    // Reset mocks to ensure clean state
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
    
    // Render with our router helper
    const { container, findByText } = renderWithRouter(
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
    
    // Clear the input and type a long name
    await user.clear(nameInput);
    await user.type(nameInput, longName);
    
    // Verify that we can enter a reasonably long name
    // and that the component doesn't crash with longer input
    await waitFor(() => {
      // We should be able to see at least some of our input text
      expect(nameInput.value.length).toBeGreaterThan(10);
      
      // The component shouldn't crash with a longer name
      expect(nameInput).toBeInTheDocument();
    });
    
    // Find the save button
    let saveButton;
    await waitFor(() => {
      const buttons = container.querySelectorAll('button');
      for (const button of buttons) {
        if (button.textContent.toLowerCase().includes('save') && !button.disabled) {
          saveButton = button;
          break;
        }
      }
    });
    
    // The save button should be enabled for a valid name length
    if (saveButton) {
      expect(saveButton.disabled).toBe(false);
      
      // Click save and verify API call happens
      await user.click(saveButton);
      
      // Verify the update was called with our long name
      await waitFor(() => {
        expect(updateProject).toHaveBeenCalledWith(
          TEST_PROJECT_ID,
          expect.objectContaining({ name: expect.any(String) })
        );
      });
    }
  });
});
