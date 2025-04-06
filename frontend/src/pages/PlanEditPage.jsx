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
import { getPlan, updatePlan } from '../api/codexApi'; // Import API functions

function PlanEditPage() {
  const { projectId } = useParams();
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  const fetchPlanContent = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSaveMessage('');
    try {
      const response = await getPlan(projectId);
      setContent(response.data.content || '');
    } catch (err) {
      console.error("Error fetching plan:", err);
      setError(`Failed to load plan for project ${projectId}.`);
      setContent('');
    } finally {
      setIsLoading(false);
    }
  }, [projectId]);

  useEffect(() => {
    fetchPlanContent();
  }, [fetchPlanContent]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSaveMessage('');
    try {
      await updatePlan(projectId, { content: content }); // Content state is updated by wrapper's onChange
      setSaveMessage('Plan saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error("Error saving plan:", err);
      setError('Failed to save plan.');
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
    return <p>Loading plan editor...</p>;
  }

  if (error && !isSaving) {
    return <p style={{ color: 'red' }}>Error: {error}</p>;
  }

  return (
    <div>
      <nav style={{ marginBottom: '1rem' }}>
        <Link to={`/projects/${projectId}`}>{"<"} Back to Project Overview</Link>
      </nav>
      <h2>Edit Project Plan</h2>
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
        {isSaving ? 'Saving...' : 'Save Plan'}
      </button>
    </div>
  );
}

export default PlanEditPage;