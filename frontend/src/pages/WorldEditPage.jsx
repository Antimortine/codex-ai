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
import { useParams, Link } from 'react-router-dom';
// import MDEditor from '@uiw/react-md-editor'; // No longer directly used
import AIEditorWrapper from '../components/AIEditorWrapper'; // Import the wrapper
import { getWorldInfo, updateWorldInfo } from '../api/codexApi';

function WorldEditPage() {
  const { projectId } = useParams();
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  const fetchWorldContent = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSaveMessage('');
    try {
      const response = await getWorldInfo(projectId);
      setContent(response.data.content || '');
    } catch (err) {
      console.error("Error fetching world info:", err);
      setError(`Failed to load world info for project ${projectId}.`);
      setContent('');
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchWorldContent();
  }, [fetchWorldContent]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSaveMessage('');
    try {
      await updateWorldInfo(projectId, { content: content });
      setSaveMessage('World info saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error("Error saving world info:", err);
      setError('Failed to save world info.');
      setSaveMessage('');
    } finally {
      setIsSaving(false);
    }
  };

  // Callback for the editor wrapper
  const handleContentChange = useCallback((newValue) => {
      setContent(newValue);
  }, []);


  if (isLoading) {
    return <p>Loading world info editor...</p>;
  }

  if (error && !isSaving) {
    return <p style={{ color: 'red' }}>Error: {error}</p>;
  }

  return (
    <div>
      <nav style={{ marginBottom: '1rem' }}>
        <Link to={`/projects/${projectId}`}> &lt; Back to Project Overview</Link>
      </nav>
      <h2>Edit Worldbuilding Info</h2>
      <p>Project ID: {projectId}</p>

      <div data-color-mode="light">
         {/* Use AIEditorWrapper */}
         <AIEditorWrapper
            value={content}
            onChange={handleContentChange}
            height={400}
            projectId={projectId}
        />
      </div>

      {error && isSaving && <p style={{ color: 'red', marginTop: '0.5rem' }}>Error: {error}</p>}
      {saveMessage && <p style={{ color: 'green', marginTop: '0.5rem' }}>{saveMessage}</p>}

      <button
        onClick={handleSave}
        disabled={isSaving}
        style={{ marginTop: '1rem' }}
      >
        {isSaving ? 'Saving...' : 'Save World Info'}
      </button>
    </div>
  );
}

export default WorldEditPage;