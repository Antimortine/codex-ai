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

// Basic styling (can be moved to CSS or refined)
const styles = {
    chapterSection: {
        border: '1px solid #eee',
        padding: '10px',
        marginBottom: '10px',
    },
    titleArea: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '5px',
    },
    titleEditInput: {
        marginRight: '0.5rem',
        fontSize: '1em',
        padding: '2px 4px',
    },
    titleEditActions: {
        marginLeft: '0.5rem',
    },
    titleDisplay: {
        fontWeight: 'bold',
    },
    actionButton: {
        marginLeft: '1rem',
        fontSize: '0.9em',
        cursor: 'pointer',
    },
    deleteButton: {
        marginLeft: '1rem',
        color: 'red',
        cursor: 'pointer',
        fontSize: '0.9em',
    },
    sceneList: {
        listStyle: 'none',
        paddingLeft: '20px',
    },
    sceneListItem: {
        marginBottom: '0.3rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
    },
    sceneDeleteButton: {
        marginLeft: '1rem',
        fontSize: '0.8em',
        color: 'orange',
        cursor: 'pointer',
    },
    loadingText: {
        marginLeft: '20px',
    },
    addGenerateArea: {
        marginLeft: '20px',
        marginTop: '10px',
        borderTop: '1px dashed #ccc',
        paddingTop: '10px',
    },
    generateInputArea: {
        marginTop: '10px',
        padding: '5px',
        backgroundColor: '#f0f8ff',
        borderRadius: '3px',
    },
    summaryInput: {
        fontSize: '0.9em',
        marginRight: '5px',
        minWidth: '250px',
    },
    errorText: {
        color: 'red',
        fontSize: '0.9em',
        marginTop: '5px',
    },
    inlineErrorText: {
        color: 'red',
        fontSize: '0.9em',
        marginTop: '5px',
        display: 'inline-block',
        marginLeft: '10px',
    },
    loadingIndicator: {
        marginLeft: '5px',
        fontStyle: 'italic',
        fontSize: '0.9em',
    }
    // NOTE: Split Chapter styles are intentionally omitted
};

function ChapterSection({
    chapter,
    scenesForChapter,
    isLoadingChapterScenes,
    isEditingThisChapter,
    editedChapterTitleForInput,
    isSavingThisChapter,
    saveChapterError,
    isGeneratingSceneForThisChapter,
    generationErrorForThisChapter,
    generationSummaryForInput,
    isAnyOperationLoading,
    projectId,
    onEditChapter,
    onSaveChapter,
    onCancelEditChapter,
    onDeleteChapter,
    onCreateScene,
    onDeleteScene,
    onGenerateScene,
    onSummaryChange,
    onTitleInputChange, // Added prop for handling input change
    // Omit props related to Split Chapter for now
}) {

    const chapterHasScenes = scenesForChapter && scenesForChapter.length > 0;
    const disableChapterActions = isAnyOperationLoading || isLoadingChapterScenes;
    // Combine flags for disabling generate button
    const disableGenerateButton = isAnyOperationLoading || isLoadingChapterScenes || isGeneratingSceneForThisChapter;
    // Combine flags for disabling summary input (should be disabled if any operation or specifically generating for this chapter)
    const disableSummaryInput = isAnyOperationLoading || isGeneratingSceneForThisChapter;


    return (
        <div data-testid={`chapter-section-${chapter.id}`} style={styles.chapterSection}>
            {/* Chapter Title/Edit UI */}
            <div style={styles.titleArea}>
                {isEditingThisChapter ? (
                    <div style={{ flexGrow: 1, marginRight: '1rem' }}>
                        <input
                            type="text"
                            value={editedChapterTitleForInput}
                            onChange={onTitleInputChange} // Use the passed-in handler
                            disabled={isSavingThisChapter}
                            style={styles.titleEditInput}
                            aria-label="Chapter Title"
                        />
                        <button
                            onClick={() => onSaveChapter(chapter.id, editedChapterTitleForInput)} // Pass edited title from props
                            disabled={isSavingThisChapter || !editedChapterTitleForInput?.trim()}
                        >
                            {isSavingThisChapter ? 'Saving...' : 'Save'}
                        </button>
                        <button
                            onClick={onCancelEditChapter}
                            disabled={isSavingThisChapter}
                            style={styles.titleEditActions}
                        >
                            Cancel
                        </button>
                        {/* Add data-testid to the error message paragraph */}
                        {saveChapterError && <p data-testid={`chapter-save-error-${chapter.id}`} style={styles.errorText}>Save Error: {saveChapterError}</p>}
                    </div>
                ) : (
                    <strong data-testid={`chapter-title-${chapter.id}`} style={styles.titleDisplay}>{chapter.order}: {chapter.title}</strong>
                )}
                {!isEditingThisChapter && (
                    <div>
                        <button
                            onClick={() => onEditChapter(chapter)}
                            style={styles.actionButton}
                            disabled={disableChapterActions}
                            title={disableChapterActions ? "Another operation is in progress..." : "Edit chapter title"}
                        >
                            Edit Title
                        </button>
                        <button
                            onClick={() => onDeleteChapter(chapter.id, chapter.title)}
                            style={styles.deleteButton}
                            disabled={disableChapterActions}
                            title={disableChapterActions ? "Another operation is in progress..." : "Delete chapter"}
                        >
                            Delete Chapter
                        </button>
                    </div>
                )}
            </div>

            {/* Scene List or Loading */}
            {isLoadingChapterScenes ? (
                <p style={styles.loadingText}>Loading scenes...</p>
            ) : (
                chapterHasScenes ? (
                    <ul style={styles.sceneList}>
                        {scenesForChapter.map(scene => (
                            <li key={scene.id} style={styles.sceneListItem}>
                                <Link to={`/projects/${projectId}/chapters/${chapter.id}/scenes/${scene.id}`}>
                                    {scene.order}: {scene.title}
                                </Link>
                                <button
                                    onClick={() => onDeleteScene(chapter.id, scene.id, scene.title)}
                                    style={styles.sceneDeleteButton}
                                    disabled={isAnyOperationLoading}
                                    title={isAnyOperationLoading ? "Another operation is in progress..." : "Delete scene"}
                                >
                                    Del Scene
                                </button>
                            </li>
                        ))}
                    </ul>
                ) : (
                    // Display message if no scenes and not loading
                    <p style={styles.loadingText}>No scenes in this chapter yet.</p>
                    // NOTE: Split Chapter input area is intentionally omitted here
                )
            )}

            {/* Add Scene / Generate Scene Area */}
            <div style={styles.addGenerateArea}>
                <button
                    onClick={() => onCreateScene(chapter.id)}
                    style={{ marginRight: '10px' }}
                    disabled={isLoadingChapterScenes || isAnyOperationLoading}
                    title={isLoadingChapterScenes || isAnyOperationLoading ? "Operation in progress..." : "Add a new scene manually"}
                >
                    + Add Scene Manually
                </button>
                <div style={styles.generateInputArea}>
                    <label htmlFor={`summary-${chapter.id}`} style={{ fontSize: '0.9em', marginRight: '5px' }}>
                        Optional Prompt/Summary for AI Scene Generation:
                    </label>
                    <input
                        type="text"
                        id={`summary-${chapter.id}`}
                        value={generationSummaryForInput}
                        onChange={(e) => onSummaryChange(chapter.id, e.target.value)}
                        placeholder="e.g., Character meets the informant"
                        disabled={disableSummaryInput} // Use combined disable flag
                        style={styles.summaryInput}
                    />
                    <button
                        onClick={() => onGenerateScene(chapter.id, generationSummaryForInput)}
                        disabled={disableGenerateButton} // Correct flag used here
                        title={disableGenerateButton ? "Operation in progress..." : "Generate the next scene using AI"}
                    >
                        {isGeneratingSceneForThisChapter ? 'Generating...' : '+ Add Scene using AI'}
                    </button>
                    {isGeneratingSceneForThisChapter && <span style={styles.loadingIndicator}> (AI is working...)</span>}
                    {/* Add data-testid to the error message paragraph */}
                    {generationErrorForThisChapter && <p data-testid={`chapter-gen-error-${chapter.id}`} style={styles.errorText}>Generate Error: {generationErrorForThisChapter}</p>}
                </div>
            </div>
        </div>
    );
}

ChapterSection.propTypes = {
    chapter: PropTypes.shape({
        id: PropTypes.string.isRequired,
        title: PropTypes.string.isRequired,
        order: PropTypes.number.isRequired,
    }).isRequired,
    scenesForChapter: PropTypes.arrayOf(PropTypes.shape({
        id: PropTypes.string.isRequired,
        title: PropTypes.string.isRequired,
        order: PropTypes.number.isRequired,
    })).isRequired,
    isLoadingChapterScenes: PropTypes.bool.isRequired,
    isEditingThisChapter: PropTypes.bool.isRequired,
    editedChapterTitleForInput: PropTypes.string.isRequired,
    isSavingThisChapter: PropTypes.bool.isRequired,
    saveChapterError: PropTypes.string,
    isGeneratingSceneForThisChapter: PropTypes.bool.isRequired,
    generationErrorForThisChapter: PropTypes.string,
    generationSummaryForInput: PropTypes.string.isRequired,
    isAnyOperationLoading: PropTypes.bool.isRequired,
    projectId: PropTypes.string.isRequired,
    onEditChapter: PropTypes.func.isRequired,
    onSaveChapter: PropTypes.func.isRequired,
    onCancelEditChapter: PropTypes.func.isRequired,
    onDeleteChapter: PropTypes.func.isRequired,
    onCreateScene: PropTypes.func.isRequired,
    onDeleteScene: PropTypes.func.isRequired,
    onGenerateScene: PropTypes.func.isRequired,
    onSummaryChange: PropTypes.func.isRequired,
    onTitleInputChange: PropTypes.func.isRequired, // Added prop type
};

export default ChapterSection;