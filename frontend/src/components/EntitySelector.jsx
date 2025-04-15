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

import React, { useState, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import { listCharacters, listScenes, getNoteTree } from '../api/codexApi';

// Styles
const styles = {
    container: {
        marginTop: '10px',
        marginBottom: '15px',
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '10px',
        cursor: 'pointer',
        borderBottom: '1px solid #eee',
        paddingBottom: '5px',
    },
    selectorContainer: {
        display: 'flex',
        flexDirection: 'column',
        marginTop: '10px',
    },
    categoryHeader: {
        fontWeight: 'bold',
        marginBottom: '5px',
        marginTop: '10px',
    },
    entityList: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '8px',
        marginBottom: '10px',
    },
    entityTag: {
        padding: '5px 10px',
        borderRadius: '15px',
        fontSize: '0.85em',
        display: 'flex',
        alignItems: 'center',
        gap: '5px',
        cursor: 'pointer',
    },
    characterTag: {
        backgroundColor: '#e3f2fd',
        border: '1px solid #90caf9',
    },
    sceneTag: {
        backgroundColor: '#e8f5e9',
        border: '1px solid #a5d6a7',
    },
    noteTag: {
        backgroundColor: '#fff8e1',
        border: '1px solid #ffe082',
    },
    selectedTag: {
        backgroundColor: '#c8e6c9',
        border: '1px solid #81c784',
    },
    toggleIcon: {
        marginLeft: '5px',
        fontSize: '0.8em',
    },
    loading: {
        fontStyle: 'italic',
        color: '#666',
        margin: '10px 0',
    },
    error: {
        color: '#d32f2f',
        margin: '10px 0',
    }
};

/**
 * A component for selecting entities (characters, scenes, notes) to include in AI generation
 */
function EntitySelector({ projectId, chapterId, onChange, selectedEntities = [], disabled = false }) {
    const [isExpanded, setIsExpanded] = useState(false);
    const [characters, setCharacters] = useState([]);
    const [scenes, setScenes] = useState([]);
    const [notes, setNotes] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // We'll now use a ref to keep track of the current selection state
    // This avoids the need to sync with parent component except on mount
    const selectedRef = useRef(selectedEntities);
    
    // Initialize selected state from props ONLY on first render
    const [selected, setSelected] = useState(selectedEntities);
    
    // Log when we receive new selectedEntities props for debugging
    useEffect(() => {
        console.log('EntitySelector: Received new selectedEntities:', selectedEntities);
    }, [selectedEntities]);
    
    // Only update internal state from props on first render
    // This ensures we maintain local state after user interactions
    useEffect(() => {
        console.log('EntitySelector: Component mounted with initial selection:', selectedEntities);
    }, []);

    // Load entities when expanded
    useEffect(() => {
        if (isExpanded && projectId) {
            loadEntities();
        }
    }, [isExpanded, projectId, chapterId]);

    const loadEntities = async () => {
        setLoading(true);
        setError(null);
        try {
            // Load characters
            const charactersResponse = await listCharacters(projectId);
            setCharacters(charactersResponse.data.characters || []);

            // Load scenes from the chapter if provided
            if (chapterId) {
                const scenesResponse = await listScenes(projectId, chapterId);
                setScenes(scenesResponse.data.scenes || []);
            } else {
                setScenes([]);
            }

            // Load notes
            const notesTreeResponse = await getNoteTree(projectId);
            const flattenedNotes = flattenNoteTree(notesTreeResponse.data.tree || []);
            setNotes(flattenedNotes);
        } catch (err) {
            console.error('Error loading entities:', err);
            setError('Failed to load entities. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const flattenNoteTree = (tree) => {
        let notes = [];
        const processNode = (node) => {
            // FIXED FILTER: More precise system node detection that doesn't filter real notes
            const isSystemNode = (
                // Criteria 1: Explicit folder markers
                (node.title === '.folder' || node.name === '.folder') ||
                (node.type === 'folder') ||
                
                // Criteria 2: Virtual directory paths - only exact matches
                (node.id && typeof node.id === 'string' && node.id.startsWith('/')) ||
                
                // Criteria 3: Only filter nodes with children if they're ALSO marked as folders
                (node.children && node.children.length > 0 && node.type === 'folder') ||
                
                // Criteria 4: Hidden files that start with dots
                (node.name && typeof node.name === 'string' && node.name.startsWith('.')) ||
                
                // Criteria 5: Special case for empty system placeholder notes
                (!node.note && !node.content && !node.text && node.name === '.folder')
            );
            
            // Debug output to see the decision for each node
            console.log('EntitySelector: Node evaluation:', {
                id: node.id,
                name: node.name,
                type: node.type,
                isSystemNode: isSystemNode,
                hasContent: !!(node.note || node.content || node.text)
            });

            if (isSystemNode) {
                // Only process children of folders, don't include folder itself
                if (node.children && node.children.length > 0) {
                    node.children.forEach(processNode);
                }
                console.log('EntitySelector: Skipping system node:', node);
                return;
            }
            
            // Skip nodes that don't have any text content to display
            if (!node.note && !node.title && !node.content && !node.text && !node.name) {
                console.log('EntitySelector: Skipping empty node:', node);
                return;
            }
            
            // Only add actual note items with good metadata
            // Extract metadata from note field if available
            const noteMetadata = node.note || {};
            
            // Build a display name with better information
            // Try multiple options for finding a good title, with decreasing priority
            let noteTitle = '';
            
            // Option 1: Use metadata title if available
            if (noteMetadata.title) {
                noteTitle = noteMetadata.title;
            }
            // Option 2: Use node name if available (this is where most notes store their titles)
            else if (node.name && node.name !== '.folder') {
                noteTitle = node.name;
            }
            // Option 3: Use node title if available
            else if (node.title && node.title !== '.folder') {
                noteTitle = node.title;
            }
            // Option 4: Use virtual path if available (without the extension)
            else if (node.path) {
                // Extract filename without extension from path
                const pathParts = node.path.split('/');
                const fileName = pathParts[pathParts.length - 1];
                noteTitle = fileName.split('.')[0] || fileName; // Remove extension if present
            }
            // Option 5: As a last resort, use a more readable version of the ID
            else if (node.id) {
                noteTitle = `Note ${node.id.substring(0, 8)}`; // Show more of ID
            }
            else {
                noteTitle = 'Untitled Note';
            }
            
            // CRITICAL FIX: If the title is empty, use a fallback
            if (!noteTitle || noteTitle.trim() === '') {
                noteTitle = `Note ${node.id ? node.id.substring(0, 8) : 'Unknown'}`;
            }
            
            notes.push({
                id: node.id,
                title: noteTitle,
                metadata: noteMetadata,
                path: node.path, // Store path for better display if needed
                originalNode: node // Store original node for debugging
            });
            
            // Process any children (though notes typically don't have children)
            if (node.children && node.children.length > 0) {
                node.children.forEach(processNode);
            }
        };
        
        tree.forEach(processNode);
        return notes;
    };

    // Format entity for display and selection
    const formatEntityForDisplay = (entity) => {
        // Different types of entities have different properties to use for display
        if (entity.type === 'character') {
            return `Character: ${entity.name || 'Unnamed Character'}`;
        } else if (entity.type === 'scene') {
            return `Scene: ${entity.title || 'Untitled Scene'}`;
        } else if (entity.type === 'note') {
            // Get note title - clean it up and make it professional
            const noteTitle = entity.title || 'Untitled Note';
            return `Note: ${noteTitle}`;
        } else {
            // Default case for other entity types
            return entity.title || entity.name || 'Unknown Entity';
        }
    };

    const toggleSelection = (entity) => {
        if (disabled) return; // Don't allow changes if disabled
        
        // CRITICAL FIX: Check that entity has a valid title/name before using it
        if (!entity || (!entity.title && !entity.name)) {
            console.error('EntitySelector: Cannot toggle selection for entity without a title or name:', entity);
            return;
        }
        
        // Create a formatted display name with entity type prefix
        const entityDisplayName = formatEntityForDisplay(entity);
        
        // Always derive from the current state to avoid staleness
        const currentSelected = [...selected]; // Create a copy to avoid mutations
        const isSelected = currentSelected.includes(entityDisplayName);
        let newSelection;
        
        if (isSelected) {
            // Remove from selection
            console.log('EntitySelector: Removing from selection:', entityDisplayName);
            newSelection = currentSelected.filter(item => item !== entityDisplayName);
        } else {
            // Add to selection
            console.log('EntitySelector: Adding to selection:', entityDisplayName);
            newSelection = [...currentSelected, entityDisplayName];
        }
        
        // Use the helper function to update state and call onChange
        handleSelectionChange(newSelection);
    };

    // Handle selection changes with proper logging
    const handleSelectionChange = (newSelection) => {
        console.log('EntitySelector: Updating selection to:', newSelection);
        
        // Update both our internal state and ref
        setSelected(newSelection);
        selectedRef.current = newSelection;
        
        // Notify parent component about the change
        if (onChange) {
            console.log('EntitySelector: Calling onChange with:', newSelection);
            onChange(newSelection);
        }
    };

    return (
        <div style={styles.container}>
            <div 
                style={{...styles.header, ...(disabled ? { opacity: 0.7, cursor: 'not-allowed' } : {})}} 
                onClick={() => !disabled && setIsExpanded(!isExpanded)}
                data-testid="entity-selector-header"
            >
                <span>Direct Sources Selection {selected.length > 0 && `(${selected.length} selected)`}</span>
                <span style={styles.toggleIcon}>{isExpanded ? '▼' : '►'}</span>
            </div>
            
            {isExpanded && (
                <div style={styles.selectorContainer}>
                    {loading && <div style={styles.loading}>Loading entities...</div>}
                    {error && <div style={styles.error}>{error}</div>}
                    
                    {!loading && (
                        <>
                            {/* Characters Section */}
                            {characters.length > 0 && (
                                <>
                                    <div style={styles.categoryHeader}>Characters</div>
                                    <div style={styles.entityList}>
                                        {characters.map(character => (
                                            <div 
                                                key={character.id}
                                                style={{
                                                    ...styles.entityTag,
                                                    ...styles.characterTag,
                                                    ...(selected.includes(`Character: ${character.name}`) ? styles.selectedTag : {})
                                                }}
                                                onClick={() => toggleSelection({...character, type: 'character'})}
                                                data-testid={`entity-character-${character.id}`}
                                            >
                                                {character.name}
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                            
                            {/* Scenes Section */}
                            {scenes.length > 0 && (
                                <>
                                    <div style={styles.categoryHeader}>Scenes</div>
                                    <div style={styles.entityList}>
                                        {scenes.map(scene => (
                                            <div 
                                                key={scene.id}
                                                style={{
                                                    ...styles.entityTag,
                                                    ...styles.sceneTag,
                                                    ...(selected.includes(`Scene: ${scene.title}`) ? styles.selectedTag : {})
                                                }}
                                                onClick={() => toggleSelection({...scene, type: 'scene'})}
                                                data-testid={`entity-scene-${scene.id}`}
                                            >
                                                {scene.title}
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                            
                            {/* Notes Section */}
                            {notes.length > 0 && (
                                <>
                                    <div style={styles.categoryHeader}>Notes</div>
                                    <div style={styles.entityList}>
                                        {notes.map(note => (
                                            <div 
                                                key={note.id}
                                                style={{
                                                    ...styles.entityTag,
                                                    ...styles.noteTag,
                                                    ...(selected.includes(formatEntityForDisplay({...note, type: 'note'})) ? styles.selectedTag : {})
                                                }}
                                                onClick={() => toggleSelection({...note, type: 'note'})}
                                                data-testid={`entity-note-${note.id}`}
                                            >
                                                {note.title}
                                            </div>
                                        ))}
                                    </div>
                                </>
                            )}
                            
                            {characters.length === 0 && scenes.length === 0 && notes.length === 0 && (
                                <div>No entities found. Create some characters, scenes, or notes first.</div>
                            )}
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

EntitySelector.propTypes = {
    projectId: PropTypes.string.isRequired,
    chapterId: PropTypes.string,
    onChange: PropTypes.func,
    selectedEntities: PropTypes.arrayOf(PropTypes.string),
    disabled: PropTypes.bool
};

export default EntitySelector;
