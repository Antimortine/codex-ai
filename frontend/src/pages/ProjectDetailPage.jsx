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

import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import MDEditor from '@uiw/react-md-editor'; // Import MDEditor for potential display
import {
    getProject, updateProject,
    listChapters, createChapter, deleteChapter,
    listCharacters, createCharacter, deleteCharacter,
    listScenes, createScene, deleteScene,
    generateSceneDraft // Import the new AI API function
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
        maxHeight: '80%',
        overflowY: 'auto',
        position: 'relative',
        minWidth: '500px' // Ensure minimum width
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
    textarea: {
        width: '98%',
        minHeight: '200px',
        marginTop: '10px',
        fontFamily: 'monospace',
        fontSize: '0.9em',
    },
    copyButton: {
         marginTop: '10px',
         marginRight: '10px',
    },
    createButton: { // Style for the new button
         marginTop: '10px',
         marginRight: '10px',
         backgroundColor: '#28a745', // Green background
         color: 'white',
    }
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
    const [isLoadingScenes, setIsLoadingScenes] = useState(true);
    const [error, setError] = useState(null);
    const [newChapterTitle, setNewChapterTitle] = useState('');
    const [newCharacterName, setNewCharacterName] = useState('');
    // --- State for Editing Project Name ---
    const [isEditingName, setIsEditingName] = useState(false);
    const [editedProjectName, setEditedProjectName] = useState('');
    const [isSavingName, setIsSavingName] = useState(false);
    const [saveNameError, setSaveNameError] = useState(null);
    const [saveNameSuccess, setSaveNameSuccess] = useState('');
    // --- State for AI Scene Generation ---
    const [generationSummaries, setGenerationSummaries] = useState({}); // { chapterId: 'summary' }
    const [isGeneratingScene, setIsGeneratingScene] = useState(false); // Track generation loading state
    const [generatingChapterId, setGeneratingChapterId] = useState(null); // Track which chapter is generating
    const [generationError, setGenerationError] = useState(null); // Store generation errors
    const [generatedSceneContent, setGeneratedSceneContent] = useState(''); // Store the generated content
    const [showGeneratedSceneModal, setShowGeneratedSceneModal] = useState(false); // Control modal visibility
    const [chapterIdForGeneratedScene, setChapterIdForGeneratedScene] = useState(null); // Store chapter ID when modal opens
    const [isCreatingSceneFromDraft, setIsCreatingSceneFromDraft] = useState(false); // Loading state for creating from draft
    const [createSceneError, setCreateSceneError] = useState(null); // Error state for creating from draft

    // --- useEffect for Data Fetching ---
    useEffect(() => {
        let isMounted = true;
        setError(null);
        setSaveNameError(null);
        setSaveNameSuccess('');
        setGenerationError(null);
        setCreateSceneError(null); // Reset create scene error

        const fetchAllData = async () => {
            // ... (existing data fetching logic remains the same) ...
            if (!projectId) {
                console.log("useEffect running, but projectId is still missing.");
                if (isMounted) setError("Project ID not found in URL.");
                setIsLoadingProject(false);
                setIsLoadingChapters(false);
                setIsLoadingCharacters(false);
                setIsLoadingScenes(false);
                return;
            }
            console.log("useEffect running with projectId:", projectId);

            if (isMounted) {
                setIsLoadingProject(true);
                setIsLoadingChapters(true);
                setIsLoadingCharacters(true);
                setIsLoadingScenes(true);
                setProject(null);
                setChapters([]);
                setCharacters([]);
                setScenes({});
                setGenerationSummaries({}); // Reset summaries on load
            }

            try {
                console.log("Fetching project...");
                const projectResponse = await getProject(projectId);
                if (isMounted) {
                    setProject(projectResponse.data);
                    setEditedProjectName(projectResponse.data.name || '');
                }
                console.log("Project fetched.");

                console.log("Fetching chapters...");
                const chaptersResponse = await listChapters(projectId);
                const sortedChapters = (chaptersResponse.data.chapters || []).sort((a, b) => a.order - b.order);
                if (isMounted) setChapters(sortedChapters);
                console.log("Chapters fetched.");

                console.log("Fetching characters...");
                const charactersResponse = await listCharacters(projectId);
                if (isMounted) setCharacters(charactersResponse.data.characters || []);
                console.log("Characters fetched.");

                console.log("Fetching scenes for chapters...");
                const scenesData = {};
                await Promise.all(sortedChapters.map(async (chapter) => {
                    try {
                        const scenesResponse = await listScenes(projectId, chapter.id);
                        const sortedScenes = (scenesResponse.data.scenes || []).sort((a, b) => a.order - b.order);
                        scenesData[chapter.id] = sortedScenes;
                    } catch (sceneErr) {
                        console.error(`Error fetching scenes for chapter ${chapter.id}:`, sceneErr);
                        scenesData[chapter.id] = [];
                        if (isMounted) setError(prev => prev ? `${prev} | Failed to load some scenes.` : 'Failed to load some scenes.');
                    }
                }));
                if (isMounted) setScenes(scenesData);
                console.log("Scenes fetched.");

            } catch (err) {
                console.error("Error during data fetching:", err);
                if (isMounted) {
                    setError(`Failed to load project data: ${err.message}`);
                    setProject(null);
                    setChapters([]);
                    setCharacters([]);
                    setScenes({});
                }
            } finally {
                if (isMounted) {
                    setIsLoadingProject(false);
                    setIsLoadingChapters(false);
                    setIsLoadingCharacters(false);
                    setIsLoadingScenes(false);
                }
                console.log("All fetching finished.");
            }
        };

        fetchAllData();

        return () => {
            isMounted = false;
            console.log("ProjectDetailPage cleanup ran.");
        };
    }, [projectId]);


    // --- Action Handlers ---
    const refreshChaptersAndScenes = async () => {
         setIsLoadingChapters(true);
         setIsLoadingScenes(true);
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
                      setError(prev => prev ? `${prev} | Failed to load some scenes.` : 'Failed to load some scenes.');
                 }
             }));
             setScenes(scenesData);

         } catch (err) {
             console.error("Error fetching chapters:", err);
             setError(prev => prev ? `${prev} | Failed to load chapters.` : 'Failed to load chapters.');
             chapterFetchError = true;
         } finally {
             setIsLoadingChapters(false);
             setIsLoadingScenes(false);
         }
     };

    // --- handleCreateChapter, handleDeleteChapter, handleCreateCharacter, handleDeleteCharacter, handleCreateScene, handleDeleteScene, handleEditNameClick, handleCancelEditName, handleSaveName remain the same ---
    // ... (omitted for brevity, assume they are unchanged) ...
     const handleCreateChapter = async (e) => {
        e.preventDefault();
        if (!newChapterTitle.trim()) return;
        const nextOrder = chapters.length > 0 ? Math.max(...chapters.map(c => c.order)) + 1 : 1;
        setIsLoadingChapters(true);
        try {
            await createChapter(projectId, { title: newChapterTitle, order: nextOrder });
            setNewChapterTitle('');
            refreshChaptersAndScenes();
        } catch (err) {
            console.error("Error creating chapter:", err);
            setError("Failed to create chapter.");
            setIsLoadingChapters(false);
        }
    };

    const handleDeleteChapter = async (chapterId, chapterTitle) => {
        if (!window.confirm(`Delete chapter "${chapterTitle}" and ALL ITS SCENES?`)) return;
        setIsLoadingChapters(true);
        setIsLoadingScenes(true);
        try {
            await deleteChapter(projectId, chapterId);
            refreshChaptersAndScenes();
        } catch (err) {
             console.error("Error deleting chapter:", err);
             setError("Failed to delete chapter.");
             setIsLoadingChapters(false);
             setIsLoadingScenes(false);
        }
    };

    const handleCreateCharacter = async (e) => {
        e.preventDefault();
        if (!newCharacterName.trim()) return;
        setIsLoadingCharacters(true);
        try {
            await createCharacter(projectId, { name: newCharacterName, description: "" });
            setNewCharacterName('');
            const response = await listCharacters(projectId);
            setCharacters(response.data.characters || []);
        } catch (err) {
             console.error("Error creating character:", err);
             setError("Failed to create character.");
        } finally {
             setIsLoadingCharacters(false);
        }
    };

    const handleDeleteCharacter = async (characterId, characterName) => {
        if (!window.confirm(`Delete character "${characterName}"?`)) return;
        setIsLoadingCharacters(true);
        try {
            await deleteCharacter(projectId, characterId);
            const response = await listCharacters(projectId);
            setCharacters(response.data.characters || []);
        } catch (err) {
             console.error("Error deleting character:", err);
             setError("Failed to delete character.");
        } finally {
             setIsLoadingCharacters(false);
        }
    };

    const handleCreateScene = async (chapterId) => {
         const currentScenes = scenes[chapterId] || [];
         const nextOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) + 1 : 1;
         setIsLoadingScenes(true);
         try {
             const newSceneData = { title: "New Scene", order: nextOrder, content: "" };
             console.log("Attempting to create scene with data:", newSceneData);
             const response = await createScene(projectId, chapterId, newSceneData);
             console.log("Scene created response:", response.data);
             refreshChaptersAndScenes(); // Refresh is handled here
         } catch(err) {
             console.error("Error creating scene:", err);
             setError("Failed to create scene.");
             setIsLoadingScenes(false); // Ensure loading state is reset on error
         } finally {
             // Loading state reset is handled by refreshChaptersAndScenes on success
         }
    };

    const handleDeleteScene = async (chapterId, sceneId, sceneTitle) => {
        if (!window.confirm(`Delete scene "${sceneTitle}"?`)) return;
         setIsLoadingScenes(true);
         try {
             await deleteScene(projectId, chapterId, sceneId);
             refreshChaptersAndScenes();
         } catch(err) {
            console.error("Error deleting scene:", err);
            setError("Failed to delete scene.");
            setIsLoadingScenes(false);
         }
    };

    const handleEditNameClick = () => {
        setEditedProjectName(project?.name || '');
        setIsEditingName(true);
        setSaveNameError(null);
        setSaveNameSuccess('');
    };

    const handleCancelEditName = () => {
        setIsEditingName(false);
    };

    const handleSaveName = async () => {
        if (!editedProjectName.trim()) {
            setSaveNameError("Project name cannot be empty.");
            return;
        }
        if (editedProjectName === project?.name) {
            setIsEditingName(false);
            return;
        }

        setIsSavingName(true);
        setSaveNameError(null);
        setSaveNameSuccess('');

        try {
            const response = await updateProject(projectId, { name: editedProjectName });
            setProject(response.data);
            setIsEditingName(false);
            setSaveNameSuccess('Project name updated successfully!');
            setTimeout(() => setSaveNameSuccess(''), 3000);
        } catch (err) {
            console.error("Error updating project name:", err);
            setSaveNameError("Failed to update project name. Please try again.");
        } finally {
            setIsSavingName(false);
        }
    };

    // --- AI Generation Handler ---
    const handleGenerateSceneDraft = async (chapterId) => {
        const summary = generationSummaries[chapterId] || ''; // Get summary for the specific chapter
        setIsGeneratingScene(true);
        setGeneratingChapterId(chapterId); // Mark which chapter is generating
        setGenerationError(null);
        setGeneratedSceneContent('');
        setShowGeneratedSceneModal(false);
        setCreateSceneError(null); // Clear any previous create error

        console.log(`Requesting scene draft for chapter ${chapterId} with summary: "${summary}"`);

        try {
            const response = await generateSceneDraft(projectId, chapterId, { prompt_summary: summary });
            console.log("AI Generation Response:", response.data);
            setGeneratedSceneContent(response.data.generated_content || "AI returned empty content.");
            setChapterIdForGeneratedScene(chapterId); // Store the relevant chapter ID
            setShowGeneratedSceneModal(true); // Show the modal with the content
        } catch (err) {
            console.error("Error generating scene draft:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to generate scene draft.';
            setGenerationError(errorMsg);
            setShowGeneratedSceneModal(false);
        } finally {
            setIsGeneratingScene(false);
            setGeneratingChapterId(null); // Reset generating chapter ID
        }
    };

    // --- Create Scene From Draft Handler ---
    const handleCreateSceneFromDraft = async () => {
        if (!chapterIdForGeneratedScene || !generatedSceneContent) {
            setCreateSceneError("Missing chapter ID or generated content.");
            return;
        }

        setIsCreatingSceneFromDraft(true);
        setCreateSceneError(null);

        try {
            // 1. Extract Title (simple logic)
            let title = "Generated Scene";
            const lines = generatedSceneContent.split('\n');
            if (lines[0]?.startsWith('#')) { // Check if first line is a Markdown heading
                title = lines[0].replace(/^[#\s]+/, '').trim(); // Remove leading '#' and spaces
            } else if (lines[0]?.trim()) { // Use first non-empty line if no heading
                 title = lines[0].trim();
            }
            // Truncate title if too long
            if (title.length > 100) {
                 title = title.substring(0, 97) + "...";
            }

            // 2. Calculate Next Order
            const currentScenes = scenes[chapterIdForGeneratedScene] || [];
            const nextOrder = currentScenes.length > 0 ? Math.max(...currentScenes.map(s => s.order)) + 1 : 1;

            // 3. Call API
            const newSceneData = {
                 title: title,
                 order: nextOrder,
                 content: generatedSceneContent
            };
            console.log("Attempting to create scene from draft with data:", newSceneData);
            await createScene(projectId, chapterIdForGeneratedScene, newSceneData);

            // 4. Close modal and refresh
            setShowGeneratedSceneModal(false);
            setGeneratedSceneContent(''); // Clear content
            setChapterIdForGeneratedScene(null); // Clear stored chapter ID
            refreshChaptersAndScenes(); // Refresh the scene list

        } catch (err) {
            console.error("Error creating scene from draft:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to create scene from draft.';
            setCreateSceneError(errorMsg); // Show error within the modal
        } finally {
            setIsCreatingSceneFromDraft(false);
        }
    };


    // Handler for updating generation summary state
    const handleSummaryChange = (chapterId, value) => {
        setGenerationSummaries(prev => ({
            ...prev,
            [chapterId]: value
        }));
    };

     // Handler for copying generated text
    const copyGeneratedText = () => {
        navigator.clipboard.writeText(generatedSceneContent)
            .then(() => {
                // Optional: Show a temporary "Copied!" message
                console.log('Generated text copied to clipboard');
            })
            .catch(err => {
                console.error('Failed to copy text: ', err);
            });
    };

    // --- Rendering Logic ---

    const isLoading = isLoadingProject || isLoadingChapters || isLoadingCharacters || isLoadingScenes;

     if (isLoadingProject && !project && !error) {
         return <p>Loading project...</p>;
     }

    if (error && !isLoading) { // Only show main error if not loading something else
        return (
             <div>
                <p style={{ color: 'red' }}>Error: {error}</p>
                <Link to="/"> &lt; Back to Project List</Link>
            </div>
        );
    }

    if (!isLoadingProject && !project) {
        return (
             <div>
                <p>Project not found.</p>
                <Link to="/"> &lt; Back to Project List</Link>
            </div>
        );
    }

    // Main render
    return (
        <div>
            {/* --- Generated Scene Modal --- */}
            {showGeneratedSceneModal && (
                <div style={modalStyles.overlay}>
                    <div style={modalStyles.content}>
                        <button
                           style={modalStyles.closeButton}
                           onClick={() => setShowGeneratedSceneModal(false)}
                           disabled={isCreatingSceneFromDraft} // Disable close while creating
                        >
                            × {/* Close button */}
                        </button>
                        <h3>Generated Scene Draft</h3>
                        {/* Display generated content in a textarea */}
                        <textarea
                            style={modalStyles.textarea}
                            value={generatedSceneContent}
                            readOnly
                        />
                        {/* Display error related to creating scene from draft */}
                        {createSceneError && <p style={{ color: 'red', marginTop:'5px', fontSize:'0.9em' }}>Error: {createSceneError}</p>}
                        {/* Action buttons */}
                        <button
                           style={modalStyles.createButton}
                           onClick={handleCreateSceneFromDraft}
                           disabled={isCreatingSceneFromDraft || !generatedSceneContent.trim()} // Disable if creating or no content
                        >
                            {isCreatingSceneFromDraft ? 'Creating Scene...' : 'Create Scene with this Draft'}
                        </button>
                        <button
                            style={modalStyles.copyButton}
                            onClick={copyGeneratedText}
                            disabled={isCreatingSceneFromDraft}
                        >
                           Copy Text
                        </button>
                        <button
                            onClick={() => setShowGeneratedSceneModal(false)}
                            disabled={isCreatingSceneFromDraft}
                        >
                           Cancel
                        </button>
                    </div>
                </div>
            )}

             {/* --- Rest of the page content (nav, header, sections) --- */}
            {/* ... (omitted for brevity, assume they are unchanged from previous version) ... */}
            <nav>
                <Link to="/"> &lt; Back to Project List</Link>
            </nav>

            {/* Project Header */}
             <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                {!isEditingName ? (
                    <>
                        <h1 style={{ marginRight: '1rem', marginBottom: 0 }}>
                            Project: {project?.name || 'Loading...'}
                        </h1>
                        {project && (
                            <button onClick={handleEditNameClick} disabled={isLoadingProject || isSavingName || isGeneratingScene || isCreatingSceneFromDraft}>
                                Edit Name
                            </button>
                        )}
                    </>
                ) : (
                    <>
                        <input
                            type="text"
                            value={editedProjectName}
                            onChange={(e) => setEditedProjectName(e.target.value)}
                            disabled={isSavingName}
                            style={{ fontSize: '1.5em', marginRight: '0.5rem' }}
                            aria-label="Project Name"
                        />
                        <button onClick={handleSaveName} disabled={isSavingName || !editedProjectName.trim()}>
                            {isSavingName ? 'Saving...' : 'Save Name'}
                        </button>
                        <button onClick={handleCancelEditName} disabled={isSavingName} style={{ marginLeft: '0.5rem' }}>
                            Cancel
                        </button>
                    </>
                )}
            </div>
            {saveNameError && <p style={{ color: 'red', marginTop: '0.2rem' }}>{saveNameError}</p>}
            {saveNameSuccess && <p style={{ color: 'green', marginTop: '0.2rem' }}>{saveNameSuccess}</p>}
            <p>ID: {projectId}</p>
            <hr />

            {/* --- AI Query Interface --- */}
            {projectId && <QueryInterface projectId={projectId} />}
            <hr /> {/* Add separator */}


            {/* Chapters Section */}
            <section>
                <h2>Chapters</h2>
                {isLoadingChapters ? <p>Loading chapters...</p> : (
                    chapters.length === 0 ? <p>No chapters yet.</p> :
                    chapters.map(chapter => (
                        <div key={chapter.id} style={{ border: '1px solid #eee', padding: '10px', marginBottom: '10px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                                <strong>{chapter.order}: {chapter.title}</strong>
                                <button onClick={() => handleDeleteChapter(chapter.id, chapter.title)} style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }} disabled={isLoadingChapters || isLoadingScenes || isGeneratingScene || isCreatingSceneFromDraft}>
                                    Delete Chapter
                                </button>
                            </div>
                            {/* --- Scene List --- */}
                            {isLoadingScenes ? <p style={{marginLeft:'20px'}}>Loading scenes...</p> : (
                                <ul style={{ listStyle: 'none', paddingLeft: '20px' }}>
                                    {(scenes[chapter.id] || []).map(scene => (
                                        <li key={scene.id} style={{ marginBottom: '0.3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                             <Link to={`/projects/${projectId}/chapters/${chapter.id}/scenes/${scene.id}`}>
                                                {scene.order}: {scene.title}
                                            </Link>
                                             <button onClick={() => handleDeleteScene(chapter.id, scene.id, scene.title)} style={{ marginLeft: '1rem', fontSize: '0.8em', color: 'orange', cursor: 'pointer' }} disabled={isLoadingScenes || isGeneratingScene || isCreatingSceneFromDraft}>
                                                Del Scene
                                            </button>
                                        </li>
                                    ))}
                                    {(scenes[chapter.id]?.length === 0 || !scenes[chapter.id]) && !isLoadingScenes && <p style={{marginLeft:'20px', fontStyle:'italic'}}>No scenes in this chapter yet.</p>}
                                </ul>
                            )}
                            {/* --- Actions for Chapter (Add Scene, Generate Scene) --- */}
                             <div style={{marginLeft: '20px', marginTop: '10px', borderTop: '1px dashed #ccc', paddingTop: '10px'}}>
                                <button onClick={() => handleCreateScene(chapter.id)} style={{marginRight: '10px'}} disabled={isLoadingScenes || isGeneratingScene || isCreatingSceneFromDraft}>+ Add Scene Manually</button>

                                {/* --- AI Scene Generation UI --- */}
                                <div style={{ marginTop: '10px', padding:'5px', backgroundColor:'#f0f8ff', borderRadius:'3px' }}>
                                    <label htmlFor={`summary-${chapter.id}`} style={{ fontSize: '0.9em', marginRight: '5px' }}>Optional Prompt/Summary for AI:</label>
                                    <input
                                        type="text"
                                        id={`summary-${chapter.id}`}
                                        value={generationSummaries[chapter.id] || ''}
                                        onChange={(e) => handleSummaryChange(chapter.id, e.target.value)}
                                        placeholder="e.g., Character meets the informant"
                                        disabled={isGeneratingScene || isCreatingSceneFromDraft}
                                        style={{ fontSize: '0.9em', marginRight: '5px', minWidth:'250px' }}
                                    />
                                    <button
                                        onClick={() => handleGenerateSceneDraft(chapter.id)}
                                        disabled={isGeneratingScene || isCreatingSceneFromDraft}
                                    >
                                        {isGeneratingScene && generatingChapterId === chapter.id ? 'Generating...' : '+ Add Scene using AI'}
                                    </button>
                                    {/* Show loading/error specific to this chapter */}
                                    {isGeneratingScene && generatingChapterId === chapter.id && <span style={{ marginLeft:'5px', fontStyle:'italic', fontSize:'0.9em' }}> (AI is working...)</span>}
                                    {generationError && generatingChapterId === chapter.id && <p style={{ color: 'red', fontSize: '0.9em', marginTop:'5px' }}>Error: {generationError}</p>}
                                </div>
                                {/* --- End AI Scene Generation UI --- */}
                            </div>
                        </div>
                    ))
                )}
                 <form onSubmit={handleCreateChapter} style={{ marginTop: '1rem' }}>
                    <input
                      type="text"
                      value={newChapterTitle}
                      onChange={(e) => setNewChapterTitle(e.target.value)}
                      placeholder="New chapter title"
                      disabled={isLoadingChapters || isGeneratingScene || isCreatingSceneFromDraft}
                    />
                    <button type="submit" disabled={isLoadingChapters || isGeneratingScene || isCreatingSceneFromDraft}>Add Chapter</button>
                 </form>
            </section>
            <hr />

            {/* Characters Section */}
             <section>
                <h2>Characters</h2>
                {isLoadingCharacters ? <p>Loading characters...</p> : (
                 <ul>
                    {characters.map(character => (
                        <li key={character.id} style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                            <Link to={`/projects/${projectId}/characters/${character.id}`}>
                                {character.name}
                            </Link>
                            <span>
                                <button onClick={() => handleDeleteCharacter(character.id, character.name)} style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }} disabled={isLoadingCharacters || isGeneratingScene || isCreatingSceneFromDraft}>
                                    Delete
                                </button>
                            </span>
                        </li>
                    ))}
                    {characters.length === 0 && !isLoadingCharacters && <p>No characters yet.</p>}
                 </ul>
             )}
                <form onSubmit={handleCreateCharacter} style={{ marginTop: '0.5rem' }}>
                    <input
                      type="text"
                      value={newCharacterName}
                      onChange={(e) => setNewCharacterName(e.target.value)}
                      placeholder="New character name"
                      disabled={isLoadingCharacters || isGeneratingScene || isCreatingSceneFromDraft}
                    />
                    <button type="submit" disabled={isLoadingCharacters || isGeneratingScene || isCreatingSceneFromDraft}>Add Character</button>
                </form>
            </section>
            <hr />

            {/* Other Content Blocks Section */}
            <section>
                <h2>Other Content</h2>
                <ul style={{ listStyle: 'none', paddingLeft: 0 }}>
                    <li style={{ marginBottom: '0.5rem' }}>
                        <Link to={`/projects/${projectId}/plan`}>Edit Plan</Link>
                    </li>
                    <li style={{ marginBottom: '0.5rem' }}>
                        <Link to={`/projects/${projectId}/synopsis`}>Edit Synopsis</Link>
                    </li>
                    <li style={{ marginBottom: '0.5rem' }}>
                        <Link to={`/projects/${projectId}/world`}>Edit World Info</Link>
                    </li>
                </ul>
            </section>

        </div>
    );
}

export default ProjectDetailPage;