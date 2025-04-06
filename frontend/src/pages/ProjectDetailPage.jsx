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
import {
    getProject, updateProject,
    listChapters, createChapter, deleteChapter,
    listCharacters, createCharacter, deleteCharacter,
    listScenes, createScene, deleteScene
} from '../api/codexApi';

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

    // --- Main useEffect for Data Fetching ---
    useEffect(() => {
        let isMounted = true;
        setError(null);
        setSaveNameError(null); // Clear name saving error on load
        setSaveNameSuccess(''); // Clear name saving success on load

        const fetchAllData = async () => {
            if (!projectId) {
                console.log("useEffect running, but projectId is still missing.");
                if (isMounted) setError("Project ID not found in URL.");
                // Set all loading to false if no projectId
                setIsLoadingProject(false);
                setIsLoadingChapters(false);
                setIsLoadingCharacters(false);
                setIsLoadingScenes(false);
                return;
            }
            console.log("useEffect running with projectId:", projectId);

            if (isMounted) { // Reset states before fetching
                setIsLoadingProject(true);
                setIsLoadingChapters(true);
                setIsLoadingCharacters(true);
                setIsLoadingScenes(true);
                setProject(null); // Clear project while loading
                setChapters([]);
                setCharacters([]);
                setScenes({});
            }

            try {
                console.log("Fetching project...");
                const projectResponse = await getProject(projectId);
                if (isMounted) {
                    setProject(projectResponse.data);
                    setEditedProjectName(projectResponse.data.name || ''); // Initialize edited name state
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

    const handleCreateChapter = async (e) => {
        e.preventDefault();
        if (!newChapterTitle.trim()) return;
        const nextOrder = chapters.length > 0 ? Math.max(...chapters.map(c => c.order)) + 1 : 0;
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
         const nextOrder = scenes[chapterId] ? (scenes[chapterId].length > 0 ? Math.max(...scenes[chapterId].map(s => s.order)) + 1 : 0) : 0;
         setIsLoadingScenes(true);
         try {
             const newSceneData = { title: "New Scene", order: nextOrder, content: "" };
             console.log("Attempting to create scene with data:", newSceneData);
             const response = await createScene(projectId, chapterId, newSceneData);
             console.log("Scene created response:", response.data);
             refreshChaptersAndScenes();
         } catch(err) {
             console.error("Error creating scene:", err);
             setError("Failed to create scene.");
             setIsLoadingScenes(false);
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

    // --- Handlers for Editing Project Name ---
    const handleEditNameClick = () => {
        setEditedProjectName(project?.name || ''); // Ensure it's initialized from current project state
        setIsEditingName(true);
        setSaveNameError(null);
        setSaveNameSuccess('');
    };

    const handleCancelEditName = () => {
        setIsEditingName(false);
        // No need to reset editedProjectName here
    };

    const handleSaveName = async () => {
        if (!editedProjectName.trim()) {
            setSaveNameError("Project name cannot be empty.");
            return;
        }
        // Only save if the name actually changed
        if (editedProjectName === project?.name) {
            setIsEditingName(false);
            return;
        }

        setIsSavingName(true);
        setSaveNameError(null);
        setSaveNameSuccess('');

        try {
            const response = await updateProject(projectId, { name: editedProjectName });
            setProject(response.data); // Update local project state with response from backend
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


    // --- Rendering Logic ---

    const isLoading = isLoadingProject || isLoadingChapters || isLoadingCharacters || isLoadingScenes;

     if (isLoadingProject && !project && !error) {
         return <p>Loading project...</p>;
     }

    if (error) {
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
            <nav>
                <Link to="/"> &lt; Back to Project List</Link>
            </nav>

            {/* --- Project Header with Editable Name --- */}
            <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                {!isEditingName ? (
                    <>
                        <h1 style={{ marginRight: '1rem', marginBottom: 0 }}>
                            Project: {project?.name || 'Loading...'}
                        </h1>
                        {/* Only show Edit button if project data is loaded */}
                        {project && (
                            <button onClick={handleEditNameClick} disabled={isLoadingProject || isSavingName}>
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
                            aria-label="Project Name" // Accessibility
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
            {/* Display Name Save Status */}
            {saveNameError && <p style={{ color: 'red', marginTop: '0.2rem' }}>{saveNameError}</p>}
            {saveNameSuccess && <p style={{ color: 'green', marginTop: '0.2rem' }}>{saveNameSuccess}</p>}


            <p>ID: {projectId}</p>
            <hr />

            {/* Chapters Section */}
            <section>
                <h2>Chapters</h2>
                {isLoadingChapters ? <p>Loading chapters...</p> : (
                    chapters.length === 0 ? <p>No chapters yet.</p> :
                    chapters.map(chapter => (
                        <div key={chapter.id} style={{ border: '1px solid #eee', padding: '10px', marginBottom: '10px' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '5px' }}>
                                <strong>{chapter.order}: {chapter.title}</strong>
                                <button onClick={() => handleDeleteChapter(chapter.id, chapter.title)} style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }} disabled={isLoadingChapters || isLoadingScenes}>
                                    Delete Chapter
                                </button>
                            </div>
                            {isLoadingScenes ? <p style={{marginLeft:'20px'}}>Loading scenes...</p> : (
                                <ul style={{ listStyle: 'none', paddingLeft: '20px' }}>
                                    {(scenes[chapter.id] || []).map(scene => (
                                        <li key={scene.id} style={{ marginBottom: '0.3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                             <Link to={`/projects/${projectId}/chapters/${chapter.id}/scenes/${scene.id}`}>
                                                {scene.order}: {scene.title}
                                            </Link>
                                             <button onClick={() => handleDeleteScene(chapter.id, scene.id, scene.title)} style={{ marginLeft: '1rem', fontSize: '0.8em', color: 'orange', cursor: 'pointer' }} disabled={isLoadingScenes}>
                                                Del Scene
                                            </button>
                                        </li>
                                    ))}
                                    {(scenes[chapter.id]?.length === 0 || !scenes[chapter.id]) && !isLoadingScenes && <p style={{marginLeft:'20px', fontStyle:'italic'}}>No scenes in this chapter yet.</p>}
                                </ul>
                            )}
                             <button onClick={() => handleCreateScene(chapter.id)} style={{marginLeft: '20px', marginTop: '5px'}} disabled={isLoadingScenes}>+ Add Scene</button>
                        </div>
                    ))
                )}
                 <form onSubmit={handleCreateChapter} style={{ marginTop: '1rem' }}>
                    <input
                      type="text"
                      value={newChapterTitle}
                      onChange={(e) => setNewChapterTitle(e.target.value)}
                      placeholder="New chapter title"
                      disabled={isLoadingChapters}
                    />
                    <button type="submit" disabled={isLoadingChapters}>Add Chapter</button>
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
                                <button onClick={() => handleDeleteCharacter(character.id, character.name)} style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }} disabled={isLoadingCharacters}>
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
                      disabled={isLoadingCharacters}
                    />
                    <button type="submit" disabled={isLoadingCharacters}>Add Character</button>
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