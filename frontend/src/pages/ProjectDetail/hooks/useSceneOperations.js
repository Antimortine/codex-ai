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

import { useState, useEffect, useCallback, useRef } from 'react';
import { 
    listScenes, 
    createScene, 
    deleteScene,
    generateSceneDraft
} from '../../../api/codexApi';

/**
 * Custom hook to manage scene-related operations
 * 
 * @param {string} projectId - The ID of the project
 * @param {Array} chapters - The list of chapters to fetch scenes for
 * @returns {Object} Scene data and operations
 */
export function useSceneOperations(projectId, chapters) {
    // Keep track of component mount status to prevent state updates after unmount
    const isMounted = useRef(true);
    // Scene state
    const [scenes, setScenes] = useState({});
    const [isLoadingScenes, setIsLoadingScenes] = useState({});
    const [sceneErrors, setSceneErrors] = useState({});
    
    // Scene generation state
    const [generationSummaries, setGenerationSummaries] = useState({});
    const [generatedSceneTitle, setGeneratedSceneTitle] = useState('');
    const [generatedSceneContent, setGeneratedSceneContent] = useState('');
    const [showGeneratedSceneModal, setShowGeneratedSceneModal] = useState(false);
    const [chapterIdForGeneratedScene, setChapterIdForGeneratedScene] = useState(null);
    const [isCreatingSceneFromDraft, setIsCreatingSceneFromDraft] = useState(false);
    const [createSceneError, setCreateSceneError] = useState(null);
    const [isGeneratingScene, setIsGeneratingScene] = useState(false);
    const [generatingChapterId, setGeneratingChapterId] = useState(null);
    const [generationError, setGenerationError] = useState(null);

    // Effect to load scenes for chapters when chapters change
    useEffect(() => {
        // Set mounted flag
        isMounted.current = true;
        
        // Create an abort controller for cancelling fetch requests
        const abortController = new AbortController();
        const signal = abortController.signal;
        
        const loadScenesForChapter = async (chapter) => {
            // Skip if component is no longer mounted
            if (!isMounted.current) return;
            
            // Store mounted state in local variable to avoid race conditions
            let isComponentMounted = isMounted.current;
            
            if (isComponentMounted) {
                setIsLoadingScenes(prev => ({ ...prev, [chapter.id]: true }));
            }
            
            try {
                // We can't pass the abort signal directly to listScenes since it likely doesn't support it,
                // but this approach still helps with cleanup management
                if (signal.aborted || !isComponentMounted) return;
                
                const response = await listScenes(projectId, chapter.id);
                
                if (isComponentMounted && isMounted.current) {
                    setScenes(prev => ({
                        ...prev,
                        [chapter.id]: response.data.scenes || []
                    }));
                    setSceneErrors(prev => ({ ...prev, [chapter.id]: null }));
                }
            } catch (err) {
                if (signal.aborted) return;
                
                console.error(`Error loading scenes for chapter ${chapter.id}:`, err);
                if (isComponentMounted && isMounted.current) {
                    setSceneErrors(prev => ({ 
                        ...prev, 
                        [chapter.id]: err.message || 'Failed to load scenes' 
                    }));
                }
            } finally {
                if (isComponentMounted && isMounted.current) {
                    setIsLoadingScenes(prev => ({ 
                        ...prev, 
                        [chapter.id]: false 
                    }));
                }
            }
        };
        
        if (!projectId || !chapters || chapters.length === 0) return;
        
        // Load scenes for each chapter
        chapters.forEach(chapter => {
            loadScenesForChapter(chapter);
        });
        
        // Cleanup function - abort any pending requests and prevent state updates
        return () => {
            abortController.abort();
            isMounted.current = false;
        };
    }, [projectId, chapters]);

    // Handle deleting a scene
    const handleDeleteScene = useCallback(async (chapterId, sceneId) => {
        if (!window.confirm('Are you sure you want to delete this scene? This action cannot be undone.')) {
            return;
        }

        // Store mounted state in local variable to avoid race conditions
        let isComponentMounted = isMounted.current;

        try {
            await deleteScene(projectId, chapterId, sceneId);
            // Only update state if component is still mounted
            if (isComponentMounted && isMounted.current) {
                // Update the scenes list
                setScenes(prev => {
                    const updatedScenes = { ...prev };
                    if (updatedScenes[chapterId]) {
                        updatedScenes[chapterId] = updatedScenes[chapterId].filter(scene => scene.id !== sceneId);
                    }
                    return updatedScenes;
                });
                setSceneErrors(prev => ({ ...prev, [chapterId]: null }));
            }
        } catch (err) {
            console.error('Error deleting scene:', err);
            if (isComponentMounted && isMounted.current) {
                setSceneErrors(prev => ({ 
                    ...prev, 
                    [chapterId]: err.message || 'Failed to delete scene' 
                }));
            }
        }
    }, [projectId]);

    // Handle generating a scene draft
    const handleGenerateSceneDraft = useCallback(async (chapterId) => {
        // Store mounted state in local variable to avoid race conditions
        let isComponentMounted = isMounted.current;
        
        if (isComponentMounted) {
            setGeneratingChapterId(chapterId);
            setIsGeneratingScene(true);
            setGenerationError('');
        }

        try {
            const response = await generateSceneDraft(projectId, chapterId);
            // Only update state if component is still mounted
            if (isComponentMounted && isMounted.current) {
                setGenerationSummaries(prev => ({
                    ...prev,
                    [chapterId]: response.data.summary || 'Scene generated.'
                }));
                // If successful, show the modal with the generated content
                setGeneratedSceneTitle(response.data.title || 'New Scene');
                setGeneratedSceneContent(response.data.content || '');
                setShowGeneratedSceneModal(true);
            }
        } catch (err) {
            console.error('Error generating scene draft:', err);
            if (isComponentMounted && isMounted.current) {
                setGenerationError(err.message || 'Failed to generate scene draft');
            }
        } finally {
            if (isComponentMounted && isMounted.current) {
                setIsGeneratingScene(false);
            }
        }
    }, [projectId]);

    // Handle creating a scene from generated draft
    const handleCreateSceneFromDraft = useCallback(async () => {
        if (!chapterIdForGeneratedScene || !generatedSceneTitle.trim()) {
            setCreateSceneError('Scene title is required');
            return;
        }
        
        setIsCreatingSceneFromDraft(true);
        setCreateSceneError(null);
        
        try {
            const response = await createScene(
                projectId, 
                chapterIdForGeneratedScene, 
                {
                    title: generatedSceneTitle,
                    content: generatedSceneContent
                }
            );
            
            // Update the scenes list
            setScenes(prev => ({
                ...prev,
                [chapterIdForGeneratedScene]: [
                    ...(prev[chapterIdForGeneratedScene] || []),
                    response.data
                ]
            }));
            
            // Close the modal and reset state
            setShowGeneratedSceneModal(false);
            setGeneratedSceneTitle('');
            setGeneratedSceneContent('');
            setChapterIdForGeneratedScene(null);
        } catch (err) {
            console.error('Error creating scene from draft:', err);
            setCreateSceneError(err.message || 'Failed to create scene');
        } finally {
            setIsCreatingSceneFromDraft(false);
        }
    }, [projectId, chapterIdForGeneratedScene, generatedSceneTitle, generatedSceneContent]);

    // Handle creating scenes from proposed splits
    const handleCreateScenesFromSplits = useCallback(async (chapterId, proposedSplits) => {
        if (!chapterId || !proposedSplits || proposedSplits.length === 0) {
            return;
        }
        
        setIsCreatingSceneFromDraft(true);
        setCreateSceneError(null);
        
        try {
            // Create scenes one by one
            for (const splitScene of proposedSplits) {
                await createScene(
                    projectId, 
                    chapterId, 
                    {
                        title: splitScene.title || 'New Scene',
                        content: splitScene.content || ''
                    }
                );
            }
            
            // Refresh the scenes list
            const response = await listScenes(projectId, chapterId);
            setScenes(prev => ({
                ...prev,
                [chapterId]: response.data.scenes || []
            }));
            
            return true; // Success flag
        } catch (err) {
            console.error('Error creating scenes from splits:', err);
            setCreateSceneError(err.message || 'Failed to create scenes from splits');
            return false; // Failure flag
        } finally {
            setIsCreatingSceneFromDraft(false);
        }
    }, [projectId]);

    return {
        // State
        scenes,
        isLoadingScenes,
        sceneErrors,
        generationSummaries,
        generatedSceneTitle,
        generatedSceneContent,
        showGeneratedSceneModal,
        chapterIdForGeneratedScene,
        isCreatingSceneFromDraft,
        createSceneError,
        isGeneratingScene,
        generatingChapterId,
        generationError,
        
        // Actions
        setGeneratedSceneTitle,
        setGeneratedSceneContent,
        setShowGeneratedSceneModal,
        handleDeleteScene,
        handleGenerateSceneDraft,
        handleCreateSceneFromDraft,
        handleCreateScenesFromSplits
    };
}
