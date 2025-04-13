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
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';
import ProjectDetailPage from './ProjectDetailPage';
import {
  renderWithRouter,
  flushPromises,
  TEST_PROJECT_ID,
  TEST_PROJECT_NAME
} from './ProjectDetailPage.test.utils';

// Mock API calls used by ProjectDetailPage
vi.mock('../api/codexApi', async () => {
  return {
    getProject: vi.fn(),
    listChapters: vi.fn(),
    listCharacters: vi.fn(),
    listScenes: vi.fn(),
    deleteChapter: vi.fn(),
    deleteCharacter: vi.fn(),
    updateProject: vi.fn(),
    createChapter: vi.fn(),
    createCharacter: vi.fn(),
    rebuildProjectIndex: vi.fn(),
    compileChapterContent: vi.fn(),
  };
});

// Import the mocked API functions
import { getProject, listChapters, listCharacters, listScenes } from '../api/codexApi';

describe('ProjectDetailPage Basic Tests', () => {
  // Set up and tear down
  beforeEach(() => {
    vi.resetAllMocks();
    
    // Setup basic mocks for most tests
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
  
    // Mock window.confirm (used in delete operations)
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // --- Basic Rendering Tests ---
  it('renders loading state initially', () => {
    const { container } = renderWithRouter(<ProjectDetailPage />);
    expect(container.textContent.toLowerCase()).toContain('loading');
  });

  it('renders project details after successful fetch', async () => {
    // Render with our router helper
    const { container } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for the data to load
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Debug rendered content
    await act(async () => { await flushPromises(); });
    
    // Verify project name is shown in the rendered output
    expect(container.textContent).toContain(TEST_PROJECT_NAME);
    
    // Verify project ID is shown
    expect(container.textContent).toContain(TEST_PROJECT_ID);
  });

  it('renders error state if fetching project details fails', async () => {
    // Setup error scenario
    const errorMsg = "Failed to fetch project";
    getProject.mockRejectedValue(new Error(errorMsg));
    
    // Render with our router helper
    const { container } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for data fetch to complete
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Debug the error state rendering
    await act(async () => { await flushPromises(); });
    
    // Check for error message in the UI (using a flexible approach)
    const hasErrorMessage = container.textContent.toLowerCase().includes('error') || 
                           container.textContent.toLowerCase().includes('failed') ||
                           container.textContent.includes(errorMsg);
    
    expect(hasErrorMessage).toBe(true);
  });

  it('renders a link to the project query page', async () => {
    // Render with our router helper
    const { container } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for initial data load
    await waitFor(() => {
      expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Debug rendered content 
    await act(async () => { await flushPromises(); });
    
    // Look for the query link with flexible matching by directly inspecting the DOM
    await waitFor(() => {
      const hasQueryLink = container.innerHTML.includes(`/projects/${TEST_PROJECT_ID}/query`);
      expect(hasQueryLink).toBe(true);
    });
    
    // Debug all links found in the container
    const links = container.querySelectorAll('a');
    
    // Verify at least one link contains the correct href
    let foundQueryLink = false;
    for (const link of links) {
      if (link.getAttribute('href') === `/projects/${TEST_PROJECT_ID}/query`) {
        foundQueryLink = true;
        break;
      }
    }
    
    // Assert that we found at least one link with the correct href
    expect(foundQueryLink).toBe(true);
  });
  
  it('renders list of chapters using ChapterSection component', async () => {
    // Setup mock data for chapters
    const mockChapters = [
      { id: 'ch-1', title: 'Chapter 1', order: 1 },
      { id: 'ch-2', title: 'Chapter 2', order: 2 }
    ];
    
    // Configure API mocks
    listChapters.mockResolvedValue({ data: { chapters: mockChapters } });
    
    // Render with our router helper
    const { container } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for data load
    await waitFor(() => {
      expect(listChapters).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Debug rendered content
    await act(async () => { await flushPromises(); });
    
    // Check for chapter titles in a flexible way
    const hasChapter1 = container.textContent.includes('Chapter 1');
    const hasChapter2 = container.textContent.includes('Chapter 2');
    
    // At least one of the chapters should be found
    expect(hasChapter1 || hasChapter2).toBe(true);
  });
  
  it('renders character list when API returns data', async () => {
    // Setup mock data for characters
    const mockCharacters = [
      { id: 'char-1', name: 'Character 1', description: 'Description 1' },
      { id: 'char-2', name: 'Character 2', description: 'Description 2' }
    ];
    
    // Configure API mocks
    listCharacters.mockResolvedValue({ data: { characters: mockCharacters } });
    
    // Render with our router helper
    const { container } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for data load
    await waitFor(() => {
      expect(listCharacters).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Debug rendered content
    await act(async () => { await flushPromises(); });
    
    // Check for character names in a flexible way
    const hasCharacter1 = container.textContent.includes('Character 1');
    const hasCharacter2 = container.textContent.includes('Character 2');
    
    // At least one of the characters should be found
    expect(hasCharacter1 || hasCharacter2).toBe(true);
  });
  
  it('renders scenes within their respective chapters', async () => {
    // Setup mock data with chapters and scenes
    const mockChapters = [
      { 
        id: 'ch-1', 
        title: 'Chapter with Scenes', 
        order: 1, 
        scenes: [
          { id: 'scene-1', title: 'Scene 1', content: 'Content 1' },
          { id: 'scene-2', title: 'Scene 2', content: 'Content 2' }
        ] 
      }
    ];
    
    // Mock scene data that will be fetched for each chapter
    const mockScenes = [
      { id: 'scene-1', title: 'Scene 1', content: 'Content 1', chapterId: 'ch-1' },
      { id: 'scene-2', title: 'Scene 2', content: 'Content 2', chapterId: 'ch-1' }
    ];
    
    // Configure API mocks
    listChapters.mockResolvedValue({ data: { chapters: mockChapters } });
    
    // Mock the listScenes function which is called for each chapter
    listScenes.mockResolvedValue({ data: { scenes: mockScenes } });
    
    // Render with our router helper
    const { container } = renderWithRouter(<ProjectDetailPage />);
    
    // Wait for data load
    await waitFor(() => {
      expect(listChapters).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });
    
    // Debug rendered content
    await act(async () => { await flushPromises(); });
    
    // Check for scenes in a flexible way - they should be rendered within their chapters
    const hasScene1 = container.textContent.includes('Scene 1');
    const hasScene2 = container.textContent.includes('Scene 2');
    
    // Log the current state for debugging
    console.log('Scene content found in test:', { hasScene1, hasScene2, content: container.textContent });
    
    // At least one of the scenes should be found
    expect(hasScene1 || hasScene2).toBe(true);
  });
});
