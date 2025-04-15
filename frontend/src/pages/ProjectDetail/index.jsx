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
import { useParams, Link } from 'react-router-dom';
import { useProjectData } from './hooks/useProjectData';
import { useChapterOperations } from './hooks/useChapterOperations';
import { useCharacterOperations } from './hooks/useCharacterOperations';
import { useSceneOperations } from './hooks/useSceneOperations';
import ProjectHeader from './ProjectHeader';
import ChapterManagement from './ChapterManagement';
import CharacterManagement from './CharacterManagement';
import ProjectTools from './ProjectTools';
import GeneratedSceneModal from './modals/GeneratedSceneModal';
import SplitChapterModal from './modals/SplitChapterModal';
import CompiledContentModal from './modals/CompiledContentModal';

/**
 * Main ProjectDetail page component that composes all project-related components
 */
function ProjectDetailPage() {
    const { projectId } = useParams();

    // Use the custom hooks to manage state and operations
    const projectData = useProjectData(projectId);
    const chapterOps = useChapterOperations(projectId);
    const characterOps = useCharacterOperations(projectId);
    const sceneOps = useSceneOperations(projectId, chapterOps.chapters);

    // Handle scene creation from chapter splits (passed to Split Modal)
    const handleCreateScenesFromSplitsForModal = async () => {
        if (!chapterOps.chapterIdForSplits || !chapterOps.proposedSplits || chapterOps.proposedSplits.length === 0) {
             console.error("Attempted to create scenes from splits with invalid data.");
            return;
        }
        const success = await sceneOps.handleCreateScenesFromSplits(
            chapterOps.chapterIdForSplits, chapterOps.proposedSplits );
        if (success) { chapterOps.handleCloseSplitModal(); }
        else { console.error("Failed to create scenes from splits."); }
    };

    // Check if any operation is loading to disable buttons
    const isAnyOperationLoading =
        projectData.isLoadingProject || chapterOps.isLoadingChapters ||
        characterOps.isLoadingCharacters || Object.values(sceneOps.isLoadingScenes).some(Boolean) ||
        projectData.isRebuildingIndex || chapterOps.isSavingChapter || chapterOps.isSplittingChapter ||
        sceneOps.isGeneratingScene || sceneOps.isCreatingSceneFromDraft ||
        characterOps.isCreatingCharacter || projectData.isSavingName;

    // Aggregate errors from different hooks (simplified view)
    const generalError = projectData.error || chapterOps.error || characterOps.characterError || null;

    if (generalError && !projectData.project) { // Only show full page error if project itself failed to load
        return ( <div style={{ padding: '20px', color: 'red' }}> <h2>Error Loading Project</h2>
                <p data-testid="project-error">{generalError}</p> <Link to="/">Back to Projects</Link> </div> );
    }
    if (!projectData.isLoadingProject && !projectData.project) {
         return ( <div style={{ padding: '20px' }}> <h2>Project Not Found</h2>
                 <p>The requested project could not be found.</p> <Link to="/">Back to Projects</Link> </div> );
    }

    return (
        <div style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
            <ProjectHeader
                project={projectData.project} isLoading={projectData.isLoadingProject}
                isEditingName={projectData.isEditingName} editedProjectName={projectData.editedProjectName}
                isSavingName={projectData.isSavingName} saveNameError={projectData.saveNameError}
                saveNameSuccess={projectData.saveNameSuccess} setEditedProjectName={projectData.setEditedProjectName}
                onEditClick={projectData.handleEditNameClick} onCancelEdit={projectData.handleCancelNameEdit}
                onSave={projectData.handleSaveProjectName} isAnyOperationLoading={isAnyOperationLoading} />
            <hr />
            <ChapterManagement
                // Core Data
                projectId={projectId} chapters={chapterOps.chapters} scenes={sceneOps.scenes}
                isLoadingChapters={chapterOps.isLoadingChapters} isLoadingScenes={sceneOps.isLoadingScenes}
                // Chapter CRUD
                newChapterTitle={chapterOps.newChapterTitle} setNewChapterTitle={chapterOps.setNewChapterTitle}
                onCreateChapter={chapterOps.handleCreateChapter}
                onDeleteChapter={chapterOps.handleDeleteChapter}
                // Chapter Editing
                editingChapterId={chapterOps.editingChapterId} editedChapterTitle={chapterOps.editedChapterTitle} // For the inline edit input in ChapterManagement (if kept)
                setEditedChapterTitle={chapterOps.setEditedChapterTitle} // Handler for internal ChapterMgt edit
                editedChapterTitleForInput={chapterOps.editedChapterTitle} // Value for ChapterSection edit input
                onTitleInputChange={(e) => chapterOps.setEditedChapterTitle(e.target.value)} // Handler for ChapterSection edit input
                isSavingChapter={chapterOps.isSavingChapter} saveChapterError={chapterOps.saveChapterError} // General error
                onEditChapter={chapterOps.handleEditChapterClick} onSaveChapter={chapterOps.handleSaveChapterTitle}
                onCancelEditChapter={chapterOps.handleCancelChapterEdit} chapterErrors={chapterOps.chapterErrors}
                 // Scene CRUD (within Chapter)
                onDeleteScene={sceneOps.handleDeleteScene} onCreateScene={sceneOps.handleCreateSceneManually}
                 sceneErrors={sceneOps.sceneErrors}
                 // AI Scene Generation (within Chapter)
                onGenerateScene={(chapterId, summary, sources) => sceneOps.handleGenerateSceneDraft(chapterId, summary, sources)} generationSummaryForInput={sceneOps.generationSummaries}
                onSummaryChange={sceneOps.handleSummaryChange} isGeneratingSceneForThisChapter={sceneOps.isGeneratingScene}
                generatingChapterId={sceneOps.generatingChapterId}
                directSourcesForInput={sceneOps.directSources} onDirectSourcesChange={sceneOps.handleDirectSourcesChange}
                 // AI Chapter Splitting (Triggered from Chapter)
                splitInputContentForThisChapter={chapterOps.splitInputContent}
                onSplitInputChange={chapterOps.handleSplitInputChange} // *** ENSURE THIS IS PASSED ***
                isSplittingThisChapter={chapterOps.isSplittingChapter} splittingChapterId={chapterOps.splittingChapterId}
                 onSplitChapter={chapterOps.handleOpenSplitModal}
                 // Chapter Compilation
                isCompilingThisChapter={chapterOps.isCompilingChapter} compilingChapterId={chapterOps.compilingChapterId}
                onCompileChapter={chapterOps.handleCompileChapter}
                 // Global State
                isAnyOperationLoading={isAnyOperationLoading}
            />
            <hr />
            <CharacterManagement
                projectId={projectId} characters={characterOps.characters} isLoading={characterOps.isLoadingCharacters}
                newCharacterName={characterOps.newCharacterName} setNewCharacterName={characterOps.setNewCharacterName}
                onCreateCharacter={characterOps.handleCreateCharacter} onDeleteCharacter={characterOps.handleDeleteCharacter}
                characterError={characterOps.characterError} isAnyOperationLoading={isAnyOperationLoading}
                isCreatingCharacter={characterOps.isCreatingCharacter} />
            <hr />
            <ProjectTools
                projectId={projectId} isRebuildingIndex={projectData.isRebuildingIndex}
                rebuildError={projectData.rebuildError} rebuildSuccessMessage={projectData.rebuildSuccessMessage}
                onRebuildIndex={projectData.handleRebuildIndex} isAnyOperationLoading={isAnyOperationLoading} />

            {/* Modals */}
            {sceneOps.showGeneratedSceneModal && (
                <GeneratedSceneModal
                    sceneTitle={sceneOps.generatedSceneTitle} sceneContent={sceneOps.generatedSceneContent}
                    onTitleChange={sceneOps.setGeneratedSceneTitle} onContentChange={sceneOps.setGeneratedSceneContent}
                    onSave={sceneOps.handleCreateSceneFromDraft} onClose={sceneOps.handleCloseGeneratedSceneModal}
                    isCreating={sceneOps.isCreatingSceneFromDraft} error={sceneOps.createSceneError}
                    sources={sceneOps.generatedSceneSources} />
            )}
            {chapterOps.showSplitModal && (
                <SplitChapterModal
                    chapterId={chapterOps.chapterIdForSplits}
                    inputContent={chapterOps.splitInputContent[chapterOps.chapterIdForSplits] || ''}
                    onInputChange={(content) => chapterOps.handleSplitInputChange(chapterOps.chapterIdForSplits, content)}
                    proposedSplits={chapterOps.proposedSplits} onSplit={chapterOps.handleSplitChapter}
                    onCreateScenes={handleCreateScenesFromSplitsForModal} onClose={chapterOps.handleCloseSplitModal}
                    isSplitting={chapterOps.isSplittingChapter} isCreating={sceneOps.isCreatingSceneFromDraft}
                    splitError={chapterOps.chapterErrors?.[`split_${chapterOps.chapterIdForSplits}`]}
                    createError={sceneOps.sceneErrors?.[`split_create_${chapterOps.chapterIdForSplits}`]} />
            )}
            {chapterOps.showCompiledContentModal && (
                <CompiledContentModal
                    filename={chapterOps.compiledFileName} content={chapterOps.compiledContent}
                    onClose={chapterOps.handleCloseCompileModal}
                    error={chapterOps.chapterErrors?.[`compile_${chapterOps.compilingChapterId}`]}
                    isLoading={chapterOps.isCompilingChapter} />
            )}
        </div>
    );
}

export default ProjectDetailPage;