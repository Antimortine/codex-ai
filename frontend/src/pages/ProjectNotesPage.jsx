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
    getNoteTree,
    createNote,
    deleteNote,
    deleteFolder,
    renameFolder,
    updateNote, // Import updateNote API for moving
} from '../api/codexApi';
import NoteTreeViewer from '../components/NoteTreeViewer';
import { v4 as uuidv4 } from 'uuid';

// Styles remain the same
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

// Helper function remains the same
const addNodeToTree = (tree, parentPath, newNode) => {
    return tree.map(node => {
        if (node.path === parentPath && node.type === 'folder') {
            return {
                ...node,
                children: [...(node.children || []), newNode].sort((a, b) => {
                     if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
                     return a.name.localeCompare(b.name);
                 })
            };
        } else if (node.children && node.children.length > 0) {
            return { ...node, children: addNodeToTree(node.children, parentPath, newNode) };
        }
        return node;
    });
};

// Helper function to get all folder paths from the tree
const getAllFolderPaths = (treeNodes) => {
    let paths = ['/']; // Always include root
    const traverse = (nodes) => {
        if (!nodes) return;
        nodes.forEach(node => {
            if (node.type === 'folder') {
                paths.push(node.path);
                if (node.children) {
                    traverse(node.children);
                }
            }
        });
    };
    traverse(treeNodes);
    return paths.sort(); // Sort for display
};


function ProjectNotesPage() {
    const { projectId } = useParams();
    const [projectName, setProjectName] = useState('');
    const [noteTree, setNoteTree] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState('');

    // Fetch project name (no changes)
    useEffect(() => {
        getProject(projectId)
            .then(response => {
                setProjectName(response.data.name || `Project ${projectId}`);
            })
            .catch(err => {
                console.error("Failed to fetch project name:", err);
                setProjectName(`Project ${projectId}`);
            });
    }, [projectId]);

    // Fetch note tree (no changes)
    const fetchNoteTree = useCallback((calledByAction = false) => {
        if (!projectId) return;
        setError('');
        if (!calledByAction) setIsLoading(true);

        getNoteTree(projectId)
            .then(response => {
                setNoteTree(response.data.tree || []);
            })
            .catch(err => {
                console.error("Failed to fetch note tree:", err);
                setError('Failed to load note structure. Please try again.');
                setNoteTree([]);
            })
            .finally(() => {
                setIsLoading(false);
                if (calledByAction) setIsProcessing(false);
            });
    }, [projectId]);

    // Fetch note tree on mount (no changes)
    useEffect(() => {
        fetchNoteTree(false);
    }, [fetchNoteTree]);

    // --- Action Handlers ---

    const handleCreateNote = useCallback(async (targetFolderPath = "/") => {
        if (isProcessing) return;
        const title = prompt(`Enter title for new note in "${targetFolderPath}":`);
        if (!title || !title.trim()) {
            if (title !== null) setError("Note title cannot be empty.");
            return;
        }
        setIsProcessing(true);
        setError('');
        try {
            await createNote(projectId, { title: title.trim(), folder_path: targetFolderPath });
            fetchNoteTree(true);
        } catch (err) {
            console.error("Failed to create note:", err);
            setError(`Failed to create note: ${err.response?.data?.detail || err.message}`);
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
                fetchNoteTree(true);
            } catch (err) {
                console.error(`Failed to delete note ${noteId}:`, err);
                setError(`Failed to delete note: ${err.response?.data?.detail || err.message}`);
                setIsProcessing(false);
            }
        }
    }, [projectId, isProcessing, fetchNoteTree]);

    const handleDeleteFolder = useCallback(async (folderPath) => {
        if (isProcessing || folderPath === '/') return;
        const isRecursive = window.confirm(`Delete folder "${folderPath}"? \n\nWARNING: If the folder is not empty, this will permanently delete all notes and subfolders within it!`);
        if (isRecursive) {
             setIsProcessing(true);
             setError('');
             try {
                 await deleteFolder(projectId, { path: folderPath, recursive: true });
                 fetchNoteTree(true);
             } catch (err) {
                 console.error(`Failed to delete folder ${folderPath}:`, err);
                 setError(`Failed to delete folder: ${err.response?.data?.detail || err.message}`);
                 setIsProcessing(false);
             }
        }
    }, [projectId, isProcessing, fetchNoteTree]);

    const handleCreateFolder = useCallback((parentPath = "/") => {
        if (isProcessing) return;
        const name = prompt(`Enter name for new folder under "${parentPath}":`);
        if (!name || !name.trim()) {
            if (name !== null) setError("Folder name cannot be empty.");
            return;
        }
        if (name.includes('/')) {
             setError("Folder name cannot contain slashes.");
             return;
        }
        setError('');
        const newPath = parentPath === '/' ? `/${name.trim()}` : `${parentPath}/${name.trim()}`;
        const tempId = `temp-folder-${uuidv4()}`;

        let parentNodeChildren = noteTree || [];
        if (parentPath !== '/') {
            const findParent = (nodes, path) => {
                if (!nodes) return null;
                for (const node of nodes) {
                    if (node.path === path && node.type === 'folder') return node.children || [];
                    if (node.children) {
                        const foundInChildren = findParent(node.children, path);
                        if (foundInChildren) return foundInChildren;
                    }
                }
                return null;
            };
            parentNodeChildren = findParent(noteTree, parentPath) || [];
        }
        const exists = parentNodeChildren.some(node => node.name === name.trim() && node.type === 'folder');

        if (exists) {
            setError(`A folder named "${name.trim()}" already exists in "${parentPath}".`);
            return;
        }

        const newFolderNode = { id: tempId, name: name.trim(), type: 'folder', path: newPath, children: [] };

        setNoteTree(currentTree => {
            const treeOrDefault = currentTree || [];
            if (parentPath === '/') {
                return [...treeOrDefault, newFolderNode].sort((a, b) => {
                     if (a.type !== b.type) return a.type === 'folder' ? -1 : 1;
                     return a.name.localeCompare(b.name);
                 });
            } else {
                return addNodeToTree(treeOrDefault, parentPath, newFolderNode);
            }
        });
    }, [noteTree, isProcessing]);

    const handleRenameFolder = useCallback(async (oldPath, oldName) => {
        if (isProcessing || oldPath === '/') return;
        const newName = prompt(`Enter new name for folder "${oldName}":`, oldName);
        if (!newName || !newName.trim() || newName.trim() === oldName || newName.includes('/')) {
            if (newName !== null && newName.trim() !== oldName) {
                 setError(newName.includes('/') ? "Folder name cannot contain slashes." : "Folder name cannot be empty.");
            }
            return;
        }

        const pathSegments = oldPath.split('/');
        pathSegments.pop();
        const parentPath = pathSegments.join('/') || '/';
        const newPath = parentPath === '/' ? `/${newName.trim()}` : `${parentPath}/${newName.trim()}`;

        let parentNodeChildren = noteTree || [];
         if (parentPath !== '/') {
             const findParent = (nodes, path) => {
                 if (!nodes) return null;
                 for (const node of nodes) {
                     if (node.path === path && node.type === 'folder') return node.children || [];
                     if (node.children) {
                         const foundInChildren = findParent(node.children, path);
                         if (foundInChildren) return foundInChildren;
                     }
                 }
                 return null;
             };
             parentNodeChildren = findParent(noteTree, parentPath) || [];
         }
         const exists = parentNodeChildren.some(node => node.name === newName.trim() && node.type === 'folder');
         if (exists) {
             setError(`A folder named "${newName.trim()}" already exists in "${parentPath}".`);
             return;
         }

        setIsProcessing(true);
        setError('');

        try {
            await renameFolder(projectId, { old_path: oldPath, new_path: newPath });
            fetchNoteTree(true);
        } catch (err) {
            console.error(`Failed to rename folder ${oldPath}:`, err);
            setError(`Failed to rename folder: ${err.response?.data?.detail || err.message}`);
            setIsProcessing(false);
        }
    }, [projectId, isProcessing, fetchNoteTree, noteTree]);

    // --- Move Note Handler (NEW) ---
    const handleMoveNote = useCallback(async (noteId, currentPath) => {
        if (isProcessing || !noteTree) return;

        // Get available folder paths from the current tree state
        const availableFolders = getAllFolderPaths(noteTree);
        const targetFolderPath = prompt(
            `Enter the target folder path to move the note to (e.g., /Ideas/Sub, or / for root).\n\nCurrent path: ${currentPath}\nAvailable folders:\n${availableFolders.join('\n')}`,
            currentPath // Default to current path
        );

        // Validate input
        if (!targetFolderPath || targetFolderPath.trim() === currentPath) {
            if (targetFolderPath !== null && targetFolderPath.trim() !== currentPath) {
                 setError("Invalid target folder path provided."); // Basic validation
            }
            return; // Exit if cancelled, empty, or same path
        }

        // Basic validation (more robust needed for real app, e.g., check against availableFolders)
        const validatedPath = targetFolderPath.trim() === '/' ? '/' : targetFolderPath.trim().replace(/\/$/, ''); // Normalize path
        if (!validatedPath.startsWith('/')) {
            setError("Target path must start with /");
            return;
        }
        if (validatedPath.includes('//')) {
             setError("Target path cannot contain //");
             return;
        }
        // Optional: Check if validatedPath exists in availableFolders for better UX
        // if (!availableFolders.includes(validatedPath)) {
        //     setError(`Target folder "${validatedPath}" does not exist.`);
        //     return;
        // }


        setIsProcessing(true);
        setError('');

        try {
            // Call updateNote API, only sending the folder_path
            await updateNote(projectId, noteId, { folder_path: validatedPath });
            fetchNoteTree(true); // Refresh tree on success
        } catch (err) {
            console.error(`Failed to move note ${noteId}:`, err);
            setError(`Failed to move note: ${err.response?.data?.detail || err.message}`);
            setIsProcessing(false); // Reset processing on error
        }
    }, [projectId, isProcessing, fetchNoteTree, noteTree]); // Added noteTree dependency

    // Define treeHandlers INSIDE the component body
    const treeHandlers = {
        onCreateNote: handleCreateNote,
        onCreateFolder: handleCreateFolder,
        onRenameFolder: handleRenameFolder,
        onDeleteFolder: handleDeleteFolder,
        onDeleteNote: handleDeleteNote,
        onMoveNote: handleMoveNote, // Pass the real handler
    };

    // Render logic
    const renderContent = () => {
        if (isLoading && noteTree === null) {
            return <p style={styles.loading}>Loading notes structure...</p>;
        }
        if (Array.isArray(noteTree)) {
            return (
                 <div style={styles.treeContainer}>
                    <NoteTreeViewer
                        projectId={projectId}
                        treeData={noteTree}
                        handlers={treeHandlers}
                        isBusy={isProcessing}
                    />
                </div>
            );
        }
        return null;
    };


    return (
        <div style={styles.container}>
            <h2 style={styles.heading}>Project Notes</h2>
            <p style={styles.subHeading}>For "{projectName}"</p>

            {error && <p style={styles.error}>{error}</p>}

            <div>
                <button
                    onClick={() => handleCreateNote("/")}
                    style={{...styles.actionButton, ...(isProcessing ? styles.disabledButton : {})}}
                    disabled={isProcessing}
                    title="Create a new note at the root level"
                >
                    + New Note (Root)
                </button>
                 <button
                     onClick={() => handleCreateFolder("/")}
                     style={{...styles.actionButton, ...(isProcessing ? styles.disabledButton : {})}}
                     disabled={isProcessing}
                     title="Create a new folder at the root level"
                 >
                     + New Folder (Root)
                 </button>
            </div>

            {renderContent()}

        </div>
    );
}

export default ProjectNotesPage;