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
// import MDEditor from '@uiw/react-md-editor'; // No longer directly used
import AIEditorWrapper from '../components/AIEditorWrapper'; // Import the wrapper
import { getCharacter, updateCharacter } from '../api/codexApi';

function CharacterEditPage() {
  const { projectId, characterId } = useParams();
  const navigate = useNavigate();

  const [name, setName] = useState('');
  const [description, setDescription] = useState(''); // Managed by wrapper's onChange
  const [originalName, setOriginalName] = useState('');

  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  const fetchCharacterData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSaveMessage('');
    try {
      const response = await getCharacter(projectId, characterId);
      setName(response.data.name || '');
      setOriginalName(response.data.name || '');
      setDescription(response.data.description || '');
    } catch (err) {
      console.error("Error fetching character:", err);
      setError(`Failed to load character ${characterId}.`);
    } finally {
      setIsLoading(false);
    }
  }, [projectId, characterId]);

  useEffect(() => {
    fetchCharacterData();
  }, [fetchCharacterData]);

  const handleSave = async () => {
    if (!name.trim()) {
        setError('Character name cannot be empty.');
        return;
    }
    setIsSaving(true);
    setError(null);
    setSaveMessage('');
    try {
      // Description comes from state updated by wrapper's onChange
      await updateCharacter(projectId, characterId, { name: name, description: description });
      setSaveMessage('Character saved successfully!');
      setOriginalName(name);
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error("Error saving character:", err);
      setError('Failed to save character.');
      setSaveMessage('');
    } finally {
      setIsSaving(false);
    }
  };

  // Callback for the editor wrapper
  const handleDescriptionChange = useCallback((newValue) => {
      setDescription(newValue);
  }, []);


  if (isLoading) {
    return <p>Loading character editor...</p>;
  }

  if (error && !isSaving) {
    return (
      <div>
        <p style={{ color: 'red' }}>Error: {error}</p>
        <Link to={`/projects/${projectId}`}> &lt; Back to Project Overview</Link>
      </div>
    );
  }

  return (
    <div>
      <nav style={{ marginBottom: '1rem' }}>
        <Link to={`/projects/${projectId}`}> &lt; Back to Project Overview</Link>
      </nav>
      <h2>Edit Character: {originalName || '...'}</h2>
      <p>Project ID: {projectId}</p>
      <p>Character ID: {characterId}</p>

      {/* Name Input */}
      <div style={{ marginBottom: '1rem' }}>
        <label htmlFor="characterName" style={{ marginRight: '0.5rem' }}>Name:</label>
        <input
          type="text"
          id="characterName"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={isSaving}
          style={{ width: '300px' }}
        />
      </div>

      {/* Description Editor - Use the Wrapper */}
      <div style={{ marginBottom: '1rem' }}>
        <label>Description (Markdown):</label>
        <div data-color-mode="light" style={{ marginTop: '0.5rem' }}>
           {/* Use AIEditorWrapper */}
           <AIEditorWrapper
                value={description}
                onChange={handleDescriptionChange}
                height={300}
                projectId={projectId}
            />
        </div>
      </div>

      {error && isSaving && <p style={{ color: 'red', marginTop: '0.5rem' }}>Error: {error}</p>}
      {saveMessage && <p style={{ color: 'green', marginTop: '0.5rem' }}>{saveMessage}</p>}

      <button
        onClick={handleSave}
        disabled={isSaving || !name.trim()}
        style={{ marginTop: '1rem' }}
      >
        {isSaving ? 'Saving...' : 'Save Character'}
      </button>
    </div>
  );
}

export default CharacterEditPage;