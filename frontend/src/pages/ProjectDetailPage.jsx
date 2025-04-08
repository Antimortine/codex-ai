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

import React, { useState, useEffect, useCallback } from 'react'; // Added useCallback
import { useParams, Link, useNavigate } from 'react-router-dom';
import MDEditor from '@uiw/react-md-editor'; // Import MDEditor for potential display
import {
    getProject, updateProject,
    listChapters, createChapter, deleteChapter,
    listCharacters, createCharacter, deleteCharacter,
    listScenes, createScene, deleteScene,
    generateSceneDraft,
    splitChapterIntoScenes // Import the new AI API function
} from '../api/codexApi';
import QueryInterface from '../components/QueryInterface';

// Basic Modal Styling (can be moved to CSS)
const modalStyles = {
    overlay: {
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.6)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
    },
    content: {
        backgroundColor: '#fff',
        padding: '20px',
        borderRadius: '5px',
        maxWidth: '80%',
        width: '700px', // Set a specific width
        maxHeight: '85vh', // Limit height
        overflowY: 'auto', // Allow scrolling
        position: 'relative',
        // minWidth: '500px' // Ensure minimum width - replaced by width
    },
    closeButton: {
        position: 'absolute',
        top: '10px',
        right: '10px',
        cursor: 'pointer',
        border: 'none',
        background: 'transparent',
        fontSize: '1.5rem',
        fontWeight: 'bold',
    },
    textarea: { // Used for generated scene draft modal
        width: '98%',
        minHeight: '200px',
        marginTop: '10px',
        fontFamily: 'monospace',
        fontSize: '0.9em',
    },
    copyButton: { // Used for generated scene draft modal
         marginTop: '10px',
         marginRight: '10px',
    },
    createButton: { // Used for generated scene draft modal
         marginTop: '10px',
         marginRight: '10px',
         backgroundColor: '#28a745', // Green background
         color: 'white',
    },
    // --- Styles for Split Modal ---
    splitSceneItem: {
        border: '1px solid #ddd',
        borderRadius: '4px',
        marginBottom: '15px',
        padding: '10px',
    },
    splitSceneTitle: {
        fontWeight: 'bold',
        marginBottom: '5px',
        borderBottom: '1px solid #eee',
        paddingBottom: '5px',
    },
    splitSceneContent: {
        maxHeight: '150px', // Limit height of content preview
        overflowY: 'auto',
        backgroundColor: '#f8f8f8',
        padding: '8px',
        borderRadius: '3px',
        fontSize: '0.9em',
        whiteSpace: 'pre-wrap', // Preserve formatting
        wordWrap: 'break-word',
    },
    splitModalActions: {
        marginTop: '20px',
        paddingTop: '10px',
        borderTop: '1px solid #ccc',
        textAlign: 'right',
    },
    splitCreateButton: {
         backgroundColor: '#28a745',
         color: 'white',
         marginRight: '10px',
    }
    // --- End Split Modal Styles ---
};

function ProjectDetailPage() {
    const { projectId } = useParams();
    const navigate = useNavigate();

    // --- State variables ---
    const [project, setProject] = useState(null);
    const [chapters, setChapters] = useState([]);
    const [characters, setCharacters] = useState([]);
    const [scenes, setScenes] = useState({}); // { chapterId: [scene1, scene2] }
    const [isLoadingProject, setIsLoadingProject] = useState(true);
    const [isLoadingChapters, setIsLoadingChapters] = useState(true);
    const [isLoadingCharacters, setIsLoadingCharacters] = useState(true);
    const [isLoadingScenes, setIsLoadingScenes] = useState({}); // Track loading per chapter: { chapterId: boolean }
    const [error, setError] = useState(null);
    const [newChapterTitle, setNewChapterTitle] = useState('');
    const [newCharacterName, setNewCharacterName] = useState('');
    const [isEditingName, setIsEditingName] = useState(false);
    const [editedProjectName, setEditedProjectName] = useState('');
    const [isSavingName, setIsSavingName] = useState(false);
    const [saveNameError, setSaveNameError] = useState(null);
    const [saveNameSuccess, setSaveNameSuccess] = useState('');
    const [generationSummaries, setGenerationSummaries] = useState({});
    const [isGeneratingScene, setIsGeneratingScene] = useState(false);
    const [generatingChapterId, setGeneratingChapterId] = useState(null);
    const [generationError, setGenerationError] = useState(null);
    const [generatedSceneContent, setGeneratedSceneContent] = useState('');
    const [showGeneratedSceneModal, setShowGeneratedSceneModal] = useState(false);
    const [chapterIdForGeneratedScene, setChapterIdForGeneratedScene] = useState(null);
    const [isCreatingSceneFromDraft, setIsCreatingSceneFromDraft] = useState(false);
    const [createSceneError, setCreateSceneError] = useState(null);

    // --- NEW State for Chapter Splitting ---
    const [isSplittingChapter, setIsSplittingChapter] = useState(false);
    const [splittingChapterId, setSplittingChapterId] = useState(null);
    const [splitError, setSplitError] = useState(null);
    const [proposedSplits, setProposedSplits] = useState([]); // Stores [{suggested_title: "", content: ""}, ...]
    const [chapterIdForSplits, setChapterIdForSplits] = useState(null);
    const [showSplitModal, setShowSplitModal] = useState(false);
    const [isCreatingScenesFromSplit, setIsCreatingScenesFromSplit] = useState(false);
    const [createFromSplitError, setCreateFromSplitError] = useState(null);
    // --- END NEW State ---

    // --- useEffect for Data Fetching ---
    // Use useCallback to memoize fetchAllData
    const fetchAllData = useCallback(async () => {
        let isMounted = true;
        setError(null);
        setSaveNameError(null);
        setSaveNameSuccess('');
        setGenerationError(null);
        setCreateSceneError(null);
        setSplitError(null); // Reset split error on refresh

        if (!projectId) {
            if (isMounted) setError("Project ID not found in URL.");
            setIsLoadingProject(false); setIsLoadingChapters(false); setIsLoadingCharacters(false); setIsLoadingScenes({});
            return;
        }

        if (isMounted) {
            setIsLoadingProject(true); setIsLoadingChapters(true); setIsLoadingCharacters(true); setIsLoadingScenes({}); // Reset scenes loading state
            setProject(null); setChapters([]); setCharacters([]); setScenes({}); setGenerationSummaries({});
        }

        try {
            const projectResponse = await getProject(projectId);
            if (isMounted) { setProject(projectResponse.data); setEditedProjectName(projectResponse.data.name || ''); }

            const chaptersResponse = await listChapters(projectId);
            const sortedChapters = (chaptersResponse.data.chapters || []).sort((a, b) => a.order - b.order);
            if (isMounted) setChapters(sortedChapters);

            const charactersResponse = await listCharacters(projectId);
            if (isMounted) setCharacters(charactersResponse.data.characters || []);

            // Fetch scenes for each chapter
            const initialSceneLoadingState = {};
            sortedChapters.forEach(ch => initialSceneLoadingState[ch.id] = true);
            if (isMounted) setIsLoadingScenes(initialSceneLoadingState);

            const scenesData = {};
            await Promise.all(sortedChapters.map(async (chapter) => {
                try {
                    const scenesResponse = await listScenes(projectId, chapter.id);
                    const sortedScenes = (scenesResponse.data.scenes || []).sort((a, b) => a.order - b.order);
                    scenesData[chapter.id] = sortedScenes;
                } catch (sceneErr) {
                    console.error(`Error fetching scenes for chapter ${chapter.id}:`, sceneErr);
                    scenesData[chapter.id] = []; // Assign empty array on error
                    if (isMounted) setError(prev => prev ? `${prev} | Failed to load scenes for ${chapter.title}.` : `Failed to load scenes for ${chapter.title}.`);
                } finally {
                     if (isMounted) setIsLoadingScenes(prev => ({ ...prev, [chapter.id]: false }));
                }
            }));
            if (isMounted) setScenes(scenesData);

        } catch (err) {
            console.error("Error during data fetching:", err);
            if (isMounted) { setError(`Failed to load project data: ${err.message}`); setProject(null); setChapters([]); setCharacters([]); setScenes({}); }
        } finally {
            if (isMounted) { setIsLoadingProject(false); setIsLoadingChapters(false); setIsLoadingCharacters(false); }
            // Scene loading is handled per chapter
        }
    }, [projectId]); // Dependency is projectId

    useEffect(() => {
        fetchAllData();
    }, [fetchAllData]); // Run fetchAllData when it changes (i.e., on projectId change)


    // --- Action Handlers ---
    const refreshChaptersAndScenes = useCallback(async () => {
         setIsLoadingChapters(true);
         const initialSceneLoadingState = {};
         chapters.forEach(ch => initialSceneLoadingState[ch.id] = true);
         setIsLoadingScenes(initialSceneLoadingState);
         setScenes({});
         let chapterFetchError = false;
         try {
             const response = await listChapters(projectId);
             const sortedChapters = (response.data.chapters || []).sort((a, b) => a.order - b.order);
             setChapters(sortedChapters);

             const scenesData = {};
             await Promise.all(sortedChapters.map(async (chapter) => {
                 try {
                      const scenesResponse = await listScenes(projectId, chapter.id);
                      const sortedScenes = (scenesResponse.data.scenes || []).sort((a,b) => a.order - b.order);
                      scenesData[chapter.id] = sortedScenes;
                 } catch(sceneErr) {
                      console.error(`Error fetching scenes for chapter ${chapter.id}:`, sceneErr);
                      scenesData[chapter.id] = [];
                      setError(prev => prev ? `${prev} | Failed to load scenes for ${chapter.title}.` : `Failed to load scenes for ${chapter.title}.`);
                 } finally {
                      setIsLoadingScenes(prev => ({ ...prev, [chapter.id]: false }));
                 }
             }));
             setScenes(scenesData);

         } catch (err) {
             console.error("Error fetching chapters:", err);
             setError(prev => prev ? `${prev} | Failed to load chapters.` : 'Failed to load chapters.');
             chapterFetchError = true;
             setIsLoadingScenes({}); // Clear loading if chapters failed
         } finally {
             setIsLoadingChapters(false);
             // Scene loading handled inside loop
         }
     }, [projectId, chapters]); // Depend on projectId and chapters list

    const handleCreateChapter = async (e) => {
        e.preventDefault();
        if (!newChapterTitle.trim()) return;
        const nextOrder = chapters.length > 0 ? Math.max(...chapters.map(c => c.order)) + 1 : 1;
        setIsLoadingChapters(true);
        try {
            await createChapter(projectId, { title: newChapterTitle, order: nextOrder });
            setNewChapterTitle('');
            refreshChaptersAndScenes(); // Refresh both
        } catch (err) {
            console.error("Error creating chapter:", err); setError("Failed to create chapter."); setIsLoadingChapters(false);
        }
    };

    const handleDeleteChapter = async (chapterId, chapterTitle) => {
        if (!window.confirm(`Delete chapter "${chapterTitle}" and ALL ITS SCENES?`)) return;
        setIsLoadingChapters(true); setIsLoadingScenes(prev => ({ ...prev, [chapterId]: true })); // Show loading for the chapter being deleted
        try {
            await deleteChapter(projectId, chapterId);
            refreshChaptersAndScenes(); // Refresh both
        } catch (err) {
             console.error("Error deleting chapter:", err); setError("Failed to delete chapter."); setIsLoadingChapters(false); setIsLoadingScenes(prev => ({ ...prev, [chapterId]: false }));
        }
    };

    const handleCreateCharacter = async (e) => {
        e.preventDefault();
        if (!newCharacterName.trim()) return;
        setIsLoadingCharacters(true);
        try {
            await createCharacter(projectId, { name: newCharacterName, description: "" });
            setNewCharacterName('');
            const response = await listCharacters(projectId); // Refresh only characters
            setCharacters(response.data.characters || []);
        } catch (err) {
             console.error("Error creating character:", err); setError("Failed to create character.");
        } finally {
             setIsLoadingCharacters(false);
        }
    };

    const handleDeleteCharacter = async (characterId, characterName) => {
        if (!window.confirm(`Delete character "${characterName}"?`)) return;
        setIsLoadingCharacters(true);
        try {
            await deleteCharacter(projectId, characterId);
            const response = await listCharacters(projectId); // Refresh only characters
            setCharacters(response.data.characters || []);
        } catch (err) {
             console.error("Error deleting character:", err); setError("Failed to delete character.");
        } finally {
             setIsLoadingCharacters(false);
        }
    };

    const handleCreateScene = async (chapterId) => {
         const currentScenes = scenes[chapterId] || [];
         const nextOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) + 1 : 1;
         setIsLoadingScenes(prev => ({ ...prev, [chapterId]: true }));
         try {
             const newSceneData = { title: "New Scene", order: nextOrder, content: "" };
             await createScene(projectId, chapterId, newSceneData);
             refreshChaptersAndScenes(); // Refresh all needed
         } catch(err) {
             console.error("Error creating scene:", err); setError("Failed to create scene."); setIsLoadingScenes(prev => ({ ...prev, [chapterId]: false }));
         }
    };

    const handleDeleteScene = async (chapterId, sceneId, sceneTitle) => {
        if (!window.confirm(`Delete scene "${sceneTitle}"?`)) return;
         setIsLoadingScenes(prev => ({ ...prev, [chapterId]: true }));
         try {
             await deleteScene(projectId, chapterId, sceneId);
             refreshChaptersAndScenes(); // Refresh all needed
         } catch(err) {
            console.error("Error deleting scene:", err); setError("Failed to delete scene."); setIsLoadingScenes(prev => ({ ...prev, [chapterId]: false }));
         }
    };

    const handleEditNameClick = () => {
        setEditedProjectName(project?.name || ''); setIsEditingName(true); setSaveNameError(null); setSaveNameSuccess('');
    };

    const handleCancelEditName = () => { setIsEditingName(false); };

    const handleSaveName = async () => {
        if (!editedProjectName.trim()) { setSaveNameError("Project name cannot be empty."); return; }
        if (editedProjectName === project?.name) { setIsEditingName(false); return; }
        setIsSavingName(true); setSaveNameError(null); setSaveNameSuccess('');
        try {
            const response = await updateProject(projectId, { name: editedProjectName });
            setProject(response.data); setIsEditingName(false); setSaveNameSuccess('Project name updated successfully!');
            setTimeout(() => setSaveNameSuccess(''), 3000);
        } catch (err) {
            console.error("Error updating project name:", err); setSaveNameError("Failed to update project name. Please try again.");
        } finally {
            setIsSavingName(false);
        }
    };

    const handleGenerateSceneDraft = async (chapterId) => {
        const summary = generationSummaries[chapterId] || '';
        setIsGeneratingScene(true); setGeneratingChapterId(chapterId); setGenerationError(null);
        setGeneratedSceneContent(''); setShowGeneratedSceneModal(false); setCreateSceneError(null);
        const currentScenesInChapter = scenes[chapterId] || [];
        const previousSceneOrder = currentScenesInChapter.length > 0 ? Math.max(...currentScenesInChapter.map(s => s.order)) : 0;
        const requestData = { prompt_summary: summary, previous_scene_order: previousSceneOrder };
        try {
            const response = await generateSceneDraft(projectId, chapterId, requestData);
            setGeneratedSceneContent(response.data.generated_content || "AI returned empty content.");
            setChapterIdForGeneratedScene(chapterId); setShowGeneratedSceneModal(true);
        } catch (err) {
            console.error("Error generating scene draft:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to generate scene draft.';
            setGenerationError(errorMsg); setShowGeneratedSceneModal(false);
        } finally {
            setIsGeneratingScene(false); setGeneratingChapterId(null);
        }
    };

    const handleCreateSceneFromDraft = async () => {
        if (!chapterIdForGeneratedScene || !generatedSceneContent) { setCreateSceneError("Missing chapter ID or generated content."); return; }
        setIsCreatingSceneFromDraft(true); setCreateSceneError(null);
        try {
            let title = "Generated Scene";
            const lines = generatedSceneContent.split('\n');
            if (lines[0]?.startsWith('#')) { title = lines[0].replace(/^[#\s]+/, '').trim(); }
            else if (lines[0]?.trim()) { title = lines[0].trim(); }
            if (title.length > 100) { title = title.substring(0, 97) + "..."; }
            const currentScenes = scenes[chapterIdForGeneratedScene] || [];
            const nextOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) + 1 : 1;
            const newSceneData = { title: title, order: nextOrder, content: generatedSceneContent };
            await createScene(projectId, chapterIdForGeneratedScene, newSceneData);
            setShowGeneratedSceneModal(false); setGeneratedSceneContent(''); setChapterIdForGeneratedScene(null);
            refreshChaptersAndScenes(); // Refresh needed
        } catch (err) {
            console.error("Error creating scene from draft:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to create scene from draft.';
            setCreateSceneError(errorMsg);
        } finally {
            setIsCreatingSceneFromDraft(false);
        }
    };

    const handleSummaryChange = (chapterId, value) => { setGenerationSummaries(prev => ({ ...prev, [chapterId]: value })); };
    const copyGeneratedText = () => { navigator.clipboard.writeText(generatedSceneContent).catch(err => console.error('Failed to copy text: ', err)); };

    // --- NEW: Chapter Split Handlers ---
    const handleSplitChapter = async (chapterId) => {
        setIsSplittingChapter(true);
        setSplittingChapterId(chapterId);
        setSplitError(null);
        setProposedSplits([]);
        setShowSplitModal(false);
        setCreateFromSplitError(null);

        try {
            const response = await splitChapterIntoScenes(projectId, chapterId, {}); // Empty request body for now
            setProposedSplits(response.data.proposed_scenes || []);
            setChapterIdForSplits(chapterId);
            setShowSplitModal(true);
        } catch (err) {
            console.error("Error splitting chapter:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to split chapter.';
            setSplitError(errorMsg);
        } finally {
            setIsSplittingChapter(false);
            setSplittingChapterId(null);
        }
    };

    const handleCreateScenesFromSplit = async () => {
        if (!chapterIdForSplits || proposedSplits.length === 0) {
            setCreateFromSplitError("No chapter ID or proposed splits available.");
            return;
        }
        setIsCreatingScenesFromSplit(true);
        setCreateFromSplitError(null);

        const existingScenes = scenes[chapterIdForSplits] || [];
        let currentMaxOrder = existingScenes.length > 0 ? Math.max(...existingScenes.map(s => s.order)) : 0;
        let scenesCreatedCount = 0;
        const errors = [];

        for (const proposedScene of proposedSplits) {
            currentMaxOrder++; // Increment order for the new scene
            const newSceneData = {
                title: proposedScene.suggested_title || `Scene ${currentMaxOrder}`,
                order: currentMaxOrder,
                content: proposedScene.content || ""
            };
            try {
                await createScene(projectId, chapterIdForSplits, newSceneData);
                scenesCreatedCount++;
            } catch (err) {
                console.error(`Error creating scene (Order ${currentMaxOrder}) from split:`, err);
                const errorMsg = err.response?.data?.detail || err.message || `Failed to create scene for "${newSceneData.title}".`;
                errors.push(errorMsg);
                // Decide whether to stop or continue on error
                // break; // Uncomment to stop on first error
            }
        }

        setIsCreatingScenesFromSplit(false);
        setShowSplitModal(false);
        setProposedSplits([]);
        setChapterIdForSplits(null);

        if (errors.length > 0) {
            setCreateFromSplitError(`Errors occurred during scene creation: ${errors.join('; ')}`);
        } else if (scenesCreatedCount > 0) {
            // Only refresh if scenes were actually created
            refreshChaptersAndScenes();
        }
    };
    // --- END NEW Handlers ---


    // --- Rendering Logic ---
     const isLoading = isLoadingProject || isLoadingChapters || isLoadingCharacters; // Base loading
     if (isLoadingProject && !project && !error) { return <p>Loading project...</p>; }
     if (error && !isLoading) { return ( <div> <p style={{ color: 'red' }}>Error: {error}</p> <Link to="/"> &lt; Back to Project List</Link> </div> ); }
     if (!isLoadingProject && !project) { return ( <div> <p>Project not found.</p> <Link to="/"> &lt; Back to Project List</Link> </div> ); }

    return (
        <div>
            {/* Scene Generation Modal */}
            {showGeneratedSceneModal && ( <div style={modalStyles.overlay}> <div style={modalStyles.content}> <button style={modalStyles.closeButton} onClick={() => setShowGeneratedSceneModal(false)} disabled={isCreatingSceneFromDraft}> × </button> <h3>Generated Scene Draft</h3> <textarea style={modalStyles.textarea} value={generatedSceneContent} readOnly /> {createSceneError && <p style={{ color: 'red', marginTop:'5px', fontSize:'0.9em' }}>Error: {createSceneError}</p>} <button style={modalStyles.createButton} onClick={handleCreateSceneFromDraft} disabled={isCreatingSceneFromDraft || !generatedSceneContent.trim()}> {isCreatingSceneFromDraft ? 'Creating Scene...' : 'Create Scene with this Draft'} </button> <button style={modalStyles.copyButton} onClick={copyGeneratedText} disabled={isCreatingSceneFromDraft}> Copy Text </button> <button onClick={() => setShowGeneratedSceneModal(false)} disabled={isCreatingSceneFromDraft}> Cancel </button> </div> </div> )}

            {/* --- NEW: Chapter Split Modal --- */}
            {showSplitModal && (
                <div style={modalStyles.overlay}>
                    <div style={modalStyles.content}>
                        <button style={modalStyles.closeButton} onClick={() => setShowSplitModal(false)} disabled={isCreatingScenesFromSplit}> × </button>
                        <h3>Proposed Scene Splits</h3>
                        {createFromSplitError && <p style={{ color: 'red', marginTop:'5px', fontSize:'0.9em' }}>Error: {createFromSplitError}</p>}
                        {proposedSplits.length > 0 ? (
                            proposedSplits.map((split, index) => (
                                <div key={index} style={modalStyles.splitSceneItem}>
                                    <div style={modalStyles.splitSceneTitle}>Proposed Scene {index + 1}: {split.suggested_title}</div>
                                    <pre style={modalStyles.splitSceneContent}><code>{split.content}</code></pre>
                                </div>
                            ))
                        ) : (
                            <p>The AI did not propose any splits for this chapter.</p>
                        )}
                        <div style={modalStyles.splitModalActions}>
                            <button
                                style={modalStyles.splitCreateButton}
                                onClick={handleCreateScenesFromSplit}
                                disabled={isCreatingScenesFromSplit || proposedSplits.length === 0}
                            >
                                {isCreatingScenesFromSplit ? 'Creating Scenes...' : 'Create Scenes from Splits'}
                            </button>
                            <button onClick={() => setShowSplitModal(false)} disabled={isCreatingScenesFromSplit}>
                                Cancel
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* --- END NEW Modal --- */}


            {/* Page Content */}
            <nav> <Link to="/"> &lt; Back to Project List</Link> </nav>
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                 {!isEditingName ? ( <> <h1 style={{ marginRight: '1rem', marginBottom: 0 }}> Project: {project?.name || 'Loading...'} </h1> {project && ( <button onClick={handleEditNameClick} disabled={isLoadingProject || isSavingName || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit}> Edit Name </button> )} </> ) : ( <> <input type="text" value={editedProjectName} onChange={(e) => setEditedProjectName(e.target.value)} disabled={isSavingName} style={{ fontSize: '1.5em', marginRight: '0.5rem' }} aria-label="Project Name" /> <button onClick={handleSaveName} disabled={isSavingName || !editedProjectName.trim()}> {isSavingName ? 'Saving...' : 'Save Name'} </button> <button onClick={handleCancelEditName} disabled={isSavingName} style={{ marginLeft: '0.5rem' }}> Cancel </button> </> )}
            </div>
            {saveNameError && <p style={{ color: 'red', marginTop: '0.2rem' }}>{saveNameError}</p>}
            {saveNameSuccess && <p style={{ color: 'green', marginTop: '0.2rem' }}>{saveNameSuccess}</p>}
            <p>ID: {projectId}</p>
            <hr />
            {projectId && <QueryInterface projectId={projectId} />}
            <hr />
            <section>
                <h2>Chapters</h2>
                {isLoadingChapters ? <p>Loading chapters...</p> : (
                    chapters.length === 0 ? <p>No chapters yet.</p> :
                    chapters.map(chapter => (
                        <div key={chapter.id} data-testid={`chapter-section-${chapter.id}`} style={{ border: '1px solid #eee', padding: '10px', marginBottom: '10px' }}>
                           <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                                <strong>{chapter.order}: {chapter.title}</strong>
                                <div> {/* Container for buttons */}
                                    {/* --- NEW: Split Chapter Button --- */}
                                    <button
                                        onClick={() => handleSplitChapter(chapter.id)}
                                        style={{ marginLeft: '1rem', cursor: 'pointer', backgroundColor: '#ffc107', color: '#333' }}
                                        disabled={isLoadingScenes[chapter.id] || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit || (scenes[chapter.id] && scenes[chapter.id].length > 0)} // Disable if scenes exist
                                        title={scenes[chapter.id] && scenes[chapter.id].length > 0 ? "Cannot split chapter that already has scenes" : "Split this chapter into scenes using AI"}
                                    >
                                        {isSplittingChapter && splittingChapterId === chapter.id ? 'Splitting...' : 'Split Chapter (AI)'}
                                    </button>
                                    {/* --- END NEW Button --- */}
                                    <button onClick={() => handleDeleteChapter(chapter.id, chapter.title)} style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }} disabled={isLoadingChapters || isLoadingScenes[chapter.id] || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit}> Delete Chapter </button>
                                </div>
                           </div>
                           {/* Display Split Error specific to this chapter */}
                           {splitError && splittingChapterId === chapter.id && <p style={{ color: 'red', fontSize: '0.9em', marginTop:'5px' }}>Split Error: {splitError}</p>}

                            {isLoadingScenes[chapter.id] ? <p style={{marginLeft:'20px'}}>Loading scenes...</p> : ( <ul style={{ listStyle: 'none', paddingLeft: '20px' }}> {(scenes[chapter.id] || []).map(scene => ( <li key={scene.id} style={{ marginBottom: '0.3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}> <Link to={`/projects/${projectId}/chapters/${chapter.id}/scenes/${scene.id}`}> {scene.order}: {scene.title} </Link> <button onClick={() => handleDeleteScene(chapter.id, scene.id, scene.title)} style={{ marginLeft: '1rem', fontSize: '0.8em', color: 'orange', cursor: 'pointer' }} disabled={isLoadingScenes[chapter.id] || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit}> Del Scene </button> </li> ))} {(scenes[chapter.id]?.length === 0 || !scenes[chapter.id]) && !isLoadingScenes[chapter.id] && <p style={{marginLeft:'20px', fontStyle:'italic'}}>No scenes in this chapter yet.</p>} </ul> )}
                             <div style={{marginLeft: '20px', marginTop: '10px', borderTop: '1px dashed #ccc', paddingTop: '10px'}}> <button onClick={() => handleCreateScene(chapter.id)} style={{marginRight: '10px'}} disabled={isLoadingScenes[chapter.id] || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit}>+ Add Scene Manually</button> <div style={{ marginTop: '10px', padding:'5px', backgroundColor:'#f0f8ff', borderRadius:'3px' }}> <label htmlFor={`summary-${chapter.id}`} style={{ fontSize: '0.9em', marginRight: '5px' }}>Optional Prompt/Summary for AI:</label> <input type="text" id={`summary-${chapter.id}`} value={generationSummaries[chapter.id] || ''} onChange={(e) => handleSummaryChange(chapter.id, e.target.value)} placeholder="e.g., Character meets the informant" disabled={isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit} style={{ fontSize: '0.9em', marginRight: '5px', minWidth:'250px' }} /> <button onClick={() => handleGenerateSceneDraft(chapter.id)} disabled={isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit}> {isGeneratingScene && generatingChapterId === chapter.id ? 'Generating...' : '+ Add Scene using AI'} </button> {isGeneratingScene && generatingChapterId === chapter.id && <span style={{ marginLeft:'5px', fontStyle:'italic', fontSize:'0.9em' }}> (AI is working...)</span>} {generationError && generatingChapterId === chapter.id && <p style={{ color: 'red', fontSize: '0.9em', marginTop:'5px' }}>Error: {generationError}</p>} </div> </div>
                        </div>
                    ))
                )}
                 <form onSubmit={handleCreateChapter} style={{ marginTop: '1rem' }}> <input type="text" value={newChapterTitle} onChange={(e) => setNewChapterTitle(e.target.value)} placeholder="New chapter title" disabled={isLoadingChapters || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit} /> <button type="submit" disabled={isLoadingChapters || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit}>Add Chapter</button> </form>
            </section>
            <hr />
            <section>
                 <h2>Characters</h2>
                {isLoadingCharacters ? <p>Loading characters...</p> : ( <ul> {characters.map(character => ( <li key={character.id} style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}> <Link to={`/projects/${projectId}/characters/${character.id}`}> {character.name} </Link> <span> <button onClick={() => handleDeleteCharacter(character.id, character.name)} style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }} disabled={isLoadingCharacters || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit}> Delete </button> </span> </li> ))} {characters.length === 0 && !isLoadingCharacters && <p>No characters yet.</p>} </ul> )}
                <form onSubmit={handleCreateCharacter} style={{ marginTop: '0.5rem' }}> <input type="text" value={newCharacterName} onChange={(e) => setNewCharacterName(e.target.value)} placeholder="New character name" disabled={isLoadingCharacters || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit} /> <button type="submit" disabled={isLoadingCharacters || isGeneratingScene || isCreatingSceneFromDraft || isSplittingChapter || isCreatingScenesFromSplit}>Add Character</button> </form>
            </section>
            <hr />
            <section>
                 <h2>Other Content</h2>
                <ul style={{ listStyle: 'none', paddingLeft: 0 }}> <li style={{ marginBottom: '0.5rem' }}> <Link to={`/projects/${projectId}/plan`}>Edit Plan</Link> </li> <li style={{ marginBottom: '0.5rem' }}> <Link to={`/projects/${projectId}/synopsis`}>Edit Synopsis</Link> </li> <li style={{ marginBottom: '0.5rem' }}> <Link to={`/projects/${projectId}/world`}>Edit World Info</Link> </li> </ul>
            </section>
        </div>
    );
}

export default ProjectDetailPage;