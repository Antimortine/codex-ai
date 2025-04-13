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

    // Handle scene creation from chapter splits
    const handleCreateScenesFromSplits = async () => {
        const success = await sceneOps.handleCreateScenesFromSplits(
            chapterOps.chapterIdForSplits,
            chapterOps.proposedSplits
        );
        
        if (success) {
            chapterOps.setShowSplitModal(false);
        }
    };

    // Check if any operation is loading to disable buttons
    const isAnyOperationLoading = 
        projectData.isLoadingProject || 
        chapterOps.isLoadingChapters || 
        characterOps.isLoadingCharacters ||
        projectData.isRebuildingIndex || 
        chapterOps.isSplittingChapter || 
        sceneOps.isGeneratingScene;

    // Show error message if any error occurs
    const error = projectData.error || null;

    if (error) {
        return (
            <div style={{ padding: '20px', color: 'red' }}>
                <h2>Error</h2>
                <p data-testid="project-error">{error}</p>
                <Link to="/projects">Back to Projects</Link>
            </div>
        );
    }

    return (
        <div style={{ padding: '20px', maxWidth: '900px', margin: '0 auto' }}>
            {/* Project header with title and edit functionality */}
            <ProjectHeader 
                project={projectData.project}
                isLoading={projectData.isLoadingProject}
                isEditingName={projectData.isEditingName}
                editedProjectName={projectData.editedProjectName}
                isSavingName={projectData.isSavingName}
                saveNameError={projectData.saveNameError}
                saveNameSuccess={projectData.saveNameSuccess}
                setEditedProjectName={projectData.setEditedProjectName}
                onEditClick={projectData.handleEditNameClick}
                onCancelEdit={projectData.handleCancelNameEdit}
                onSave={projectData.handleSaveProjectName}
            />

            <hr />

            {/* Chapters section */}
            <ChapterManagement
                projectId={projectId}
                chapters={chapterOps.chapters}
                isLoading={chapterOps.isLoadingChapters}
                newChapterTitle={chapterOps.newChapterTitle}
                setNewChapterTitle={chapterOps.setNewChapterTitle}
                onCreateChapter={chapterOps.handleCreateChapter}
                onDeleteChapter={chapterOps.handleDeleteChapter}
                editingChapterId={chapterOps.editingChapterId}
                editedChapterTitle={chapterOps.editedChapterTitle}
                setEditedChapterTitle={chapterOps.setEditedChapterTitle}
                isSavingChapter={chapterOps.isSavingChapter}
                saveChapterError={chapterOps.saveChapterError}
                onEditChapter={chapterOps.handleEditChapterClick}
                onSaveChapterTitle={chapterOps.handleSaveChapterTitle}
                onCancelChapterEdit={chapterOps.handleCancelChapterEdit}
                onGenerateScene={sceneOps.handleGenerateSceneDraft}
                onSplitChapter={chapterOps.handleOpenSplitModal}
                onCompileChapter={chapterOps.handleCompileChapter}
                isGeneratingScene={sceneOps.isGeneratingScene}
                generatingChapterId={sceneOps.generatingChapterId}
                generationSummaries={sceneOps.generationSummaries}
                isCompilingChapter={chapterOps.isCompilingChapter}
                compilingChapterId={chapterOps.compilingChapterId}
                scenes={sceneOps.scenes}
                isLoadingScenes={sceneOps.isLoadingScenes}
                onDeleteScene={sceneOps.handleDeleteScene}
                isAnyOperationLoading={isAnyOperationLoading}
            />

            <hr />

            {/* Characters section */}
            <CharacterManagement
                projectId={projectId}
                characters={characterOps.characters}
                isLoading={characterOps.isLoadingCharacters}
                newCharacterName={characterOps.newCharacterName}
                setNewCharacterName={characterOps.setNewCharacterName}
                onCreateCharacter={characterOps.handleCreateCharacter}
                onDeleteCharacter={characterOps.handleDeleteCharacter}
                characterError={characterOps.characterError}
                isAnyOperationLoading={isAnyOperationLoading}
            />

            <hr />

            {/* Project tools section */}
            <ProjectTools
                projectId={projectId}
                isRebuildingIndex={projectData.isRebuildingIndex}
                rebuildError={projectData.rebuildError}
                rebuildSuccessMessage={projectData.rebuildSuccessMessage}
                onRebuildIndex={projectData.handleRebuildIndex}
                isAnyOperationLoading={isAnyOperationLoading}
            />

            {/* Generated scene modal */}
            {sceneOps.showGeneratedSceneModal && (
                <GeneratedSceneModal
                    sceneTitle={sceneOps.generatedSceneTitle}
                    sceneContent={sceneOps.generatedSceneContent}
                    onTitleChange={sceneOps.setGeneratedSceneTitle}
                    onContentChange={sceneOps.setGeneratedSceneContent}
                    onSave={sceneOps.handleCreateSceneFromDraft}
                    onClose={() => sceneOps.setShowGeneratedSceneModal(false)}
                    isCreating={sceneOps.isCreatingSceneFromDraft}
                    error={sceneOps.createSceneError}
                />
            )}

            {/* Split chapter modal */}
            {chapterOps.showSplitModal && (
                <SplitChapterModal
                    chapterId={chapterOps.chapterIdForSplits}
                    inputContent={chapterOps.splitInputContent[chapterOps.chapterIdForSplits] || ''}
                    onInputChange={(content) => chapterOps.setSplitInputContent(prev => ({
                        ...prev,
                        [chapterOps.chapterIdForSplits]: content
                    }))}
                    proposedSplits={chapterOps.proposedSplits}
                    onSplit={chapterOps.handleSplitChapter}
                    onCreateScenes={handleCreateScenesFromSplits}
                    onClose={() => chapterOps.setShowSplitModal(false)}
                    isSplitting={chapterOps.isSplittingChapter}
                    isCreating={chapterOps.isCreatingScenesFromSplit}
                    splitError={chapterOps.splitError}
                    createError={chapterOps.createFromSplitError}
                />
            )}

            {/* Compiled content modal */}
            {chapterOps.showCompiledContentModal && (
                <CompiledContentModal
                    content={chapterOps.compiledContent}
                    onClose={() => chapterOps.setShowCompiledContentModal(false)}
                    error={chapterOps.compileError}
                />
            )}
        </div>
    );
}

export default ProjectDetailPage;
