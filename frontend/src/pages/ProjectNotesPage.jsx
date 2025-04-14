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
import { useParams } from 'react-router-dom'; // Use the potentially mocked version
import {
    getProject,
    getNoteTree,
    createNote,
    deleteNote,
    deleteFolder,
    renameFolder,
    updateNote,
} from '../api/codexApi';
import NoteTreeViewer from '../components/NoteTreeViewer';
import Modal from '../components/Modal';
import { v4 as uuidv4 } from 'uuid';

// Styles remain the same
const styles = { /* ... */ };

// Helper functions
const addNodeToTree = (tree, parentPath, newNode) => { /* ... */ };

// Get all folder paths from the note tree, ensuring it always returns an array
const getAllFolderPaths = (treeNodes) => {
    if (!treeNodes || !Array.isArray(treeNodes) || treeNodes.length === 0) {
        return ['/'];
    }
    
    const paths = new Set(['/']); // Always include root
    
    const traverse = (nodes, currentPath = '/') => {
        if (!nodes || !Array.isArray(nodes)) return;
        
        for (const node of nodes) {
            if (node.type === 'folder') {
                const nodePath = currentPath === '/' ? `/${node.name}` : `${currentPath}/${node.name}`;
                paths.add(nodePath);
                if (node.children && Array.isArray(node.children)) {
                    traverse(node.children, nodePath);
                }
            }
        }
    };
    
    traverse(treeNodes);
    return Array.from(paths);
};

const getModalTitle = (modalType) => {
    switch (modalType) {
        case 'createNote': return 'Create New Note';
        case 'createFolder': return 'Create New Folder';
        case 'renameFolder': return 'Rename Folder';
        case 'moveNote': return 'Move Note';
        default: return 'Action';
    }
};


function ProjectNotesPage() {
    // Get projectId from router params
    const { projectId } = useParams() || {}; // Add default empty object for safety in tests

    const [projectName, setProjectName] = useState('');
    const [noteTree, setNoteTree] = useState([]); // Initialize with empty array
    const [isLoading, setIsLoading] = useState(true); // Still true initially
    const [isProcessing, setIsProcessing] = useState(false);
    const [error, setError] = useState('');

    const [modalType, setModalType] = useState(null);
    const [modalData, setModalData] = useState({});
    const [modalInputValue, setModalInputValue] = useState('');
    const [modalSelectValue, setModalSelectValue] = useState('');
    const [modalError, setModalError] = useState('');

    // Fetch project name - Guard against missing projectId
    useEffect(() => {
        if (projectId) {
            // console.log("Fetching project name for:", projectId); // Debug
            getProject(projectId)
                .then(response => setProjectName(response.data.name || `Project ${projectId}`))
                .catch(err => console.error("Failed to fetch project name:", err));
        } else {
            // console.log("Skipping project name fetch - no projectId"); // Debug
        }
    }, [projectId]);

    // Fetch note tree - Guard against missing projectId
    const fetchNoteTree = useCallback((calledByAction = false) => {
        if (!projectId) {
            // console.log("Skipping fetchNoteTree - no projectId"); // Debug
            setIsLoading(false); // Ensure loading stops if no projectId
            return;
        }
        // console.log(`fetchNoteTree called (calledByAction: ${calledByAction})`); // Debug
        setError('');
        // Set loading true only on initial load *if* not already processing
        if (!calledByAction && !isProcessing) {
             setIsLoading(true);
        }

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
                // console.log(`fetchNoteTree finally (calledByAction: ${calledByAction})`); // Debug
                setIsLoading(false);
                if (calledByAction) {
                    setIsProcessing(false);
                }
            });
    }, [projectId]); // Removed isProcessing dependency

    // Fetch note tree on mount - Guarded by projectId check inside fetchNoteTree
    useEffect(() => {
        // console.log("Mount effect - projectId:", projectId); // Debug
        fetchNoteTree(false);
    }, [projectId, fetchNoteTree]); // Keep dependencies

    // --- Modal Open/Close ---
    const openModal = useCallback((type, data = {}) => {
        setModalType(type);
        setModalData(data);
        setModalInputValue(data.initialValue || '');
        setModalSelectValue(data.initialPath || '/');
        setModalError('');
    }, []);
    
    const closeModal = useCallback(() => {
        setModalType(null);
        setModalData({});
        setModalInputValue('');
        setModalSelectValue('');
        setModalError('');
    }, []);

    // --- Action Handlers ---
    // Minimal dependencies where possible
    const handleCreateNote = useCallback((targetFolderPath = "/") => {
        if (isProcessing) return;
        openModal('createNote', { targetFolderPath });
    }, [isProcessing, openModal]);

    const handleDeleteNote = useCallback(async (noteId, noteTitle) => {
        if (isProcessing) return;
        if (window.confirm(`Are you sure you want to delete the note "${noteTitle}"?`)) {
            setIsProcessing(true);
            setError('');
            try {
                await deleteNote(projectId, noteId);
                fetchNoteTree(true);
            } catch (err) { 
                setError(`Failed to delete note: ${err.message || 'Unknown error'}`);
                setIsProcessing(false); 
            }
        }
    }, [projectId, isProcessing, fetchNoteTree]); // Needs projectId

    const handleDeleteFolder = useCallback(async (folderPath) => {
        if (isProcessing || folderPath === '/') return;
        
        // Extract folder name from path for a more descriptive confirmation message
        const folderName = folderPath === '/' ? 'Root' : 
            folderPath.split('/').filter(Boolean).pop() || folderPath;
            
        if (window.confirm(`Are you sure you want to delete the folder "${folderName}" and all its contents?`)) {
            setIsProcessing(true); 
            setError('');
            try {
                await deleteFolder(projectId, { path: folderPath, recursive: true }); 
                fetchNoteTree(true);
            } catch (err) { 
                setError(`Failed to delete folder: ${err.message || 'Unknown error'}`); 
                setIsProcessing(false); 
            }
        }
    }, [projectId, isProcessing, fetchNoteTree]); // Needs projectId

    const handleCreateFolder = useCallback((parentPath = "/") => {
        if (isProcessing) return;
        openModal('createFolder', { parentPath });
    }, [isProcessing, openModal]);

    const handleRenameFolder = useCallback((oldPath, oldName) => {
        if (isProcessing || oldPath === '/') return;
        openModal('renameFolder', { oldPath, oldName, initialValue: oldName });
    }, [isProcessing, openModal]);

    const handleMoveNote = useCallback((noteId, currentPath) => {
        // Guard moved inside openModal if needed, or rely on initial state []
        if (isProcessing) return;
        // Get available folders, ensuring we always get at least ['/'] even if noteTree is empty
        const availableFolders = getAllFolderPaths(noteTree);
        // Safely determine default path
        const defaultPath = availableFolders.includes(currentPath) ? currentPath : (availableFolders[0] || '/');
        openModal('moveNote', { noteId, currentPath, availableFolders, initialPath: defaultPath });
    }, [isProcessing, noteTree, openModal]); // Added openModal as dependency

    // --- Modal Submission Handler ---
    // Handles all modal form submissions based on modalType
    const handleModalSubmit = useCallback(async () => {
        if (isProcessing) return;
        
        setIsProcessing(true);
        setModalError('');
        
        try {
            switch(modalType) {
                case 'createNote':
                    if (!modalInputValue.trim()) {
                        setModalError('Please enter a valid note name');
                        setIsProcessing(false);
                        return;
                    }
                    
                    const noteId = uuidv4();
                    await createNote(projectId, {
                        note_id: noteId,
                        title: modalInputValue.trim(),
                        content: '',
                        folder_path: modalData.targetFolderPath || '/'
                    });
                    break;
                    
                case 'createFolder':
                    if (!modalInputValue.trim()) {
                        setModalError('Please enter a valid folder name');
                        setIsProcessing(false);
                        return;
                    }
                    
                    // Folder names can't contain slashes
                    if (modalInputValue.includes('/')) {
                        setModalError('Folder names cannot contain "/" characters');
                        setIsProcessing(false);
                        return;
                    }
                    
                    const folderPath = modalData.parentPath === '/' ? 
                        `/${modalInputValue.trim()}` : 
                        `${modalData.parentPath}/${modalInputValue.trim()}`;
                    
                    // Create a placeholder note with title '.folder' in the target folder path
                    // This will implicitly create the folder in the tree structure
                    const folderId = uuidv4();
                    await createNote(projectId, {
                        note_id: folderId,
                        title: '.folder',  // Hidden note that will be filtered out in UI
                        content: '',
                        folder_path: folderPath
                    });
                    break;
                    
                case 'renameFolder':
                    if (!modalInputValue.trim()) {
                        setModalError('Please enter a valid folder name');
                        setIsProcessing(false);
                        return;
                    }
                    
                    // Folder names can't contain slashes
                    if (modalInputValue.includes('/')) {
                        setModalError('Folder names cannot contain "/" characters');
                        setIsProcessing(false);
                        return;
                    }
                    
                    if (modalInputValue.trim() !== modalData.oldName) {
                        await renameFolder(projectId, {
                            old_path: modalData.oldPath,
                            new_name: modalInputValue.trim()
                        });
                    }
                    break;
                
                case 'moveNote':
                    if (modalSelectValue !== modalData.currentPath) {
                        // Only move if destination is different from current path
                        await updateNote(projectId, modalData.noteId, {
                            folder_path: modalSelectValue
                        });
                    }
                    break;
                    
                default:
                    console.warn('Unknown modal type:', modalType);
                    break;
            }
            
            // Refresh the note tree and close modal
            fetchNoteTree(true); // true indicates it was called by an action
            closeModal();
            
        } catch (err) {
            console.error('Error in modal submission:', err);
            setModalError(`Failed to perform action: ${err.message || 'Unknown error'}`);
            setIsProcessing(false);
        }
    }, [
        projectId, isProcessing, modalType, modalData, modalInputValue, modalSelectValue, 
        noteTree, fetchNoteTree, closeModal
    ]);

    // Define treeHandlers INSIDE the component body with all required handlers
    const treeHandlers = {
        onCreateNote: handleCreateNote,
        onDeleteNote: handleDeleteNote,
        onCreateFolder: handleCreateFolder,
        onDeleteFolder: handleDeleteFolder,
        onRenameFolder: handleRenameFolder,
        onMoveNote: handleMoveNote
    };
    
    // Render Modal Content function
    const renderModalContent = () => {
        switch(modalType) {
            case 'createNote':
                return (
                    <div>
                        <p>Enter a name for the new note:</p>
                        <input
                            type="text"
                            value={modalInputValue}
                            onChange={(e) => setModalInputValue(e.target.value)}
                            placeholder="Note name"
                            autoFocus
                        />
                        {modalError && <p style={{ color: 'red' }}>{modalError}</p>}
                        <div style={{ marginTop: '20px' }}>
                            <button onClick={handleModalSubmit} disabled={isProcessing}>Create</button>
                            <button onClick={closeModal} disabled={isProcessing}>Cancel</button>
                        </div>
                    </div>
                );
            case 'createFolder':
                return (
                    <div>
                        <p>Enter a name for the new folder:</p>
                        <input
                            type="text"
                            value={modalInputValue}
                            onChange={(e) => setModalInputValue(e.target.value)}
                            placeholder="Folder name"
                            autoFocus
                        />
                        {modalError && <p style={{ color: 'red' }}>{modalError}</p>}
                        <div style={{ marginTop: '20px' }}>
                            <button onClick={handleModalSubmit} disabled={isProcessing}>Create</button>
                            <button onClick={closeModal} disabled={isProcessing}>Cancel</button>
                        </div>
                    </div>
                );
            case 'renameFolder':
                return (
                    <div>
                        <p>Enter a new name for the folder:</p>
                        <input
                            type="text"
                            value={modalInputValue}
                            onChange={(e) => setModalInputValue(e.target.value)}
                            placeholder="Folder name"
                            autoFocus
                        />
                        {modalError && <p style={{ color: 'red' }}>{modalError}</p>}
                        <div style={{ marginTop: '20px' }}>
                            <button onClick={handleModalSubmit} disabled={isProcessing}>Rename</button>
                            <button onClick={closeModal} disabled={isProcessing}>Cancel</button>
                        </div>
                    </div>
                );
            case 'moveNote':
                return (
                    <div>
                        <p>Select a destination folder:</p>
                        <select 
                            value={modalSelectValue}
                            onChange={(e) => setModalSelectValue(e.target.value)}
                        >
                            {modalData.availableFolders && modalData.availableFolders.map(folder => (
                                <option key={folder} value={folder}>
                                    {folder === '/' ? 'Root' : folder}
                                </option>
                            ))}
                        </select>
                        {modalError && <p style={{ color: 'red' }}>{modalError}</p>}
                        <div style={{ marginTop: '20px' }}>
                            <button onClick={handleModalSubmit} disabled={isProcessing}>Move</button>
                            <button onClick={closeModal} disabled={isProcessing}>Cancel</button>
                        </div>
                    </div>
                );
            default:
                return null;
        }
    };

    // Render logic for the main page content
    const renderPageContent = () => {
        // Use isLoading for the initial loading state
        if (isLoading) {
            return <p style={styles.loading}>Loading notes structure...</p>;
        }
        // Render tree viewer if noteTree is an array (even if empty)
        if (Array.isArray(noteTree)) {
            return (
                 <div style={styles.treeContainer}>
                    <NoteTreeViewer
                        projectId={projectId}
                        treeData={noteTree} // Pass empty array if fetch failed or no notes
                        handlers={treeHandlers}
                        isBusy={isProcessing}
                    />
                </div>
            );
        }
        // Should not happen if initialized to [], but fallback
        return <p>Error loading notes.</p>;
    };


    return (
        <div style={styles.container}>
            {/* Render heading only when project name is known? Or use placeholder */}
            <h2 style={styles.heading}>Project Notes</h2>
            <p style={styles.subHeading}>For "{projectName || 'Loading...'}"</p>

            {error && <p style={styles.error}>{error}</p>}

            {/* Root Actions - Disable if projectId is missing? */}
            <div>
                <button
                    onClick={() => handleCreateNote("/")}
                    style={{...styles.actionButton, ...((isProcessing || !projectId) ? styles.disabledButton : {})}}
                    disabled={isProcessing || !projectId}
                    title="Create a new note at the root level"
                >
                    + New Note (Root)
                </button>
                 <button
                     onClick={() => handleCreateFolder("/")}
                     style={{...styles.actionButton, ...((isProcessing || !projectId) ? styles.disabledButton : {})}}
                     disabled={isProcessing || !projectId}
                     title="Create a new folder at the root level"
                 >
                     + New Folder (Root)
                 </button>
            </div>

            {renderPageContent()}

            {/* Modal Dialog - Only render when modalType is not null */}
            {modalType && (
                <Modal 
                    title={getModalTitle(modalType)}
                    onClose={closeModal}
                >
                    {renderModalContent()}
                </Modal>
            )}
        </div>
    );
}

export default ProjectNotesPage;