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
import { useParams, Link, useNavigate } from 'react-router-dom';
import { getNote, updateNote } from '../api/codexApi';
import AIEditorWrapper from '../components/AIEditorWrapper'; // Assuming this path is correct

// Basic Styles
const styles = {
    container: { padding: '20px' },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' },
    heading: { margin: 0 },
    backLink: { textDecoration: 'none' },
    error: { color: 'red', marginBottom: '10px', marginTop: '10px' },
    success: { color: 'green', marginBottom: '10px', marginTop: '10px'},
    loading: { fontStyle: 'italic', marginBottom: '10px' },
    formGroup: { marginBottom: '15px' },
    label: { display: 'block', marginBottom: '5px', fontWeight: 'bold' },
    input: { width: '100%', padding: '8px', boxSizing: 'border-box' },
    saveButton: { padding: '10px 20px', cursor: 'pointer', marginTop: '10px' },
    disabledButton: { cursor: 'not-allowed', opacity: 0.6 },
};

function NoteEditPage() {
    const { projectId, noteId } = useParams();
    const navigate = useNavigate();

    const [title, setTitle] = useState('');
    const [content, setContent] = useState('');
    const [originalNote, setOriginalNote] = useState(null); // Store original for comparison
    const [isLoading, setIsLoading] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [fetchError, setFetchError] = useState(''); // Error during initial load
    const [saveError, setSaveError] = useState('');   // Error during save operation
    const [saveSuccess, setSaveSuccess] = useState(false); // To show success message


    // Fetch Note Data
    useEffect(() => {
        setIsLoading(true);
        setFetchError('');
        getNote(projectId, noteId)
            .then(response => {
                const noteData = response.data;
                setTitle(noteData.title);
                setContent(noteData.content);
                setOriginalNote(noteData); // Store original fetched data
            })
            .catch(err => {
                console.error("Failed to fetch note:", err);
                setFetchError(`Failed to load note ${noteId}. Please ensure it exists and try again.`);
                setOriginalNote(null); // Ensure original note is null on error
            })
            .finally(() => {
                setIsLoading(false);
            });
    }, [projectId, noteId]);

    // Handle Content Change from Editor
    const handleContentChange = useCallback((newContent) => {
        setContent(newContent || ''); // Ensure content is always a string
        setSaveSuccess(false); // Clear success message on edit
    }, []);

    // Handle Title Change
    const handleTitleChange = (e) => {
        setTitle(e.target.value);
        setSaveSuccess(false); // Clear success message on edit
    };

    // Handle Save
    const handleSaveNote = useCallback(() => {
        if (isSaving || isLoading) return; // Prevent saving if busy or not loaded

        // Basic validation (optional, backend handles it too)
        if (!title.trim()) {
            setSaveError('Note title cannot be empty.');
            return;
        }

        // Determine what changed
        const payload = {};
        if (title !== originalNote?.title) {
            payload.title = title.trim();
        }
        if (content !== originalNote?.content) {
             // Treat null/undefined from editor as empty string for comparison/payload
            payload.content = content ?? '';
        }

        // Only save if something actually changed
        if (Object.keys(payload).length === 0) {
             setSaveSuccess(true); // Indicate "saved" even if no change
             setTimeout(() => setSaveSuccess(false), 3000);
            return;
        }


        setIsSaving(true);
        setSaveError('');
        setSaveSuccess(false);

        updateNote(projectId, noteId, payload)
            .then(response => {
                // Update originalNote state to reflect the saved state
                setOriginalNote(response.data);
                // Optionally update title/content state again if backend modifies them,
                // but usually PATCH returns the updated resource as confirmation.
                setTitle(response.data.title);
                setContent(response.data.content);

                setSaveSuccess(true);
                // Optionally clear success message after a delay
                setTimeout(() => setSaveSuccess(false), 3000);
            })
            .catch(err => {
                console.error("Failed to save note:", err);
                setSaveError('Failed to save note. Please try again.');
            })
            .finally(() => {
                setIsSaving(false);
            });
    }, [projectId, noteId, title, content, originalNote, isSaving, isLoading]);


    // Determine if the note has unsaved changes
    const hasUnsavedChanges = originalNote && (title !== originalNote.title || content !== originalNote.content);


    // Render Logic
    if (isLoading) {
        return <div style={styles.container}><p style={styles.loading}>Loading note...</p></div>;
    }

    if (fetchError) {
        return (
            <div style={styles.container}>
                 <div style={styles.header}>
                    <h2 style={styles.heading}>Error Loading Note</h2>
                    <Link to={`/projects/${projectId}/notes`} style={styles.backLink}>Back to Notes List</Link>
                </div>
                <p style={styles.error}>{fetchError}</p>
            </div>
        );
    }

    return (
        <div style={styles.container}>
            <div style={styles.header}>
                <h2 style={styles.heading}>Edit Note</h2>
                <Link to={`/projects/${projectId}/notes`} style={styles.backLink}>Back to Notes List</Link>
            </div>

            {saveError && <p style={styles.error}>{saveError}</p>}
            {saveSuccess && <p style={styles.success}>Note saved successfully!</p>}

            <div style={styles.formGroup}>
                <label htmlFor="noteTitle" style={styles.label}>Title</label>
                <input
                    id="noteTitle"
                    type="text"
                    value={title}
                    onChange={handleTitleChange}
                    style={styles.input}
                    disabled={isSaving}
                    aria-label="Note Title"
                />
            </div>

            <div style={styles.formGroup}>
                 <label style={styles.label}>Content</label>
                 {/* Render editor only when originalNote is loaded to prevent issues */}
                 {originalNote !== null && (
                     <AIEditorWrapper
                         projectId={projectId}
                         value={content}
                         onChange={handleContentChange}
                         // Pass other necessary props like uniqueId if needed by wrapper
                     />
                 )}
            </div>

            <button
                onClick={handleSaveNote}
                disabled={isSaving || !hasUnsavedChanges} // Disable if saving or no changes
                style={{
                    ...styles.saveButton,
                    ...(isSaving || !hasUnsavedChanges ? styles.disabledButton : {})
                }}
            >
                {isSaving ? 'Saving...' : 'Save Note'}
            </button>
        </div>
    );
}

export default NoteEditPage;