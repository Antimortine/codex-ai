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
import { useCharacterOperations } from './useCharacterOperations';
import { listCharacters, createCharacter, deleteCharacter } from '../../../api/codexApi';
import { vi, describe, test, expect, beforeEach, afterEach } from 'vitest';

// Mock the API module
vi.mock('../../../api/codexApi', () => ({
  listCharacters: vi.fn(),
  createCharacter: vi.fn(),
  deleteCharacter: vi.fn()
}));

describe('useCharacterOperations Hook', () => {
  const mockProjectId = 'test-project-id';
  const mockCharacters = [
    { id: 'char-1', project_id: mockProjectId, name: 'Character 1' },
    { id: 'char-2', project_id: mockProjectId, name: 'Character 2' }
  ];

  // Mock window.confirm
  const originalConfirm = window.confirm;

  beforeEach(() => {
    // Clear all mocks before each test
    vi.clearAllMocks();
    
    // Set default successful responses
    listCharacters.mockResolvedValue({ data: { characters: mockCharacters } });
    createCharacter.mockResolvedValue({ 
      data: { id: 'char-3', project_id: mockProjectId, name: 'Character 3' } 
    });
    deleteCharacter.mockResolvedValue({ success: true });
    
    // Mock window.confirm to return true by default
    window.confirm = vi.fn().mockReturnValue(true);
  });

  afterEach(() => {
    // Restore original window.confirm
    window.confirm = originalConfirm;
  });

  describe('Initial Load', () => {
    test('should fetch characters and update state on successful load', async () => {
      const { result } = renderHook(() => useCharacterOperations(mockProjectId));

      // Initial state should show loading
      expect(result.current.isLoadingCharacters).toBe(true);
      expect(result.current.characters).toEqual([]);
      expect(result.current.characterError).toBe(null);
      
      // Wait for loading to complete
      await waitFor(() => {
        expect(result.current.isLoadingCharacters).toBe(false);
      }, { timeout: 5000 });
      
      // Verify state after successful load
      expect(result.current.characters).toEqual(mockCharacters);
      expect(result.current.characterError).toBe(null);
      expect(listCharacters).toHaveBeenCalledWith(mockProjectId);
    });

    test('should handle error when character fetch fails', async () => {
      const mockError = new Error('Failed to fetch characters');
      listCharacters.mockRejectedValue(mockError);

      const { result } = renderHook(() => useCharacterOperations(mockProjectId));

      // Initial state should show loading
      expect(result.current.isLoadingCharacters).toBe(true);
      
      // Wait for error to be processed
      await waitFor(() => {
        expect(result.current.isLoadingCharacters).toBe(false);
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.characters).toEqual([]);
      expect(result.current.characterError).toBe(mockError.message);
      expect(listCharacters).toHaveBeenCalledWith(mockProjectId);
    });
  });

  describe('Character Creation', () => {
    test('should handle creating a new character successfully', async () => {
      const { result } = renderHook(() => useCharacterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingCharacters).toBe(false);
      }, { timeout: 5000 });
      
      // Set a new character name
      act(() => {
        result.current.setNewCharacterName('Character 3');
      });
      
      // Submit the new character
      act(() => {
        result.current.handleCreateCharacter();
      });
      
      // Should show loading state
      expect(result.current.isCreatingCharacter).toBe(true);
      
      // Wait for creation to complete
      await waitFor(() => {
        expect(result.current.isCreatingCharacter).toBe(false);
      }, { timeout: 5000 });
      
      // Verify creation success
      const newCharacter = { id: 'char-3', project_id: mockProjectId, name: 'Character 3' };
      
      // Check if the new character is in the updated list
      expect(result.current.characters).toContainEqual(newCharacter);
      expect(result.current.newCharacterName).toBe('');
      expect(result.current.characterError).toBe(null);
      expect(createCharacter).toHaveBeenCalledWith(mockProjectId, { name: 'Character 3' });
    });

    test('should not create character if name is empty', async () => {
      const { result } = renderHook(() => useCharacterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingCharacters).toBe(false);
      }, { timeout: 5000 });
      
      // Set an empty name
      act(() => {
        result.current.setNewCharacterName('  ');
      });
      
      // Attempt to create with empty name
      act(() => {
        result.current.handleCreateCharacter();
      });
      
      // Verify API was not called
      expect(createCharacter).not.toHaveBeenCalled();
      expect(result.current.characters).toEqual(mockCharacters);
    });

    test('should handle error when creating character fails', async () => {
      const mockError = new Error('Failed to create character');
      createCharacter.mockRejectedValue(mockError);

      const { result } = renderHook(() => useCharacterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingCharacters).toBe(false);
      }, { timeout: 5000 });
      
      // Set a new character name
      act(() => {
        result.current.setNewCharacterName('Character 3');
      });
      
      // Submit the new character
      act(() => {
        result.current.handleCreateCharacter();
      });
      
      // Should show loading state
      expect(result.current.isCreatingCharacter).toBe(true);
      
      // Wait for creation attempt to complete
      await waitFor(() => {
        expect(result.current.isCreatingCharacter).toBe(false);
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.characters).toEqual(mockCharacters); // No change in character list
      expect(result.current.characterError).toBe(mockError.message);
      expect(createCharacter).toHaveBeenCalledWith(mockProjectId, { name: 'Character 3' });
    });
  });

  describe('Character Deletion', () => {
    test('should handle deleting a character successfully', async () => {
      const { result } = renderHook(() => useCharacterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingCharacters).toBe(false);
      }, { timeout: 5000 });
      
      // Character to delete
      const characterIdToDelete = 'char-1';
      
      // Delete character
      act(() => {
        result.current.handleDeleteCharacter(characterIdToDelete);
      });
      
      // Should show deleting state
      expect(result.current.isDeletingCharacter).toBe(characterIdToDelete);
      
      // Wait for deletion to complete
      await waitFor(() => {
        expect(result.current.isDeletingCharacter).toBe(null);
      }, { timeout: 5000 });
      
      // Verify character was removed from list
      expect(result.current.characters).toHaveLength(1);
      expect(result.current.characters.find(c => c.id === characterIdToDelete)).toBe(undefined);
      expect(result.current.characterError).toBe(null);
      expect(deleteCharacter).toHaveBeenCalledWith(mockProjectId, characterIdToDelete);
      expect(window.confirm).toHaveBeenCalled();
    });

    test('should not delete character if confirmation is cancelled', async () => {
      // Mock the confirmation dialog to return false
      window.confirm = vi.fn().mockReturnValue(false);

      const { result } = renderHook(() => useCharacterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingCharacters).toBe(false);
      }, { timeout: 5000 });
      
      // Character to delete
      const characterIdToDelete = 'char-1';
      
      // Attempt to delete character
      act(() => {
        result.current.handleDeleteCharacter(characterIdToDelete);
      });
      
      // Verify the API was not called
      expect(deleteCharacter).not.toHaveBeenCalled();
      expect(result.current.characters).toEqual(mockCharacters); // List should remain unchanged
      expect(window.confirm).toHaveBeenCalled();
    });

    test('should handle error when deleting character fails', async () => {
      const mockError = new Error('Failed to delete character');
      deleteCharacter.mockRejectedValue(mockError);

      const { result } = renderHook(() => useCharacterOperations(mockProjectId));
      
      // Wait for initial load
      await waitFor(() => {
        expect(result.current.isLoadingCharacters).toBe(false);
      }, { timeout: 5000 });
      
      // Character to delete
      const characterIdToDelete = 'char-1';
      
      // Delete character
      act(() => {
        result.current.handleDeleteCharacter(characterIdToDelete);
      });
      
      // Should show deleting state
      expect(result.current.isDeletingCharacter).toBe(characterIdToDelete);
      
      // Wait for deletion attempt to complete
      await waitFor(() => {
        expect(result.current.isDeletingCharacter).toBe(null);
      }, { timeout: 5000 });
      
      // Verify error state
      expect(result.current.characters).toEqual(mockCharacters); // List should remain unchanged
      expect(result.current.characterError).toBe(mockError.message);
      expect(deleteCharacter).toHaveBeenCalledWith(mockProjectId, characterIdToDelete);
      expect(window.confirm).toHaveBeenCalled();
    });
  });
});
