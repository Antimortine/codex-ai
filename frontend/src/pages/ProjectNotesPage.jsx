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

import React, { useState, useEffect, useCallback } from 'react';
import { useParams } from 'react-router-dom';
import {
    getProject,
    getNoteTree, // Use getNoteTree instead of listNotes
    createNote,
    deleteNote,
    deleteFolder, // Import folder delete API
    // renameFolder, // Import later when implementing rename
} from '../api/codexApi';
import NoteTreeViewer from '../components/NoteTreeViewer'; // Import the new component

// Basic styles (can be refined)
const styles = {
    container: { padding: '20px' },
    heading: { marginBottom: '10px' },
    subHeading: { marginBottom: '20px', color: '#555', fontSize: '1.1em' },
    error: { color: 'red', marginBottom: '10px', border: '1px solid red', padding: '10px', borderRadius: '4px' },
    loading: { fontStyle: 'italic', marginBottom: '10px' },
    actionButton: { padding: '8px 15px', cursor: 'pointer', marginRight: '10px' },
    disabledButton: { cursor: 'not-allowed', opacity: 0.6 },
    treeContainer: { marginTop: '20px', border: '1px solid #eee', padding: '15px', borderRadius: '4px' },
};

function ProjectNotesPage() {
    const { projectId } = useParams();
    const [projectName, setProjectName] = useState('');
    const [noteTree, setNoteTree] = useState([]); // State for the tree structure
    const [isLoading, setIsLoading] = useState(true);
    const [isProcessing, setIsProcessing] = useState(false); // General busy state
    const [error, setError] = useState('');

    // Fetch project name (keep as before)
    useEffect(() => {
        getProject(projectId)
            .then(response => {
                setProjectName(response.data.name || `Project ${projectId}`);
            })
            .catch(err => {
                console.error("Failed to fetch project name:", err);
                setProjectName(`Project ${projectId}`);
                // Optionally set an error state here as well
            });
    }, [projectId]);

    // Function to fetch the note tree structure
    const fetchNoteTree = useCallback(() => {
        setError('');
        setIsLoading(true); // Set loading true when fetching starts
        getNoteTree(projectId)
            .then(response => {
                setNoteTree(response.data.tree || []);
            })
            .catch(err => {
                console.error("Failed to fetch note tree:", err);
                setError('Failed to load note structure. Please try again.');
                setNoteTree([]); // Clear tree on error
            })
            .finally(() => {
                setIsLoading(false);
            });
    }, [projectId]);

    // Fetch note tree on component mount
    useEffect(() => {
        fetchNoteTree();
    }, [fetchNoteTree]);

    // --- Action Handlers ---

    const handleCreateNote = useCallback(async (targetFolderPath = "/") => {
        if (isProcessing) return;

        const title = prompt(`Enter title for new note in "${targetFolderPath}":`);
        if (!title || !title.trim()) {
            if (title !== null) { // Avoid error if user cancels prompt
                 setError("Note title cannot be empty.");
            }
            return;
        }

        setIsProcessing(true);
        setError('');

        try {
            await createNote(projectId, { title: title.trim(), folder_path: targetFolderPath });
            fetchNoteTree(); // Refresh tree on success
        } catch (err) {
            console.error("Failed to create note:", err);
            setError(`Failed to create note: ${err.response?.data?.detail || err.message}`);
        } finally {
            setIsProcessing(false);
        }
    }, [projectId, isProcessing, fetchNoteTree]);

    const handleDeleteNote = useCallback(async (noteId, noteTitle) => {
        if (isProcessing) return;

        if (window.confirm(`Are you sure you want to delete the note "${noteTitle}"?`)) {
            setIsProcessing(true);
            setError('');
            try {
                await deleteNote(projectId, noteId);
                fetchNoteTree(); // Refresh tree
            } catch (err) {
                console.error(`Failed to delete note ${noteId}:`, err);
                setError(`Failed to delete note: ${err.response?.data?.detail || err.message}`);
            } finally {
                setIsProcessing(false);
            }
        }
    }, [projectId, isProcessing, fetchNoteTree]);

    const handleDeleteFolder = useCallback(async (folderPath) => {
        if (isProcessing || folderPath === '/') return; // Cannot delete root

        // Basic check - ideally, the tree component would know if it has children
        const isRecursive = window.confirm(`Delete folder "${folderPath}"? \n\nWARNING: If the folder is not empty, this will permanently delete all notes and subfolders within it!`);

        if (isRecursive) { // Only proceed if confirmed recursive for now
             setIsProcessing(true);
             setError('');
             try {
                 await deleteFolder(projectId, { path: folderPath, recursive: true });
                 fetchNoteTree(); // Refresh tree
             } catch (err) {
                 console.error(`Failed to delete folder ${folderPath}:`, err);
                 setError(`Failed to delete folder: ${err.response?.data?.detail || err.message}`);
             } finally {
                 setIsProcessing(false);
             }
        }
        // Later: Add non-recursive check and API call if needed
        // else {
        //     alert("Non-recursive delete not implemented yet. Or folder might be empty.");
        // }

    }, [projectId, isProcessing, fetchNoteTree]);

    // --- Placeholder Handlers ---
    const handleCreateFolder = useCallback((parentPath = "/") => {
        // TODO: Implement folder creation UI (likely just local state update first)
        alert(`Placeholder: Create folder under "${parentPath}"`);
    }, []);

    const handleRenameFolder = useCallback((oldPath) => {
        // TODO: Implement folder rename UI and API call
        alert(`Placeholder: Rename folder "${oldPath}"`);
    }, []);

    const handleMoveNote = useCallback((noteId, targetFolderPath) => {
        // TODO: Implement note move UI (e.g., drag/drop) and API call
        alert(`Placeholder: Move note ${noteId} to "${targetFolderPath}"`);
    }, []);

    // Combine handlers for the NoteTreeViewer
    const treeHandlers = {
        onCreateNote: handleCreateNote,
        onCreateFolder: handleCreateFolder,
        onRenameFolder: handleRenameFolder,
        onDeleteFolder: handleDeleteFolder,
        onDeleteNote: handleDeleteNote,
        onMoveNote: handleMoveNote,
    };

    return (
        <div style={styles.container}>
            <h2 style={styles.heading}>Project Notes</h2>
            <p style={styles.subHeading}>For "{projectName}"</p>

            {error && <p style={styles.error}>{error}</p>}

            {/* Root level actions */}
            <div>
                <button
                    onClick={() => handleCreateNote("/")} // Create at root
                    style={{...styles.actionButton, ...(isProcessing ? styles.disabledButton : {})}}
                    disabled={isProcessing}
                >
                    + New Note (Root)
                </button>
                 {/* <button
                     onClick={() => handleCreateFolder("/")} // Create folder at root
                     style={{...styles.actionButton, ...(isProcessing ? styles.disabledButton : {})}}
                     disabled={isProcessing}
                 >
                     + New Folder (Root)
                 </button> */}
            </div>

            {isLoading ? (
                <p style={styles.loading}>Loading notes structure...</p>
            ) : (
                <div style={styles.treeContainer}>
                    <NoteTreeViewer
                        projectId={projectId}
                        treeData={noteTree}
                        handlers={treeHandlers}
                        isBusy={isProcessing}
                    />
                </div>
            )}
        </div>
    );
}

export default ProjectNotesPage;