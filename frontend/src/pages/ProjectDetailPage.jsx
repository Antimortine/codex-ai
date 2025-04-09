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
    splitChapterIntoScenes // Import the split API function
} from '../api/codexApi';
import QueryInterface from '../components/QueryInterface';
import ChapterSection from '../components/ChapterSection';

// Basic Modal Styling (Add back split styles)
const modalStyles = {
    overlay: {
        position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.6)', display: 'flex',
        alignItems: 'center', justifyContent: 'center', zIndex: 1000,
    },
    content: {
        backgroundColor: '#fff', padding: '20px', borderRadius: '5px',
        maxWidth: '80%', width: '700px', maxHeight: '85vh',
        overflowY: 'auto', position: 'relative',
    },
    closeButton: {
        position: 'absolute', top: '10px', right: '10px', cursor: 'pointer',
        border: 'none', background: 'transparent', fontSize: '1.5rem', fontWeight: 'bold',
    },
    textarea: { width: '98%', minHeight: '200px', marginTop: '10px', fontFamily: 'monospace', fontSize: '0.9em' },
    copyButton: { marginTop: '10px', marginRight: '10px' },
    createButton: { marginTop: '10px', marginRight: '10px', backgroundColor: '#28a745', color: 'white' },
    // Split scene styles
    splitSceneItem: { border: '1px solid #ddd', borderRadius: '4px', marginBottom: '15px', padding: '10px' },
    splitSceneTitle: { fontWeight: 'bold', marginBottom: '5px', borderBottom: '1px solid #eee', paddingBottom: '5px' },
    splitSceneContent: { maxHeight: '150px', overflowY: 'auto', backgroundColor: '#f8f8f8', padding: '8px', borderRadius: '3px', fontSize: '0.9em', whiteSpace: 'pre-wrap', wordWrap: 'break-word' },
    splitModalActions: { marginTop: '20px', paddingTop: '10px', borderTop: '1px solid #ccc', textAlign: 'right' },
    splitCreateButton: { backgroundColor: '#28a745', color: 'white', marginRight: '10px' },
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
    const [generatedSceneContent, setGeneratedSceneContent] = useState('');
    const [showGeneratedSceneModal, setShowGeneratedSceneModal] = useState(false);
    const [chapterIdForGeneratedScene, setChapterIdForGeneratedScene] = useState(null);
    const [isCreatingSceneFromDraft, setIsCreatingSceneFromDraft] = useState(false);
    const [createSceneError, setCreateSceneError] = useState(null);
    const [isGeneratingScene, setIsGeneratingScene] = useState(false);
    const [generatingChapterId, setGeneratingChapterId] = useState(null);
    const [generationError, setGenerationError] = useState(null); // Stores errors for specific chapters
    const [splitInputContent, setSplitInputContent] = useState({});
    const [proposedSplits, setProposedSplits] = useState([]);
    const [chapterIdForSplits, setChapterIdForSplits] = useState(null);
    const [showSplitModal, setShowSplitModal] = useState(false);
    const [isCreatingScenesFromSplit, setIsCreatingScenesFromSplit] = useState(false);
    const [createFromSplitError, setCreateFromSplitError] = useState(null);
    const [isSplittingChapter, setIsSplittingChapter] = useState(false);
    const [splittingChapterId, setSplittingChapterId] = useState(null);
    const [splitError, setSplitError] = useState(null); // Stores errors for specific chapters


    // --- Data Fetching (Unchanged) ---
    useEffect(() => {
        let isMounted = true;
        setIsLoadingProject(true); setError(null);
        setProject(null); setChapters([]); setCharacters([]); setScenes({});
        if (!projectId) { if (isMounted) { setError("Project ID not found in URL."); setIsLoadingProject(false); } return; }
        getProject(projectId)
            .then(response => { if (isMounted) { setProject(response.data); setEditedProjectName(response.data.name || ''); } })
            .catch(err => { if (isMounted) setError(`Failed to load project data: ${err.message}`); })
            .finally(() => { if (isMounted) setIsLoadingProject(false); });
        return () => { isMounted = false; };
    }, [projectId]);

    useEffect(() => {
        let isMounted = true;
        if (!project || isLoadingProject) { if (!isLoadingProject) { setIsLoadingChapters(true); setIsLoadingCharacters(true); } return; }
        setIsLoadingChapters(true); setIsLoadingCharacters(true); setChapters([]); setCharacters([]);
        const fetchChaptersAndChars = async () => {
            try {
                const results = await Promise.allSettled([ listChapters(projectId), listCharacters(projectId) ]);
                if (isMounted) {
                    if (results[0].status === 'fulfilled') {
                        const sortedChapters = (results[0].value.data.chapters || []).sort((a, b) => a.order - b.order);
                        setChapters(sortedChapters);
                        const initialSummaries = {}; const initialSplitContent = {};
                        sortedChapters.forEach(ch => { initialSummaries[ch.id] = ''; initialSplitContent[ch.id] = ''; });
                        setGenerationSummaries(initialSummaries); setSplitInputContent(initialSplitContent);
                    } else { setError(prev => prev ? `${prev} | Failed to load chapters.` : 'Failed to load chapters.'); }
                    if (results[1].status === 'fulfilled') { setCharacters(results[1].value.data.characters || []); }
                    else { setError(prev => prev ? `${prev} | Failed to load characters.` : 'Failed to load characters.'); }
                }
            } catch (err) { if (isMounted) setError(prev => prev ? `${prev} | Error processing chapter/character fetches.` : 'Error processing chapter/character fetches.'); }
            finally { if (isMounted) { setIsLoadingChapters(false); setIsLoadingCharacters(false); } }
        };
        fetchChaptersAndChars(); return () => { isMounted = false; };
    }, [project, projectId, isLoadingProject]);

    useEffect(() => {
        let isMounted = true;
        if (!Array.isArray(chapters) || chapters.length === 0 || isLoadingChapters) { setIsLoadingScenes({}); setScenes({}); return; }
        const initialLoadingState = {}; chapters.forEach(ch => { initialLoadingState[ch.id] = true; }); setIsLoadingScenes(initialLoadingState); setScenes({});
        const fetchAllScenes = async () => {
            const scenesPromises = chapters.map(async (chapter) => {
                try { const r = await listScenes(projectId, chapter.id); return { chapterId: chapter.id, scenes: (r.data.scenes || []).sort((a, b) => a.order - b.order), success: true }; }
                catch (err) { return { chapterId: chapter.id, error: err, success: false, chapterTitle: chapter.title }; }
            });
            try {
                const results = await Promise.allSettled(scenesPromises);
                if (isMounted) {
                    const newScenesState = {}; const newLoadingState = {};
                    results.forEach(result => {
                        if (result.status === 'fulfilled') {
                            const data = result.value; newLoadingState[data.chapterId] = false;
                            if (data.success) { newScenesState[data.chapterId] = data.scenes; }
                            else { newScenesState[data.chapterId] = []; setError(prev => prev ? `${prev} | Failed to load scenes for ${data.chapterTitle}.` : `Failed to load scenes for ${data.chapterTitle}.`); }
                        } else { console.error("Effect 3: A scene fetch promise rejected:", result.reason); }
                    });
                    setScenes(newScenesState); setIsLoadingScenes(newLoadingState);
                }
            } catch (err) { if (isMounted) { setError(prev => prev ? `${prev} | Error processing scene fetches.` : 'Error processing scene fetches.'); const r = {}; chapters.forEach(ch => { r[ch.id] = false; }); setIsLoadingScenes(r); } }
        };
        fetchAllScenes(); return () => { isMounted = false; };
    }, [chapters, projectId, isLoadingChapters]);


    // --- Action Handlers ---

    const refreshData = useCallback(async () => {
        let isMounted = true;
        setIsLoadingChapters(true); setIsLoadingCharacters(true);
        try {
            const [chaptersResponse, charactersResponse] = await Promise.all([ listChapters(projectId), listCharacters(projectId) ]);
            if (isMounted) {
                setChapters((chaptersResponse.data.chapters || []).sort((a, b) => a.order - b.order));
                setCharacters(charactersResponse.data.characters || []);
            }
        } catch (err) { if (isMounted) setError(prev => prev ? `${prev} | Failed to refresh data.` : 'Failed to refresh data.'); }
        finally { if (isMounted) { setIsLoadingChapters(false); setIsLoadingCharacters(false); } }
    }, [projectId]);


    // --- CRUD Handlers ---
    const handleCreateChapter = useCallback(async (e) => {
        e.preventDefault(); if (!newChapterTitle.trim()) return;
        try { await createChapter(projectId, { title: newChapterTitle, order: chapters.length > 0 ? Math.max(...chapters.map(c => c.order)) + 1 : 1 }); setNewChapterTitle(''); refreshData(); }
        catch (err) { setError("Failed to create chapter."); }
    }, [newChapterTitle, chapters, projectId, refreshData]);

    const handleDeleteChapter = useCallback(async (chapterId, chapterTitle) => {
        if (!window.confirm(`Delete chapter "${chapterTitle}" and ALL ITS SCENES?`)) return;
        try { await deleteChapter(projectId, chapterId); refreshData(); }
        catch (err) { setError("Failed to delete chapter."); }
    }, [projectId, refreshData]);

    const handleCreateCharacter = useCallback(async (e) => {
        e.preventDefault(); if (!newCharacterName.trim()) return;
        try { await createCharacter(projectId, { name: newCharacterName, description: "" }); setNewCharacterName(''); refreshData(); }
        catch (err) { setError("Failed to create character."); }
    }, [newCharacterName, projectId, refreshData]);

    const handleDeleteCharacter = useCallback(async (characterId, characterName) => {
        if (!window.confirm(`Delete character "${characterName}"?`)) return;
        try { await deleteCharacter(projectId, characterId); refreshData(); }
        catch (err) { setError("Failed to delete character."); }
    }, [projectId, refreshData]);

    const handleCreateScene = useCallback(async (chapterId) => {
        const currentScenes = scenes[chapterId] || []; const nextOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) + 1 : 1;
        try { const r = await createScene(projectId, chapterId, { title: "New Scene", order: nextOrder, content: "" }); setScenes(p => ({ ...p, [chapterId]: [...(p[chapterId] || []), r.data].sort((a, b) => a.order - b.order) })); refreshData(); }
        catch(err) { setError("Failed to create scene."); }
    }, [scenes, projectId, refreshData]);

    // --- MODIFIED handleDeleteScene ---
    const handleDeleteScene = useCallback(async (chapterId, sceneId, sceneTitle) => {
        if (!window.confirm(`Delete scene "${sceneTitle}"?`)) return;
         try {
             await deleteScene(projectId, chapterId, sceneId);
             // Optimistic UI update: Remove scene locally
             setScenes(prevScenes => {
                 const chapterScenes = prevScenes[chapterId] || [];
                 const updatedChapterScenes = chapterScenes.filter(scene => scene.id !== sceneId);
                 // Re-order remaining scenes (optional but good practice)
                 const reorderedScenes = updatedChapterScenes.map((scene, index) => ({
                     ...scene,
                     order: index + 1, // Re-assign order based on new position
                 }));
                 return {
                     ...prevScenes,
                     [chapterId]: reorderedScenes
                 };
             });
             // No refreshData() call needed here anymore
         } catch(err) {
            console.error("Error deleting scene:", err);
            setError("Failed to delete scene.");
            // Optionally, could trigger refreshData() here on error to ensure consistency
            // refreshData();
        }
    }, [projectId, setScenes, setError]); // Removed refreshData, added setScenes, setError

    const handleEditNameClick = useCallback(() => { setEditedProjectName(project?.name || ''); setIsEditingName(true); setSaveNameError(null); setSaveNameSuccess(''); }, [project]);
    const handleCancelEditName = useCallback(() => { setIsEditingName(false); }, []);
    const handleSaveName = useCallback(async () => {
        if (!editedProjectName.trim()) { setSaveNameError("Project name cannot be empty."); return; }
        if (editedProjectName === project?.name) { setIsEditingName(false); return; }
        setIsSavingName(true); setSaveNameError(null); setSaveNameSuccess('');
        try { const r = await updateProject(projectId, { name: editedProjectName }); setProject(r.data); setIsEditingName(false); setSaveNameSuccess('Project name updated successfully!'); setTimeout(() => setSaveNameSuccess(''), 3000); }
        catch (err) { setSaveNameError("Failed to update project name. Please try again."); }
        finally { setIsSavingName(false); }
    }, [editedProjectName, project, projectId]);

    const handleEditChapterClick = useCallback((chapter) => { setEditingChapterId(chapter.id); setEditedChapterTitle(chapter.title); setSaveChapterError(null); }, []);
    const handleCancelEditChapter = useCallback(() => { setEditingChapterId(null); setEditedChapterTitle(''); setSaveChapterError(null); }, []);
    const handleChapterTitleChange = useCallback((event) => { setEditedChapterTitle(event.target.value); if (saveChapterError) { setSaveChapterError(null); } }, [saveChapterError]);
    const handleSaveChapter = useCallback(async (chapterId, currentEditedTitle) => {
        if (!currentEditedTitle.trim()) { setSaveChapterError("Chapter title cannot be empty."); return; }
        setIsSavingChapter(true); setSaveChapterError(null);
        try { await updateChapter(projectId, chapterId, { title: currentEditedTitle }); setEditingChapterId(null); setEditedChapterTitle(''); refreshData(); }
        catch (err) { const msg = err.response?.data?.detail || err.message || 'Failed to update chapter.'; setSaveChapterError(msg); }
        finally { setIsSavingChapter(false); }
    }, [projectId, refreshData]);

    // --- AI Handlers ---
    const handleGenerateSceneDraft = useCallback(async (chapterId, summary) => {
        console.log(`[ProjectDetail] handleGenerateSceneDraft called for chapter ${chapterId}`);
        setIsGeneratingScene(true);
        setGeneratingChapterId(chapterId);
        setGenerationError(null); // Clear previous error for this chapter
        setGeneratedSceneContent('');
        setShowGeneratedSceneModal(false);
        setCreateSceneError(null);

        const currentScenes = scenes[chapterId] || [];
        const prevOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) : 0;

        try {
            const response = await generateSceneDraft(projectId, chapterId, { prompt_summary: summary, previous_scene_order: prevOrder });
            const generatedText = response.data?.generated_content;
            console.log(`[ProjectDetail] Received generation response. Content starts with: "${generatedText?.substring(0, 50)}..."`);

            // --- ADDED: Check if the returned content is an error message ---
            if (typeof generatedText === 'string' && generatedText.trim().startsWith("Error:")) {
                console.warn(`[ProjectDetail] Scene generation returned an error message: ${generatedText}`);
                setGenerationError(generatedText); // Set the error state for this chapter
                setShowGeneratedSceneModal(false); // Ensure modal doesn't show
            } else {
                // --- END ADDED ---
                console.log("[ProjectDetail] Scene generation successful, showing modal.");
                setGeneratedSceneContent(generatedText || "AI returned empty content.");
                setChapterIdForGeneratedScene(chapterId);
                setShowGeneratedSceneModal(true);
                setGenerationError(null); // Clear error on success
            }
        } catch (err) {
            console.error("[ProjectDetail] Error calling generateSceneDraft API:", err);
            const msg = err.response?.data?.detail || err.message || 'Failed to generate scene draft.';
            setGenerationError(msg); // Set error state for this chapter
            setShowGeneratedSceneModal(false);
        } finally {
            console.log("[ProjectDetail] Finished handleGenerateSceneDraft.");
            setIsGeneratingScene(false);
            // Keep generatingChapterId set if there was an error, otherwise it's cleared implicitly by success/modal close
            // If we clear it here unconditionally, the error message might disappear too soon.
            // Let's clear it only if successful or modal is closed.
            // We'll clear it when the modal closes or a new generation starts.
        }
    }, [scenes, projectId]); // Added scenes and projectId dependencies

    const handleCreateSceneFromDraft = useCallback(async () => {
        if (!chapterIdForGeneratedScene || !generatedSceneContent) { setCreateSceneError("Missing chapter ID or generated content."); return; }
        setIsCreatingSceneFromDraft(true); setCreateSceneError(null);
        try {
            let title = "Generated Scene"; const lines = generatedSceneContent.split('\n');
            if (lines[0]?.startsWith('#')) { title = lines[0].replace(/^[#\s]+/, '').trim(); } else if (lines[0]?.trim()) { title = lines[0].trim(); }
            if (title.length > 100) { title = title.substring(0, 97) + "..."; }
            const currentScenes = scenes[chapterIdForGeneratedScene] || []; const nextOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) + 1 : 1;
            const r = await createScene(projectId, chapterIdForGeneratedScene, { title: title, order: nextOrder, content: generatedSceneContent });
            setScenes(p => ({ ...p, [chapterIdForGeneratedScene]: [...(p[chapterIdForGeneratedScene] || []), r.data].sort((a, b) => a.order - b.order) }));
            setShowGeneratedSceneModal(false); setGeneratedSceneContent(''); setChapterIdForGeneratedScene(null); setGeneratingChapterId(null); // Clear generating ID on success
            refreshData();
        } catch (err) { const msg = err.response?.data?.detail || err.message || 'Failed to create scene from draft.'; setCreateSceneError(msg); }
        finally { setIsCreatingSceneFromDraft(false); }
    }, [chapterIdForGeneratedScene, generatedSceneContent, scenes, projectId, refreshData]);

    const handleSummaryChange = useCallback((chapterId, value) => {
        setGenerationSummaries(prev => ({ ...prev, [chapterId]: value }));
        // Clear error for this specific chapter if user starts typing a new summary
        if (generationError && generatingChapterId === chapterId) {
            setGenerationError(null);
            setGeneratingChapterId(null);
        }
     }, [generationError, generatingChapterId]); // Added dependencies

    const copyGeneratedText = useCallback(() => { navigator.clipboard.writeText(generatedSceneContent).catch(err => console.error('Failed to copy text: ', err)); }, [generatedSceneContent]);

    // --- Split Chapter Handlers ---
    const handleSplitInputChange = useCallback((chapterId, value) => {
        setSplitInputContent(prev => ({ ...prev, [chapterId]: value }));
        // Clear error for this specific chapter if user starts typing new content
        if (splitError && splittingChapterId === chapterId) {
            setSplitError(null);
            setSplittingChapterId(null);
        }
    }, [splitError, splittingChapterId]); // Added dependencies

    const handleSplitChapter = useCallback(async (chapterId) => {
        const contentToSplit = splitInputContent[chapterId] || '';
        if (!contentToSplit.trim()) {
            setSplitError("Please paste the chapter content...");
            setSplittingChapterId(chapterId);
            return;
        }
        setIsSplittingChapter(true);
        setSplittingChapterId(chapterId);
        setSplitError(null); // Clear previous error for this chapter
        setProposedSplits([]);
        setShowSplitModal(false);
        setCreateFromSplitError(null);

        try {
            const response = await splitChapterIntoScenes(projectId, chapterId, { chapter_content: contentToSplit });
            // --- ADDED: Check for error message in response (though less likely here) ---
            // Assuming the backend raises HTTPException for errors, this might not be needed,
            // but added for robustness in case it returns an error structure differently.
            if (response.data?.error) { // Check for a potential 'error' field
                 console.error(`[ProjectDetail] Split chapter returned an error: ${response.data.error}`);
                 setSplitError(response.data.error);
                 setShowSplitModal(false);
            } else {
            // --- END ADDED ---
                 setProposedSplits(response.data.proposed_scenes || []);
                 setChapterIdForSplits(chapterId);
                 setShowSplitModal(true);
                 setSplitError(null); // Clear error on success
            }
        } catch (err) {
            console.error("[ProjectDetail] Error calling splitChapterIntoScenes API:", err);
            const msg = err.response?.data?.detail || err.message || 'Failed to split chapter.';
            setSplitError(msg); // Set error state for this chapter
            setShowSplitModal(false);
        } finally {
            console.log("[ProjectDetail] Finished handleSplitChapter.");
            setIsSplittingChapter(false);
            // Keep splittingChapterId set if there was an error
            // Clear it only on success or modal close
        }
    }, [splitInputContent, projectId]); // Added dependencies

    const handleCreateScenesFromSplit = useCallback(async () => {
        if (!chapterIdForSplits || proposedSplits.length === 0) { setCreateFromSplitError("No chapter ID or proposed splits available."); return; }
        setIsCreatingScenesFromSplit(true); setCreateFromSplitError(null);
        const existingScenes = scenes[chapterIdForSplits] || []; let currentMaxOrder = existingScenes.length > 0 ? Math.max(...existingScenes.map(s => s.order)) : 0;
        const errors = []; const createdScenes = [];
        for (const proposedScene of proposedSplits) {
            currentMaxOrder++; const newSceneData = { title: proposedScene.suggested_title || `Scene ${currentMaxOrder}`, order: currentMaxOrder, content: proposedScene.content || "" };
            try { const result = await createScene(projectId, chapterIdForSplits, newSceneData); createdScenes.push(result.data); }
            catch (err) { const msg = err.response?.data?.detail || err.message || `Failed to create scene for "${newSceneData.title}".`; errors.push(msg); }
        }
        if (createdScenes.length > 0) { setScenes(p => ({ ...p, [chapterIdForSplits]: [...(p[chapterIdForSplits] || []), ...createdScenes].sort((a, b) => a.order - b.order) })); }
        setIsCreatingScenesFromSplit(false);
        if (errors.length > 0) { setCreateFromSplitError(errors.join(' | ')); }
        else { setShowSplitModal(false); setProposedSplits([]); setChapterIdForSplits(null); setSplittingChapterId(null); } // Clear splitting ID on success
        refreshData();
    }, [chapterIdForSplits, proposedSplits, scenes, projectId, refreshData]);

    const handleCloseSplitModal = useCallback(() => {
        setShowSplitModal(false); setProposedSplits([]); setChapterIdForSplits(null); setCreateFromSplitError(null);
        // Clear the specific chapter's split error if the modal is closed
        if (splitError && chapterIdForSplits === splittingChapterId) {
            setSplitError(null);
            setSplittingChapterId(null);
        }
    }, [splitError, chapterIdForSplits, splittingChapterId]); // Added dependencies

    // --- Callback for closing the generated scene modal ---
    const handleCloseGeneratedSceneModal = useCallback(() => {
        setShowGeneratedSceneModal(false);
        setGeneratedSceneContent('');
        setChapterIdForGeneratedScene(null);
        setCreateSceneError(null);
        // Clear the specific chapter's generation error if the modal is closed
        if (generationError && chapterIdForGeneratedScene === generatingChapterId) {
            setGenerationError(null);
            setGeneratingChapterId(null);
        }
    }, [generationError, chapterIdForGeneratedScene, generatingChapterId]); // Added dependencies


    // --- Combined Loading State ---
    const isAnyOperationLoading = isSavingName || isSavingChapter || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit;

    // --- DEBUG LOGGING (Removed) ---


    // --- Rendering Logic ---
     if (isLoadingProject) { return <p>Loading project...</p>; }
     if (error && !project) { return ( <div> <p style={{ color: 'red' }}>Error: {error}</p> <Link to="/"> &lt; Back to Project List</Link> </div> ); }
     if (!project) { return ( <div> <p>Project not found.</p> <Link to="/"> &lt; Back to Project List</Link> </div> ); }

    const isContentLoading = isLoadingChapters || isLoadingCharacters;

    return (
        <div>
            {/* Modals */}
            {showGeneratedSceneModal && (
                <div data-testid="generated-scene-modal" style={modalStyles.overlay}>
                     <div style={modalStyles.content}>
                        {/* Use the specific close handler */}
                        <button onClick={handleCloseGeneratedSceneModal} style={modalStyles.closeButton}>×</button>
                        <h3>Generated Scene Draft</h3>
                        {createSceneError && <p style={{ color: 'red', marginBottom: '10px' }}>Error: {createSceneError}</p>}
                        <textarea readOnly value={generatedSceneContent} style={modalStyles.textarea} />
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
                        {createFromSplitError && (
                            <div style={{ color: 'red', marginBottom: '10px' }}>
                                <div data-testid="split-error-general">Errors occurred during scene creation:</div>
                                <div data-testid="split-error-specific">{createFromSplitError}</div>
                            </div>
                        )}
                        <div>
                            {proposedSplits.map((split, index) => (
                                <div key={index} style={modalStyles.splitSceneItem}>
                                    <div style={modalStyles.splitSceneTitle}>{index + 1}. {split.suggested_title}</div>
                                    <div style={modalStyles.splitSceneContent}>{split.content}</div>
                                </div>
                            ))}
                        </div>
                        <div style={modalStyles.splitModalActions}>
                            <button onClick={handleCreateScenesFromSplit} style={modalStyles.splitCreateButton} disabled={isCreatingScenesFromSplit}>
                                {isCreatingScenesFromSplit ? 'Creating...' : 'Create Scenes'}
                            </button>
                            <button onClick={handleCloseSplitModal}> Cancel </button>
                        </div>
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
                                    // Pass down the specific error for this chapter's generation
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
                                    // Pass split props
                                    splitInputContentForThisChapter={splitInputContent[chapter.id] || ''}
                                    isSplittingThisChapter={isSplittingChapter && splittingChapterId === chapter.id}
                                    // Pass down the specific error for this chapter's split
                                    splitErrorForThisChapter={splittingChapterId === chapter.id ? splitError : null}
                                    onSplitInputChange={handleSplitInputChange}
                                    onSplitChapter={handleSplitChapter}
                                />
                            ))
                        )}
                        <form onSubmit={handleCreateChapter} style={{ marginTop: '1rem' }}>
                            <input
                                type="text"
                                value={newChapterTitle}
                                onChange={(e) => setNewChapterTitle(e.target.value)}
                                placeholder="New chapter title"
                                disabled={isAnyOperationLoading} // Use the master flag
                            />
                            <button type="submit" disabled={isAnyOperationLoading || !newChapterTitle.trim()}>
                                Add Chapter
                            </button>
                        </form>
                    </section>
                    <hr />
                    <section>
                        <h2>Characters</h2>
                        {characters.length === 0 ? <p>No characters yet.</p> : (
                            <ul>
                                {characters.map(character => (
                                    <li key={character.id} style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                        <Link to={`/projects/${projectId}/characters/${character.id}`}> {character.name} </Link>
                                        <span>
                                            <button
                                                onClick={() => handleDeleteCharacter(character.id, character.name)}
                                                style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }}
                                                disabled={isAnyOperationLoading} // Use the master flag
                                                title={isAnyOperationLoading ? "Operation in progress..." : "Delete character"}
                                            >
                                                Delete
                                            </button>
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        )}
                        <form onSubmit={handleCreateCharacter} style={{ marginTop: '0.5rem' }}>
                            <input
                                type="text"
                                value={newCharacterName}
                                onChange={(e) => setNewCharacterName(e.target.value)}
                                placeholder="New character name"
                                disabled={isAnyOperationLoading} // Use the master flag
                            />
                            <button type="submit" disabled={isAnyOperationLoading || !newCharacterName.trim()}>
                                Add Character
                            </button>
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

export default ProjectDetailPage; // Added missing export