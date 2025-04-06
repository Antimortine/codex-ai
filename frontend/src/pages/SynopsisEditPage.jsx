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
import MDEditor from '@uiw/react-md-editor'; // Import the editor
import { getSynopsis, updateSynopsis } from '../api/codexApi'; // Import API functions FOR SYNOPSIS

function SynopsisEditPage() {
  const { projectId } = useParams();
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  const fetchSynopsisContent = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSaveMessage('');
    try {
      // Use the correct API function
      const response = await getSynopsis(projectId);
      setContent(response.data.content || '');
    } catch (err) {
      console.error("Error fetching synopsis:", err);
      setError(`Failed to load synopsis for project ${projectId}.`);
      setContent('');
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchSynopsisContent();
  }, [fetchSynopsisContent]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSaveMessage('');
    try {
      // Use the correct API function
      await updateSynopsis(projectId, { content: content });
      setSaveMessage('Synopsis saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error("Error saving synopsis:", err);
      setError('Failed to save synopsis.');
      setSaveMessage('');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <p>Loading synopsis editor...</p>;
  }

  if (error && !isSaving) {
    return <p style={{ color: 'red' }}>Error: {error}</p>;
  }

  return (
    <div>
      <nav style={{ marginBottom: '1rem' }}>
        <Link to={`/projects/${projectId}`}> &lt; Back to Project Overview</Link>
      </nav>
      {/* Update Title */}
      <h2>Edit Project Synopsis</h2>
      <p>Project ID: {projectId}</p>

      <div data-color-mode="light">
        <MDEditor
          value={content}
          onChange={(value) => setContent(value || '')}
          height={400}
        />
      </div>

      {error && isSaving && <p style={{ color: 'red', marginTop: '0.5rem' }}>Error: {error}</p>}
      {saveMessage && <p style={{ color: 'green', marginTop: '0.5rem' }}>{saveMessage}</p>}

      <button
        onClick={handleSave}
        disabled={isSaving}
        style={{ marginTop: '1rem' }}
      >
        {/* Update Button Text */}
        {isSaving ? 'Saving...' : 'Save Synopsis'}
      </button>
    </div>
  );
}

export default SynopsisEditPage;