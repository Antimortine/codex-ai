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
import { getScene, updateScene } from '../api/codexApi';

const TEST_PROJECT_ID = 'scene-proj-xyz';
const TEST_CHAPTER_ID = 'chap-id-abc';
const TEST_SCENE_ID = 'scene-id-789';
const INITIAL_SCENE_TITLE = 'The Confrontation';
const INITIAL_SCENE_CONTENT = 'They finally met.';
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
      </Routes>
    </MemoryRouter>
  );
};

describe('SceneEditPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Default mocks for successful operations
    getScene.mockResolvedValue({ data: {
        id: TEST_SCENE_ID,
        project_id: TEST_PROJECT_ID,
        chapter_id: TEST_CHAPTER_ID,
        title: INITIAL_SCENE_TITLE,
        order: 1, // Include order even if not editable here
        content: INITIAL_SCENE_CONTENT
    }});
    updateScene.mockResolvedValue({}); // Simulate successful save
  });

  it('renders loading state initially', () => {
    getScene.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
    expect(screen.getByText(/loading scene editor.../i)).toBeInTheDocument();
  });

  it('fetches and displays scene title and content after loading', async () => {
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    // Wait for loading to finish
    const titleInput = await screen.findByLabelText(/title/i);
    const editor = await screen.findByTestId('mock-editor');

    expect(titleInput).toBeInTheDocument();
    expect(editor).toBeInTheDocument();
    expect(titleInput).toHaveValue(INITIAL_SCENE_TITLE);
    expect(editor).toHaveValue(INITIAL_SCENE_CONTENT);
    expect(screen.queryByText(/loading scene editor.../i)).not.toBeInTheDocument();
    expect(getScene).toHaveBeenCalledTimes(1);
    expect(getScene).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID, TEST_SCENE_ID);
    // Check if order is displayed
    expect(screen.getByText(`Order: 1`)).toBeInTheDocument();
  });

  it('displays an error message if fetching fails', async () => {
    const errorMessage = 'Network Error fetching scene';
    getScene.mockRejectedValue(new Error(errorMessage));
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    expect(await screen.findByText(/failed to load scene/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading scene editor.../i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/title/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId('mock-editor')).not.toBeInTheDocument();
  });

  it('allows editing the title and content via inputs', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    const titleInput = await screen.findByLabelText(/title/i);
    const editor = await screen.findByTestId('mock-editor');
    expect(titleInput).toHaveValue(INITIAL_SCENE_TITLE);
    expect(editor).toHaveValue(INITIAL_SCENE_CONTENT);

    // Edit title
    await user.clear(titleInput);
    await user.type(titleInput, UPDATED_SCENE_TITLE);
    expect(titleInput).toHaveValue(UPDATED_SCENE_TITLE);

    // Edit content
    await user.clear(editor);
    await user.type(editor, UPDATED_SCENE_CONTENT);
    expect(editor).toHaveValue(UPDATED_SCENE_CONTENT);
  });

  it('calls updateScene API on save button click with updated data', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    const titleInput = await screen.findByLabelText(/title/i);
    const editor = await screen.findByTestId('mock-editor');

    // Edit both fields
    await user.clear(titleInput);
    await user.type(titleInput, UPDATED_SCENE_TITLE);
    await user.clear(editor);
    await user.type(editor, UPDATED_SCENE_CONTENT);

    const saveButton = screen.getByRole('button', { name: /save scene/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(updateScene).toHaveBeenCalledTimes(1);
      // Verify updated title and content are sent (order is not sent)
      expect(updateScene).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID, TEST_SCENE_ID, {
        title: UPDATED_SCENE_TITLE,
        content: UPDATED_SCENE_CONTENT
      });
    });

    // Check for success message
    expect(await screen.findByText(/scene saved successfully!/i)).toBeInTheDocument();
    expect(screen.queryByText(/saving.../i)).not.toBeInTheDocument();
    // Check if displayed title updates (originalTitle state)
    expect(screen.getByRole('heading', { name: `Edit Scene: ${UPDATED_SCENE_TITLE}`})).toBeInTheDocument();
  });

   it('prevents saving if title is empty', async () => {
    const user = userEvent.setup();
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    const titleInput = await screen.findByLabelText(/title/i);
    await user.clear(titleInput); // Make title empty

    const saveButton = screen.getByRole('button', { name: /save scene/i });
    await user.click(saveButton);

    expect(updateScene).not.toHaveBeenCalled();
    expect(await screen.findByText(/scene title cannot be empty/i)).toBeInTheDocument();
    expect(saveButton).not.toBeDisabled(); // Should not be in saving state
  });

  it('displays an error message if saving fails', async () => {
    const user = userEvent.setup();
    const saveErrorMessage = 'Server error saving scene';
    updateScene.mockRejectedValue(new Error(saveErrorMessage));
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    const titleInput = await screen.findByLabelText(/title/i);
    await user.type(titleInput, ' change'); // Make a change

    const saveButton = screen.getByRole('button', { name: /save scene/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(updateScene).toHaveBeenCalledTimes(1);
    });

    // Check for error message
    expect(await screen.findByText(/failed to save scene/i)).toBeInTheDocument();
    expect(screen.queryByText(/scene saved successfully!/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/saving.../i)).not.toBeInTheDocument();
  });

  it('disables save button while saving', async () => {
    const user = userEvent.setup();
    // Make updateScene take time
    updateScene.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
    renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });

    const titleInput = await screen.findByLabelText(/title/i);
    await user.type(titleInput, ' change');

    const saveButton = screen.getByRole('button', { name: /save scene/i });
    await user.click(saveButton);

    // Check button is disabled and text changes
    expect(saveButton).toBeDisabled();
    expect(screen.getByText(/saving.../i)).toBeInTheDocument();

    // Wait for save to complete
    await waitFor(() => {
      expect(saveButton).not.toBeDisabled();
    });
    expect(screen.queryByText(/saving.../i)).not.toBeInTheDocument();
  });

  it('renders a link back to the project overview', async () => {
     renderWithRouter(<SceneEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/scenes/${TEST_SCENE_ID}`] });
     // Wait for loading to finish
     await screen.findByLabelText(/title/i);
     const backLink = screen.getByRole('link', { name: /back to project overview/i });
     expect(backLink).toBeInTheDocument();
     expect(backLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}`);
   });

});