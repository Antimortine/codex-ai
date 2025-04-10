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
import {
    getProject, updateProject,
    listChapters, createChapter, deleteChapter, updateChapter,
    listCharacters, createCharacter, deleteCharacter,
    listScenes, createScene, deleteScene,
    generateSceneDraft,
    splitChapterIntoScenes
} from '../api/codexApi';
import QueryInterface from '../components/QueryInterface';
import ChapterSection from '../components/ChapterSection';

// Styles remain the same...
const modalStyles = {
    overlay: { position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, backgroundColor: 'rgba(0, 0, 0, 0.6)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000, },
    content: { backgroundColor: '#fff', padding: '20px', borderRadius: '5px', maxWidth: '80%', width: '700px', maxHeight: '85vh', overflowY: 'auto', position: 'relative', },
    closeButton: { position: 'absolute', top: '10px', right: '10px', cursor: 'pointer', border: 'none', background: 'transparent', fontSize: '1.5rem', fontWeight: 'bold', },
    textarea: { width: '98%', minHeight: '200px', marginTop: '10px', fontFamily: 'monospace', fontSize: '0.9em' },
    copyButton: { marginTop: '10px', marginRight: '10px' },
    createButton: { marginTop: '10px', marginRight: '10px', backgroundColor: '#28a745', color: 'white' },
    splitSceneItem: { border: '1px solid #ddd', borderRadius: '4px', marginBottom: '15px', padding: '10px' },
    splitSceneTitle: { fontWeight: 'bold', marginBottom: '5px', borderBottom: '1px solid #eee', paddingBottom: '5px' },
    splitSceneContent: { maxHeight: '150px', overflowY: 'auto', backgroundColor: '#f8f8f8', padding: '8px', borderRadius: '3px', fontSize: '0.9em', whiteSpace: 'pre-wrap', wordWrap: 'break-word' },
    splitModalActions: { marginTop: '20px', paddingTop: '10px', borderTop: '1px solid #ccc', textAlign: 'right' },
    splitCreateButton: { backgroundColor: '#28a745', color: 'white', marginRight: '10px' },
    generatedTitle: { marginTop: '0', marginBottom: '10px', borderBottom: '1px solid #ccc', paddingBottom: '5px' }
};


function ProjectDetailPage() {
    const { projectId } = useParams();
    const navigate = useNavigate();

    // --- State variables (remain the same) ---
    const [project, setProject] = useState(null);
    const [chapters, setChapters] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [scenes, setScenes] = useState({});
    const [isLoadingProject, setIsLoadingProject] = useState(true);
    const [isLoadingChapters, setIsLoadingChapters] = useState(true);
    const [isLoadingCharacters, setIsLoadingCharacters] = useState(true);
    const [isLoadingScenes, setIsLoadingScenes] = useState({});
    const [error, setError] = useState(null);
    const [newChapterTitle, setNewChapterTitle] = useState('');
    const [newCharacterName, setNewCharacterName] = useState('');
    const [isEditingName, setIsEditingName] = useState(false);
    const [editedProjectName, setEditedProjectName] = useState('');
    const [isSavingName, setIsSavingName] = useState(false);
    const [saveNameError, setSaveNameError] = useState(null);
    const [saveNameSuccess, setSaveNameSuccess] = useState('');
    const [editingChapterId, setEditingChapterId] = useState(null);
    const [editedChapterTitle, setEditedChapterTitle] = useState('');
    const [isSavingChapter, setIsSavingChapter] = useState(false);
    const [saveChapterError, setSaveChapterError] = useState(null);
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
    const [splitInputContent, setSplitInputContent] = useState({});
    const [proposedSplits, setProposedSplits] = useState([]);
    const [chapterIdForSplits, setChapterIdForSplits] = useState(null);
    const [showSplitModal, setShowSplitModal] = useState(false);
    const [isCreatingScenesFromSplit, setIsCreatingScenesFromSplit] = useState(false);
    const [createFromSplitError, setCreateFromSplitError] = useState(null);
    const [isSplittingChapter, setIsSplittingChapter] = useState(false);
    const [splittingChapterId, setSplittingChapterId] = useState(null);
    const [splitError, setSplitError] = useState(null);
    // --- END State variables ---


    // --- Data Fetching (Initial loads remain the same) ---
    useEffect(() => {
        let isMounted = true;
        setIsLoadingProject(true);
        setError(null);
        setProject(null); setChapters([]); setCharacters([]); setScenes({});

        if (!projectId) {
            console.error("[ProjectDetail] Project ID is missing!");
            if (isMounted) { setError("Project ID not found in URL."); setIsLoadingProject(false); }
            return;
        }
        getProject(projectId)
            .then(response => {
                if (isMounted) { setProject(response.data); setEditedProjectName(response.data.name || ''); }
            })
            .catch(err => {
                console.error("[ProjectDetail] getProject FAILED:", err);
                if (isMounted) { setError(`Failed to load project data: ${err.message}`); }
            })
            .finally(() => {
                if (isMounted) { setIsLoadingProject(false); }
            });

        return () => { isMounted = false; };
    }, [projectId]);

    useEffect(() => {
        let isMounted = true;
        if (!project || isLoadingProject) {
            if (!isLoadingProject) { setIsLoadingChapters(true); setIsLoadingCharacters(true); }
            return;
        }
        setIsLoadingChapters(true);
        setIsLoadingCharacters(true);
        setChapters([]);
        setCharacters([]);
        const fetchChaptersAndChars = async () => {
            let chaptersResult = null;
            let charactersResult = null;
            let fetchError = null;
            try {
                chaptersResult = await listChapters(projectId);
                charactersResult = await listCharacters(projectId);
            } catch (err) {
                console.error("[ProjectDetail] fetchChaptersAndChars: Error during sequential fetch:", err);
                fetchError = err;
            }
            if (isMounted) {
                if (fetchError) { setError(prev => prev ? `${prev} | Error fetching chapters/characters.` : 'Error fetching chapters/characters.'); }
                else {
                    if (chaptersResult) {
                        const sortedChapters = (chaptersResult.data.chapters || []).sort((a, b) => a.order - b.order);
                        setChapters(sortedChapters);
                        const initialSummaries = {}; const initialSplitContent = {};
                        sortedChapters.forEach(ch => { initialSummaries[ch.id] = ''; initialSplitContent[ch.id] = ''; });
                        setGenerationSummaries(initialSummaries); setSplitInputContent(initialSplitContent);
                    } else { console.error("[ProjectDetail] fetchChaptersAndChars: chaptersResult is null/undefined after await."); setError(prev => prev ? `${prev} | Failed to load chapters (null result).` : 'Failed to load chapters (null result).'); }
                    if (charactersResult) { const chars = charactersResult.data.characters || []; setCharacters(chars); }
                    else { console.error("[ProjectDetail] fetchChaptersAndChars: charactersResult is null/undefined after await."); setError(prev => prev ? `${prev} | Failed to load characters (null result).` : 'Failed to load characters (null result).'); }
                }
                setIsLoadingChapters(false);
                setIsLoadingCharacters(false);
            }
        };
        fetchChaptersAndChars();
        return () => { isMounted = false; };
    }, [project, projectId, isLoadingProject]);

    useEffect(() => {
        let isMounted = true;
        if (!Array.isArray(chapters) || chapters.length === 0 || isLoadingChapters) { setIsLoadingScenes({}); setScenes({}); return; }
        const initialLoadingState = {}; chapters.forEach(ch => { initialLoadingState[ch.id] = true; });
        setIsLoadingScenes(initialLoadingState);
        setScenes({});
        const fetchAllScenes = async () => {
            const scenesPromises = chapters.map(async (chapter) => {
                try { const r = await listScenes(projectId, chapter.id); return { chapterId: chapter.id, scenes: (r.data.scenes || []).sort((a, b) => a.order - b.order), success: true }; }
                catch (err) { console.error(`[ProjectDetail] fetchAllScenes: Error fetching scenes for chapter ${chapter.id}:`, err); return { chapterId: chapter.id, error: err, success: false, chapterTitle: chapter.title }; }
            });
            try {
                const results = await Promise.allSettled(scenesPromises);
                if (isMounted) {
                    const newScenesState = {}; const newLoadingState = {};
                    results.forEach(result => {
                        if (result.status === 'fulfilled') {
                            const data = result.value;
                            newLoadingState[data.chapterId] = false;
                            if (data.success) { newScenesState[data.chapterId] = data.scenes; }
                            else { newScenesState[data.chapterId] = []; setError(prev => prev ? `${prev} | Failed to load scenes for ${data.chapterTitle}.` : `Failed to load scenes for ${data.chapterTitle}.`); }
                        } else { console.error("[ProjectDetail] fetchAllScenes: A scene fetch promise rejected unexpectedly:", result.reason); }
                    });
                    setScenes(newScenesState);
                    setIsLoadingScenes(newLoadingState);
                }
            } catch (err) {
                console.error("[ProjectDetail] fetchAllScenes: Unexpected error processing scene fetches:", err);
                if (isMounted) { setError(prev => prev ? `${prev} | Error processing scene fetches.` : 'Error processing scene fetches.'); const finalLoadingState = {}; chapters.forEach(ch => { finalLoadingState[ch.id] = false; }); setIsLoadingScenes(finalLoadingState); }
            }
        };
        fetchAllScenes();
        return () => { isMounted = false; };
    }, [chapters, projectId, isLoadingChapters]); // This hook should ONLY depend on chapters, projectId, isLoadingChapters


    // --- Action Handlers ---

    // --- REVISED: refreshData accepts options object ---
    const refreshData = useCallback(async (specificChapterId = null, options = {}) => {
        let isMounted = true;
        const { refreshChapters = true, refreshCharacters = true } = options;
        console.log(`[ProjectDetail] Refreshing data... ${specificChapterId ? `(Specific Chapter: ${specificChapterId})` : '(Full Refresh)'} Options:`, options);

        // Set loading states based on options
        if (refreshChapters) setIsLoadingChapters(true);
        if (refreshCharacters) setIsLoadingCharacters(true);

        const loadingSceneStates = { ...isLoadingScenes };
        const chaptersToRefreshScenes = specificChapterId ? [chapters.find(c => c.id === specificChapterId)].filter(Boolean) : chapters;
        chaptersToRefreshScenes.forEach(ch => { loadingSceneStates[ch.id] = true; });
        setIsLoadingScenes(loadingSceneStates);

        let currentChapters = chapters; // Use current state if not refreshing

        try {
            // Fetch chapters and characters only if requested
            if (refreshChapters || refreshCharacters) {
                const promises = [];
                if (refreshChapters) promises.push(listChapters(projectId)); else promises.push(Promise.resolve(null)); // Placeholder
                if (refreshCharacters) promises.push(listCharacters(projectId)); else promises.push(Promise.resolve(null)); // Placeholder

                const [chaptersResponse, charactersResponse] = await Promise.all(promises);

                if (isMounted) {
                    if (refreshChapters && chaptersResponse) {
                        const sortedChapters = (chaptersResponse.data.chapters || []).sort((a, b) => a.order - b.order);
                        setChapters(sortedChapters); // Update chapters state
                        currentChapters = sortedChapters; // Use the newly fetched chapters for scene fetching
                        setIsLoadingChapters(false);
                    } else if (refreshChapters) {
                        // Handle error if chapter fetch failed but was requested
                        console.error("[ProjectDetail] refreshData: Failed to fetch chapters when requested.");
                        setError(prev => prev ? `${prev} | Failed to refresh chapters.` : 'Failed to refresh chapters.');
                        setIsLoadingChapters(false);
                    }

                    if (refreshCharacters && charactersResponse) {
                        setCharacters(charactersResponse.data.characters || []); // Update characters state
                        setIsLoadingCharacters(false);
                    } else if (refreshCharacters) {
                        // Handle error if character fetch failed but was requested
                        console.error("[ProjectDetail] refreshData: Failed to fetch characters when requested.");
                        setError(prev => prev ? `${prev} | Failed to refresh characters.` : 'Failed to refresh characters.');
                        setIsLoadingCharacters(false);
                    }
                } else {
                    return () => { isMounted = false; }; // Early exit if unmounted
                }
            }

            // Fetch scenes: either specific chapter or all based on *currentChapters* state
            const finalChaptersToFetchScenes = specificChapterId
                ? currentChapters.filter(ch => ch.id === specificChapterId)
                : currentChapters; // Use potentially updated chapter list

            if (finalChaptersToFetchScenes.length === 0 && specificChapterId) {
                 console.warn(`[ProjectDetail] refreshData: Chapter ${specificChapterId} not found in chapter list during scene refresh.`);
                 if (isMounted) {
                      const finalLoadingState = { ...isLoadingScenes };
                      finalLoadingState[specificChapterId] = false; // Mark as not loading
                      setIsLoadingScenes(finalLoadingState);
                 }
                 return () => { isMounted = false; };
            }

            const scenesPromises = finalChaptersToFetchScenes.map(async (chapter) => {
                 try {
                      console.log(`[ProjectDetail] refreshData: Fetching scenes for chapter ${chapter.id}`);
                      const r = await listScenes(projectId, chapter.id);
                      return { chapterId: chapter.id, scenes: (r.data.scenes || []).sort((a, b) => a.order - b.order), success: true };
                 } catch (err) {
                      console.error(`[ProjectDetail] refreshData: Error refreshing scenes for chapter ${chapter.id}:`, err);
                      return { chapterId: chapter.id, error: err, success: false, chapterTitle: chapter.title };
                 }
            });

            const results = await Promise.allSettled(scenesPromises);

            if (isMounted) {
                const newScenesState = { ...scenes }; // Start with existing scenes
                const newLoadingState = { ...isLoadingScenes };
                results.forEach(result => {
                     if (result.status === 'fulfilled') {
                         const data = result.value;
                         newLoadingState[data.chapterId] = false; // Mark as loaded
                         if (data.success) {
                             newScenesState[data.chapterId] = data.scenes; // Update specific chapter's scenes
                         } else {
                             newScenesState[data.chapterId] = []; // Clear on error
                             setError(prev => prev ? `${prev} | Failed to refresh scenes for ${data.chapterTitle}.` : `Failed to refresh scenes for ${data.chapterTitle}.`);
                         }
                     } else {
                         console.error("[ProjectDetail] refreshData: Scene refresh promise rejected:", result.reason);
                         // Potentially find chapterId from reason if possible and mark loading false
                     }
                });
                // Ensure any chapter that wasn't fetched is marked as not loading
                currentChapters.forEach(ch => {
                    if (!(ch.id in newLoadingState) || newLoadingState[ch.id] === undefined) {
                        newLoadingState[ch.id] = false;
                    }
                });

                setScenes(newScenesState);
                setIsLoadingScenes(newLoadingState);
                console.log("[ProjectDetail] refreshData complete.");
            }
        } catch (err) {
            console.error("[ProjectDetail] Refresh data failed:", err);
            if (isMounted) {
                setError(prev => prev ? `${prev} | Failed to refresh data.` : 'Failed to refresh data.');
                // Ensure loading states are reset on general error
                setIsLoadingChapters(false);
                setIsLoadingCharacters(false);
                const finalLoadingState = {};
                chapters.forEach(ch => { finalLoadingState[ch.id] = false; });
                setIsLoadingScenes(finalLoadingState);
            }
        }

        return () => { isMounted = false; };
    }, [projectId, chapters, scenes, isLoadingScenes]); // Dependencies needed for reading current state
    // --- END REVISED ---

    const handleCreateChapter = useCallback(async (e) => {
        e.preventDefault(); if (!newChapterTitle.trim()) return;
        try { await createChapter(projectId, { title: newChapterTitle, order: chapters.length > 0 ? Math.max(...chapters.map(c => c.order)) + 1 : 1 }); setNewChapterTitle(''); refreshData(null, { refreshChapters: true, refreshCharacters: false }); } // Refresh chapters, not chars
        catch (err) { console.error("Create chapter error:", err); setError("Failed to create chapter."); }
    }, [newChapterTitle, chapters, projectId, refreshData]);

    const handleDeleteChapter = useCallback(async (chapterId, chapterTitle) => {
        if (!window.confirm(`Delete chapter "${chapterTitle}" and ALL ITS SCENES?`)) return;
        try { await deleteChapter(projectId, chapterId); refreshData(null, { refreshChapters: true, refreshCharacters: false }); } // Refresh chapters for reordering
        catch (err) { console.error("Delete chapter error:", err); setError("Failed to delete chapter."); }
    }, [projectId, refreshData]);

    const handleCreateCharacter = useCallback(async (e) => {
        e.preventDefault(); if (!newCharacterName.trim()) return;
        try { await createCharacter(projectId, { name: newCharacterName, description: "" }); setNewCharacterName(''); refreshData(null, { refreshChapters: false, refreshCharacters: true }); } // Refresh chars, not chapters
        catch (err) { console.error("Create character error:", err); setError("Failed to create character."); }
    }, [newCharacterName, projectId, refreshData]);

    const handleDeleteCharacter = useCallback(async (characterId, characterName) => {
        if (!window.confirm(`Delete character "${characterName}"?`)) return;
        try { await deleteCharacter(projectId, characterId); refreshData(null, { refreshChapters: false, refreshCharacters: true }); } // Refresh chars, not chapters
        catch (err) { console.error("Delete character error:", err); setError("Failed to delete character."); }
    }, [projectId, refreshData]);

    const handleCreateScene = useCallback(async (chapterId) => {
        try {
             const r = await createScene(projectId, chapterId, { title: "New Scene", content: "", order: null });
             // --- MODIFIED: Refresh only this chapter's scenes, don't refresh core data ---
             await refreshData(chapterId, { refreshChapters: false, refreshCharacters: false });
             // --- END MODIFIED ---
        }
        catch(err) { console.error("Create scene error:", err); setError("Failed to create scene."); }
    }, [projectId, refreshData]); // Depend on refreshData

    const handleDeleteScene = useCallback(async (chapterId, sceneId, sceneTitle) => {
        if (!window.confirm(`Delete scene "${sceneTitle}"?`)) return;
         try {
             await deleteScene(projectId, chapterId, sceneId);
             // --- MODIFIED: Refresh only this chapter's scenes, don't refresh core data ---
             await refreshData(chapterId, { refreshChapters: false, refreshCharacters: false });
             // --- END MODIFIED ---
         } catch(err) { console.error("Error deleting scene:", err); setError("Failed to delete scene."); }
    }, [projectId, refreshData]); // Depend on refreshData

    // (Other handlers remain the same, calling refreshData appropriately)
    const handleEditNameClick = useCallback(() => { setEditedProjectName(project?.name || ''); setIsEditingName(true); setSaveNameError(null); setSaveNameSuccess(''); }, [project]);
    const handleCancelEditName = useCallback(() => { setIsEditingName(false); }, []);
    const handleSaveName = useCallback(async () => {
        if (!editedProjectName.trim()) { setSaveNameError("Project name cannot be empty."); return; }
        if (editedProjectName === project?.name) { setIsEditingName(false); return; }
        setIsSavingName(true); setSaveNameError(null); setSaveNameSuccess('');
        try { const r = await updateProject(projectId, { name: editedProjectName }); setProject(r.data); setIsEditingName(false); setSaveNameSuccess('Project name updated successfully!'); setTimeout(() => setSaveNameSuccess(''), 3000); }
        catch (err) { console.error("Save project name error:", err); setSaveNameError("Failed to update project name. Please try again."); }
        finally { setIsSavingName(false); }
    }, [editedProjectName, project, projectId]);

    const handleEditChapterClick = useCallback((chapter) => { setEditingChapterId(chapter.id); setEditedChapterTitle(chapter.title); setSaveChapterError(null); }, []);
    const handleCancelEditChapter = useCallback(() => { setEditingChapterId(null); setEditedChapterTitle(''); setSaveChapterError(null); }, []);
    const handleChapterTitleChange = useCallback((event) => { setEditedChapterTitle(event.target.value); if (saveChapterError) { setSaveChapterError(null); } }, [saveChapterError]);
    const handleSaveChapter = useCallback(async (chapterId, currentEditedTitle) => {
        if (!currentEditedTitle.trim()) { setSaveChapterError("Chapter title cannot be empty."); return; }
        setIsSavingChapter(true); setSaveChapterError(null);
        try { await updateChapter(projectId, chapterId, { title: currentEditedTitle }); setEditingChapterId(null); setEditedChapterTitle(''); refreshData(null, { refreshChapters: true, refreshCharacters: false }); } // Refresh chapters
        catch (err) { console.error("Save chapter title error:", err); const msg = err.response?.data?.detail || err.message || 'Failed to update chapter.'; setSaveChapterError(msg); }
        finally { setIsSavingChapter(false); }
    }, [projectId, refreshData]);

    const handleGenerateSceneDraft = useCallback(async (chapterId, summary) => {
        setIsGeneratingScene(true);
        setGeneratingChapterId(chapterId);
        setGenerationError(null);
        setGeneratedSceneContent('');
        setGeneratedSceneTitle('');
        setShowGeneratedSceneModal(false);
        setCreateSceneError(null);

        const currentScenesForChapter = scenes[chapterId] || [];
        const prevOrder = currentScenesForChapter.length > 0 ? Math.max(...currentScenesForChapter.map(s => s.order)) : 0;

        try {
            const response = await generateSceneDraft(projectId, chapterId, { prompt_summary: summary, previous_scene_order: prevOrder });
            const generatedTitle = response.data?.title;
            const generatedContent = response.data?.content;

            const potentialError = (typeof generatedContent === 'string' && generatedContent.trim().startsWith("Error:")) ||
                                 (typeof generatedTitle === 'string' && generatedTitle.trim().startsWith("Error:"));

            if (potentialError) {
                const errorMessage = generatedContent.trim().startsWith("Error:") ? generatedContent : generatedTitle;
                console.warn(`[ProjectDetail] Scene generation returned an error message: ${errorMessage}`);
                setGenerationError(errorMessage);
                setShowGeneratedSceneModal(false);
            } else if (generatedTitle !== undefined && generatedContent !== undefined) {
                setGeneratedSceneTitle(generatedTitle || "Untitled Scene");
                setGeneratedSceneContent(generatedContent);
                setChapterIdForGeneratedScene(chapterId);
                setShowGeneratedSceneModal(true);
                setGenerationError(null);
            } else {
                 console.error("[ProjectDetail] Unexpected response format from generateSceneDraft:", response.data);
                 setGenerationError("Error: Received unexpected response format from AI.");
                 setShowGeneratedSceneModal(false);
            }
        } catch (err) {
            console.error("[ProjectDetail] Error calling generateSceneDraft API:", err);
            if (err.response?.status === 429) {
                console.warn("[ProjectDetail] Received 429 status code.");
                setGenerationError("AI feature temporarily unavailable due to free tier limits. Please try again later.");
            } else {
                 const msg = err.response?.data?.detail || err.message || 'Failed to generate scene draft.';
                 setGenerationError(msg);
            }
            setShowGeneratedSceneModal(false);
        } finally {
            setIsGeneratingScene(false);
        }
    }, [scenes, projectId]);

    const handleCreateSceneFromDraft = useCallback(async () => {
        if (!chapterIdForGeneratedScene || !generatedSceneTitle || generatedSceneContent === undefined || generatedSceneContent === null) {
             setCreateSceneError("Missing chapter ID, generated title, or generated content.");
             return;
        }
        setIsCreatingSceneFromDraft(true); setCreateSceneError(null);
        try {
            const titleToSave = generatedSceneTitle;
            const r = await createScene(projectId, chapterIdForGeneratedScene, { title: titleToSave, content: generatedSceneContent, order: null });

            // --- MODIFIED: Refresh only this chapter's scenes, don't refresh core data ---
            await refreshData(chapterIdForGeneratedScene, { refreshChapters: false, refreshCharacters: false });
            // --- END MODIFIED ---

            setShowGeneratedSceneModal(false);
            setGeneratedSceneContent('');
            setGeneratedSceneTitle('');
            setChapterIdForGeneratedScene(null);
            setGeneratingChapterId(null);
        } catch (err) {
            console.error("Create scene from draft error:", err);
            const msg = err.response?.data?.detail || err.message || 'Failed to create scene from draft.';
            if (typeof msg === 'string' && msg.includes("already exists")) {
                setCreateSceneError(`Order conflict: ${msg}. Please try creating manually or refresh.`);
            } else {
                setCreateSceneError(msg);
            }
        }
        finally { setIsCreatingSceneFromDraft(false); }
    }, [chapterIdForGeneratedScene, generatedSceneTitle, generatedSceneContent, projectId, refreshData]);

    const handleSummaryChange = useCallback((chapterId, value) => {
        setGenerationSummaries(prev => ({ ...prev, [chapterId]: value }));
        if (generationError && generatingChapterId === chapterId) {
            setGenerationError(null);
            setGeneratingChapterId(null);
        }
     }, [generationError, generatingChapterId]);

    const copyGeneratedText = useCallback(() => {
        const textToCopy = `## ${generatedSceneTitle}\n\n${generatedSceneContent}`;
        navigator.clipboard.writeText(textToCopy)
            .then(() => console.log("Generated title and content copied."))
            .catch(err => console.error('Failed to copy text: ', err));
    }, [generatedSceneTitle, generatedSceneContent]);

    const handleSplitInputChange = useCallback((chapterId, value) => {
        setSplitInputContent(prev => ({ ...prev, [chapterId]: value }));
        if (splitError && splittingChapterId === chapterId) {
            setSplitError(null);
            setSplittingChapterId(null);
        }
    }, [splitError, splittingChapterId]);

    const handleSplitChapter = useCallback(async (chapterId) => {
        const contentToSplit = splitInputContent[chapterId] || '';
        if (!contentToSplit.trim()) {
            setSplitError("Please paste the chapter content...");
            setSplittingChapterId(chapterId);
            return;
        }
        setIsSplittingChapter(true);
        setSplittingChapterId(chapterId);
        setSplitError(null);
        setProposedSplits([]);
        setShowSplitModal(false);
        setCreateFromSplitError(null);

        try {
            const response = await splitChapterIntoScenes(projectId, chapterId, { chapter_content: contentToSplit });
            if (response.data?.error) {
                 console.error(`[ProjectDetail] Split chapter returned an error: ${response.data.error}`);
                 setSplitError(response.data.error);
                 setShowSplitModal(false);
            } else {
                 setProposedSplits(response.data.proposed_scenes || []);
                 setChapterIdForSplits(chapterId);
                 setShowSplitModal(true);
                 setSplitError(null);
            }
        } catch (err) {
            console.error("[ProjectDetail] Error calling splitChapterIntoScenes API:", err);
             if (err.response?.status === 429) {
                console.warn("[ProjectDetail] Split Received 429 status code.");
                setSplitError("AI feature temporarily unavailable due to free tier limits. Please try again later.");
            } else {
                const msg = err.response?.data?.detail || err.message || 'Failed to split chapter.';
                setSplitError(msg);
            }
            setShowSplitModal(false);
        } finally {
            setIsSplittingChapter(false);
        }
    }, [splitInputContent, projectId]);

    const handleCreateScenesFromSplit = useCallback(async () => {
        if (!chapterIdForSplits || proposedSplits.length === 0) { setCreateFromSplitError("No chapter ID or proposed splits available."); return; }
        setIsCreatingScenesFromSplit(true); setCreateFromSplitError(null);
        const errors = []; const createdScenes = [];
        for (const proposedScene of proposedSplits) {
            const newSceneData = { title: proposedScene.suggested_title || `Scene`, order: null, content: proposedScene.content || "" };
            try { const result = await createScene(projectId, chapterIdForSplits, newSceneData); createdScenes.push(result.data); }
            catch (err) { console.error("Create scene from split error:", err); const msg = err.response?.data?.detail || err.message || `Failed to create scene for "${newSceneData.title}".`; errors.push(msg); }
        }

        // --- MODIFIED: Refresh only this chapter's scenes ---
        if (createdScenes.length > 0) {
            await refreshData(chapterIdForSplits, { refreshChapters: false, refreshCharacters: false });
        }
        // --- END MODIFIED ---

        setIsCreatingScenesFromSplit(false);
        if (errors.length > 0) { setCreateFromSplitError(errors.join(' | ')); }
        else { setShowSplitModal(false); setProposedSplits([]); setChapterIdForSplits(null); setSplittingChapterId(null); }
    }, [chapterIdForSplits, proposedSplits, projectId, refreshData]);

    const handleCloseSplitModal = useCallback(() => {
        setShowSplitModal(false); setProposedSplits([]); setChapterIdForSplits(null); setCreateFromSplitError(null);
        if (splitError && chapterIdForSplits === splittingChapterId) {
            setSplitError(null);
            setSplittingChapterId(null);
        }
    }, [splitError, chapterIdForSplits, splittingChapterId]);

    const handleCloseGeneratedSceneModal = useCallback(() => {
        setShowGeneratedSceneModal(false);
        setGeneratedSceneContent('');
        setGeneratedSceneTitle('');
        setChapterIdForGeneratedScene(null);
        setCreateSceneError(null);
        if (generationError && chapterIdForGeneratedScene === generatingChapterId) {
            setGenerationError(null);
            setGeneratingChapterId(null);
        }
    }, [generationError, chapterIdForGeneratedScene, generatingChapterId]);


    // --- Combined Loading State ---
    const isAnyOperationLoading = isSavingName || isSavingChapter || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit;

    // --- Rendering Logic (remains the same) ---
     if (isLoadingProject) {
         return <p>Loading project...</p>;
     }
     if (error && !project) {
         return ( <div> <p style={{ color: 'red' }}>Error: {error}</p> <Link to="/"> &lt; Back to Project List</Link> </div> );
     }
     if (!project) {
         return ( <div> <p>Project not found.</p> <Link to="/"> &lt; Back to Project List</Link> </div> );
     }

    const isContentLoading = isLoadingChapters || isLoadingCharacters;

    return (
        <div>
            {/* Modals */}
            {showGeneratedSceneModal && (
                <div data-testid="generated-scene-modal" style={modalStyles.overlay}>
                     <div style={modalStyles.content}>
                        <button onClick={handleCloseGeneratedSceneModal} style={modalStyles.closeButton}>×</button>
                        <h3>Generated Scene Draft</h3>
                        {generatedSceneTitle && <h4 style={modalStyles.generatedTitle} data-testid="generated-scene-title">{generatedSceneTitle}</h4>}
                        {createSceneError && <p style={{ color: 'red', marginBottom: '10px' }}>Error: {createSceneError}</p>}
                        <textarea readOnly value={generatedSceneContent} style={modalStyles.textarea} data-testid="generated-scene-content-area"/>
                        <div>
                            <button onClick={copyGeneratedText} style={modalStyles.copyButton}> Copy Draft </button>
                            <button onClick={handleCreateSceneFromDraft} style={modalStyles.createButton} disabled={isCreatingSceneFromDraft}>
                                {isCreatingSceneFromDraft ? 'Creating...' : 'Create Scene from Draft'}
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {showSplitModal && (
                <div data-testid="split-chapter-modal" style={modalStyles.overlay}>
                     <div style={modalStyles.content}>
                        <button onClick={handleCloseSplitModal} style={modalStyles.closeButton}>×</button>
                        <h3>Proposed Scene Splits</h3>
                        {createFromSplitError && ( <div style={{ color: 'red', marginBottom: '10px' }} data-testid="split-error-general">Errors occurred during scene creation: <div data-testid="split-error-specific">{createFromSplitError}</div> </div> )}
                        <div> {proposedSplits.map((split, index) => ( <div key={index} style={modalStyles.splitSceneItem}> <div style={modalStyles.splitSceneTitle}>{index + 1}. {split.suggested_title}</div> <div style={modalStyles.splitSceneContent}>{split.content}</div> </div> ))} </div>
                        <div style={modalStyles.splitModalActions}> <button onClick={handleCreateScenesFromSplit} style={modalStyles.splitCreateButton} disabled={isCreatingScenesFromSplit}> {isCreatingScenesFromSplit ? 'Creating...' : 'Create Scenes'} </button> <button onClick={handleCloseSplitModal}> Cancel </button> </div>
                    </div>
                </div>
            )}

            {/* Page Content */}
            <nav> <Link to="/"> &lt; Back to Project List</Link> </nav>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                 {!isEditingName ? ( <> <h1 style={{ marginRight: '1rem', marginBottom: 0 }}> Project: {project.name} </h1> <button onClick={handleEditNameClick} disabled={isAnyOperationLoading}> Edit Name </button> </> ) : ( <> <input type="text" value={editedProjectName} onChange={(e) => setEditedProjectName(e.target.value)} disabled={isSavingName} style={{ fontSize: '1.5em', marginRight: '0.5rem' }} aria-label="Project Name" /> <button onClick={handleSaveName} disabled={isSavingName || !editedProjectName.trim()}> {isSavingName ? 'Saving...' : 'Save Name'} </button> <button onClick={handleCancelEditName} disabled={isSavingName} style={{ marginLeft: '0.5rem' }}> Cancel </button> </> )}
            </div>
            {saveNameError && <p data-testid="save-name-error" style={{ color: 'red', marginTop: '0.2rem' }}>{saveNameError}</p>}
            {saveNameSuccess && <p style={{ color: 'green', marginTop: '0.2rem' }}>{saveNameSuccess}</p>}
            <p>ID: {projectId}</p>
            {error && <p style={{ color: 'orange', marginTop: '0.2rem' }}>Warning: {error}</p>}
            <hr />
            {projectId && <QueryInterface projectId={projectId} />}
            <hr />

            {/* --- Sections --- */}
            {isContentLoading ? (
                <p>Loading chapters and characters...</p>
            ) : (
                <>
                    <section>
                        <h2>Chapters</h2>
                        {chapters.length === 0 ? <p>No chapters yet.</p> : (
                            chapters.map(chapter => (
                                <ChapterSection
                                    key={chapter.id}
                                    chapter={chapter}
                                    scenesForChapter={scenes[chapter.id] || []}
                                    isLoadingChapterScenes={!!isLoadingScenes[chapter.id]}
                                    isEditingThisChapter={editingChapterId === chapter.id}
                                    editedChapterTitleForInput={editedChapterTitle}
                                    isSavingThisChapter={isSavingChapter && editingChapterId === chapter.id}
                                    saveChapterError={editingChapterId === chapter.id ? saveChapterError : null}
                                    isGeneratingSceneForThisChapter={isGeneratingScene && generatingChapterId === chapter.id}
                                    generationErrorForThisChapter={generatingChapterId === chapter.id ? generationError : null}
                                    generationSummaryForInput={generationSummaries[chapter.id] || ''}
                                    isAnyOperationLoading={isAnyOperationLoading}
                                    projectId={projectId}
                                    onEditChapter={handleEditChapterClick}
                                    onSaveChapter={handleSaveChapter}
                                    onCancelEditChapter={handleCancelEditChapter}
                                    onDeleteChapter={handleDeleteChapter}
                                    onCreateScene={handleCreateScene}
                                    onDeleteScene={handleDeleteScene}
                                    onGenerateScene={handleGenerateSceneDraft}
                                    onSummaryChange={handleSummaryChange}
                                    onTitleInputChange={handleChapterTitleChange}
                                    splitInputContentForThisChapter={splitInputContent[chapter.id] || ''}
                                    isSplittingThisChapter={isSplittingChapter && splittingChapterId === chapter.id}
                                    splitErrorForThisChapter={splittingChapterId === chapter.id ? splitError : null}
                                    onSplitInputChange={handleSplitInputChange}
                                    onSplitChapter={handleSplitChapter}
                                />
                            ))
                        )}
                        <form onSubmit={handleCreateChapter} style={{ marginTop: '1rem' }}>
                            <input type="text" value={newChapterTitle} onChange={(e) => setNewChapterTitle(e.target.value)} placeholder="New chapter title" disabled={isAnyOperationLoading} />
                            <button type="submit" disabled={isAnyOperationLoading || !newChapterTitle.trim()}> Add Chapter </button>
                        </form>
                    </section>
                    <hr />
                    <section>
                        <h2>Characters</h2>
                        {characters.length === 0 ? <p>No characters yet.</p> : (
                            <ul> {characters.map(character => ( <li key={character.id} style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}> <Link to={`/projects/${projectId}/characters/${character.id}`}> {character.name} </Link> <span> <button onClick={() => handleDeleteCharacter(character.id, character.name)} style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }} disabled={isAnyOperationLoading} title={isAnyOperationLoading ? "Operation in progress..." : "Delete character"}> Delete </button> </span> </li> ))} </ul>
                        )}
                        <form onSubmit={handleCreateCharacter} style={{ marginTop: '0.5rem' }}>
                            <input type="text" value={newCharacterName} onChange={(e) => setNewCharacterName(e.target.value)} placeholder="New character name" disabled={isAnyOperationLoading} />
                            <button type="submit" disabled={isAnyOperationLoading || !newCharacterName.trim()}> Add Character </button>
                        </form>
                    </section>
                </>
            )}
            {/* --- END Sections --- */}

            <hr />
            <section>
                 <h2>Other Content</h2>
                 <ul style={{ listStyle: 'none', paddingLeft: 0 }}> <li style={{ marginBottom: '0.5rem' }}> <Link to={`/projects/${projectId}/plan`}>Edit Plan</Link> </li> <li style={{ marginBottom: '0.5rem' }}> <Link to={`/projects/${projectId}/synopsis`}>Edit Synopsis</Link> </li> <li style={{ marginBottom: '0.5rem' }}> <Link to={`/projects/${projectId}/world`}>Edit World Info</Link> </li> </ul>
            </section>
        </div>
    );
}

export default ProjectDetailPage;