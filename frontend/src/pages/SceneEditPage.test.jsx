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
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock API calls
vi.mock('../api/codexApi', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getScene: vi.fn(),
    updateScene: vi.fn(),
    listScenes: vi.fn(), // Mock listScenes
  };
});

// Mock the AIEditorWrapper component
vi.mock('../components/AIEditorWrapper', () => ({
  // Default export mock
  default: ({ value, onChange }) => (
    <textarea
      data-testid="mock-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)} // Simulate onChange behavior
      aria-label="Scene Content" // Add accessible name
    />
  ),
}));


// Import the component *after* mocks
import SceneEditPage from './SceneEditPage';
// Import mocked functions
import { getScene, updateScene, listScenes } from '../api/codexApi';

const TEST_PROJECT_ID = 'scene-proj-xyz';
const TEST_CHAPTER_ID = 'chap-id-abc';
const TEST_SCENE_ID = 'scene-id-789';
const PREV_SCENE_ID = 'scene-id-123';
const NEXT_SCENE_ID = 'scene-id-456';
const INITIAL_SCENE_TITLE = 'The Confrontation';
const INITIAL_SCENE_CONTENT = 'They finally met.';
const INITIAL_SCENE_ORDER = 2; // Assume it's the second scene for neighbor tests
const UPDATED_SCENE_TITLE = 'The Final Confrontation';
const UPDATED_SCENE_CONTENT = 'They finally met, swords drawn.';

// Helper to render with Router context and params
const renderWithRouter = (ui, { initialEntries = ['/'] } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        {/* Define the route that SceneEditPage expects */}
        <Route path="/projects/:projectId/chapters/:chapterId/scenes/:sceneId" element={ui} />
        {/* Add other routes if needed for navigation links */}
        <Route path="/projects/:projectId" element={<div>Project Overview Mock</div>} />
        {/* Add routes for prev/next scene navigation */}
        <Route path={`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${PREV_SCENE_ID}`} element={<div>Previous Scene Mock Page</div>} />
        <Route path={`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${NEXT_SCENE_ID}`} element={<div>Next Scene Mock Page</div>} />
      </Routes>
    </MemoryRouter>
  );
};

// --- REVISED: Helper function to wait for loading states to resolve ---
async function waitForLoaders(waitForList = true) {
    // Wait for the main scene loading text to disappear
    await waitFor(() => {
        expect(screen.queryByText(/loading scene editor.../i)).not.toBeInTheDocument();
    });
    if (waitForList) {
        // Wait for the scene navigation container to be present, indicating list fetch has attempted/finished
        await screen.findByTestId("scene-navigation");
    }
}
// --- END REVISED ---


describe('SceneEditPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Default mocks for successful operations
    getScene.mockResolvedValue({ data: {
        id: TEST_SCENE_ID,
        project_id: TEST_PROJECT_ID,
        chapter_id: TEST_CHAPTER_ID,
        title: INITIAL_SCENE_TITLE,
        order: INITIAL_SCENE_ORDER, // Use constant
        content: INITIAL_SCENE_CONTENT
    }});
    // Default mock for scene list (can be overridden in tests)
    listScenes.mockResolvedValue({ data: { scenes: [
        { id: PREV_SCENE_ID, order: 1, title: 'Previous Scene' },
        { id: TEST_SCENE_ID, order: INITIAL_SCENE_ORDER, title: INITIAL_SCENE_TITLE },
        { id: NEXT_SCENE_ID, order: 3, title: 'Next Scene' },
    ]}});
    updateScene.mockResolvedValue({}); // Simulate successful save
  });

  // --- Existing Tests (mostly unchanged, but use revised waitForLoaders) ---
  it('renders loading state initially', () => {
    getScene.mockImplementation(() => new Promise(() => {})); // Never resolves
    listScenes.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    expect(screen.getByText(/loading scene editor.../i)).toBeInTheDocument();
  });

  it('fetches and displays scene title and content after loading', async () => {
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders(); // Wait for both fetches

    const titleInput = screen.getByLabelText(/title/i);
    const editor = screen.getByTestId('mock-editor');

    expect(titleInput).toBeInTheDocument();
    expect(editor).toBeInTheDocument();
    expect(titleInput).toHaveValue(INITIAL_SCENE_TITLE);
    expect(editor).toHaveValue(INITIAL_SCENE_CONTENT);
    expect(getScene).toHaveBeenCalledTimes(1);
    expect(getScene).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID, TEST_SCENE_ID);
    expect(listScenes).toHaveBeenCalledTimes(1); // Verify list fetch
    expect(listScenes).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID);
    expect(screen.getByText(`Order: ${INITIAL_SCENE_ORDER}`)).toBeInTheDocument();
  });

  it('displays an error message if fetching scene fails', async () => {
    const errorMessage = 'Network Error fetching scene';
    getScene.mockRejectedValue(new Error(errorMessage));
    listScenes.mockResolvedValue({ data: { scenes: [] } }); // Assume list succeeds
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    // Wait for the main loading to finish (even though it failed)
    await waitFor(() => {
        expect(screen.queryByText(/loading scene editor.../i)).not.toBeInTheDocument();
    });
    // Now check for the error message
    expect(await screen.findByText(/failed to load scene/i)).toBeInTheDocument();
  });

  it('displays an error message if fetching scene list fails', async () => {
    const errorMessage = 'Network Error fetching list';
    listScenes.mockRejectedValue(new Error(errorMessage));
    // Assume main scene fetch succeeds
    getScene.mockResolvedValue({ data: { id: TEST_SCENE_ID, title: 'Scene Title', order: 1, content: 'Content' } });
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    await waitForLoaders(); // Wait for main load and list attempt
    expect(await screen.findByText(/failed to load scene list/i)).toBeInTheDocument();
  });

  // ... (other existing tests like edit, save, etc. remain the same, using waitForLoaders()) ...
  it('allows editing the title and content via inputs', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders();

    const titleInput = screen.getByLabelText(/title/i);
    const editor = screen.getByTestId('mock-editor');

    await user.clear(titleInput);
    await user.type(titleInput, UPDATED_SCENE_TITLE);
    expect(titleInput).toHaveValue(UPDATED_SCENE_TITLE);

    await user.clear(editor);
    await user.type(editor, UPDATED_SCENE_CONTENT);
    expect(editor).toHaveValue(UPDATED_SCENE_CONTENT);
  });

  it('calls updateScene API on save button click with updated data', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders();

    const titleInput = screen.getByLabelText(/title/i);
    const editor = screen.getByTestId('mock-editor');

    await user.clear(titleInput);
    await user.type(titleInput, UPDATED_SCENE_TITLE);
    await user.clear(editor);
    await user.type(editor, UPDATED_SCENE_CONTENT);

    const saveButton = screen.getByRole('button', { name: /save scene/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(updateScene).toHaveBeenCalledTimes(1);
      expect(updateScene).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID, TEST_SCENE_ID, {
        title: UPDATED_SCENE_TITLE,
        content: UPDATED_SCENE_CONTENT
      });
    });

    expect(await screen.findByText(/scene saved successfully!/i)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: `Edit Scene: ${UPDATED_SCENE_TITLE}`})).toBeInTheDocument();
  });

   it('prevents saving if title is empty', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders();

    const titleInput = screen.getByLabelText(/title/i);
    await user.clear(titleInput);

    const saveButton = screen.getByRole('button', { name: /save scene/i });
    await user.click(saveButton);

    expect(updateScene).not.toHaveBeenCalled();
    expect(await screen.findByText(/scene title cannot be empty/i)).toBeInTheDocument();
  });

  it('displays an error message if saving fails', async () => {
    const user = userEvent.setup();
    const saveErrorMessage = 'Server error saving scene';
    updateScene.mockRejectedValue(new Error(saveErrorMessage));
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders();

    const titleInput = screen.getByLabelText(/title/i);
    await user.type(titleInput, ' change');

    const saveButton = screen.getByRole('button', { name: /save scene/i });
    await user.click(saveButton);

    await waitFor(() => { expect(updateScene).toHaveBeenCalledTimes(1); });
    expect(await screen.findByText(/failed to save scene/i)).toBeInTheDocument();
  });

  it('disables save button while saving', async () => {
    const user = userEvent.setup();
    updateScene.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders();

    const titleInput = screen.getByLabelText(/title/i);
    await user.type(titleInput, ' change');

    const saveButton = screen.getByRole('button', { name: /save scene/i });
    await user.click(saveButton);

    expect(saveButton).toBeDisabled();
    expect(screen.getByText(/saving.../i)).toBeInTheDocument();

    await waitFor(() => { expect(saveButton).not.toBeDisabled(); });
    expect(screen.queryByText(/saving.../i)).not.toBeInTheDocument();
  });

  it('renders a link back to the project overview', async () => {
     renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
     await waitForLoaders();
     const backLink = screen.getByRole('link', { name: /back to project overview/i });
     expect(backLink).toBeInTheDocument();
     expect(backLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}`);
   });


  // --- Navigation Tests (using revised waitForLoaders) ---

  it('renders Previous and Next links for a middle scene', async () => {
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders(); // Wait for main load and list load

    const prevLink = screen.getByRole('link', { name: /previous scene/i });
    const nextLink = screen.getByRole('link', { name: /next scene/i });

    expect(prevLink).toBeInTheDocument();
    expect(prevLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${PREV_SCENE_ID}`);
    expect(prevLink).not.toHaveStyle('pointer-events: none');

    expect(nextLink).toBeInTheDocument();
    expect(nextLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${NEXT_SCENE_ID}`);
    expect(nextLink).not.toHaveStyle('pointer-events: none');
  });

  it('disables Previous link for the first scene', async () => {
    getScene.mockResolvedValue({ data: { id: TEST_SCENE_ID, order: 1, title: 'First Scene', content: '...' } });
    listScenes.mockResolvedValue({ data: { scenes: [
        { id: TEST_SCENE_ID, order: 1, title: 'First Scene' },
        { id: NEXT_SCENE_ID, order: 2, title: 'Next Scene' },
    ]}});
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders();

    const prevSpan = screen.getByText(/previous scene/i);
    const nextLink = screen.getByRole('link', { name: /next scene/i });

    expect(prevSpan).toBeInTheDocument();
    expect(prevSpan).toHaveStyle('pointer-events: none');
    expect(screen.queryByRole('link', { name: /previous scene/i })).not.toBeInTheDocument();

    expect(nextLink).toBeInTheDocument();
    expect(nextLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${NEXT_SCENE_ID}`);
    expect(nextLink).not.toHaveStyle('pointer-events: none');
  });

  it('disables Next link for the last scene', async () => {
    getScene.mockResolvedValue({ data: { id: TEST_SCENE_ID, order: 2, title: 'Last Scene', content: '...' } });
    listScenes.mockResolvedValue({ data: { scenes: [
        { id: PREV_SCENE_ID, order: 1, title: 'Previous Scene' },
        { id: TEST_SCENE_ID, order: 2, title: 'Last Scene' },
    ]}});
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders();

    const prevLink = screen.getByRole('link', { name: /previous scene/i });
    const nextSpan = screen.getByText(/next scene/i);

    expect(prevLink).toBeInTheDocument();
    expect(prevLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${PREV_SCENE_ID}`);
    expect(prevLink).not.toHaveStyle('pointer-events: none');

    expect(nextSpan).toBeInTheDocument();
    expect(nextSpan).toHaveStyle('pointer-events: none');
    expect(screen.queryByRole('link', { name: /next scene/i })).not.toBeInTheDocument();
  });

  it('disables both links for a single scene chapter', async () => {
    getScene.mockResolvedValue({ data: { id: TEST_SCENE_ID, order: 1, title: 'Only Scene', content: '...' } });
    listScenes.mockResolvedValue({ data: { scenes: [ { id: TEST_SCENE_ID, order: 1, title: 'Only Scene' } ]}});
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    await waitForLoaders();

    const prevSpan = screen.getByText(/previous scene/i);
    const nextSpan = screen.getByText(/next scene/i);

    expect(prevSpan).toBeInTheDocument();
    expect(prevSpan).toHaveStyle('pointer-events: none');
    expect(screen.queryByRole('link', { name: /previous scene/i })).not.toBeInTheDocument();

    expect(nextSpan).toBeInTheDocument();
    expect(nextSpan).toHaveStyle('pointer-events: none');
    expect(screen.queryByRole('link', { name: /next scene/i })).not.toBeInTheDocument();
  });

  // --- REVISED TEST ---
  it('disables links while scene list is loading', async () => {
    // Mock getScene resolves quickly
    getScene.mockResolvedValue({ data: { id: TEST_SCENE_ID, order: 1, title: 'Scene Title', content: '...' } });
    // Mock listScenes never resolves
    listScenes.mockImplementation(() => new Promise(() => {}));

    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    // Wait for the main scene content to load (isLoading becomes false)
    await waitForLoaders(false); // Pass false to skip waiting for scene list

    // Check that links are disabled placeholders because isLoadingSceneList is still true
    const navContainer = screen.getByTestId("scene-navigation");
    const prevSpan = screen.getByText(/previous scene/i);
    const nextSpan = screen.getByText(/next scene/i);

    expect(navContainer).toBeInTheDocument(); // Container should be there

    expect(prevSpan).toBeInTheDocument();
    expect(prevSpan).toHaveStyle('pointer-events: none');
    expect(screen.queryByRole('link', { name: /previous scene/i })).not.toBeInTheDocument();

    expect(nextSpan).toBeInTheDocument();
    expect(nextSpan).toHaveStyle('pointer-events: none');
    expect(screen.queryByRole('link', { name: /next scene/i })).not.toBeInTheDocument();

    // Verify the main loading text is gone
    expect(screen.queryByText(/loading scene editor.../i)).not.toBeInTheDocument();
  });
  // --- END REVISED TEST ---

});