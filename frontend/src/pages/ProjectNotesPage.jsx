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
import { useParams, Link } from 'react-router-dom';
import { listNotes, createNote, getProject, deleteNote } from '../api/codexApi'; // Import deleteNote

// Basic styles (keep as before)
const styles = {
    container: { padding: '20px' },
    heading: { marginBottom: '20px' },
    error: { color: 'red', marginBottom: '10px' },
    loading: { fontStyle: 'italic', marginBottom: '10px' },
    createForm: { marginBottom: '20px', display: 'flex', gap: '10px', alignItems: 'center' },
    input: { padding: '8px', flexGrow: 1 },
    button: { padding: '8px 15px', cursor: 'pointer' },
    disabledButton: { cursor: 'not-allowed', opacity: 0.6 },
    noteList: { listStyle: 'none', padding: 0 },
    noteItem: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '10px', borderBottom: '1px solid #eee' },
    noteLink: { textDecoration: 'none', color: '#007bff', flexGrow: 1, marginRight: '10px' },
    deleteButton: { padding: '5px 10px', cursor: 'pointer', backgroundColor: '#dc3545', color: 'white', border: 'none', borderRadius: '3px' }
};

function ProjectNotesPage() {
    const { projectId } = useParams();
    const [projectName, setProjectName] = useState('');
    const [notes, setNotes] = useState([]);
    const [newNoteTitle, setNewNoteTitle] = useState('');
    const [isLoading, setIsLoading] = useState(true);
    const [isCreating, setIsCreating] = useState(false);
    const [deletingNoteId, setDeletingNoteId] = useState(null);
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
            });
    }, [projectId]);

    // Function to fetch notes (keep as before)
    const fetchNotes = useCallback(() => {
        setError('');
        listNotes(projectId)
            .then(response => {
                setNotes(response.data.notes || []);
            })
            .catch(err => {
                console.error("Failed to fetch notes:", err);
                setError('Failed to load notes. Please try again.');
                setNotes([]);
            })
            .finally(() => {
                setIsLoading(false);
            });
    }, [projectId]);

    // Fetch notes on component mount (keep as before)
    useEffect(() => {
        setIsLoading(true);
        fetchNotes();
    }, [fetchNotes]);

    // Handle creating a new note (FIXED ORDER OF CHECKS)
    const handleCreateNote = (e) => {
        e.preventDefault();

        // --- FIX: Validate title *first* ---
        if (!newNoteTitle.trim()) {
            setError('Note title cannot be empty.');
            return;
        }
        // --- Then check if busy ---
        if (isCreating || deletingNoteId) return;

        // --- Proceed if valid and not busy ---
        setIsCreating(true);
        setError(''); // Clear previous errors only if proceeding

        createNote(projectId, { title: newNoteTitle.trim() })
            .then(() => {
                setNewNoteTitle('');
                fetchNotes(); // Refresh the list
            })
            .catch(err => {
                console.error("Failed to create note:", err);
                setError('Failed to create note. Please try again.');
            })
            .finally(() => {
                setIsCreating(false);
            });
    };

    // Handle deleting a note (keep as before)
    const handleDeleteNote = (noteId, noteTitle) => {
         if (isCreating || deletingNoteId) return;

        if (window.confirm(`Are you sure you want to delete the note "${noteTitle}"?`)) {
            setDeletingNoteId(noteId);
            setError('');

            deleteNote(projectId, noteId)
                .then(() => {
                    fetchNotes();
                })
                .catch(err => {
                    console.error(`Failed to delete note ${noteId}:`, err);
                    setError('Failed to delete note. Please try again.');
                })
                .finally(() => {
                    setDeletingNoteId(null);
                });
        }
    };

    // Determine if any operation is in progress (keep as before)
    const isBusy = isCreating || !!deletingNoteId;

    // Render logic (keep as before, button disabled logic is correct now)
    return (
        <div style={styles.container}>
            <h2 style={styles.heading}>Project Notes for "{projectName}"</h2>

            {error && <p style={styles.error}>{error}</p>}

            <div style={styles.createForm}>
                <input
                    type="text"
                    value={newNoteTitle}
                    onChange={(e) => setNewNoteTitle(e.target.value)}
                    placeholder="New note title..."
                    style={styles.input}
                    disabled={isBusy}
                    aria-label="New note title"
                />
                <button
                    onClick={handleCreateNote}
                    disabled={isBusy || !newNoteTitle.trim()} // This logic is correct
                    style={{
                        ...styles.button,
                        ...(isBusy || !newNoteTitle.trim() ? styles.disabledButton : {})
                    }}
                >
                    {isCreating ? 'Creating...' : 'Create Note'}
                </button>
            </div>

            {isLoading ? (
                <p style={styles.loading}>Loading notes...</p>
            ) : (
                <ul style={styles.noteList}>
                    {notes.length === 0 && !isLoading ? (
                        <li>No notes found for this project.</li>
                    ) : (
                        notes.map(note => (
                            <li key={note.id} style={styles.noteItem}>
                                <Link
                                    to={`/projects/${projectId}/notes/${note.id}`}
                                    style={styles.noteLink}
                                    onClick={(e) => { if (deletingNoteId === note.id) e.preventDefault(); }}
                                    aria-disabled={deletingNoteId === note.id}
                                >
                                    {note.title}
                                </Link>
                                <button
                                    onClick={() => handleDeleteNote(note.id, note.title)}
                                    style={{
                                        ...styles.deleteButton,
                                        ...(isBusy ? styles.disabledButton : {})
                                    }}
                                    disabled={isBusy}
                                    aria-label={`Delete note ${note.title}`}
                                >
                                    {deletingNoteId === note.id ? 'Deleting...' : 'Delete'}
                                </button>
                            </li>
                        ))
                    )}
                </ul>
            )}
        </div>
    );
}

export default ProjectNotesPage;