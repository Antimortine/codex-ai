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

// --- MODIFICATION: Import React ---
import React, { memo } from 'react';
// --- END MODIFICATION ---
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';

// Basic styling (remains the same)
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
        marginTop:'5px',
        display: 'inline-block',
        marginLeft: '10px',
    },
    loadingIndicator: {
        marginLeft: '5px',
        fontStyle: 'italic',
        fontSize: '0.9em',
    },
    // Styles for Split Chapter UI (re-using some modal styles)
    splitInputArea: {
        marginTop: '10px',
        padding: '10px',
        border: '1px dashed #ffc107',
        borderRadius: '4px',
        backgroundColor: '#fff9e6',
        marginLeft: '20px', // Align with scene list area
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
    },
    splitButtonDisabled: {
        cursor: 'not-allowed',
        backgroundColor: '#ffeeba',
        color: '#666',
    }
};

// --- MODIFICATION: Wrap component definition in memo ---
const ChapterSection = memo(function ChapterSection({ // Use memo and give the function a name for DevTools
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
    // Split Chapter Props
    splitInputContentForThisChapter,
    isSplittingThisChapter,
    splitErrorForThisChapter,
    onSplitInputChange,
    onSplitChapter,
}) {

    // --- Component logic remains the same ---
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
                        <button
                            onClick={() => onSaveChapter(chapter.id, editedChapterTitleForInput)}
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
}); // --- END MODIFICATION: Close memo HOC ---

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