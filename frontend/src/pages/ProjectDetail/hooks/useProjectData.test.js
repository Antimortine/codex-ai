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
import { useProjectData } from './useProjectData';
import { getProject, updateProject, rebuildProjectIndex } from '../../../api/codexApi';
import { vi, describe, test, expect, beforeEach, afterAll } from 'vitest';

// Mock the API module
vi.mock('../../../api/codexApi', () => ({
  getProject: vi.fn(),
  updateProject: vi.fn(),
  rebuildProjectIndex: vi.fn()
}));

// Define tests for useProjectData hook
describe('useProjectData Hook', () => {
  const mockProjectId = 'test-project-id';
  const mockProject = {
    id: mockProjectId,
    name: 'Test Project',
    path: '/path/to/project',
    created_at: '2025-01-01T00:00:00Z'
  };

  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    
    // Set default successful responses
    getProject.mockResolvedValue({ data: mockProject });
    updateProject.mockResolvedValue({ data: { ...mockProject, name: 'New Project Name' } });
    rebuildProjectIndex.mockResolvedValue({ success: true });
    
    // Reset mocked timers
    vi.useRealTimers();
  });

  // Reset the timers after all tests
  afterAll(() => {
    vi.useRealTimers();
  });

  describe('Initial Load', () => {
    test('should fetch project and update state on successful load', async () => {
      const { result } = renderHook(() => useProjectData(mockProjectId));

      // Initial state should show loading
      expect(result.current.isLoadingProject).toBe(true);
      expect(result.current.project).toBe(null);
      expect(result.current.error).toBe('');
      
      // After loading completes
      await waitFor(() => {
        expect(result.current.isLoadingProject).toBe(false);
      });
      
      // Verify state after successful load
      expect(result.current.project).toEqual(mockProject);
      expect(result.current.error).toBe('');
      expect(getProject).toHaveBeenCalledWith(mockProjectId);
    });

    test('should handle error when project fetch fails', async () => {
      const mockError = new Error('Failed to fetch project');
      getProject.mockRejectedValue(mockError);

      const { result } = renderHook(() => useProjectData(mockProjectId));

      // Initial state should show loading
      expect(result.current.isLoadingProject).toBe(true);
      expect(result.current.project).toBe(null);
      
      // After error occurs
      await waitFor(() => {
        expect(result.current.isLoadingProject).toBe(false);
      });
      
      // Verify state after error
      expect(result.current.project).toBe(null);
      expect(result.current.error).toBe(mockError.message);
      expect(getProject).toHaveBeenCalledWith(mockProjectId);
    });
  });

  describe('Project Name Editing', () => {
    test('should handle entering and canceling edit mode correctly', async () => {
      const { result } = renderHook(() => useProjectData(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingProject).toBe(false);
      });
      
      // Enter edit mode
      act(() => {
        result.current.handleEditNameClick();
      });
      
      // Verify edit mode state
      expect(result.current.isEditingName).toBe(true);
      expect(result.current.editedProjectName).toBe(mockProject.name);
      
      // Change the project name
      act(() => {
        result.current.setEditedProjectName('New Project Name');
      });
      
      // Verify name change
      expect(result.current.editedProjectName).toBe('New Project Name');
      
      // Cancel edit
      act(() => {
        result.current.handleCancelNameEdit();
      });
      
      // Verify state after cancel
      expect(result.current.isEditingName).toBe(false);
      expect(result.current.editedProjectName).toBe(mockProject.name);
      expect(result.current.saveNameError).toBe(null);
      expect(result.current.saveNameSuccess).toBe('');
    });
  });

  describe('Save Project Name', () => {
    test('should successfully save project name', async () => {
      // Skip using fake timers as they can cause issues with waitFor
      // vi.useFakeTimers();

      const { result } = renderHook(() => useProjectData(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingProject).toBe(false);
      });
      
      // Enter edit mode
      act(() => {
        result.current.handleEditNameClick();
      });
      
      // Change the project name
      act(() => {
        result.current.setEditedProjectName('New Project Name');
      });
      
      // Save the project name
      act(() => {
        result.current.handleSaveProjectName();
      });
      
      // Should initially be in saving state
      expect(result.current.isSavingName).toBe(true);
      
      // Wait for save to complete
      await waitFor(() => {
        expect(result.current.isSavingName).toBe(false);
      }, { timeout: 5000 });
      
      // Verify state after save
      expect(result.current.isEditingName).toBe(false);
      expect(result.current.saveNameSuccess).toBe('Project name updated successfully!');
      expect(result.current.saveNameError).toBe(null);
      expect(result.current.project.name).toBe('New Project Name');
      expect(updateProject).toHaveBeenCalledWith(mockProjectId, { name: 'New Project Name' });
      
      // Without advancing timers, the success message will still be set
      // Verify success message is set correctly
      expect(result.current.saveNameSuccess).toBe('Project name updated successfully!');
    });

    test('should handle error when saving project name fails', async () => {
      const mockError = new Error('Failed to update project name');
      updateProject.mockRejectedValue(mockError);

      const { result } = renderHook(() => useProjectData(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingProject).toBe(false);
      });
      
      // Enter edit mode
      act(() => {
        result.current.handleEditNameClick();
      });
      
      // Change the project name
      act(() => {
        result.current.setEditedProjectName('New Project Name');
      });
      
      // Save the project name
      act(() => {
        result.current.handleSaveProjectName();
      });
      
      // Should initially be in saving state
      expect(result.current.isSavingName).toBe(true);
      
      // Wait for save attempt to complete
      await waitFor(() => {
        expect(result.current.isSavingName).toBe(false);
      }, { timeout: 5000 });
      
      // Verify state after error
      expect(result.current.isEditingName).toBe(true); // Should remain in edit mode
      expect(result.current.saveNameSuccess).toBe('');
      expect(result.current.saveNameError).toBe(mockError.message);
      expect(updateProject).toHaveBeenCalledWith(mockProjectId, { name: 'New Project Name' });
    });

    test('should validate project name is not empty', async () => {
      const { result } = renderHook(() => useProjectData(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingProject).toBe(false);
      });
      
      // Enter edit mode
      act(() => {
        result.current.handleEditNameClick();
      });
      
      // Set empty project name
      act(() => {
        result.current.setEditedProjectName('  ');
      });
      
      // Try to save empty name
      act(() => {
        result.current.handleSaveProjectName();
      });
      
      // Should show validation error without calling API
      expect(result.current.saveNameError).toBe('Project name cannot be empty');
      expect(updateProject).not.toHaveBeenCalled();
    });
  });

  describe('Rebuild Project Index', () => {
    test('should rebuild project index successfully', async () => {
      // Skip using fake timers as they can cause issues with waitFor
      // vi.useFakeTimers();

      const { result } = renderHook(() => useProjectData(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingProject).toBe(false);
      });
      
      // Trigger index rebuild
      act(() => {
        result.current.handleRebuildIndex();
      });
      
      // Should initially be in rebuilding state
      expect(result.current.isRebuildingIndex).toBe(true);
      
      // Wait for rebuild to complete
      await waitFor(() => {
        expect(result.current.isRebuildingIndex).toBe(false);
      }, { timeout: 5000 });
      
      // Verify successful rebuild
      expect(result.current.rebuildSuccessMessage).toBe('Project index rebuilt successfully!');
      expect(result.current.rebuildError).toBe(null);
      expect(rebuildProjectIndex).toHaveBeenCalledWith(mockProjectId);
      
      // Without advancing timers, the success message will still be set
      // Verify success message is set correctly
      expect(result.current.rebuildSuccessMessage).toBe('Project index rebuilt successfully!');
    });

    test('should handle error when rebuilding project index fails', async () => {
      const mockError = new Error('Failed to rebuild index');
      rebuildProjectIndex.mockRejectedValue(mockError);

      const { result } = renderHook(() => useProjectData(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingProject).toBe(false);
      });
      
      // Trigger index rebuild
      act(() => {
        result.current.handleRebuildIndex();
      });
      
      // Should initially be in rebuilding state
      expect(result.current.isRebuildingIndex).toBe(true);
      
      // Wait for rebuild attempt to complete
      await waitFor(() => {
        expect(result.current.isRebuildingIndex).toBe(false);
      });
      
      // Verify error state
      expect(result.current.rebuildSuccessMessage).toBe('');
      expect(result.current.rebuildError).toBe(mockError.message);
      expect(rebuildProjectIndex).toHaveBeenCalledWith(mockProjectId);
    });
  });
});
