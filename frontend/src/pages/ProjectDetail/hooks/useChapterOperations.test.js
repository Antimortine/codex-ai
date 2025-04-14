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
import { useChapterOperations } from './useChapterOperations';
import { 
  listChapters, 
  createChapter, 
  updateChapter, 
  deleteChapter, 
  splitChapterIntoScenes, 
  compileChapterContent 
} from '../../../api/codexApi';
import { saveAs } from 'file-saver';
import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';

// Mock the API module and file-saver
vi.mock('../../../api/codexApi', () => ({
  listChapters: vi.fn(),
  createChapter: vi.fn(),
  updateChapter: vi.fn(),
  deleteChapter: vi.fn(),
  splitChapterIntoScenes: vi.fn(),
  compileChapterContent: vi.fn()
}));

vi.mock('file-saver', () => ({
  saveAs: vi.fn()
}));

describe('useChapterOperations Hook', () => {
  const mockProjectId = 'test-project-id';
  const mockChapters = [
    { id: 'chapter-1', project_id: mockProjectId, title: 'Chapter 1', order: 1 },
    { id: 'chapter-2', project_id: mockProjectId, title: 'Chapter 2', order: 2 }
  ];

  // Original window.confirm
  const originalConfirm = window.confirm;

  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    
    // Set default successful responses
    listChapters.mockResolvedValue({ data: { chapters: mockChapters } });
    createChapter.mockResolvedValue({ 
      data: { id: 'chapter-3', project_id: mockProjectId, title: 'Chapter 3', order: 3 } 
    });
    updateChapter.mockResolvedValue({
      data: { id: 'chapter-1', project_id: mockProjectId, title: 'Updated Chapter 1', order: 1 }
    });
    deleteChapter.mockResolvedValue({ success: true });
    splitChapterIntoScenes.mockResolvedValue({
      data: { 
        proposed_scenes: [
          { title: 'Scene 1', content: 'Scene 1 content' },
          { title: 'Scene 2', content: 'Scene 2 content' }
        ]
      }
    });
    compileChapterContent.mockResolvedValue({
      data: { content: 'Compiled content', filename: 'chapter-1.md' }
    });
    
    // Mock window.confirm to return true by default
    window.confirm = vi.fn().mockReturnValue(true);
  });

  afterEach(() => {
    // Restore original window.confirm
    window.confirm = originalConfirm;
  });

  describe('Initial Load', () => {
    test('should fetch chapters and update state on successful load', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));

      // Initial state should show loading
      expect(result.current.isLoadingChapters).toBe(true);
      expect(result.current.chapters).toEqual([]);
      expect(result.current.error).toBe(null);
      
      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Verify state after successful load
      expect(result.current.chapters).toEqual(mockChapters);
      expect(result.current.error).toBe(null);
      expect(listChapters).toHaveBeenCalledWith(mockProjectId);
    });

    test('should handle error when chapter fetch fails', async () => {
      const mockError = new Error('Failed to fetch chapters');
      listChapters.mockRejectedValue(mockError);

      const { result } = renderHook(() => useChapterOperations(mockProjectId));

      // Initial state should show loading
      expect(result.current.isLoadingChapters).toBe(true);
      
      // Wait for error to be processed
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.chapters).toEqual([]);
      expect(result.current.error).toBe(mockError.message);
      expect(listChapters).toHaveBeenCalledWith(mockProjectId);
    });
  });

  describe('Chapter Creation', () => {
    test('should handle creating a new chapter successfully', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Set a new chapter title
      act(() => {
        result.current.setNewChapterTitle('Chapter 3');
      });
      
      // Submit the new chapter
      act(() => {
        result.current.handleCreateChapter();
      });
      
      // Should show loading state
      expect(result.current.isCreatingChapter).toBe(true);
      
      // Wait for creation to complete
      await waitFor(() => {
        expect(result.current.isCreatingChapter).toBe(false);
      }, { timeout: 5000 });
      
      // Verify creation success
      const newChapter = { id: 'chapter-3', project_id: mockProjectId, title: 'Chapter 3', order: 3 };
      
      // Check if the new chapter is in the updated list (sorted by order)
      expect(result.current.chapters).toContainEqual(newChapter);
      expect(result.current.newChapterTitle).toBe('');
      expect(result.current.error).toBe(null);
      expect(createChapter).toHaveBeenCalledWith(mockProjectId, { title: 'Chapter 3', order: 3 });
    });

    test('should not create chapter if title is empty', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Set an empty title
      act(() => {
        result.current.setNewChapterTitle('  ');
      });
      
      // Attempt to create with empty title
      act(() => {
        result.current.handleCreateChapter();
      });
      
      // Verify API was not called
      expect(createChapter).not.toHaveBeenCalled();
      expect(result.current.chapters).toEqual(mockChapters);
    });

    test('should handle error when creating chapter fails', async () => {
      const mockError = new Error('Failed to create chapter');
      createChapter.mockRejectedValue(mockError);

      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Set a new chapter title
      act(() => {
        result.current.setNewChapterTitle('Chapter 3');
      });
      
      // Submit the new chapter
      act(() => {
        result.current.handleCreateChapter();
      });
      
      // Should show loading state
      expect(result.current.isCreatingChapter).toBe(true);
      
      // Wait for creation attempt to complete
      await waitFor(() => {
        expect(result.current.isCreatingChapter).toBe(false);
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.chapters).toEqual(mockChapters); // No change in chapter list
      expect(result.current.error).toBe(mockError.message);
      expect(createChapter).toHaveBeenCalled();
    });
  });

  describe('Chapter Editing', () => {
    test('should handle entering and exiting edit mode correctly', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Enter edit mode for the first chapter
      act(() => {
        result.current.handleEditChapterClick(mockChapters[0]);
      });
      
      // Verify edit mode state
      expect(result.current.editingChapterId).toBe(mockChapters[0].id);
      expect(result.current.editedChapterTitle).toBe(mockChapters[0].title);
      
      // Change the chapter title
      act(() => {
        result.current.setEditedChapterTitle('Updated Chapter 1');
      });
      
      // Verify title change
      expect(result.current.editedChapterTitle).toBe('Updated Chapter 1');
      
      // Cancel edit
      act(() => {
        result.current.handleCancelChapterEdit();
      });
      
      // Verify state after cancel
      expect(result.current.editingChapterId).toBe(null);
      expect(result.current.editedChapterTitle).toBe('');
    });

    test('should save chapter title successfully', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Enter edit mode for the first chapter
      act(() => {
        result.current.handleEditChapterClick(mockChapters[0]);
      });
      
      // Change the chapter title
      act(() => {
        result.current.setEditedChapterTitle('Updated Chapter 1');
      });
      
      // Save the chapter title
      act(() => {
        result.current.handleSaveChapterTitle();
      });
      
      // Should show saving state
      expect(result.current.isSavingChapter).toBe(true);
      
      // Wait for save to complete
      await waitFor(() => {
        expect(result.current.isSavingChapter).toBe(false);
      }, { timeout: 5000 });
      
      // Verify chapter was updated
      const updatedChapter = { id: 'chapter-1', project_id: mockProjectId, title: 'Updated Chapter 1', order: 1 };
      expect(result.current.chapters.find(c => c.id === 'chapter-1').title).toBe('Updated Chapter 1');
      expect(result.current.editingChapterId).toBe(null);
      expect(result.current.editedChapterTitle).toBe('');
      expect(updateChapter).toHaveBeenCalledWith(mockProjectId, 'chapter-1', { title: 'Updated Chapter 1', order: 1 });
    });

    test('should handle error when saving chapter title fails', async () => {
      const mockError = new Error('Failed to update chapter');
      updateChapter.mockRejectedValue(mockError);

      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Enter edit mode for the first chapter
      act(() => {
        result.current.handleEditChapterClick(mockChapters[0]);
      });
      
      // Change the chapter title
      act(() => {
        result.current.setEditedChapterTitle('Updated Chapter 1');
      });
      
      // Save the chapter title
      act(() => {
        result.current.handleSaveChapterTitle();
      });
      
      // Should show saving state
      expect(result.current.isSavingChapter).toBe(true);
      
      // Wait for save attempt to complete
      await waitFor(() => {
        expect(result.current.isSavingChapter).toBe(false);
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.chapterErrors[mockChapters[0].id]).toBe(mockError.message);
      expect(result.current.editingChapterId).toBe(mockChapters[0].id); // Should remain in edit mode
      expect(updateChapter).toHaveBeenCalledWith(mockProjectId, 'chapter-1', { title: 'Updated Chapter 1', order: 1 });
    });
  });

  describe('Chapter Deletion', () => {
    test('should handle deleting a chapter successfully', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Chapter to delete
      const chapterIdToDelete = 'chapter-1';
      const chapterTitleToDelete = 'Chapter 1';
      
      // Delete chapter
      act(() => {
        result.current.handleDeleteChapter(chapterIdToDelete, chapterTitleToDelete);
      });
      
      // Wait for deletion to complete
      await waitFor(() => {
        expect(result.current.chapters).toHaveLength(1);
      }, { timeout: 5000 });
      
      // Verify chapter was removed from list
      expect(result.current.chapters.find(c => c.id === chapterIdToDelete)).toBe(undefined);
      expect(result.current.chapterErrors[chapterIdToDelete]).toBe(undefined);
      expect(deleteChapter).toHaveBeenCalledWith(mockProjectId, chapterIdToDelete);
      expect(window.confirm).toHaveBeenCalled();
    });

    test('should not delete chapter if confirmation is cancelled', async () => {
      // Mock the confirmation dialog to return false
      window.confirm = vi.fn().mockReturnValue(false);

      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Chapter to delete
      const chapterIdToDelete = 'chapter-1';
      const chapterTitleToDelete = 'Chapter 1';
      
      // Attempt to delete chapter
      act(() => {
        result.current.handleDeleteChapter(chapterIdToDelete, chapterTitleToDelete);
      });
      
      // Verify the API was not called
      expect(deleteChapter).not.toHaveBeenCalled();
      expect(result.current.chapters).toEqual(mockChapters); // List should remain unchanged
      expect(window.confirm).toHaveBeenCalled();
    });

    test('should handle error when deleting chapter fails', async () => {
      const mockError = new Error('Failed to delete chapter');
      deleteChapter.mockRejectedValue(mockError);

      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Chapter to delete
      const chapterIdToDelete = 'chapter-1';
      const chapterTitleToDelete = 'Chapter 1';
      
      // Delete chapter
      act(() => {
        result.current.handleDeleteChapter(chapterIdToDelete, chapterTitleToDelete);
      });
      
      // Wait for rejection to be processed
      await waitFor(() => {
        expect(result.current.chapterErrors[chapterIdToDelete]).toBeTruthy();
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.chapters).toEqual(mockChapters); // List should remain unchanged
      expect(result.current.chapterErrors[chapterIdToDelete]).toBe(mockError.message);
      expect(deleteChapter).toHaveBeenCalledWith(mockProjectId, chapterIdToDelete);
      expect(window.confirm).toHaveBeenCalled();
    });
  });

  describe('Chapter Splitting', () => {
    test('should handle opening and closing the split modal', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Open split modal for the first chapter
      act(() => {
        result.current.handleOpenSplitModal(mockChapters[0].id);
      });
      
      // Verify modal state
      expect(result.current.showSplitModal).toBe(true);
      expect(result.current.chapterIdForSplits).toBe(mockChapters[0].id);
      expect(result.current.proposedSplits).toEqual([]);
      
      // Close split modal
      act(() => {
        result.current.handleCloseSplitModal();
      });
      
      // Verify modal closed
      expect(result.current.showSplitModal).toBe(false);
      expect(result.current.chapterIdForSplits).toBe(null);
    });

    test('should handle split input changes', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Set a chapter for splitting
      const chapterId = mockChapters[0].id;
      const splitContent = 'Split this content into scenes';
      
      // Open split modal and set content
      act(() => {
        result.current.handleOpenSplitModal(chapterId);
        result.current.handleSplitInputChange(chapterId, splitContent);
      });
      
      // Verify content was set
      expect(result.current.splitInputContent[chapterId]).toBe(splitContent);
    });

    test('should handle splitting a chapter successfully', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Set up chapter for splitting
      const chapterId = mockChapters[0].id;
      const splitContent = 'Split this content into scenes';
      
      // Open split modal and set content
      act(() => {
        result.current.handleOpenSplitModal(chapterId);
        result.current.handleSplitInputChange(chapterId, splitContent);
      });
      
      // Trigger split
      act(() => {
        result.current.handleSplitChapter();
      });
      
      // Should show splitting state
      expect(result.current.isSplittingChapter).toBe(true);
      expect(result.current.splittingChapterId).toBe(chapterId);
      
      // Wait for splitting to complete
      await waitFor(() => {
        expect(result.current.isSplittingChapter).toBe(false);
      }, { timeout: 5000 });
      
      // Verify proposed splits
      expect(result.current.proposedSplits).toEqual([
        { title: 'Scene 1', content: 'Scene 1 content' },
        { title: 'Scene 2', content: 'Scene 2 content' }
      ]);
      expect(splitChapterIntoScenes).toHaveBeenCalledWith(
        mockProjectId, 
        chapterId, 
        { chapter_content: splitContent }
      );
    });

    test('should handle error when splitting chapter fails', async () => {
      const mockError = new Error('Failed to split chapter');
      splitChapterIntoScenes.mockRejectedValue(mockError);
      
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Set up chapter for splitting
      const chapterId = mockChapters[0].id;
      const splitContent = 'Split this content into scenes';
      const errorKey = `split_${chapterId}`;
      
      // Open split modal and set content
      act(() => {
        result.current.handleOpenSplitModal(chapterId);
        result.current.handleSplitInputChange(chapterId, splitContent);
      });
      
      // Trigger split
      act(() => {
        result.current.handleSplitChapter();
      });
      
      // Wait for error to be processed
      await waitFor(() => {
        expect(result.current.chapterErrors[errorKey]).toBeTruthy();
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.proposedSplits).toEqual([]);
      expect(result.current.chapterErrors[errorKey]).toBe(mockError.message);
    });
  });

  describe('Chapter Compilation', () => {
    test('should handle compiling a chapter successfully', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Chapter to compile
      const chapterId = mockChapters[0].id;
      
      // Compile chapter
      act(() => {
        result.current.handleCompileChapter(chapterId);
      });
      
      // Should show compiling state
      expect(result.current.isCompilingChapter).toBe(true);
      expect(result.current.compilingChapterId).toBe(chapterId);
      
      // Wait for compilation to complete
      await waitFor(() => {
        expect(result.current.isCompilingChapter).toBe(false);
      }, { timeout: 5000 });
      
      // Verify compilation
      expect(result.current.compiledContent).toBe('Compiled content');
      expect(result.current.compiledFileName).toBe('chapter-1.md');
      expect(compileChapterContent).toHaveBeenCalledWith(
        mockProjectId, 
        chapterId,
        { include_titles: true, separator: '\n\n' }
      );
      expect(saveAs).toHaveBeenCalled();
    });

    test('should handle error when compiling chapter fails', async () => {
      const mockError = new Error('Failed to compile chapter');
      compileChapterContent.mockRejectedValue(mockError);
      
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Chapter to compile
      const chapterId = mockChapters[0].id;
      const errorKey = `compile_${chapterId}`;
      
      // Compile chapter
      act(() => {
        result.current.handleCompileChapter(chapterId);
      });
      
      // Wait for error to be processed
      await waitFor(() => {
        expect(result.current.chapterErrors[errorKey]).toBeTruthy();
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.chapterErrors[errorKey]).toBe(mockError.message);
      expect(saveAs).not.toHaveBeenCalled();
    });

    test('should initialize modal state correctly', async () => {
      const { result } = renderHook(() => useChapterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingChapters).toBe(false);
      }, { timeout: 5000 });
      
      // Verify initial modal state
      expect(result.current.showCompiledContentModal).toBe(false);
      expect(result.current.compiledContent).toBe('');
      expect(result.current.compiledFileName).toBe('');
      expect(result.current.compilingChapterId).toBe(null);
      
      // The handleCloseCompileModal function should exist
      expect(typeof result.current.handleCloseCompileModal).toBe('function');
    });
  });
});
