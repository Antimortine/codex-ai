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
// Import the refactored component wrapper
import ProjectDetailPage from './ProjectDetailPage';
import {
  renderWithRouter,
  flushPromises,
  TEST_PROJECT_ID,
  TEST_PROJECT_NAME,
  UPDATED_PROJECT_NAME
} from '../utils/testing';

// We'll use a different approach to handle component dependencies

// Mock ChapterSection component to avoid prop validation issues
vi.mock('../components/ChapterSection', () => {
  return {
    default: ({ chapter, scenesForChapter, onDeleteChapter }) => (
      <div data-testid={`chapter-section-${chapter.id}`}>
        {chapter.title}
        {scenesForChapter && <div>Scenes: {scenesForChapter.length}</div>}
        <button 
          data-testid={`delete-chapter-${chapter.id}`}
          onClick={() => onDeleteChapter && onDeleteChapter()}
        >
          Delete
        </button>
      </div>
    )
  };
});

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

// Import the mocked API functions
import { 
  getProject, 
  updateProject,
  listChapters, 
  listCharacters,
  listScenes
} from '../api/codexApi';

describe('ProjectDetailPage Edit Basic Tests', () => {
  // Set up and tear down
  beforeEach(() => {
    vi.resetAllMocks();
    
    // Setup basic mocks for most tests
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });
    
    // Default success response for project update
    updateProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: UPDATED_PROJECT_NAME } });
  
    // Mock window.confirm (used in delete operations)
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('allows editing and saving the project name', async () => {
    // Setup test data and user event instance
    const user = userEvent.setup();
    
    // Reset mocks to ensure clean state
    getProject.mockReset();
    listChapters.mockReset();
    listCharacters.mockReset();
    updateProject.mockReset();
    
    // Configure API mocks
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    updateProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: UPDATED_PROJECT_NAME } });
    
    // Render with our router helper
    const { container, getByText, findByText, findByDisplayValue } = renderWithRouter(
      <ProjectDetailPage />, 
      `/projects/${TEST_PROJECT_ID}`
    );
    
    // Wait for initial data load and project name to be displayed
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Verify initial project name is displayed
    await findByText(TEST_PROJECT_NAME);
    
    // Find and click the edit button using a more reliable approach with findByRole
    // If we can't use findByRole, we'll look for a button with 'edit' text
    let editButton;
    try {
      // Try to find a button with text containing 'edit'
      editButton = await findByText(/edit/i, { selector: 'button' });
    } catch (e) {
      // If we can't find it that way, look for any button that might be the edit button
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
    }
    
    // Click the edit button
    await user.click(editButton);
    
    // After clicking edit, an input field should appear with the current project name
    // Find the name input field
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
    
    // Clear the input and type the new name
    await user.clear(nameInput);
    await user.type(nameInput, UPDATED_PROJECT_NAME);
    
    // Verify the input has the updated value
    await findByDisplayValue(UPDATED_PROJECT_NAME);
    
    // Find and click the save button
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
    
    await user.click(saveButton);
    
    // Verify the updateProject API was called with the correct parameters
    await waitFor(() => {
      expect(updateProject).toHaveBeenCalledWith(
        TEST_PROJECT_ID, 
        expect.objectContaining({ name: UPDATED_PROJECT_NAME })
      );
    });
    
    // Verify the UI shows the updated project name or success message
    await waitFor(() => {
      const content = container.textContent;
      const hasUpdatedName = 
        content.includes(UPDATED_PROJECT_NAME) || 
        content.includes('Updated') || 
        content.includes('updated') || 
        content.includes('success');
      
      expect(hasUpdatedName).toBe(true);
    });
  });

  it('allows cancelling the project name edit', async () => {
    // Setup test data and user event instance
    const user = userEvent.setup();
    
    // Reset mocks to ensure clean state
    getProject.mockReset();
    listChapters.mockReset();
    listCharacters.mockReset();
    updateProject.mockReset();
    
    // Configure API mocks
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    
    // Render with our router helper
    const { container, findByText, findByDisplayValue } = renderWithRouter(
      <ProjectDetailPage />, 
      `/projects/${TEST_PROJECT_ID}`
    );
    
    // Wait for initial data load and project name to be displayed
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Verify initial project name is displayed
    await findByText(TEST_PROJECT_NAME);
    
    // Find and click the edit button
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
    
    // After clicking edit, wait for the input field to appear
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
    
    // Type a new project name
    const tempProjectName = 'Something New';
    await user.clear(nameInput);
    await user.type(nameInput, tempProjectName);
    
    // Verify the input has the new value
    await findByDisplayValue(tempProjectName);
    
    // Find and click the cancel button
    let cancelButton;
    await waitFor(() => {
      const buttons = container.querySelectorAll('button');
      for (const button of buttons) {
        if (button.textContent.toLowerCase().includes('cancel')) {
          cancelButton = button;
          break;
        }
      }
      expect(cancelButton).toBeTruthy();
    });
    
    // Click the cancel button
    await user.click(cancelButton);
    
    // After cancellation, verify the updateProject API was NOT called
    expect(updateProject).not.toHaveBeenCalled();
    
    // Verify the UI shows the original project name (not the cancelled edit)
    await waitFor(() => {
      expect(container.textContent).toContain(TEST_PROJECT_NAME);
      // Also make sure the temporary name is not visible
      expect(container.textContent).not.toContain(tempProjectName);
    });
  });
});
