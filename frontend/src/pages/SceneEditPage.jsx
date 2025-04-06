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
import MDEditor from '@uiw/react-md-editor';
import { getScene, updateScene } from '../api/codexApi'; // Import scene API functions

function SceneEditPage() {
  const { projectId, chapterId, sceneId } = useParams(); // Get all IDs
  const navigate = useNavigate();

  // State for scene data
  const [title, setTitle] = useState('');
  const [content, setContent] = useState('');
  const [order, setOrder] = useState(0); // Keep track of order if needed for display/context
  const [originalTitle, setOriginalTitle] = useState('');

  // State for loading/saving/errors
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  const fetchSceneData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSaveMessage('');
    try {
      const response = await getScene(projectId, chapterId, sceneId);
      setTitle(response.data.title || '');
      setOriginalTitle(response.data.title || '');
      setContent(response.data.content || '');
      setOrder(response.data.order || 0);
    } catch (err) {
      console.error("Error fetching scene:", err);
      setError(`Failed to load scene ${sceneId}.`);
      // Optionally navigate back
    } finally {
      setIsLoading(false);
    }
  }, [projectId, chapterId, sceneId]);

  useEffect(() => {
    fetchSceneData();
  }, [fetchSceneData]);

  const handleSave = async () => {
    if (!title.trim()) {
        setError('Scene title cannot be empty.');
        return;
    }
    setIsSaving(true);
    setError(null);
    setSaveMessage('');
    try {
      // Send updated fields (title, content). We don't typically update order here.
      // Order updates usually happen via drag-and-drop or dedicated buttons on the list view.
      await updateScene(projectId, chapterId, sceneId, { title: title, content: content });
      setSaveMessage('Scene saved successfully!');
      setOriginalTitle(title); // Update original title display on success
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error("Error saving scene:", err);
      setError('Failed to save scene.');
      setSaveMessage('');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <p>Loading scene editor...</p>;
  }

  if (error && !isSaving) {
    return (
      <div>
        <p style={{ color: 'red' }}>Error: {error}</p>
        {/* Provide link back to project, as chapter ID might be invalid too */}
        <Link to={`/projects/${projectId}`}>&lt; Back to Project Overview</Link>
      </div>
    );
  }

  return (
    <div>
      <nav style={{ marginBottom: '1rem' }}>
        {/* Link back to the main project detail page */}
        <Link to={`/projects/${projectId}`}>&lt; Back to Project Overview</Link>
        {/* TODO: Maybe link back to a specific Chapter view later */}
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
          style={{ width: '80%' }} // Make title wider
        />
      </div>

      {/* Content Editor */}
      <div style={{ marginBottom: '1rem' }}>
        <label>Content (Markdown):</label>
        <div data-color-mode="light" style={{ marginTop: '0.5rem' }}>
          <MDEditor
            value={content}
            onChange={(value) => setContent(value || '')}
            height={500} // Make editor taller for scenes
          />
        </div>
      </div>

      {/* Display save error */}
      {error && isSaving && <p style={{ color: 'red', marginTop: '0.5rem' }}>Error: {error}</p>}
      {/* Display save success message */}
      {saveMessage && <p style={{ color: 'green', marginTop: '0.5rem' }}>{saveMessage}</p>}

      <button
        onClick={handleSave}
        disabled={isSaving || !title.trim()} // Disable if saving or title empty
        style={{ marginTop: '1rem' }}
      >
        {isSaving ? 'Saving...' : 'Save Scene'}
      </button>
    </div>
  );
}

export default SceneEditPage;