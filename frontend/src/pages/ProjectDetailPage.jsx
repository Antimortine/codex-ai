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

    // --- State variables ---
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


    // --- Data Fetching ---
    useEffect(() => {
        let isMounted = true;
        // console.log("[ProjectDetail] Initial useEffect running. projectId:", projectId); // Removed log
        setIsLoadingProject(true);
        setError(null);
        setProject(null); setChapters([]); setCharacters([]); setScenes({});

        if (!projectId) {
            console.error("[ProjectDetail] Project ID is missing!"); // Keep error log
            if (isMounted) { setError("Project ID not found in URL."); setIsLoadingProject(false); }
            return;
        }

        // console.log(`[ProjectDetail] Calling getProject(${projectId})...`); // Removed log
        getProject(projectId)
            .then(response => {
                // console.log("[ProjectDetail] getProject successful:", response.data); // Removed log
                if (isMounted) { setProject(response.data); setEditedProjectName(response.data.name || ''); }
            })
            .catch(err => {
                console.error("[ProjectDetail] getProject FAILED:", err); // Keep error log
                if (isMounted) { setError(`Failed to load project data: ${err.message}`); }
            })
            .finally(() => {
                // console.log("[ProjectDetail] getProject finally block. Setting isLoadingProject to false."); // Removed log
                if (isMounted) { setIsLoadingProject(false); }
            });

        return () => {
            // console.log("[ProjectDetail] Initial useEffect cleanup."); // Removed log
            isMounted = false;
        };
    }, [projectId]);

    useEffect(() => {
        let isMounted = true;
        // console.log(`[ProjectDetail] Chapters/Chars useEffect running. project: ${project ? 'Exists' : 'null'}, isLoadingProject: ${isLoadingProject}`); // Removed log

        if (!project || isLoadingProject) {
            if (!isLoadingProject) {
                 // console.log("[ProjectDetail] Chapters/Chars useEffect: Project not loaded or isLoadingProject is true. Resetting states."); // Removed log
                 setIsLoadingChapters(true);
                 setIsLoadingCharacters(true);
            } else {
                 // console.log("[ProjectDetail] Chapters/Chars useEffect: Project not loaded or isLoadingProject is true. Skipping fetch."); // Removed log
            }
            return;
        }

        // console.log("[ProjectDetail] Chapters/Chars useEffect: Project loaded. Setting loading states and fetching..."); // Removed log
        setIsLoadingChapters(true);
        setIsLoadingCharacters(true);
        setChapters([]);
        setCharacters([]);

        const fetchChaptersAndChars = async () => {
            let chaptersResult = null;
            let charactersResult = null;
            let fetchError = null;

            try {
                // console.log("[ProjectDetail] fetchChaptersAndChars: Awaiting listChapters..."); // Removed log
                chaptersResult = await listChapters(projectId);
                // console.log("[ProjectDetail] fetchChaptersAndChars: listChapters successful:", chaptersResult?.data); // Removed log

                // console.log("[ProjectDetail] fetchChaptersAndChars: Awaiting listCharacters..."); // Removed log
                charactersResult = await listCharacters(projectId);
                // console.log("[ProjectDetail] fetchChaptersAndChars: listCharacters successful:", charactersResult?.data); // Removed log

            } catch (err) {
                console.error("[ProjectDetail] fetchChaptersAndChars: Error during sequential fetch:", err); // Keep error log
                fetchError = err;
            }

            if (isMounted) {
                if (fetchError) {
                     setError(prev => prev ? `${prev} | Error fetching chapters/characters.` : 'Error fetching chapters/characters.');
                } else {
                    if (chaptersResult) {
                        const sortedChapters = (chaptersResult.data.chapters || []).sort((a, b) => a.order - b.order);
                        // console.log(`[ProjectDetail] fetchChaptersAndChars: Processing chapters (${sortedChapters.length} chapters).`); // Removed log
                        setChapters(sortedChapters);
                        const initialSummaries = {}; const initialSplitContent = {};
                        sortedChapters.forEach(ch => { initialSummaries[ch.id] = ''; initialSplitContent[ch.id] = ''; });
                        setGenerationSummaries(initialSummaries); setSplitInputContent(initialSplitContent);
                    } else {
                         console.error("[ProjectDetail] fetchChaptersAndChars: chaptersResult is null/undefined after await."); // Keep error log
                         setError(prev => prev ? `${prev} | Failed to load chapters (null result).` : 'Failed to load chapters (null result).');
                    }
                    if (charactersResult) {
                        const chars = charactersResult.data.characters || [];
                        // console.log(`[ProjectDetail] fetchChaptersAndChars: Processing characters (${chars.length} characters).`); // Removed log
                        setCharacters(chars);
                    } else {
                         console.error("[ProjectDetail] fetchChaptersAndChars: charactersResult is null/undefined after await."); // Keep error log
                         setError(prev => prev ? `${prev} | Failed to load characters (null result).` : 'Failed to load characters (null result).');
                    }
                }
                // console.log("[ProjectDetail] fetchChaptersAndChars: Setting loading states to false."); // Removed log
                setIsLoadingChapters(false);
                setIsLoadingCharacters(false);
            } else {
                // console.log("[ProjectDetail] fetchChaptersAndChars: Component unmounted before processing results."); // Removed log
            }
        };

        fetchChaptersAndChars();

        return () => {
            // console.log("[ProjectDetail] Chapters/Chars useEffect cleanup."); // Removed log
            isMounted = false;
        };
    }, [project, projectId, isLoadingProject]);

    useEffect(() => {
        let isMounted = true;
        // console.log(`[ProjectDetail] Scenes useEffect running. chapters count: ${chapters.length}, isLoadingChapters: ${isLoadingChapters}`); // Removed log
        if (!Array.isArray(chapters) || chapters.length === 0 || isLoadingChapters) {
            // console.log("[ProjectDetail] Scenes useEffect: Skipping fetch (no chapters or still loading). Resetting scenes."); // Removed log
            setIsLoadingScenes({});
            setScenes({});
            return;
        }

        const initialLoadingState = {}; chapters.forEach(ch => { initialLoadingState[ch.id] = true; });
        setIsLoadingScenes(initialLoadingState);
        setScenes({});

        const fetchAllScenes = async () => {
            // console.log("[ProjectDetail] fetchAllScenes: Starting fetches for all chapters."); // Removed log
            const scenesPromises = chapters.map(async (chapter) => {
                try {
                    const r = await listScenes(projectId, chapter.id);
                    return { chapterId: chapter.id, scenes: (r.data.scenes || []).sort((a, b) => a.order - b.order), success: true };
                } catch (err) {
                    console.error(`[ProjectDetail] fetchAllScenes: Error fetching scenes for chapter ${chapter.id}:`, err); // Keep error log
                    return { chapterId: chapter.id, error: err, success: false, chapterTitle: chapter.title };
                }
            });
            try {
                const results = await Promise.allSettled(scenesPromises);
                // console.log("[ProjectDetail] fetchAllScenes: Promise.allSettled finished. Results:", results); // Removed log
                if (isMounted) {
                    const newScenesState = {}; const newLoadingState = {};
                    results.forEach(result => {
                        if (result.status === 'fulfilled') {
                            const data = result.value;
                            newLoadingState[data.chapterId] = false;
                            if (data.success) {
                                newScenesState[data.chapterId] = data.scenes;
                                // console.log(`[ProjectDetail] fetchAllScenes: Successfully loaded ${data.scenes.length} scenes for chapter ${data.chapterId}.`); // Removed log
                            } else {
                                newScenesState[data.chapterId] = [];
                                setError(prev => prev ? `${prev} | Failed to load scenes for ${data.chapterTitle}.` : `Failed to load scenes for ${data.chapterTitle}.`);
                            }
                        } else {
                            console.error("[ProjectDetail] fetchAllScenes: A scene fetch promise rejected unexpectedly:", result.reason); // Keep error log
                        }
                    });
                    setScenes(newScenesState);
                    setIsLoadingScenes(newLoadingState);
                } else {
                     // console.log("[ProjectDetail] fetchAllScenes: Component unmounted before processing results."); // Removed log
                }
            } catch (err) {
                console.error("[ProjectDetail] fetchAllScenes: Unexpected error processing scene fetches:", err); // Keep error log
                if (isMounted) {
                    setError(prev => prev ? `${prev} | Error processing scene fetches.` : 'Error processing scene fetches.');
                    const finalLoadingState = {}; chapters.forEach(ch => { finalLoadingState[ch.id] = false; });
                    setIsLoadingScenes(finalLoadingState);
                }
            }
        };
        fetchAllScenes();
        return () => {
             // console.log("[ProjectDetail] Scenes useEffect cleanup."); // Removed log
             isMounted = false;
        };
    }, [chapters, projectId, isLoadingChapters]);


    // --- Action Handlers ---
    const refreshData = useCallback(async () => {
        let isMounted = true;
        // console.log("[ProjectDetail] Refreshing data..."); // Removed log
        setIsLoadingChapters(true); setIsLoadingCharacters(true);
        try {
            const [chaptersResponse, charactersResponse] = await Promise.all([ listChapters(projectId), listCharacters(projectId) ]);
            if (isMounted) {
                // console.log("[ProjectDetail] Refresh successful."); // Removed log
                setChapters((chaptersResponse.data.chapters || []).sort((a, b) => a.order - b.order));
                setCharacters(charactersResponse.data.characters || []);
            }
        } catch (err) {
            console.error("[ProjectDetail] Refresh data failed:", err); // Keep error log
            if (isMounted) setError(prev => prev ? `${prev} | Failed to refresh data.` : 'Failed to refresh data.');
        } finally {
            if (isMounted) { setIsLoadingChapters(false); setIsLoadingCharacters(false); }
        }
        return () => { isMounted = false; };
    }, [projectId]);

    const handleCreateChapter = useCallback(async (e) => {
        e.preventDefault(); if (!newChapterTitle.trim()) return;
        try { await createChapter(projectId, { title: newChapterTitle, order: chapters.length > 0 ? Math.max(...chapters.map(c => c.order)) + 1 : 1 }); setNewChapterTitle(''); refreshData(); }
        catch (err) { console.error("Create chapter error:", err); setError("Failed to create chapter."); } // Added console.error
    }, [newChapterTitle, chapters, projectId, refreshData]);

    const handleDeleteChapter = useCallback(async (chapterId, chapterTitle) => {
        if (!window.confirm(`Delete chapter "${chapterTitle}" and ALL ITS SCENES?`)) return;
        try { await deleteChapter(projectId, chapterId); refreshData(); }
        catch (err) { console.error("Delete chapter error:", err); setError("Failed to delete chapter."); } // Added console.error
    }, [projectId, refreshData]);

    const handleCreateCharacter = useCallback(async (e) => {
        e.preventDefault(); if (!newCharacterName.trim()) return;
        try { await createCharacter(projectId, { name: newCharacterName, description: "" }); setNewCharacterName(''); refreshData(); }
        catch (err) { console.error("Create character error:", err); setError("Failed to create character."); } // Added console.error
    }, [newCharacterName, projectId, refreshData]);

    const handleDeleteCharacter = useCallback(async (characterId, characterName) => {
        if (!window.confirm(`Delete character "${characterName}"?`)) return;
        try { await deleteCharacter(projectId, characterId); refreshData(); }
        catch (err) { console.error("Delete character error:", err); setError("Failed to delete character."); } // Added console.error
    }, [projectId, refreshData]);

    const handleCreateScene = useCallback(async (chapterId) => {
        const currentScenes = scenes[chapterId] || []; const nextOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) + 1 : 1;
        try { const r = await createScene(projectId, chapterId, { title: "New Scene", order: nextOrder, content: "" }); setScenes(p => ({ ...p, [chapterId]: [...(p[chapterId] || []), r.data].sort((a, b) => a.order - b.order) })); /* refreshData(); */ } // Removed refreshData for optimistic update
        catch(err) { console.error("Create scene error:", err); setError("Failed to create scene."); } // Added console.error
    }, [scenes, projectId /*, refreshData */]); // Removed refreshData dependency

    const handleDeleteScene = useCallback(async (chapterId, sceneId, sceneTitle) => {
        if (!window.confirm(`Delete scene "${sceneTitle}"?`)) return;
         try {
             await deleteScene(projectId, chapterId, sceneId);
             setScenes(prevScenes => {
                 const chapterScenes = prevScenes[chapterId] || [];
                 const updatedChapterScenes = chapterScenes.filter(scene => scene.id !== sceneId);
                 const reorderedScenes = updatedChapterScenes.map((scene, index) => ({ ...scene, order: index + 1, }));
                 return { ...prevScenes, [chapterId]: reorderedScenes };
             });
         } catch(err) { console.error("Error deleting scene:", err); setError("Failed to delete scene."); }
    }, [projectId, setScenes, setError]);

    const handleEditNameClick = useCallback(() => { setEditedProjectName(project?.name || ''); setIsEditingName(true); setSaveNameError(null); setSaveNameSuccess(''); }, [project]);
    const handleCancelEditName = useCallback(() => { setIsEditingName(false); }, []);
    const handleSaveName = useCallback(async () => {
        if (!editedProjectName.trim()) { setSaveNameError("Project name cannot be empty."); return; }
        if (editedProjectName === project?.name) { setIsEditingName(false); return; }
        setIsSavingName(true); setSaveNameError(null); setSaveNameSuccess('');
        try { const r = await updateProject(projectId, { name: editedProjectName }); setProject(r.data); setIsEditingName(false); setSaveNameSuccess('Project name updated successfully!'); setTimeout(() => setSaveNameSuccess(''), 3000); }
        catch (err) { console.error("Save project name error:", err); setSaveNameError("Failed to update project name. Please try again."); } // Added console.error
        finally { setIsSavingName(false); }
    }, [editedProjectName, project, projectId]);

    const handleEditChapterClick = useCallback((chapter) => { setEditingChapterId(chapter.id); setEditedChapterTitle(chapter.title); setSaveChapterError(null); }, []);
    const handleCancelEditChapter = useCallback(() => { setEditingChapterId(null); setEditedChapterTitle(''); setSaveChapterError(null); }, []);
    const handleChapterTitleChange = useCallback((event) => { setEditedChapterTitle(event.target.value); if (saveChapterError) { setSaveChapterError(null); } }, [saveChapterError]);
    const handleSaveChapter = useCallback(async (chapterId, currentEditedTitle) => {
        if (!currentEditedTitle.trim()) { setSaveChapterError("Chapter title cannot be empty."); return; }
        setIsSavingChapter(true); setSaveChapterError(null);
        try { await updateChapter(projectId, chapterId, { title: currentEditedTitle }); setEditingChapterId(null); setEditedChapterTitle(''); refreshData(); }
        catch (err) { console.error("Save chapter title error:", err); const msg = err.response?.data?.detail || err.message || 'Failed to update chapter.'; setSaveChapterError(msg); } // Added console.error
        finally { setIsSavingChapter(false); }
    }, [projectId, refreshData]);

    const handleGenerateSceneDraft = useCallback(async (chapterId, summary) => {
        // console.log(`[ProjectDetail] handleGenerateSceneDraft called for chapter ${chapterId}`); // Removed log
        setIsGeneratingScene(true);
        setGeneratingChapterId(chapterId);
        setGenerationError(null);
        setGeneratedSceneContent('');
        setGeneratedSceneTitle('');
        setShowGeneratedSceneModal(false);
        setCreateSceneError(null);

        const currentScenes = scenes[chapterId] || [];
        const prevOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) : 0;

        try {
            const response = await generateSceneDraft(projectId, chapterId, { prompt_summary: summary, previous_scene_order: prevOrder });
            const generatedTitle = response.data?.title;
            const generatedContent = response.data?.content;
            // console.log(`[ProjectDetail] Received generation response. Title: "${generatedTitle}", Content starts with: "${generatedContent?.substring(0, 50)}..."`); // Removed log

            const potentialError = (typeof generatedContent === 'string' && generatedContent.trim().startsWith("Error:")) ||
                                 (typeof generatedTitle === 'string' && generatedTitle.trim().startsWith("Error:"));

            if (potentialError) {
                const errorMessage = generatedContent.trim().startsWith("Error:") ? generatedContent : generatedTitle;
                console.warn(`[ProjectDetail] Scene generation returned an error message: ${errorMessage}`); // Keep warn log
                setGenerationError(errorMessage);
                setShowGeneratedSceneModal(false);
            } else if (generatedTitle !== undefined && generatedContent !== undefined) {
                // console.log("[ProjectDetail] Scene generation successful, showing modal."); // Removed log
                setGeneratedSceneTitle(generatedTitle || "Untitled Scene");
                setGeneratedSceneContent(generatedContent);
                setChapterIdForGeneratedScene(chapterId);
                setShowGeneratedSceneModal(true);
                setGenerationError(null);
            } else {
                 console.error("[ProjectDetail] Unexpected response format from generateSceneDraft:", response.data); // Keep error log
                 setGenerationError("Error: Received unexpected response format from AI.");
                 setShowGeneratedSceneModal(false);
            }
        } catch (err) {
            console.error("[ProjectDetail] Error calling generateSceneDraft API:", err); // Keep error log
            if (err.response?.status === 429) {
                console.warn("[ProjectDetail] Received 429 status code."); // Keep warn log
                setGenerationError("AI feature temporarily unavailable due to free tier limits. Please try again later.");
            } else {
                 const msg = err.response?.data?.detail || err.message || 'Failed to generate scene draft.';
                 setGenerationError(msg);
            }
            setShowGeneratedSceneModal(false);
        } finally {
            // console.log("[ProjectDetail] Finished handleGenerateSceneDraft."); // Removed log
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
            const currentScenes = scenes[chapterIdForGeneratedScene] || [];
            const nextOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) + 1 : 1;
            const r = await createScene(projectId, chapterIdForGeneratedScene, { title: titleToSave, order: nextOrder, content: generatedSceneContent });
            setScenes(p => ({ ...p, [chapterIdForGeneratedScene]: [...(p[chapterIdForGeneratedScene] || []), r.data].sort((a, b) => a.order - b.order) }));
            setShowGeneratedSceneModal(false);
            setGeneratedSceneContent('');
            setGeneratedSceneTitle('');
            setChapterIdForGeneratedScene(null);
            setGeneratingChapterId(null);
            refreshData();
        } catch (err) { console.error("Create scene from draft error:", err); const msg = err.response?.data?.detail || err.message || 'Failed to create scene from draft.'; setCreateSceneError(msg); } // Added console.error
        finally { setIsCreatingSceneFromDraft(false); }
    }, [chapterIdForGeneratedScene, generatedSceneTitle, generatedSceneContent, scenes, projectId, refreshData]);

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
            .then(() => console.log("Generated title and content copied.")) // Keep log
            .catch(err => console.error('Failed to copy text: ', err)); // Keep error log
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
                 console.error(`[ProjectDetail] Split chapter returned an error: ${response.data.error}`); // Keep error log
                 setSplitError(response.data.error);
                 setShowSplitModal(false);
            } else {
                 setProposedSplits(response.data.proposed_scenes || []);
                 setChapterIdForSplits(chapterId);
                 setShowSplitModal(true);
                 setSplitError(null);
            }
        } catch (err) {
            console.error("[ProjectDetail] Error calling splitChapterIntoScenes API:", err); // Keep error log
             if (err.response?.status === 429) {
                console.warn("[ProjectDetail] Split Received 429 status code."); // Keep warn log
                setSplitError("AI feature temporarily unavailable due to free tier limits. Please try again later.");
            } else {
                const msg = err.response?.data?.detail || err.message || 'Failed to split chapter.';
                setSplitError(msg);
            }
            setShowSplitModal(false);
        } finally {
            // console.log("[ProjectDetail] Finished handleSplitChapter."); // Removed log
            setIsSplittingChapter(false);
        }
    }, [splitInputContent, projectId]);

    const handleCreateScenesFromSplit = useCallback(async () => {
        if (!chapterIdForSplits || proposedSplits.length === 0) { setCreateFromSplitError("No chapter ID or proposed splits available."); return; }
        setIsCreatingScenesFromSplit(true); setCreateFromSplitError(null);
        const existingScenes = scenes[chapterIdForSplits] || []; let currentMaxOrder = existingScenes.length > 0 ? Math.max(...existingScenes.map(s => s.order)) : 0;
        const errors = []; const createdScenes = [];
        for (const proposedScene of proposedSplits) {
            currentMaxOrder++; const newSceneData = { title: proposedScene.suggested_title || `Scene ${currentMaxOrder}`, order: currentMaxOrder, content: proposedScene.content || "" };
            try { const result = await createScene(projectId, chapterIdForSplits, newSceneData); createdScenes.push(result.data); }
            catch (err) { console.error("Create scene from split error:", err); const msg = err.response?.data?.detail || err.message || `Failed to create scene for "${newSceneData.title}".`; errors.push(msg); } // Added console.error
        }
        if (createdScenes.length > 0) { setScenes(p => ({ ...p, [chapterIdForSplits]: [...(p[chapterIdForSplits] || []), ...createdScenes].sort((a, b) => a.order - b.order) })); }
        setIsCreatingScenesFromSplit(false);
        if (errors.length > 0) { setCreateFromSplitError(errors.join(' | ')); }
        else { setShowSplitModal(false); setProposedSplits([]); setChapterIdForSplits(null); setSplittingChapterId(null); }
        refreshData();
    }, [chapterIdForSplits, proposedSplits, scenes, projectId, refreshData]);

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

    // --- Rendering Logic ---
    // console.log(`[ProjectDetail] Rendering - isLoadingProject: ${isLoadingProject}, isLoadingChapters: ${isLoadingChapters}, isLoadingCharacters: ${isLoadingCharacters}, error: ${error}, project: ${project ? 'Exists' : 'null'}`); // Removed log

     if (isLoadingProject) {
         // console.log("[ProjectDetail] Rendering Loading project state..."); // Removed log
         return <p>Loading project...</p>;
     }
     if (error && !project) {
         // console.log("[ProjectDetail] Rendering Error state (project load failed)..."); // Removed log
         return ( <div> <p style={{ color: 'red' }}>Error: {error}</p> <Link to="/"> &lt; Back to Project List</Link> </div> );
     }
     if (!project) {
         // console.log("[ProjectDetail] Rendering Not Found state..."); // Removed log
         return ( <div> <p>Project not found.</p> <Link to="/"> &lt; Back to Project List</Link> </div> );
     }

    // console.log("[ProjectDetail] Rendering Main Content structure..."); // Removed log
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