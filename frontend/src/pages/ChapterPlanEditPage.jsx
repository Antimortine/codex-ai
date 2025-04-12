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
import AIEditorWrapper from '../components/AIEditorWrapper';
import { getChapterPlan, updateChapterPlan } from '../api/codexApi'; // Use chapter-specific API

function ChapterPlanEditPage() {
  const { projectId, chapterId } = useParams(); // Get both IDs
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState(null);
  const [saveMessage, setSaveMessage] = useState('');

  const fetchContent = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    setSaveMessage('');
    try {
      const response = await getChapterPlan(projectId, chapterId); // Use chapter API
      setContent(response.data.content || '');
    } catch (err) {
      console.error("Error fetching chapter plan:", err);
      setError(`Failed to load plan for chapter ${chapterId}.`);
      setContent('');
    } finally {
      setIsLoading(false);
    }
  }, [projectId, chapterId]); // Depend on both IDs

  useEffect(() => {
    fetchContent();
  }, [fetchContent]);

  const handleSave = async () => {
    setIsSaving(true);
    setError(null);
    setSaveMessage('');
    try {
      await updateChapterPlan(projectId, chapterId, { content: content }); // Use chapter API
      setSaveMessage('Chapter plan saved successfully!');
      setTimeout(() => setSaveMessage(''), 3000);
    } catch (err) {
      console.error("Error saving chapter plan:", err);
      setError('Failed to save chapter plan.');
      setSaveMessage('');
    } finally {
      setIsSaving(false);
    }
  };

  const handleContentChange = useCallback((newValue) => {
      setContent(newValue);
  }, []);

  if (isLoading) {
    return <p>Loading chapter plan editor...</p>;
  }

  if (error && !isSaving) {
    return <p style={{ color: 'red' }}>Error: {error}</p>;
  }

  return (
    <div>
      <nav style={{ marginBottom: '1rem' }}>
        <Link to={`/projects/${projectId}`}>{"<"} Back to Project Overview</Link>
      </nav>
      {/* TODO: Fetch and display chapter title here? */}
      <h2>Edit Plan for Chapter</h2>
      <p>Project ID: {projectId}</p>
      <p>Chapter ID: {chapterId}</p>

      <div data-color-mode="light">
        <AIEditorWrapper
            value={content}
            onChange={handleContentChange}
            height={400}
            projectId={projectId} // Pass projectId for potential AI features
        />
      </div>

      {error && isSaving && <p style={{ color: 'red', marginTop: '0.5rem' }}>Error: {error}</p>}
      {saveMessage && <p style={{ color: 'green', marginTop: '0.5rem' }}>{saveMessage}</p>}

      <button
        onClick={handleSave}
        disabled={isSaving}
        style={{ marginTop: '1rem' }}
      >
        {isSaving ? 'Saving...' : 'Save Chapter Plan'}
      </button>
    </div>
  );
}

export default ChapterPlanEditPage;