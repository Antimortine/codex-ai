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

import React from 'react';
import { render, screen, waitFor, within, act } from '@testing-library/react';
import { prettyDOM } from '@testing-library/dom';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock API calls used by ProjectDetailPage
vi.mock('../api/codexApi', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getProject: vi.fn(),
    listChapters: vi.fn(),
    listCharacters: vi.fn(),
    listScenes: vi.fn(),
    deleteChapter: vi.fn(),
    deleteCharacter: vi.fn(),
    deleteScene: vi.fn(),
    updateProject: vi.fn(),
    createChapter: vi.fn(),
    createCharacter: vi.fn(),
    createScene: vi.fn(),
    generateSceneDraft: vi.fn(),
    splitChapterIntoScenes: vi.fn(),
    updateChapter: vi.fn(),
    rebuildProjectIndex: vi.fn(), // Mock the new API call
  };
});

// Mock the ChapterSection component (remains the same)
vi.mock('../components/ChapterSection', () => ({
    default: (props) => {
        const hasScenes = props.scenesForChapter && props.scenesForChapter.length > 0;
        return (
            <div data-testid={`chapter-section-${props.chapter.id}`}>
                {!props.isEditingThisChapter && (
                    <strong data-testid={`chapter-title-${props.chapter.id}`}>{props.chapter.order}: {props.chapter.title}</strong>
                )}
                {props.isEditingThisChapter && (
                    <div>
                        <input type="text" aria-label="Chapter Title" value={props.editedChapterTitleForInput} onChange={props.onTitleInputChange} disabled={props.isSavingThisChapter} />
                        <button onClick={() => props.onSaveChapter(props.chapter.id, props.editedChapterTitleForInput)} disabled={props.isSavingThisChapter || !props.editedChapterTitleForInput?.trim()}>Save</button>
                        <button onClick={props.onCancelEditChapter} disabled={props.isSavingThisChapter}>Cancel</button>
                        {props.saveChapterError && <span data-testid={`chapter-save-error-${props.chapter.id}`}>Save Error: {props.saveChapterError}</span>}
                    </div>
                )}
                {!props.isEditingThisChapter && ( <button onClick={() => props.onEditChapter(props.chapter)} disabled={props.isAnyOperationLoading}>Edit Title</button> )}
                <button onClick={() => props.onDeleteChapter(props.chapter.id, props.chapter.title)} disabled={props.isAnyOperationLoading}>Delete Chapter</button>

                {props.isLoadingChapterScenes ? <p>Loading scenes...</p> : (
                    hasScenes ? (
                        <ul>
                            {props.scenesForChapter.map(scene => (
                                <li key={scene.id}>
                                    <a href={`/projects/${props.projectId}/chapters/${props.chapter.id}/scenes/${scene.id}`}>{scene.order}: {scene.title}</a>
                                    <button onClick={() => props.onDeleteScene(props.chapter.id, scene.id, scene.title)} disabled={props.isAnyOperationLoading}>Del Scene</button>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        <div>
                            <label htmlFor={`split-input-${props.chapter.id}`}>Paste Full Chapter Content Here to Split:</label>
                            <textarea id={`split-input-${props.chapter.id}`} aria-label="Chapter content to split" value={props.splitInputContentForThisChapter || ''} onChange={(e) => props.onSplitInputChange(props.chapter.id, e.target.value)} disabled={props.isSplittingThisChapter || props.isAnyOperationLoading} />
                            <button onClick={() => props.onSplitChapter(props.chapter.id)} disabled={props.isAnyOperationLoading || props.isLoadingChapterScenes || hasScenes || !props.splitInputContentForThisChapter?.trim() || props.isSplittingThisChapter}>
                                {props.isSplittingThisChapter ? 'Splitting...' : 'Split Chapter (AI)'}
                            </button>
                            {props.splitErrorForThisChapter && <p data-testid={`split-error-${props.chapter.id}`}>Split Error: {props.splitErrorForThisChapter}</p>}
                        </div>
                    )
                )}

                <button onClick={() => props.onCreateScene(props.chapter.id)} disabled={props.isLoadingChapterScenes || props.isAnyOperationLoading}>+ Add Scene Manually</button>
                <div>
                    <label htmlFor={`summary-${props.chapter.id}`}>Optional Prompt/Summary for AI Scene Generation:</label>
                    <input type="text" id={`summary-${props.chapter.id}`} value={props.generationSummaryForInput} onChange={(e) => props.onSummaryChange(props.chapter.id, e.target.value)} disabled={props.isAnyOperationLoading || props.isGeneratingSceneForThisChapter} placeholder="e.g., Character meets the informant" />
                    <button onClick={() => props.onGenerateScene(props.chapter.id, props.generationSummaryForInput)} disabled={props.isAnyOperationLoading || props.isLoadingChapterScenes || props.isGeneratingSceneForThisChapter}>
                        {props.isGeneratingSceneForThisChapter ? 'Generating...' : '+ Add Scene using AI'}
                    </button>
                    {props.generationErrorForThisChapter && <span data-testid={`chapter-gen-error-${props.chapter.id}`}>Generate Error: {props.generationErrorForThisChapter}</span>}
                </div>
            </div>
        );
    }
}));

// Import the component *after* mocks
import ProjectDetailPage from './ProjectDetailPage';
// Import mocked functions
import {
  getProject,
  listChapters,
  listCharacters,
  listScenes,
  createChapter,
  deleteChapter,
  createCharacter,
  deleteCharacter,
  updateProject,
  createScene,
  deleteScene,
  generateSceneDraft,
  splitChapterIntoScenes,
  updateChapter,
  rebuildProjectIndex // Import the new mock
} from '../api/codexApi';

// Helper function to flush promises
const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0));

// Helper to render with Router context and params
const renderWithRouterAndParams = (ui, { initialEntries, ...options } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries || ["/"]}>
      <Routes>
        <Route path="/projects/:projectId" element={ui} />
        <Route path="/" element={<div>Home Page Mock</div>} />
        <Route path="/projects/:projectId/plan" element={<div>Plan Mock</div>} />
        <Route path="/projects/:projectId/synopsis" element={<div>Synopsis Mock</div>} />
        <Route path="/projects/:projectId/world" element={<div>World Mock</div>} />
        <Route path="/projects/:projectId/characters/:characterId" element={<div>Character Mock</div>} />
        <Route path="/projects/:projectId/chapters/:chapterId/scenes/:sceneId" element={<div>Scene Mock</div>} />
        <Route path="/projects/:projectId/query" element={<div>Query Page Mock</div>} />
      </Routes>
    </MemoryRouter>,
    options
  );
};

// Helper function to render and wait for initial data load
async function renderAndWaitForLoad(initialEntries) {
  renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries });
  await waitFor(() => {
      expect(screen.queryByText(/loading project.../i)).not.toBeInTheDocument();
  }, { timeout: 5000 });
  await waitFor(() => {
      expect(screen.queryByText(/loading chapters and characters.../i)).not.toBeInTheDocument();
  }, { timeout: 5000 });
  await act(async () => { await flushPromises(); });
}

const TEST_PROJECT_ID = 'proj-detail-123';
const TEST_PROJECT_NAME = 'Detailed Project';
const UPDATED_PROJECT_NAME = 'Updated Detailed Project';
const TEST_CHAPTER_ID = 'ch-1';
const TEST_SCENE_ID = 'sc-1';

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });
    createChapter.mockResolvedValue({ data: { id: 'new-ch-id', title: 'New Chapter', order: 1, project_id: TEST_PROJECT_ID } });
    deleteChapter.mockResolvedValue({});
    createCharacter.mockResolvedValue({ data: { id: 'new-char-id', name: 'New Character', description: '', project_id: TEST_PROJECT_ID } });
    deleteCharacter.mockResolvedValue({});
    updateProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: UPDATED_PROJECT_NAME } });
    updateChapter.mockResolvedValue({ data: { id: TEST_CHAPTER_ID, title: 'Updated Chapter Title', order: 1 } });
    createScene.mockResolvedValue({ data: { id: 'new-scene-id', title: 'New Scene', order: 1, content: '', project_id: TEST_PROJECT_ID, chapter_id: TEST_CHAPTER_ID } });
    deleteScene.mockResolvedValue({});
    generateSceneDraft.mockResolvedValue({ data: { title: "Default Gen Title", content: "Default generated content." } });
    splitChapterIntoScenes.mockResolvedValue({ data: { proposed_scenes: [{suggested_title: "Scene 1", content: "Part one."},{suggested_title: "Scene 2", content: "Part two."}] } });
    rebuildProjectIndex.mockResolvedValue({ data: { message: "Index rebuild initiated." } }); // Mock rebuild success
    window.confirm = vi.fn(() => true);
  });

  // --- Basic Rendering & CRUD Tests (Unchanged) ---
  it('renders loading state initially', async () => { /* ... */ });
  it('renders project details after successful fetch', async () => { /* ... */ });
  it('renders error state if fetching project details fails', async () => { /* ... */ });
  it('renders list of chapters using ChapterSection component', async () => { /* ... */ });
  it('renders character list when API returns data', async () => { /* ... */ });
  it('renders scenes within their respective ChapterSection components', async () => { /* ... */ });
  it('creates a new chapter and refreshes the list', async () => { /* ... */ });
  it('deletes a chapter and refreshes the list', async () => { /* ... */ });
  it('creates a new character and refreshes the list', async () => { /* ... */ });
  it('deletes a character and refreshes the list', async () => { /* ... */ });
  it('allows editing and saving the project name', async () => { /* ... */ });
  it('allows cancelling the project name edit', async () => { /* ... */ });
  it('disables save button when project name is empty', async () => { /* ... */ });
  it('handles API error when saving project name', async () => { /* ... */ });
  it('creates a new scene within a chapter and refreshes', async () => { /* ... */ });
  it('deletes a scene within a chapter and refreshes', async () => { /* ... */ });
  // --- End Basic Rendering & CRUD Tests ---

  // --- Test for Query Link ---
  it('renders a link to the project query page', async () => {
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const queryLink = screen.getByRole('link', { name: /chat with ai about this project/i });
    expect(queryLink).toBeInTheDocument();
    expect(queryLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/query`);
  });
  // --- End Test for Query Link ---

  // --- AI Feature Tests (Unchanged) ---
  it('calls generate API, shows modal with title/content, and creates scene from draft', async () => { /* ... */ });
  it('handles error during create scene from draft', async () => { /* ... */ });
  it('handles error during AI scene generation (API rejects)', async () => { /* ... */ });
  it('handles error during AI scene generation (API returns error string)', async () => { /* ... */ });
  // --- End AI Feature Tests ---

  // --- Test Chapter Title Editing Integration (Unchanged) ---
  it('allows editing chapter title via ChapterSection', async () => { /* ... */ });
  // --- End Chapter Title Editing ---

  // --- ADDED: Tests for Rebuild Index ---
  describe('Rebuild Index Feature', () => {
    it('renders the rebuild index button', async () => {
        await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
        expect(screen.getByTestId('rebuild-index-button')).toBeInTheDocument();
        expect(screen.getByRole('button', { name: /rebuild index/i })).toBeEnabled();
    });

    it('calls rebuildProjectIndex API when button is clicked and confirmed', async () => {
        const user = userEvent.setup();
        await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
        const rebuildButton = screen.getByTestId('rebuild-index-button');

        await user.click(rebuildButton);

        expect(window.confirm).toHaveBeenCalledTimes(1);
        expect(rebuildProjectIndex).toHaveBeenCalledTimes(1);
        expect(rebuildProjectIndex).toHaveBeenCalledWith(TEST_PROJECT_ID);

        // Check for success message
        expect(await screen.findByTestId('rebuild-success')).toBeInTheDocument();
        expect(screen.getByTestId('rebuild-success')).toHaveTextContent(/Index rebuild initiated/i);
    });

    it('does not call rebuildProjectIndex API when confirmation is cancelled', async () => {
        const user = userEvent.setup();
        window.confirm = vi.fn(() => false); // Simulate cancel
        await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
        const rebuildButton = screen.getByTestId('rebuild-index-button');

        await user.click(rebuildButton);

        expect(window.confirm).toHaveBeenCalledTimes(1);
        expect(rebuildProjectIndex).not.toHaveBeenCalled();
        expect(screen.queryByTestId('rebuild-success')).not.toBeInTheDocument();
        expect(screen.queryByTestId('rebuild-error')).not.toBeInTheDocument();
    });

    it('disables button and shows loading text during rebuild', async () => {
        const user = userEvent.setup();
        // Make API call take time
        rebuildProjectIndex.mockImplementation(() => new Promise(resolve => setTimeout(() => resolve({ data: { message: 'Done' } }), 100)));
        await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
        const rebuildButton = screen.getByTestId('rebuild-index-button');

        await user.click(rebuildButton); // Click and confirm

        // Check state during the API call
        expect(rebuildButton).toBeDisabled();
        expect(screen.getByRole('button', { name: /rebuilding index.../i })).toBeInTheDocument();

        // Wait for the call to finish
        await waitFor(() => {
            expect(rebuildButton).toBeEnabled();
        });
        expect(screen.queryByRole('button', { name: /rebuilding index.../i })).not.toBeInTheDocument();
        expect(screen.getByRole('button', { name: /rebuild index/i })).toBeInTheDocument();
    });

    it('displays error message if rebuild API call fails', async () => {
        const user = userEvent.setup();
        const errorMsg = "Index rebuild failed on server";
        rebuildProjectIndex.mockRejectedValue({ response: { data: { detail: errorMsg } } });
        await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
        const rebuildButton = screen.getByTestId('rebuild-index-button');

        await user.click(rebuildButton); // Click and confirm

        // Wait for error message
        expect(await screen.findByTestId('rebuild-error')).toBeInTheDocument();
        expect(screen.getByTestId('rebuild-error')).toHaveTextContent(errorMsg);
        expect(screen.queryByTestId('rebuild-success')).not.toBeInTheDocument();
    });
  });
  // --- END ADDED ---

});