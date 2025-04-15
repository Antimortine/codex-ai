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
import { useNavigate } from 'react-router-dom';
import {
    listScenes,
    createScene,
    deleteScene,
    generateSceneDraft
} from '../../../api/codexApi';

const RAG_GENERATION_PREVIOUS_SCENE_COUNT = 3;

/**
 * Helper function to extract a user-friendly error message string.
 * Handles Axios errors and potential FastAPI validation details.
 * @param {Error} error - The error object.
 * @param {string} defaultMessage - Default message if extraction fails.
 * @returns {string} - Extracted error message.
 */
const getApiErrorMessage = (error, defaultMessage = 'An unknown error occurred') => {
    // Log the raw error detail for debugging
    // console.debug("Raw API Error Detail:", error?.response?.data?.detail);

    if (error?.response?.data?.detail) {
        const detail = error.response.data.detail;
        // Handle FastAPI validation errors (often arrays of objects)
        if (Array.isArray(detail)) {
            try {
                // Format all validation errors, not just the first one
                return detail.map(err => {
                    const field = (Array.isArray(err?.loc) && err.loc.length > 1) // loc[0] is often 'body'
                                    ? err.loc.slice(1).join('.') // Join nested fields like 'body.field.subfield'
                                    : (Array.isArray(err?.loc) && err.loc.length === 1 ? err.loc[0] : 'input'); // Handle top-level field or default
                    const msg = err?.msg || 'Invalid input';
                    return `${msg} (field: ${field})`;
                }).join('; '); // Join multiple errors with semicolon
            } catch (e) {
                // Fallback if formatting fails
                console.error("Error formatting validation detail:", e);
                return JSON.stringify(detail);
            }
        }
        // Handle simple string detail messages
        if (typeof detail === 'string') {
             return detail;
        }
        // Handle potential object detail (less common for validation)
        if (typeof detail === 'object' && detail !== null) {
            return JSON.stringify(detail);
        }
    }
    // Handle non-response errors (network issues, etc.)
    if (error?.message) {
        return error.message;
    }
    // Ultimate fallback
    return defaultMessage;
};


export function useSceneOperations(projectId, chapters) {
    const navigate = useNavigate();
    const isMounted = useRef(true);
    const [scenes, setScenes] = useState({});
    const [isLoadingScenes, setIsLoadingScenes] = useState({});
    const [sceneErrors, setSceneErrors] = useState({});
    const [generationSummaries, setGenerationSummaries] = useState({});
    const [directSources, setDirectSources] = useState({});
    const [generatedSceneTitle, setGeneratedSceneTitle] = useState('');
    const [generatedSceneContent, setGeneratedSceneContent] = useState('');
    const [showGeneratedSceneModal, setShowGeneratedSceneModal] = useState(false);
    const [chapterIdForGeneratedScene, setChapterIdForGeneratedScene] = useState(null);
    const [generatedSceneSources, setGeneratedSceneSources] = useState({
        source_nodes: [],
        direct_sources: []
    });
    const [isCreatingSceneFromDraft, setIsCreatingSceneFromDraft] = useState(false);
    const [createSceneError, setCreateSceneError] = useState(null);
    const [isGeneratingScene, setIsGeneratingScene] = useState(false);
    const [generatingChapterId, setGeneratingChapterId] = useState(null);

    useEffect(() => { isMounted.current = true; return () => { isMounted.current = false; }; }, []);

    useEffect(() => {
        const abortController = new AbortController(); const signal = abortController.signal;
        const loadScenesForChapter = async (chapterId) => {
             if (!isMounted.current || !projectId || !chapterId) return;
            let isComponentMounted = isMounted.current;
            if (isComponentMounted) {
                setIsLoadingScenes(prev => ({ ...prev, [chapterId]: true }));
                 setSceneErrors(prev => { const n = { ...prev }; delete n[chapterId]; return n; });
            }
            try {
                 if (signal.aborted) return;
                const response = await listScenes(projectId, chapterId);
                if (isComponentMounted && isMounted.current && !signal.aborted) {
                    const scenesData = (response.data.scenes || []).map(s => ({...s, order: Number(s.order) || 0 }));
                    setScenes(prev => ({ ...prev, [chapterId]: scenesData }));
                }
            } catch (err) {
                if (signal.aborted) return; console.error(`Error loading scenes for chapter ${chapterId}:`, err);
                if (isComponentMounted && isMounted.current) {
                    setSceneErrors(prev => ({ ...prev, [chapterId]: getApiErrorMessage(err, 'Failed to load scenes') }));
                }
            } finally {
                if (isComponentMounted && isMounted.current) { setIsLoadingScenes(prev => ({ ...prev, [chapterId]: false })); }
            }
        };
        if (!projectId || !chapters || chapters.length === 0) { setScenes({}); setIsLoadingScenes({}); setSceneErrors({}); return; }
        chapters.forEach(chapter => { if (chapter?.id) loadScenesForChapter(chapter.id); });
        return () => { abortController.abort(); };
    }, [projectId, chapters]);

    const handleSummaryChange = useCallback((chapterId, summary) => {
        setGenerationSummaries(prev => ({
            ...prev,
            [chapterId]: summary
        }));
    }, []);

    const handleDirectSourcesChange = useCallback((chapterId, sources) => {
        console.log('useSceneOperations: handleDirectSourcesChange called with:', chapterId, sources);
        // Always ensure we're working with a valid array of sources
        const validSources = Array.isArray(sources) ? sources : [];
        
        // Update the directSources state with the new selection
        setDirectSources(prev => {
            const updated = {
                ...prev,
                [chapterId]: validSources
            };
            console.log('useSceneOperations: Updated directSources state:', updated);
            return updated;
        });
    }, []);

    const handleDeleteScene = useCallback(async (chapterId, sceneId, sceneTitle) => {
        const confirmMessage = `Are you sure you want to delete the scene "${sceneTitle || 'this scene'}"? This action cannot be undone.`;
        if (!window.confirm(confirmMessage)) return;
        let isComponentMounted = isMounted.current; const errorKey = `del_${sceneId}`;
        setSceneErrors(prev => { const n = { ...prev }; delete n[errorKey]; return n; });
        try {
            await deleteScene(projectId, chapterId, sceneId);
            if (isComponentMounted && isMounted.current) {
                setScenes(prev => {
                    const updatedScenes = { ...prev };
                    if (updatedScenes[chapterId]) {
                        updatedScenes[chapterId] = updatedScenes[chapterId]
                            .filter(scene => scene.id !== sceneId)
                            .map((scene, index) => ({ ...scene, order: index + 1 }));
                    }
                    return updatedScenes;
                });
                setSceneErrors(prev => { const n = { ...prev }; delete n[chapterId]; return n; });
            }
        } catch (err) {
            console.error('Error deleting scene:', err);
            if (isComponentMounted && isMounted.current) { setSceneErrors(prev => ({ ...prev, [errorKey]: getApiErrorMessage(err, 'Failed to delete scene') })); }
        }
    }, [projectId]);

    const handleCreateSceneManually = useCallback((chapterId) => {
         if (!projectId || !chapterId) return;
         const currentScenes = scenes[chapterId] || [];
         const nextOrder = currentScenes.length > 0 ? Math.max(0, ...currentScenes.map(s => Number(s.order) || 0)) + 1 : 1;
         navigate(`/projects/${projectId}/chapters/${chapterId}/scenes/new?order=${nextOrder}`);
    }, [navigate, projectId, scenes]);

    const handleGenerateSceneDraft = useCallback(async (chapterId, summaryText, explicitSources) => {
        let isComponentMounted = isMounted.current;
        const summary = summaryText || generationSummaries[chapterId] || '';
        
        // Get direct sources for this specific chapter - this is critical
        // Log the full directSources object for debugging
        console.log('useSceneOperations: Full directSources object:', directSources);
        console.log('useSceneOperations: explicitSources:', explicitSources);
        console.log('useSceneOperations: chapterId:', chapterId);
        
        // IMPORTANT FIX: Make sure we properly retrieve direct sources
        let sources = [];
        
        // First priority: use explicit sources passed from the calling component
        if (Array.isArray(explicitSources) && explicitSources.length > 0) {
            sources = explicitSources;
            console.log('useSceneOperations: Using explicitSources:', sources);
        } 
        // Second priority: check our state object using chapter ID as the key
        else if (directSources && typeof directSources === 'object' && 
                 directSources[chapterId] && Array.isArray(directSources[chapterId])) {
            sources = directSources[chapterId];
            console.log('useSceneOperations: Using directSources[chapterId]:', sources);
        }
        
        // Log final sources decision
        console.log('useSceneOperations: FINAL DECISION - using sources:', sources);
        
        const errorKey = `gen_${chapterId}`;

        if (isComponentMounted) {
            console.log('useSceneOperations: handleGenerateSceneDraft called with chapterId:', chapterId, 'and summary:', summary);
            console.log('useSceneOperations: direct sources:', sources);
            setGeneratingChapterId(chapterId); setIsGeneratingScene(true);
            setSceneErrors(prev => { const n = { ...prev }; delete n[errorKey]; return n; });
        }

        try {
             // Use prompt_summary instead of summary to match the backend model
             const requestData = { prompt_summary: summary };
             
             // CRITICAL FIX: Preserve the direct sources in a reference copy
             // This ensures we have a valid copy for the API response handler
             const originalSources = [...sources];
             console.log('useSceneOperations: Processing direct sources for API call:', sources);
             
             // URGENT FIX: Set the source names in a special variable we'll check at the end
             // This guarantees we always have the raw names for display in the modal
             window.__LATEST_SELECTED_SOURCES = originalSources;
             
             // Add direct sources to the request payload
             if (sources && sources.length > 0) {
                 // CRITICAL FIX: The backend expects direct_sources to be an array of strings, not objects
                 // We only use objects with type and name for display in the modal
                 requestData.direct_sources = sources;
                 console.log('useSceneOperations: Using direct sources as strings for API request:', requestData.direct_sources);
             } else {
                 // Always include direct_sources in the request, even if empty
                 requestData.direct_sources = [];
             }

             // Also save the sources directly in state so we have them for later
             // This is our fallback for displaying in the modal
             if (originalSources.length > 0) {
                 console.log('useSceneOperations: Saving non-empty originalSources to state:', originalSources);
                 // Format sources as objects with type and name properties for display
                 const formattedSources = originalSources.map(source => ({ 
                     type: "DirectSource", 
                     name: source 
                 }));
                 
                 // Save them to state immediately
                 setGeneratedSceneSources(prev => ({
                     ...prev,
                     direct_sources: formattedSources
                 }));
                 
                 console.log('useSceneOperations: Saved direct_sources for modal display:', formattedSources);
             } else {
                 console.log('useSceneOperations: No direct sources to save');
             }
             
             const previousScenes = scenes[chapterId]
                 ?.slice(-RAG_GENERATION_PREVIOUS_SCENE_COUNT)
                 .sort((a, b) => (Number(a.order) || 0) - (Number(b.order) || 0))
                 || [];
             
             // Get the highest previous scene order number or null if there are no scenes
             const previousSceneOrders = previousScenes
                .map(s => Number(s.order))
                .filter(order => Number.isInteger(order) && order > 0);
                
             // Set previous_scene_order to the highest scene order or null if there are no scenes
             // Backend expects an integer, not an array
             requestData.previous_scene_order = previousSceneOrders.length > 0 
                ? Math.max(...previousSceneOrders) 
                : null;

            //  console.log('useSceneOperations: Calling generateSceneDraft API with:', projectId, chapterId, JSON.stringify(requestData)); // Log stringified data
            const response = await generateSceneDraft(projectId, chapterId, requestData);
            //  console.log('useSceneOperations: API response received:', response.data);

            if (isComponentMounted && isMounted.current) {
                //  console.log('useSceneOperations: Processing successful API response');
                setGeneratedSceneTitle(response.data.title || 'Generated Scene'); 
                setGeneratedSceneContent(response.data.content || '');
                
                // Store source information from API response
                console.log('useSceneOperations: API response sources:', {
                    source_nodes: response.data.source_nodes || [],
                    direct_sources: response.data.direct_sources || []
                });
                
                // *** CRITICAL FIX: Force use of our own formatted direct sources for display ***
                // These are the sources we saved earlier with proper type+name format
                // This ensures they will actually appear in the modal
                
                // EMERGENCY FIX: Retrieve the sources we saved in a global variable
                const lastSelectedSources = window.__LATEST_SELECTED_SOURCES || [];
                console.log('useSceneOperations: Retrieved sources from global variable:', lastSelectedSources);
                
                // Format them for display
                const currentFormattedSources = lastSelectedSources.length > 0 ?
                    lastSelectedSources.map(s => ({ type: "DirectSource", name: s })) : [];
                
                console.log('useSceneOperations: Formatted current sources:', currentFormattedSources);
                console.log('useSceneOperations: API returned sources:', response.data.direct_sources || []);
                
                // Now update the state with BOTH the API response sources AND our own
                setGeneratedSceneSources(prev => {
                    // Decide which direct sources to use - prioritize non-empty collections
                    let directSources = [];
                    
                    // Option 1: Use API response sources if available
                    if (response.data.direct_sources && response.data.direct_sources.length > 0) {
                        directSources = response.data.direct_sources;
                        console.log('useSceneOperations: Using API returned direct_sources');
                    }
                    // Option 2: Use our own saved sources from earlier in this function
                    else if (currentFormattedSources.length > 0) {
                        directSources = currentFormattedSources;
                        console.log('useSceneOperations: Using our own formatted sources');
                    }
                    // Option 3: Use previously saved sources in state as last resort
                    else if (prev.direct_sources && prev.direct_sources.length > 0) {
                        directSources = prev.direct_sources;
                        console.log('useSceneOperations: Using previous state direct_sources');
                    }
                    
                    console.log('useSceneOperations: FINAL direct_sources for modal:', directSources);
                    
                    return {
                        ...prev,
                        source_nodes: response.data.source_nodes || [],
                        direct_sources: directSources
                    };
                });
                
                setChapterIdForGeneratedScene(chapterId); 
                setShowGeneratedSceneModal(true);
            }
        } catch (err) {
            console.error('useSceneOperations: Error generating scene draft:', err);
            if (isComponentMounted && isMounted.current) {
                 console.log('useSceneOperations: Setting generation error state');
                 // Use updated helper function for potentially more detailed error
                setSceneErrors(prev => ({ ...prev, [errorKey]: getApiErrorMessage(err, 'Failed to generate scene draft') }));
            }
        } finally {
            if (isComponentMounted && isMounted.current) { console.log('useSceneOperations: Setting generating state OFF'); setIsGeneratingScene(false); }
        }
    }, [projectId, scenes, generationSummaries, isMounted]);

    const handleCreateSceneFromDraft = useCallback(async () => {
        if (!chapterIdForGeneratedScene || !generatedSceneTitle.trim()) { setCreateSceneError('Scene title is required'); return; }
        let isComponentMounted = isMounted.current; setIsCreatingSceneFromDraft(true); setCreateSceneError(null);
        try {
             const currentScenes = scenes[chapterIdForGeneratedScene] || [];
             const nextOrder = currentScenes.length > 0 ? Math.max(0, ...currentScenes.map(s => Number(s.order) || 0)) + 1 : 1;
            const response = await createScene( projectId, chapterIdForGeneratedScene, { title: generatedSceneTitle, content: generatedSceneContent, order: nextOrder });
             if (isComponentMounted && isMounted.current) {
                setScenes(prev => ({ ...prev, [chapterIdForGeneratedScene]: [ ...(prev[chapterIdForGeneratedScene] || []), response.data ].sort((a, b) => (Number(a.order) || 0) - (Number(b.order) || 0)) }));
                setShowGeneratedSceneModal(false); setGeneratedSceneTitle(''); setGeneratedSceneContent('');
                setGeneratedSceneSources({ source_nodes: [], direct_sources: [] });
                setChapterIdForGeneratedScene(null); setGeneratingChapterId(null);
                 setGenerationSummaries(prev => ({ ...prev, [chapterIdForGeneratedScene]: '' }));
             }
        } catch (err) {
            console.error('Error creating scene from draft:', err);
             if (isComponentMounted && isMounted.current) { setCreateSceneError(getApiErrorMessage(err, 'Failed to create scene')); }
        } finally {
             if (isComponentMounted && isMounted.current) { setIsCreatingSceneFromDraft(false); }
        }
    }, [projectId, chapterIdForGeneratedScene, generatedSceneTitle, generatedSceneContent, scenes, isMounted]);

    const handleCreateScenesFromSplits = useCallback(async (chapterId, proposedSplits) => {
        if (!chapterId || !proposedSplits || proposedSplits.length === 0) { console.error("handleCreateScenesFromSplits called with invalid arguments"); return false; }
        let isComponentMounted = isMounted.current; let overallSuccess = true; const errorKey = `split_create_${chapterId}`;
        setIsCreatingSceneFromDraft(true); setSceneErrors(prev => { const n = { ...prev }; delete n[errorKey]; return n; });
        try {
            let currentOrder = 1;
            const creationPromises = proposedSplits.map(async (splitScene, index) => {
                return createScene( projectId, chapterId, { title: splitScene.title || `Scene ${index + 1}`, content: splitScene.content || '', order: currentOrder++ }); });
            const results = await Promise.allSettled(creationPromises);
            if (isComponentMounted && isMounted.current) {
                 const failedCreations = results.filter(r => r.status === 'rejected');
                 if (failedCreations.length > 0) {
                     console.error('Some scenes failed to create from splits:', failedCreations);
                     const firstReason = failedCreations[0]?.reason;
                     setSceneErrors(prev => ({ ...prev, [errorKey]: getApiErrorMessage(firstReason, `Failed to create ${failedCreations.length} scene(s) from split.`) }));
                     overallSuccess = false;
                 }
                 try {
                     const response = await listScenes(projectId, chapterId);
                     if (isComponentMounted && isMounted.current) {
                         const scenesData = (response.data.scenes || []).map(s => ({...s, order: Number(s.order) || 0 }));
                         setScenes(prev => ({ ...prev, [chapterId]: scenesData }));
                     }
                 } catch (listErr) {
                     console.error(`Error reloading scenes after split creation for chapter ${chapterId}:`, listErr);
                     setSceneErrors(prev => ({ ...prev, [chapterId]: 'Failed to reload scenes after split creation.' }));
                     overallSuccess = false;
                 }
            } else { overallSuccess = false; }
            return overallSuccess;
        } catch (err) {
            console.error('Unexpected error creating scenes from splits:', err);
             if (isComponentMounted && isMounted.current) { setSceneErrors(prev => ({ ...prev, [errorKey]: getApiErrorMessage(err, 'Unexpected error creating scenes from splits') })); }
            return false;
        } finally {
            if (isComponentMounted && isMounted.current) { setIsCreatingSceneFromDraft(false); }
        }
    }, [projectId, isMounted]);

    const handleCloseGeneratedSceneModal = useCallback(() => {
        setShowGeneratedSceneModal(false); 
        setGeneratedSceneTitle(''); 
        setGeneratedSceneContent('');
        setGeneratedSceneSources({ source_nodes: [], direct_sources: [] });
        setChapterIdForGeneratedScene(null); setGeneratingChapterId(null); setCreateSceneError(null);
    }, []);

    return {
        scenes, isLoadingScenes, sceneErrors, generationSummaries, generatedSceneTitle,
        generatedSceneContent, showGeneratedSceneModal, chapterIdForGeneratedScene,
        generatedSceneSources, isCreatingSceneFromDraft, createSceneError, isGeneratingScene, generatingChapterId,
        setGeneratedSceneTitle, setGeneratedSceneContent, handleDeleteScene, handleGenerateSceneDraft,
        handleCreateSceneFromDraft, handleCreateScenesFromSplits, handleCloseGeneratedSceneModal,
        handleSummaryChange, handleDirectSourcesChange, handleCreateSceneManually,
    };
}