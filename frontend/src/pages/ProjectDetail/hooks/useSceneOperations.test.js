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

import { renderHook, waitFor, act } from '@testing-library/react';
import { useSceneOperations } from './useSceneOperations';
import { 
  listScenes, 
  createScene, 
  deleteScene, 
  generateSceneDraft 
} from '../../../api/codexApi';
import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';

// Mock react-router-dom
vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn()
}));

// Mock the API module
vi.mock('../../../api/codexApi', () => ({
  listScenes: vi.fn(),
  createScene: vi.fn(),
  deleteScene: vi.fn(),
  generateSceneDraft: vi.fn()
}));

describe('useSceneOperations Hook', () => {
  const mockProjectId = 'test-project-id';
  const mockChapters = [
    { id: 'chapter-1', project_id: mockProjectId, title: 'Chapter 1', order: 1 },
    { id: 'chapter-2', project_id: mockProjectId, title: 'Chapter 2', order: 2 }
  ];
  const mockScenesMap = {
    'chapter-1': [
      { id: 'scene-1', chapter_id: 'chapter-1', title: 'Scene 1', content: 'Scene 1 content', order: 1 },
      { id: 'scene-2', chapter_id: 'chapter-1', title: 'Scene 2', content: 'Scene 2 content', order: 2 }
    ],
    'chapter-2': [
      { id: 'scene-3', chapter_id: 'chapter-2', title: 'Scene 3', content: 'Scene 3 content', order: 1 }
    ]
  };

  // Original window.confirm
  const originalConfirm = window.confirm;

  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    
    // Set default successful responses
    listScenes.mockImplementation((projectId, chapterId) => {
      return Promise.resolve({ 
        data: { 
          scenes: mockScenesMap[chapterId] || [] 
        } 
      });
    });
    
    createScene.mockResolvedValue({ 
      data: { id: 'new-scene-id', chapter_id: 'chapter-1', title: 'New Scene', content: 'New scene content', order: 3 } 
    });
    
    deleteScene.mockResolvedValue({ success: true });
    
    generateSceneDraft.mockResolvedValue({
      data: { 
        title: 'Generated Scene',
        content: 'Generated scene content' 
      }
    });
    
    // Mock window.confirm to return true by default
    window.confirm = vi.fn().mockReturnValue(true);
  });

  afterEach(() => {
    // Restore original window.confirm
    window.confirm = originalConfirm;
  });

  describe('Initial Load', () => {
    test('should fetch scenes for chapters on init', async () => {
      const { result } = renderHook(() => useSceneOperations(mockProjectId, mockChapters));
      
      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.isLoadingScenes['chapter-1']).toBe(false);
        expect(result.current.isLoadingScenes['chapter-2']).toBe(false);
      }, { timeout: 5000 });
      
      // Verify API calls and state
      expect(listScenes).toHaveBeenCalledTimes(mockChapters.length);
      expect(listScenes).toHaveBeenCalledWith(mockProjectId, 'chapter-1');
      expect(listScenes).toHaveBeenCalledWith(mockProjectId, 'chapter-2');
      expect(result.current.scenes['chapter-1']).toEqual(mockScenesMap['chapter-1']);
    });

    test('should handle API errors when loading scenes', async () => {
      const mockError = new Error('Failed to load scenes');
      listScenes.mockRejectedValueOnce(mockError);
      
      const { result } = renderHook(() => useSceneOperations(mockProjectId, mockChapters));
      
      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.isLoadingScenes['chapter-1']).toBe(false);
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.sceneErrors['chapter-1']).toBeTruthy();
    });
  });

  describe('Scene Deletion', () => {
    test('should delete scene and update state', async () => {
      const { result } = renderHook(() => useSceneOperations(mockProjectId, mockChapters));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingScenes['chapter-1']).toBe(false);
      }, { timeout: 5000 });
      
      // Delete a scene
      await act(async () => {
        await result.current.handleDeleteScene('chapter-1', 'scene-1', 'Scene 1');
      });
      
      // Verify API call
      expect(deleteScene).toHaveBeenCalledWith(mockProjectId, 'chapter-1', 'scene-1');
      expect(window.confirm).toHaveBeenCalled();
      
      // Check scenes are updated (scene-1 should be removed)
      expect(result.current.scenes['chapter-1'].find(s => s.id === 'scene-1')).toBeUndefined();
    });

    test('should not delete scene if confirmation is cancelled', async () => {
      // Set confirm to return false
      window.confirm = vi.fn().mockReturnValue(false);
      
      const { result } = renderHook(() => useSceneOperations(mockProjectId, mockChapters));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingScenes['chapter-1']).toBe(false);
      }, { timeout: 5000 });
      
      // Try to delete a scene
      await act(async () => {
        await result.current.handleDeleteScene('chapter-1', 'scene-1', 'Scene 1');
      });
      
      // Verify API was NOT called
      expect(deleteScene).not.toHaveBeenCalled();
      expect(window.confirm).toHaveBeenCalled();
    });
  });

  describe('Scene Summary', () => {
    test('should update summary state', async () => {
      const { result } = renderHook(() => useSceneOperations(mockProjectId, mockChapters));
      
      // Set a summary
      act(() => {
        result.current.handleSummaryChange('chapter-1', 'Test summary');
      });
      
      // Verify state update
      expect(result.current.generationSummaries['chapter-1']).toBe('Test summary');
    });
  });

  describe('Scene Generation', () => {
    test('should call generateSceneDraft with correct parameters', async () => {
      const { result } = renderHook(() => useSceneOperations(mockProjectId, mockChapters));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingScenes['chapter-1']).toBe(false);
      }, { timeout: 5000 });
      
      // Set a summary
      act(() => {
        result.current.handleSummaryChange('chapter-1', 'Test summary');
      });
      
      // Generate scene draft
      await act(async () => {
        await result.current.handleGenerateSceneDraft('chapter-1');
      });
      
      // Verify API call
      expect(generateSceneDraft).toHaveBeenCalledWith(
        mockProjectId,
        'chapter-1',
        expect.objectContaining({
          prompt_summary: 'Test summary',
          previous_scene_order: 2 // Highest order from mock scenes
        })
      );
    });
  });

  describe('Direct API Testing', () => {
    test('should correctly mock createScene API', async () => {
      const newScene = {
        title: 'Test Scene',
        content: 'Test content',
        order: 3
      };
      
      // Call the API directly
      const result = await createScene(mockProjectId, 'chapter-1', newScene);
      
      // Verify result
      expect(result.data).toHaveProperty('id');
      expect(result.data.title).toBe('New Scene');
      expect(createScene).toHaveBeenCalledWith(mockProjectId, 'chapter-1', newScene);
    });
    
    test('should handle errors from createScene API', async () => {
      // Mock API to reject
      const mockError = new Error('API error');
      createScene.mockRejectedValueOnce(mockError);
      
      // Call and expect rejection
      await expect(createScene(mockProjectId, 'chapter-1', {})).rejects.toThrow('API error');
    });
  });
});
