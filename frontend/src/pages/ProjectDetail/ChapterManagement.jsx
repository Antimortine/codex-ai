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

import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import ChapterSection from '../../components/ChapterSection';

// Styles for the chapter management components
const styles = {
    container: {
        marginBottom: '20px'
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
    },
    heading: {
        margin: 0
    },
    newChapterForm: {
        display: 'flex',
        marginTop: '10px',
        marginBottom: '20px'
    },
    input: {
        padding: '8px',
        fontSize: '1em',
        width: '250px',
        marginRight: '10px'
    },
    addButton: {
        padding: '8px 15px',
        backgroundColor: '#0f9d58',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer'
    },
    disabledButton: {
        opacity: 0.6,
        cursor: 'not-allowed'
    },
    chapterList: {
        listStyle: 'none',
        padding: 0
    },
    chapterItem: {
        marginBottom: '15px',
        padding: '15px',
        borderRadius: '4px',
        backgroundColor: '#f5f5f5',
        border: '1px solid #ddd'
    },
    chapterHeader: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '10px'
    },
    editingContainer: {
        display: 'flex',
        alignItems: 'center',
        marginBottom: '10px'
    },
    actionButton: {
        marginLeft: '10px',
        padding: '5px 10px',
        borderRadius: '4px',
        border: 'none',
        cursor: 'pointer',
        fontSize: '0.9em'
    },
    editButton: {
        backgroundColor: '#4285f4',
        color: 'white'
    },
    deleteButton: {
        backgroundColor: '#db4437',
        color: 'white'
    },
    generateButton: {
        backgroundColor: '#f4b400',
        color: 'white'
    },
    compileButton: {
        backgroundColor: '#0f9d58',
        color: 'white'
    },
    sceneList: {
        listStyle: 'none',
        padding: '0 0 0 20px'
    },
    sceneItem: {
        marginBottom: '8px'
    },
    errorMessage: {
        color: 'red',
        marginTop: '5px'
    },
    summaryText: {
        fontSize: '0.9em',
        color: '#666',
        fontStyle: 'italic',
        marginTop: '5px'
    }
};

/**
 * ChapterManagement component that handles chapter listing, creation, editing, and deletion
 */
function ChapterManagement({
    projectId,
    chapters,
    isLoading,
    newChapterTitle,
    setNewChapterTitle,
    onCreateChapter,
    onDeleteChapter,
    editingChapterId,
    editedChapterTitle,
    setEditedChapterTitle,
    isSavingChapter,
    saveChapterError,
    onEditChapter,
    onSaveChapterTitle,
    onCancelChapterEdit,
    onGenerateScene,
    onSplitChapter,
    onCompileChapter,
    isGeneratingScene,
    generatingChapterId,
    generationSummaries,
    isCompilingChapter,
    compilingChapterId,
    scenes,
    isLoadingScenes,
    onDeleteScene,
    isAnyOperationLoading
}) {
    // Handle new chapter form submission
    const handleSubmit = (e) => {
        e.preventDefault();
        onCreateChapter();
    };

    return (
        <section style={styles.container}>
            <div style={styles.header}>
                <h2 style={styles.heading}>Chapters</h2>
            </div>
            
            {/* New chapter form */}
            <form onSubmit={handleSubmit} style={styles.newChapterForm}>
                <input
                    type="text"
                    value={newChapterTitle}
                    onChange={(e) => setNewChapterTitle(e.target.value)}
                    placeholder="New chapter title"
                    style={styles.input}
                    data-testid="new-chapter-input"
                />
                <button
                    type="submit"
                    disabled={!newChapterTitle.trim() || isAnyOperationLoading}
                    style={{
                        ...styles.addButton,
                        ...((!newChapterTitle.trim() || isAnyOperationLoading) ? styles.disabledButton : {})
                    }}
                    data-testid="add-chapter-button"
                >
                    Add Chapter
                </button>
            </form>
            
            {/* Chapter list */}
            {isLoading ? (
                <p>Loading chapters...</p>
            ) : chapters.length === 0 ? (
                <p>No chapters yet. Add your first chapter to get started.</p>
            ) : (
                <ul style={styles.chapterList}>
                    {chapters.map(chapter => (
                        <li key={chapter.id} style={styles.chapterItem}>
                            {editingChapterId === chapter.id ? (
                                <div style={styles.editingContainer}>
                                    <input
                                        type="text"
                                        value={editedChapterTitle}
                                        onChange={(e) => setEditedChapterTitle(e.target.value)}
                                        style={styles.input}
                                        autoFocus
                                        data-testid={`edit-chapter-input-${chapter.id}`}
                                    />
                                    <button
                                        onClick={onSaveChapterTitle}
                                        disabled={!editedChapterTitle.trim() || isSavingChapter}
                                        style={{
                                            ...styles.actionButton,
                                            ...styles.editButton,
                                            ...((!editedChapterTitle.trim() || isSavingChapter) ? styles.disabledButton : {})
                                        }}
                                        data-testid={`save-chapter-button-${chapter.id}`}
                                    >
                                        {isSavingChapter ? 'Saving...' : 'Save'}
                                    </button>
                                    <button
                                        onClick={onCancelChapterEdit}
                                        disabled={isSavingChapter}
                                        style={{
                                            ...styles.actionButton,
                                            ...styles.deleteButton,
                                            ...(isSavingChapter ? styles.disabledButton : {})
                                        }}
                                        data-testid={`cancel-chapter-edit-button-${chapter.id}`}
                                    >
                                        Cancel
                                    </button>
                                </div>
                            ) : (
                                <div style={styles.chapterHeader}>
                                    <ChapterSection 
                                        chapter={chapter} 
                                        projectId={projectId}
                                        scenesForChapter={scenes[chapter.id] || []}
                                        isLoadingChapterScenes={isLoadingScenes[chapter.id] || false}
                                        isEditingThisChapter={editingChapterId === chapter.id}
                                        editedChapterTitle={editingChapterId === chapter.id ? editedChapterTitle : ''}
                                        isSavingThisChapter={isSavingChapter}
                                        saveChapterError={saveChapterError}
                                        isGeneratingSceneForThisChapter={isGeneratingScene && generatingChapterId === chapter.id}
                                        generationSummaryForInput={generationSummaries[chapter.id] || ''}
                                        isCompilingThisChapter={isCompilingChapter && compilingChapterId === chapter.id}
                                        isAnyOperationLoading={isAnyOperationLoading}
                                        onEditChapter={() => onEditChapter(chapter)}
                                        onSaveChapter={() => onSaveChapterTitle()}
                                        onCancelEditChapter={onCancelChapterEdit}
                                        onDeleteChapter={() => onDeleteChapter(chapter.id)}
                                        onDeleteScene={(sceneId) => onDeleteScene(chapter.id, sceneId)}
                                        onGenerateScene={() => onGenerateScene(chapter.id)}
                                        onSplitChapter={() => onSplitChapter(chapter.id)}
                                        onCompileChapter={() => onCompileChapter(chapter.id)}
                                    />
                                    <div>
                                        <button
                                            onClick={() => onEditChapter(chapter)}
                                            disabled={isAnyOperationLoading}
                                            style={{
                                                ...styles.actionButton,
                                                ...styles.editButton,
                                                ...(isAnyOperationLoading ? styles.disabledButton : {})
                                            }}
                                            data-testid={`edit-chapter-button-${chapter.id}`}
                                        >
                                            Edit Title
                                        </button>
                                        <button
                                            onClick={() => onDeleteChapter(chapter.id)}
                                            disabled={isAnyOperationLoading}
                                            style={{
                                                ...styles.actionButton,
                                                ...styles.deleteButton,
                                                ...(isAnyOperationLoading ? styles.disabledButton : {})
                                            }}
                                            data-testid={`delete-chapter-button-${chapter.id}`}
                                        >
                                            Delete
                                        </button>
                                        <button
                                            onClick={() => onGenerateScene(chapter.id)}
                                            disabled={isAnyOperationLoading}
                                            style={{
                                                ...styles.actionButton,
                                                ...styles.generateButton,
                                                ...(isAnyOperationLoading ? styles.disabledButton : {})
                                            }}
                                            data-testid={`generate-scene-button-${chapter.id}`}
                                        >
                                            {isGeneratingScene && generatingChapterId === chapter.id
                                                ? 'Generating...'
                                                : 'Generate Scene'}
                                        </button>
                                        <button
                                            onClick={() => onSplitChapter(chapter.id)}
                                            disabled={isAnyOperationLoading}
                                            style={{
                                                ...styles.actionButton,
                                                ...styles.generateButton,
                                                ...(isAnyOperationLoading ? styles.disabledButton : {})
                                            }}
                                            data-testid={`split-chapter-button-${chapter.id}`}
                                        >
                                            Split Content
                                        </button>
                                        <button
                                            onClick={() => onCompileChapter(chapter.id)}
                                            disabled={isAnyOperationLoading}
                                            style={{
                                                ...styles.actionButton,
                                                ...styles.compileButton,
                                                ...(isAnyOperationLoading ? styles.disabledButton : {})
                                            }}
                                            data-testid={`compile-chapter-button-${chapter.id}`}
                                        >
                                            {isCompilingChapter && compilingChapterId === chapter.id
                                                ? 'Compiling...'
                                                : 'Compile Chapter'}
                                        </button>
                                    </div>
                                </div>
                            )}
                            
                            {/* Display any error messages */}
                            {editingChapterId === chapter.id && saveChapterError && (
                                <div style={styles.errorMessage} data-testid={`chapter-error-${chapter.id}`}>
                                    {saveChapterError}
                                </div>
                            )}
                            
                            {/* Generation summary */}
                            {generationSummaries[chapter.id] && (
                                <div style={styles.summaryText} data-testid={`generation-summary-${chapter.id}`}>
                                    {generationSummaries[chapter.id]}
                                </div>
                            )}
                            
                            {/* Scene list */}
                            <div style={{ marginTop: '10px' }}>
                                <Link 
                                    to={`/projects/${projectId}/chapters/${chapter.id}/plan`}
                                    style={{ marginRight: '15px' }}
                                >
                                    Chapter Plan
                                </Link>
                                <Link 
                                    to={`/projects/${projectId}/chapters/${chapter.id}/synopsis`}
                                >
                                    Chapter Synopsis
                                </Link>
                            </div>
                            
                            <div style={{ marginTop: '10px' }}>
                                <h4 style={{ margin: '10px 0 5px 0' }}>Scenes</h4>
                                {isLoadingScenes[chapter.id] ? (
                                    <p>Loading scenes...</p>
                                ) : !scenes[chapter.id] || scenes[chapter.id].length === 0 ? (
                                    <p>No scenes yet.</p>
                                ) : (
                                    <ul style={styles.sceneList}>
                                        {scenes[chapter.id].map(scene => (
                                            <li key={scene.id} style={styles.sceneItem}>
                                                <Link to={`/projects/${projectId}/chapters/${chapter.id}/scenes/${scene.id}`}>
                                                    {scene.title}
                                                </Link>
                                                <button
                                                    onClick={() => onDeleteScene(chapter.id, scene.id)}
                                                    disabled={isAnyOperationLoading}
                                                    style={{
                                                        marginLeft: '10px',
                                                        fontSize: '0.8em',
                                                        color: 'white',
                                                        backgroundColor: '#db4437',
                                                        border: 'none',
                                                        borderRadius: '3px',
                                                        padding: '2px 5px',
                                                        cursor: 'pointer',
                                                        ...(isAnyOperationLoading ? styles.disabledButton : {})
                                                    }}
                                                >
                                                    Delete
                                                </button>
                                            </li>
                                        ))}
                                    </ul>
                                )}
                            </div>
                        </li>
                    ))}
                </ul>
            )}
        </section>
    );
}

ChapterManagement.propTypes = {
    projectId: PropTypes.string.isRequired,
    chapters: PropTypes.array.isRequired,
    isLoading: PropTypes.bool.isRequired,
    newChapterTitle: PropTypes.string.isRequired,
    setNewChapterTitle: PropTypes.func.isRequired,
    onCreateChapter: PropTypes.func.isRequired,
    onDeleteChapter: PropTypes.func.isRequired,
    editingChapterId: PropTypes.string,
    editedChapterTitle: PropTypes.string.isRequired,
    setEditedChapterTitle: PropTypes.func.isRequired,
    isSavingChapter: PropTypes.bool.isRequired,
    saveChapterError: PropTypes.string,
    onEditChapter: PropTypes.func.isRequired,
    onSaveChapterTitle: PropTypes.func.isRequired,
    onCancelChapterEdit: PropTypes.func.isRequired,
    onGenerateScene: PropTypes.func.isRequired,
    onSplitChapter: PropTypes.func.isRequired,
    onCompileChapter: PropTypes.func.isRequired,
    isGeneratingScene: PropTypes.bool.isRequired,
    generatingChapterId: PropTypes.string,
    generationSummaries: PropTypes.object.isRequired,
    isCompilingChapter: PropTypes.bool.isRequired,
    compilingChapterId: PropTypes.string,
    scenes: PropTypes.object.isRequired,
    isLoadingScenes: PropTypes.object.isRequired,
    onDeleteScene: PropTypes.func.isRequired,
    isAnyOperationLoading: PropTypes.bool.isRequired
};

export default ChapterManagement;
