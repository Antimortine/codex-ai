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

import { useState, useEffect, useCallback, useRef } from 'react';
import { listCharacters, createCharacter, deleteCharacter } from '../../../api/codexApi';

/**
 * Custom hook to manage character-related operations
 * 
 * @param {string} projectId - The ID of the project
 * @returns {Object} Character data and operations
 */
export function useCharacterOperations(projectId) {
    // Keep track of component mount status to prevent state updates after unmount
    const isMounted = useRef(true);
    // Character state
    const [characters, setCharacters] = useState([]);
    const [isLoadingCharacters, setIsLoadingCharacters] = useState(true);
    const [newCharacterName, setNewCharacterName] = useState('');
    const [characterError, setCharacterError] = useState(null);
    const [isCreatingCharacter, setIsCreatingCharacter] = useState(false);
    const [isDeletingCharacter, setIsDeletingCharacter] = useState(null);

    // Fetch characters when project ID changes
    useEffect(() => {
        // Set mounted flag
        isMounted.current = true;
        
        // Create an abort controller for cancelling fetch requests
        const abortController = new AbortController();
        
        const fetchCharacters = async () => {
            if (!projectId) return;
            
            // Store mounted state in local variable to avoid race conditions
            let isComponentMounted = isMounted.current;
            
            if (isComponentMounted) {
                setIsLoadingCharacters(true);
            }
            
            try {
                if (abortController.signal.aborted || !isComponentMounted) return;
                
                const response = await listCharacters(projectId);
                
                if (isComponentMounted && isMounted.current) {
                    const sortedCharacters = response.data.characters.sort((a, b) => a.name.localeCompare(b.name));
                    setCharacters(sortedCharacters);
                    setCharacterError(null);
                }
            } catch (err) {
                if (abortController.signal.aborted) return;
                
                console.error('Error loading characters:', err);
                
                if (isComponentMounted && isMounted.current) {
                    setCharacterError(err.message || 'Failed to load characters');
                }
            } finally {
                if (isComponentMounted && isMounted.current) {
                    setIsLoadingCharacters(false);
                }
            }
        };
        
        fetchCharacters();
        
        // Cleanup function - abort any pending requests and prevent state updates
        return () => {
            abortController.abort();
            isMounted.current = false;
        };
    }, [projectId]);

    // Handle creating a new character
    const handleCreateCharacter = useCallback(async () => {
        if (!newCharacterName.trim()) return;
        
        // Store mounted state in local variable to avoid race conditions
        let isComponentMounted = isMounted.current;
        
        if (isComponentMounted) {
            setIsCreatingCharacter(true);
            setCharacterError(null);
        }
        
        try {
            const response = await createCharacter(projectId, { name: newCharacterName });
            
            if (isComponentMounted && isMounted.current) {
                setCharacters(prev => {
                    const updated = [...prev, response.data];
                    return updated.sort((a, b) => a.name.localeCompare(b.name));
                });
                setNewCharacterName('');
            }
        } catch (err) {
            console.error('Error creating character:', err);
            
            if (isComponentMounted && isMounted.current) {
                setCharacterError(err.message || 'Failed to create character');
            }
        } finally {
            if (isComponentMounted && isMounted.current) {
                setIsCreatingCharacter(false);
            }
        }
    }, [projectId, newCharacterName]);

    // Handle deleting a character
    const handleDeleteCharacter = useCallback(async (characterId) => {
        if (!window.confirm('Are you sure you want to delete this character? This action cannot be undone.')) {
            return;
        }
        
        // Store mounted state in local variable to avoid race conditions
        let isComponentMounted = isMounted.current;
        
        if (isComponentMounted) {
            setIsDeletingCharacter(characterId);
            setCharacterError(null);
        }
        
        try {
            await deleteCharacter(projectId, characterId);
            
            if (isComponentMounted && isMounted.current) {
                setCharacters(prev => prev.filter(c => c.id !== characterId));
            }
        } catch (err) {
            console.error('Error deleting character:', err);
            
            if (isComponentMounted && isMounted.current) {
                setCharacterError(err.message || 'Failed to delete character');
            }
        } finally {
            if (isComponentMounted && isMounted.current) {
                setIsDeletingCharacter(null);
            }
        }
    }, [projectId]);

    return {
        // State
        characters,
        isLoadingCharacters,
        newCharacterName,
        characterError,
        isCreatingCharacter,
        isDeletingCharacter,
        
        // Actions
        setNewCharacterName,
        handleCreateCharacter,
        handleDeleteCharacter
    };
}
