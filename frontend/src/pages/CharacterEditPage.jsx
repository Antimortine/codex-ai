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
import { getCharacter, updateCharacter } from '../api/codexApi';

function CharacterEditPage() {
  const { projectId, characterId } = useParams(); // Get both IDs
  const navigate = useNavigate(); // To navigate back after save/error

  // State for character data
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [originalName, setOriginalName] = useState(''); // Keep original name for title

  // State for loading/saving/errors
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
      setOriginalName(response.data.name || ''); // Set original name
      setDescription(response.data.description || '');
    } catch (err) {
      console.error("Error fetching character:", err);
      setError(`Failed to load character ${characterId}.`);
      // Optionally navigate back or show persistent error
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
      // Send only updated fields (name, description)
      await updateCharacter(projectId, characterId, { name: name, description: description });
      setSaveMessage('Character saved successfully!');
      setOriginalName(name); // Update original name display on successful save
      // Optionally navigate back to project page or clear message
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error("Error saving character:", err);
      setError('Failed to save character.');
      setSaveMessage('');
    } finally {
      setIsSaving(false);
    }
  };

  if (isLoading) {
    return <p>Loading character editor...</p>;
  }

  // Show persistent error if loading failed
  if (error && !isSaving) {
    return (
      <div>
        <p style={{ color: 'red' }}>Error: {error}</p>
        <Link to={`/projects/${projectId}`}>&lt; Back to Project Overview</Link>
      </div>
    );
  }

  return (
    <div>
      <nav style={{ marginBottom: '1rem' }}>
        <Link to={`/projects/${projectId}`}>&lt; Back to Project Overview</Link>
      </nav>
      {/* Use originalName in title in case user clears the input */}
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

      {/* Description Editor */}
      <div style={{ marginBottom: '1rem' }}>
        <label>Description (Markdown):</label>
        <div data-color-mode="light" style={{ marginTop: '0.5rem' }}>
          <MDEditor
            value={description}
            onChange={(value) => setDescription(value || '')}
            height={300} // Adjust height
          />
        </div>
      </div>

      {/* Display save error */}
      {error && isSaving && <p style={{ color: 'red', marginTop: '0.5rem' }}>Error: {error}</p>}
      {/* Display save success message */}
      {saveMessage && <p style={{ color: 'green', marginTop: '0.5rem' }}>{saveMessage}</p>}

      <button
        onClick={handleSave}
        disabled={isSaving || !name.trim()} // Also disable if name is empty
        style={{ marginTop: '1rem' }}
      >
        {isSaving ? 'Saving...' : 'Save Character'}
      </button>
    </div>
  );
}

export default CharacterEditPage;