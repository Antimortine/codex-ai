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

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import AIEditorWrapper from '../components/AIEditorWrapper';
import { getScene, updateScene, listScenes } from '../api/codexApi';

const navLinkStyle = {
    margin: '0 10px',
    textDecoration: 'none',
    color: '#007bff',
};
const disabledNavLinkStyle = {
    margin: '0 10px',
    textDecoration: 'none',
    color: '#aaa',
    cursor: 'default',
    pointerEvents: 'none', // Prevent clicks
};

function SceneEditPage() {
  const { projectId, chapterId, sceneId } = useParams();
  const navigate = useNavigate();

  // State for current scene data
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [order, setOrder] = useState(0);
  const [originalTitle, setOriginalTitle] = useState('');

  // State for chapter scene list
  const [chapterScenes, setChapterScenes] = useState([]);
  const [isLoadingSceneList, setIsLoadingSceneList] = useState(true);

  // State for loading/saving/errors
  const [isLoading, setIsLoading] = useState(true); // Loading current scene
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  // --- REVISED: Fetch current scene AND chapter scene list with better loading state handling ---
  const fetchData = useCallback(async () => {
    // Reset states
    setIsLoading(true); // Loading main scene content
    setIsLoadingSceneList(true); // Loading the list for nav
    setError(null);
    setSaveMessage('');
    setChapterScenes([]);

    let sceneFetchError = null;
    let listFetchError = null;

    // Fetch current scene first
    try {
        const sceneResponse = await getScene(projectId, chapterId, sceneId);
        setTitle(sceneResponse.data.title || '');
        setOriginalTitle(sceneResponse.data.title || '');
        setContent(sceneResponse.data.content || '');
        setOrder(sceneResponse.data.order || 0);
        setIsLoading(false); // <<< Set main loading false AFTER scene data is fetched
    } catch (err) {
        console.error("Error fetching current scene:", err);
        sceneFetchError = `Failed to load scene ${sceneId}.`;
        setIsLoading(false); // <<< Also set main loading false on error
    }

    // Then fetch the scene list for navigation
    try {
        const listResponse = await listScenes(projectId, chapterId);
        const sortedScenes = (listResponse.data.scenes || []).sort((a, b) => a.order - b.order);
        setChapterScenes(sortedScenes);
    } catch (err) {
        console.error("Error fetching chapter scenes:", err);
        listFetchError = `Failed to load scene list for chapter.`;
    } finally {
        setIsLoadingSceneList(false); // <<< Set list loading false when list fetch finishes/fails
    }

    // Combine errors if any occurred
    if (sceneFetchError || listFetchError) {
        setError([sceneFetchError, listFetchError].filter(Boolean).join(' '));
    }

  }, [projectId, chapterId, sceneId]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);
  // --- END REVISED ---


  // Calculate previous/next scene IDs using useMemo (remains the same)
  const { prevSceneId, nextSceneId } = useMemo(() => {
    if (isLoadingSceneList || chapterScenes.length === 0 || order <= 0) {
        return { prevSceneId: null, nextSceneId: null };
    }
    const currentSceneIndex = chapterScenes.findIndex(s => s.id === sceneId);
    if (currentSceneIndex === -1) {
        console.warn("Current scene not found in chapter scene list, cannot determine neighbors.");
        return { prevSceneId: null, nextSceneId: null };
    }
    const prev = currentSceneIndex > 0 ? chapterScenes[currentSceneIndex - 1] : null;
    const next = currentSceneIndex < chapterScenes.length - 1 ? chapterScenes[currentSceneIndex + 1] : null;
    return {
        prevSceneId: prev ? prev.id : null,
        nextSceneId: next ? next.id : null,
    };
  }, [chapterScenes, sceneId, order, isLoadingSceneList]);


  const handleSave = async () => {
    if (!title.trim()) {
        setError('Scene title cannot be empty.');
        return;
    }
    setIsSaving(true);
    setError(null);
    setSaveMessage('');
    try {
      await updateScene(projectId, chapterId, sceneId, { title: title, content: content });
      setSaveMessage('Scene saved successfully!');
      setOriginalTitle(title);
      // Optionally re-fetch scene list if needed after save
      // await fetchData(); // Or just update local state if confident
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error("Error saving scene:", err);
      setError('Failed to save scene.');
      setSaveMessage('');
    } finally {
      setIsSaving(false);
    }
  };

  const handleContentChange = useCallback((newValue) => {
      setContent(newValue);
  }, []);


  if (isLoading) { // Only show main loader while fetching current scene
    return <p>Loading scene editor...</p>;
  }

  // Show error if main scene fetch failed
  if (error && !content && !title) { // Check if core content failed to load
    return (
      <div>
        <p style={{ color: 'red' }}>Error: {error}</p>
        <Link to={`/projects/${projectId}`}>&lt; Back to Project Overview</Link>
      </div>
    );
  }

  return (
    <div>
      <nav style={{ marginBottom: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        {/* Back Link */}
        <Link to={`/projects/${projectId}`}>&lt; Back to Project Overview</Link>

        {/* Scene Navigation */}
        {/* --- MODIFIED: Added data-testid to container --- */}
        <div data-testid="scene-navigation">
            {isLoadingSceneList ? (
                <>
                    {/* Render placeholders while list is loading */}
                    <span style={disabledNavLinkStyle}>&lt; Previous Scene</span>
                    <span style={disabledNavLinkStyle}>Next Scene &gt;</span>
                </>
            ) : (
                <>
                    {/* Render actual links or disabled spans based on calculated IDs */}
                    {prevSceneId ? (
                        <Link style={navLinkStyle} to={`/projects/${projectId}/chapters/${chapterId}/scenes/${prevSceneId}`}>
                            &lt; Previous Scene
                        </Link>
                    ) : (
                        <span style={disabledNavLinkStyle}>&lt; Previous Scene</span>
                    )}

                    {nextSceneId ? (
                        <Link style={navLinkStyle} to={`/projects/${projectId}/chapters/${chapterId}/scenes/${nextSceneId}`}>
                            Next Scene  &gt;
                        </Link>
                    ) : (
                        <span style={disabledNavLinkStyle}>Next Scene &gt;</span>
                    )}
                </>
            )}
        </div>
        {/* --- END MODIFIED --- */}

      </nav>
      <h2>Edit Scene: {originalTitle || '...'}</h2>
      <p>Project ID: {projectId}</p>
      <p>Chapter ID: {chapterId}</p>
      <p>Scene ID: {sceneId}</p>
      <p>Order: {order}</p>


      {/* Title Input */}
      <div style={{ marginBottom: '1rem' }}>
        <label htmlFor="sceneTitle" style={{ marginRight: '0.5rem' }}>Title:</label>
        <input
          type="text"
          id="sceneTitle"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          disabled={isSaving}
          style={{ width: '80%' }}
        />
      </div>

      {/* Content Editor - Use the Wrapper */}
      <div style={{ marginBottom: '1rem' }}>
        <label>Content (Markdown):</label>
        <div data-color-mode="light" style={{ marginTop: '0.5rem' }}>
          <AIEditorWrapper
            value={content}
            onChange={handleContentChange}
            height={500}
            projectId={projectId}
          />
        </div>
      </div>

      {/* Display errors that occurred during save or list fetch */}
      {error && <p style={{ color: 'red', marginTop: '0.5rem' }}>Error: {error}</p>}
      {saveMessage && <p style={{ color: 'green', marginTop: '0.5rem' }}>{saveMessage}</p>}

      <button
        onClick={handleSave}
        disabled={isSaving}
        style={{ marginTop: '1rem' }}
      >
        {isSaving ? 'Saving...' : 'Save Scene'}
      </button>
    </div>
  );
}

export default SceneEditPage;