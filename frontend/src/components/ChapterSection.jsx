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

import React, { memo } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

// Basic styling (remains the same)
const styles = {
    chapterSection: {
        border: '1px solid #eee',
        padding: '10px',
        marginBottom: '10px',
        backgroundColor: '#fff', // Added background for clarity
        borderRadius: '4px', // Added border radius
    },
    titleArea: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: '10px', // Increased margin
        paddingBottom: '5px', // Added padding
        borderBottom: '1px solid #eee', // Added border
    },
    titleEditInput: {
        marginRight: '0.5rem',
        fontSize: '1em',
        padding: '4px 6px', // Adjusted padding
    },
    titleEditActions: {
        marginLeft: '0.5rem',
        display: 'flex', // Align buttons
        gap: '5px', // Space between buttons
    },
    titleDisplay: {
        fontWeight: 'bold',
        fontSize: '1.1em', // Slightly larger title
    },
    actionButton: {
        marginLeft: '0.5rem', // Reduced margin
        fontSize: '0.85em', // Slightly smaller
        cursor: 'pointer',
        padding: '3px 8px', // Adjusted padding
        border: '1px solid #ccc',
        borderRadius: '3px',
        backgroundColor: '#f8f9fa',
    },
    deleteButton: {
        marginLeft: '0.5rem', // Reduced margin
        color: '#dc3545', // Bootstrap danger red
        cursor: 'pointer',
        fontSize: '0.85em',
        padding: '3px 8px',
        border: '1px solid #dc3545',
        borderRadius: '3px',
        backgroundColor: '#f8f9fa',
    },
    sceneList: {
        listStyle: 'none',
        paddingLeft: '15px', // Reduced padding
        marginTop: '10px', // Added margin top
    },
    sceneListItem: {
        marginBottom: '0.4rem', // Adjusted margin
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '0.95em', // Slightly larger scene text
    },
    sceneDeleteButton: {
        marginLeft: '1rem',
        fontSize: '0.8em',
        color: '#fd7e14', // Bootstrap orange
        cursor: 'pointer',
        background: 'none',
        border: 'none',
        padding: '2px 5px',
    },
    loadingText: {
        marginLeft: '20px',
        fontStyle: 'italic',
        color: '#6c757d', // Bootstrap secondary color
    },
    addGenerateArea: {
        marginLeft: '15px', // Reduced margin
        marginTop: '15px', // Increased margin
        borderTop: '1px dashed #ccc',
        paddingTop: '15px', // Increased padding
    },
    generateInputArea: {
        marginTop: '10px',
        padding: '8px', // Adjusted padding
        backgroundColor: '#f0f8ff',
        borderRadius: '3px',
        display: 'flex', // Use flexbox
        alignItems: 'center', // Align items vertically
        flexWrap: 'wrap', // Allow wrapping
        gap: '8px', // Space between items
    },
    summaryInput: {
        fontSize: '0.9em',
        // marginRight: '5px', // Removed, using gap
        minWidth: '250px',
        flexGrow: 1, // Allow input to grow
        padding: '4px 6px',
    },
    errorText: {
        color: 'red',
        fontSize: '0.9em',
        marginTop: '5px',
        width: '100%', // Ensure error takes full width if wrapped
    },
    inlineErrorText: {
        color: 'red',
        fontSize: '0.9em',
        // marginTop:'5px', // Removed, using gap
        display: 'inline-block',
        // marginLeft: '10px', // Removed, using gap
    },
    loadingIndicator: {
        // marginLeft: '5px', // Removed, using gap
        fontStyle: 'italic',
        fontSize: '0.9em',
        color: '#6c757d',
    },
    splitInputArea: {
        marginTop: '10px',
        padding: '10px',
        border: '1px dashed #ffc107',
        borderRadius: '4px',
        backgroundColor: '#fff9e6',
        marginLeft: '15px', // Align with scene list area
    },
    splitTextarea: {
        width: '98%',
        minHeight: '100px',
        marginTop: '5px',
        marginBottom: '5px',
        display: 'block',
    },
    splitButton: {
        cursor: 'pointer',
        backgroundColor: '#ffc107',
        color: '#333',
        padding: '4px 10px', // Adjusted padding
        border: '1px solid #dda800',
        borderRadius: '3px',
    },
    splitButtonDisabled: {
        cursor: 'not-allowed',
        backgroundColor: '#ffeeba',
        color: '#666',
        padding: '4px 10px',
        border: '1px solid #ffdf7e',
        borderRadius: '3px',
    },
    // --- ADDED: Styles for chapter plan/synopsis links ---
    chapterLinks: {
        fontSize: '0.85em',
        marginLeft: '15px',
        marginTop: '8px',
        display: 'flex',
        gap: '15px',
    }
    // --- END ADDED ---
};

const ChapterSection = memo(function ChapterSection({
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
    onTitleInputChange,
    splitInputContentForThisChapter,
    isSplittingThisChapter,
    splitErrorForThisChapter,
    onSplitInputChange,
    onSplitChapter,
}) {

    const chapterHasScenes = scenesForChapter && scenesForChapter.length > 0;
    const disableChapterActions = isAnyOperationLoading || isLoadingChapterScenes;
    const disableGenerateButton = isAnyOperationLoading || isLoadingChapterScenes || isGeneratingSceneForThisChapter;
    const disableSummaryInput = isAnyOperationLoading || isGeneratingSceneForThisChapter;
    const disableSplitButton = isAnyOperationLoading || isLoadingChapterScenes || chapterHasScenes || !splitInputContentForThisChapter?.trim() || isSplittingThisChapter;
    const splitButtonTitle = chapterHasScenes ? "Cannot split chapter that already has scenes"
                           : !splitInputContentForThisChapter?.trim() ? "Paste chapter content below to enable splitting"
                           : isSplittingThisChapter ? "AI is currently splitting this chapter..."
                           : isAnyOperationLoading ? "Another operation is in progress..."
                           : "Split this chapter into scenes using AI";
    const splitButtonStyle = disableSplitButton ? styles.splitButtonDisabled : styles.splitButton;


    return (
        <div data-testid={`chapter-section-${chapter.id}`} style={styles.chapterSection}>
            {/* Chapter Title/Edit UI */}
            <div style={styles.titleArea}>
                {isEditingThisChapter ? (
                    <div style={{ flexGrow: 1, marginRight: '1rem' }}>
                        <input
                            type="text"
                            value={editedChapterTitleForInput}
                            onChange={onTitleInputChange}
                            disabled={isSavingThisChapter}
                            style={styles.titleEditInput}
                            aria-label="Chapter Title"
                        />
                        <span style={styles.titleEditActions}>
                            <button
                                onClick={() => onSaveChapter(chapter.id, editedChapterTitleForInput)}
                                disabled={isSavingThisChapter || !editedChapterTitleForInput?.trim()}
                            >
                                {isSavingThisChapter ? 'Saving...' : 'Save'}
                            </button>
                            <button
                                onClick={onCancelEditChapter}
                                disabled={isSavingThisChapter}
                            >
                                Cancel
                            </button>
                        </span>
                        {saveChapterError && <p data-testid={`chapter-save-error-${chapter.id}`} style={styles.errorText}>Save Error: {saveChapterError}</p>}
                    </div>
                ) : (
                    <strong data-testid={`chapter-title-${chapter.id}`} style={styles.titleDisplay}>{chapter.order}: {chapter.title}</strong>
                )}
                {!isEditingThisChapter && (
                    <div style={{ whiteSpace: 'nowrap' }}> {/* Prevent buttons wrapping */}
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

            {/* --- ADDED: Chapter Plan/Synopsis Links --- */}
            <div style={styles.chapterLinks}>
                <Link to={`/projects/${projectId}/chapters/${chapter.id}/plan`}>Edit Chapter Plan</Link>
                <Link to={`/projects/${projectId}/chapters/${chapter.id}/synopsis`}>Edit Chapter Synopsis</Link>
            </div>
            {/* --- END ADDED --- */}


            {/* Scene List or Split Area or Loading */}
            {isLoadingChapterScenes ? (
                <p style={styles.loadingText}>Loading scenes...</p>
            ) : (
                !chapterHasScenes ? (
                    <div style={styles.splitInputArea}>
                        <label htmlFor={`split-input-${chapter.id}`} style={{ display: 'block', marginBottom: '5px', fontSize: '0.9em', fontWeight: 'bold' }}>
                            Paste Full Chapter Content Here to Split:
                        </label>
                        <textarea
                            id={`split-input-${chapter.id}`}
                            style={styles.splitTextarea}
                            rows={6}
                            placeholder={`Paste the full text of chapter "${chapter.title}" here...`}
                            value={splitInputContentForThisChapter || ''}
                            onChange={(e) => onSplitInputChange(chapter.id, e.target.value)}
                            disabled={isSplittingThisChapter || isAnyOperationLoading}
                            aria-label="Chapter content to split" // Accessibility
                        />
                        <button
                            onClick={() => onSplitChapter(chapter.id)}
                            style={splitButtonStyle}
                            disabled={disableSplitButton}
                            title={splitButtonTitle}
                        >
                            {isSplittingThisChapter ? 'Splitting...' : 'Split Chapter (AI)'}
                        </button>
                        {splitErrorForThisChapter && (
                            <p data-testid={`split-error-${chapter.id}`} style={styles.inlineErrorText}>
                                Split Error: {splitErrorForThisChapter}
                            </p>
                        )}
                    </div>
                ) : (
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
                        disabled={disableSummaryInput} // Use corrected flag
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
                    {generationErrorForThisChapter && <p data-testid={`chapter-gen-error-${chapter.id}`} style={styles.errorText}>Generate Error: {generationErrorForThisChapter}</p>}
                </div>
            </div>
        </div>
    );
});

// PropTypes remain the same
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
    onTitleInputChange: PropTypes.func.isRequired,
    // Split Chapter Props
    splitInputContentForThisChapter: PropTypes.string, // Can be undefined initially
    isSplittingThisChapter: PropTypes.bool.isRequired,
    splitErrorForThisChapter: PropTypes.string,
    onSplitInputChange: PropTypes.func.isRequired,
    onSplitChapter: PropTypes.func.isRequired,
};

export default ChapterSection;