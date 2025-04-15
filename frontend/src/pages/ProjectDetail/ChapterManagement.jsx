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
import ChapterSection from '../../components/ChapterSection'; // Corrected import path

// Styles (keep existing styles)
const styles = {
    container: { marginBottom: '20px', border: '1px solid #e0e0e0', borderRadius: '5px', padding: '15px', backgroundColor: '#f9f9f9', },
    header: { display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '15px', paddingBottom: '10px', borderBottom: '1px solid #ccc', },
    heading: { margin: 0, fontSize: '1.4em', },
    newChapterForm: { display: 'flex', gap: '10px', marginTop: '10px', marginBottom: '20px', },
    input: { padding: '8px 10px', fontSize: '1em', flexGrow: 1, marginRight: '0', border: '1px solid #ccc', borderRadius: '4px', },
    addButton: { padding: '8px 15px', backgroundColor: '#0f9d58', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '1em', whiteSpace: 'nowrap', },
    disabledButton: { opacity: 0.6, cursor: 'not-allowed', },
    chapterList: { listStyle: 'none', padding: 0, },
    chapterItemContainer: { marginBottom: '20px', },
    errorMessage: { color: 'red', marginTop: '5px', fontSize: '0.9em', },
    loadingText: { fontStyle: 'italic', color: '#555', },
};

/**
 * ChapterManagement component - Acts as a container and passes props down.
 */
function ChapterManagement({
    // Core Data
    projectId, chapters, scenes, isLoadingChapters, isLoadingScenes,
    // Chapter CRUD
    newChapterTitle, setNewChapterTitle, onCreateChapter,
    onDeleteChapter, // Received
    // Chapter Editing
    editingChapterId, editedChapterTitleForInput, onTitleInputChange, isSavingChapter,
    saveChapterError, onEditChapter, onSaveChapter, onCancelEditChapter, chapterErrors,
    // Scene CRUD
    onDeleteScene, onCreateScene, sceneErrors,
    // AI Scene Generation
    onGenerateScene, generationSummaryForInput, onSummaryChange, isGeneratingSceneForThisChapter,
    generatingChapterId, directSourcesForInput, onDirectSourcesChange,
    // AI Chapter Splitting
    splitInputContentForThisChapter,
    onSplitInputChange, // Received
    isSplittingThisChapter, splittingChapterId, onSplitChapter,
    // Chapter Compilation
    isCompilingThisChapter, compilingChapterId, onCompileChapter,
    // Global State
    isAnyOperationLoading,
}) {

    const handleSubmitNewChapter = (e) => {
        e.preventDefault();
        if (!newChapterTitle.trim() || isAnyOperationLoading) return;
        onCreateChapter();
    };

    return (
        <section data-testid="chapter-management-section" style={styles.container}>
            <div style={styles.header}> <h2 style={styles.heading}>Chapters</h2> </div>
            <form onSubmit={handleSubmitNewChapter} style={styles.newChapterForm}>
                <input type="text" value={newChapterTitle} onChange={(e) => setNewChapterTitle(e.target.value)}
                    placeholder="New chapter title..." style={styles.input} disabled={isAnyOperationLoading}
                    aria-label="New chapter title" data-testid="new-chapter-input" />
                <button type="submit" disabled={!newChapterTitle.trim() || isAnyOperationLoading} style={{
                        ...styles.addButton, ...((!newChapterTitle.trim() || isAnyOperationLoading) ? styles.disabledButton : {}), }}
                    data-testid="add-chapter-button"> + Add Chapter </button>
            </form>
             {chapterErrors?.general && <p style={styles.errorMessage}>{chapterErrors.general}</p>}

            {isLoadingChapters ? ( <p style={styles.loadingText}>Loading chapters...</p>
            ) : chapters.length === 0 ? ( <p>No chapters yet. Add your first chapter above.</p>
            ) : (
                <ul style={styles.chapterList}>
                    {chapters.map((chapter) => {
                        const isEditingThis = editingChapterId === chapter.id;
                        const isSavingThis = isEditingThis && isSavingChapter;
                        const saveErrorForThis = chapterErrors?.[chapter.id] || (isSavingThis ? saveChapterError : null);
                        const scenesForThis = scenes[chapter.id] || [];
                        const isLoadingScenesForThis = isLoadingScenes[chapter.id] || false;
                        const isGeneratingForThis = isGeneratingSceneForThisChapter && generatingChapterId === chapter.id;
                        const generationErrorForThis = sceneErrors?.[`gen_${chapter.id}`];
                        const generationSummaryValue = generationSummaryForInput[chapter.id] || '';
                        const isSplittingThis = isSplittingThisChapter && splittingChapterId === chapter.id;
                        const splitErrorForThis = chapterErrors?.[`split_${chapter.id}`];
                        const splitInputValue = splitInputContentForThisChapter[chapter.id] || '';
                        const isCompilingThis = isCompilingThisChapter && compilingChapterId === chapter.id;
                        const compileErrorForThis = chapterErrors?.[`compile_${chapter.id}`];

                        return (
                            <li key={chapter.id} style={styles.chapterItemContainer}>
                                <ChapterSection
                                    // Pass all props down
                                    chapter={chapter} projectId={projectId} scenesForChapter={scenesForThis}
                                    isLoadingChapterScenes={isLoadingScenesForThis}
                                    isEditingThisChapter={isEditingThis}
                                    editedChapterTitleForInput={isEditingThis ? editedChapterTitleForInput : chapter.title}
                                    onTitleInputChange={onTitleInputChange} isSavingThisChapter={isSavingThis}
                                    saveChapterError={saveErrorForThis} onEditChapter={onEditChapter}
                                    onSaveChapter={onSaveChapter} onCancelEditChapter={onCancelEditChapter}
                                    onDeleteChapter={onDeleteChapter} // Pass down
                                    onCreateScene={onCreateScene} onDeleteScene={onDeleteScene}
                                    isGeneratingSceneForThisChapter={isGeneratingForThis}
                                    generationErrorForThisChapter={generationErrorForThis}
                                    generationSummaryForInput={generationSummaryValue} onGenerateScene={(chapterId, summary, sources) => onGenerateScene(chapterId, summary, sources)}
                                    onSummaryChange={onSummaryChange}
                                    directSourcesForInput={directSourcesForInput && directSourcesForInput[chapter.id] || []}
                                    onDirectSourcesChange={onDirectSourcesChange}
                                    splitInputContentForThisChapter={splitInputValue}
                                    isSplittingThisChapter={isSplittingThis} splitErrorForThisChapter={splitErrorForThis}
                                    onSplitInputChange={onSplitInputChange} // Pass down
                                    onSplitChapter={onSplitChapter}
                                    isCompilingThisChapter={isCompilingThis} compileErrorForThisChapter={compileErrorForThis}
                                    onCompileChapter={onCompileChapter}
                                    isAnyOperationLoading={isAnyOperationLoading}
                                />
                                {/* Display scene deletion errors */}
                                {Object.keys(sceneErrors || {}).filter(key => key.startsWith(`del_`) && scenesForThis.some(s => `del_${s.id}` === key)).map(key => (
                                     <p key={key} style={{...styles.errorMessage, marginLeft: '15px'}}>Scene Error: {sceneErrors[key]}</p>
                                ))}
                            </li>
                        );
                    })}
                </ul>
            )}
        </section>
    );
}

// Update PropTypes - Add onSplitInputChange
ChapterManagement.propTypes = {
    // Core Data
    projectId: PropTypes.string.isRequired, chapters: PropTypes.array.isRequired, scenes: PropTypes.object.isRequired,
    isLoadingChapters: PropTypes.bool.isRequired, isLoadingScenes: PropTypes.object.isRequired,
    // Chapter CRUD
    newChapterTitle: PropTypes.string.isRequired, setNewChapterTitle: PropTypes.func.isRequired,
    onCreateChapter: PropTypes.func.isRequired, onDeleteChapter: PropTypes.func.isRequired,
    // Chapter Editing
    editingChapterId: PropTypes.string, editedChapterTitleForInput: PropTypes.string.isRequired,
    onTitleInputChange: PropTypes.func.isRequired, isSavingChapter: PropTypes.bool.isRequired,
    saveChapterError: PropTypes.string, onEditChapter: PropTypes.func.isRequired,
    onSaveChapter: PropTypes.func.isRequired, onCancelEditChapter: PropTypes.func.isRequired,
    chapterErrors: PropTypes.object,
    // Scene CRUD
    onDeleteScene: PropTypes.func.isRequired, onCreateScene: PropTypes.func.isRequired, sceneErrors: PropTypes.object,
    // AI Scene Generation
    onGenerateScene: PropTypes.func.isRequired,
    generationSummaryForInput: PropTypes.object.isRequired,
    onSummaryChange: PropTypes.func.isRequired,
    isGeneratingSceneForThisChapter: PropTypes.bool.isRequired,
    generatingChapterId: PropTypes.string,
    directSourcesForInput: PropTypes.object,
    onDirectSourcesChange: PropTypes.func,
    // AI Chapter Splitting
    splitInputContentForThisChapter: PropTypes.object.isRequired,
    onSplitInputChange: PropTypes.func.isRequired, // *** ADDED PROP TYPE ***
    isSplittingThisChapter: PropTypes.bool.isRequired, splittingChapterId: PropTypes.string,
    onSplitChapter: PropTypes.func.isRequired,
    // Chapter Compilation
    isCompilingThisChapter: PropTypes.bool.isRequired, compilingChapterId: PropTypes.string,
    onCompileChapter: PropTypes.func.isRequired,
    // Global State
    isAnyOperationLoading: PropTypes.bool.isRequired,
};

export default ChapterManagement;