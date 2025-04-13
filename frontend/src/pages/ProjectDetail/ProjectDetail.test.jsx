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
import { waitFor, screen } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import userEvent from '@testing-library/user-event';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import ProjectDetailPage from './index';
import {
  renderWithRouter,
  flushPromises,
  TEST_PROJECT_ID,
  TEST_PROJECT_NAME,
  UPDATED_PROJECT_NAME,
  TEST_CHAPTER_ID,
  TEST_CHAPTER_TITLE,
  NEW_CHAPTER_TITLE
} from '../ProjectDetailPage.test.utils';

// Mock API calls used by ProjectDetailPage
vi.mock('../../api/codexApi', async () => {
  return {
    getProject: vi.fn(),
    updateProject: vi.fn(),
    listChapters: vi.fn(),
    listCharacters: vi.fn(),
    listScenes: vi.fn(),
    createChapter: vi.fn(),
    rebuildProjectIndex: vi.fn(),
  };
});

// Import the mocked API functions
import { 
  getProject, 
  updateProject,
  listChapters, 
  listCharacters,
  listScenes,
  createChapter,
  rebuildProjectIndex
} from '../../api/codexApi';

describe('Refactored ProjectDetailPage Tests', () => {
  beforeEach(() => {
    // Reset all mocks before each test
    vi.resetAllMocks();
    
    // Setup default mock responses
    getProject.mockResolvedValue({
      data: {
        id: TEST_PROJECT_ID,
        name: TEST_PROJECT_NAME
      }
    });
    
    listChapters.mockResolvedValue({
      data: {
        chapters: [
          {
            id: TEST_CHAPTER_ID,
            title: TEST_CHAPTER_TITLE,
            order: 1
          }
        ]
      }
    });
    
    listCharacters.mockResolvedValue({
      data: {
        characters: []
      }
    });
    
    listScenes.mockResolvedValue({
      data: {
        scenes: []
      }
    });
  });
  
  afterEach(() => {
    vi.clearAllMocks();
  });
  
  // Test 1: Basic rendering
  it('renders the project name correctly', async () => {
    const { getByTestId } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for data fetching
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    await waitFor(() => {
      expect(getByTestId('project-title')).toHaveTextContent(TEST_PROJECT_NAME);
    });
  });
  
  // Test 2: Project name editing
  it('allows editing the project name', async () => {
    const user = userEvent.setup();
    const { getByTestId } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for initial data load
    await waitFor(() => {
      expect(getByTestId('project-title')).toHaveTextContent(TEST_PROJECT_NAME);
    });
    
    // Mock successful update
    updateProject.mockResolvedValueOnce({
      data: {
        id: TEST_PROJECT_ID,
        name: UPDATED_PROJECT_NAME
      }
    });
    
    // Click edit button, change name, and save
    await user.click(getByTestId('edit-project-name-button'));
    await user.clear(getByTestId('project-name-input'));
    await user.type(getByTestId('project-name-input'), UPDATED_PROJECT_NAME);
    await user.click(getByTestId('save-project-name-button'));
    
    // Verify API call
    await waitFor(() => {
      expect(updateProject).toHaveBeenCalledWith(TEST_PROJECT_ID, { name: UPDATED_PROJECT_NAME });
    });
    
    // Verify updated UI
    await waitFor(() => {
      expect(getByTestId('project-title')).toHaveTextContent(UPDATED_PROJECT_NAME);
    });
  });
  
  // Test 3: Adding a chapter
  it('allows adding a new chapter', async () => {
    const user = userEvent.setup();
    const { getByTestId } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for initial data load
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Mock successful chapter creation
    createChapter.mockResolvedValueOnce({
      data: {
        id: 'new-chapter-id',
        title: NEW_CHAPTER_TITLE,
        order: 2
      }
    });
    
    // Enter new chapter title and submit
    await user.type(getByTestId('new-chapter-input'), NEW_CHAPTER_TITLE);
    await user.click(getByTestId('add-chapter-button'));
    
    // Verify API call
    await waitFor(() => {
      expect(createChapter).toHaveBeenCalledWith(TEST_PROJECT_ID, { title: NEW_CHAPTER_TITLE });
    });
  });
  
  // Test 4: Rebuilding index
  it('allows rebuilding the project index', async () => {
    const user = userEvent.setup();
    const { getByTestId } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for initial data load
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Mock successful index rebuild
    rebuildProjectIndex.mockResolvedValueOnce({
      data: {
        success: true,
        message: 'Index rebuilt successfully'
      }
    });
    
    // Click rebuild index button
    await user.click(getByTestId('rebuild-index-button'));
    
    // Verify API call
    await waitFor(() => {
      expect(rebuildProjectIndex).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Success message should appear
    await waitFor(() => {
      expect(getByTestId('rebuild-success')).toBeInTheDocument();
    });
  });
  
  // More tests can be added here to test other features...
});
