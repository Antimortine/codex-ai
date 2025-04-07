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
    getCharacter: vi.fn(),
    updateCharacter: vi.fn(),
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
      aria-label="Character Description" // Add accessible name
    />
  ),
}));


// Import the component *after* mocks
import CharacterEditPage from './CharacterEditPage';
// Import mocked functions
import { getCharacter, updateCharacter } from '../api/codexApi';

const TEST_PROJECT_ID = 'char-proj-abc';
const TEST_CHARACTER_ID = 'char-id-123';
const INITIAL_CHAR_NAME = 'Gandalf';
const INITIAL_CHAR_DESC = 'A powerful wizard.';
const UPDATED_CHAR_NAME = 'Gandalf the White';
const UPDATED_CHAR_DESC = 'A powerful wizard, returned.';

// Helper to render with Router context and params
const renderWithRouter = (ui, { initialEntries = ['/'] } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        {/* Define the route that CharacterEditPage expects */}
        <Route path="/projects/:projectId/characters/:characterId" element={ui} />
        {/* Add other routes if needed for navigation links */}
        <Route path="/projects/:projectId" element={<div>Project Overview Mock</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('CharacterEditPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Default mocks for successful operations
    getCharacter.mockResolvedValue({ data: {
        id: TEST_CHARACTER_ID,
        project_id: TEST_PROJECT_ID,
        name: INITIAL_CHAR_NAME,
        description: INITIAL_CHAR_DESC
    }});
    updateCharacter.mockResolvedValue({}); // Simulate successful save
  });

  it('renders loading state initially', () => {
    getCharacter.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });
    expect(screen.getByText(/loading character editor.../i)).toBeInTheDocument();
  });

  it('fetches and displays character name and description after loading', async () => {
    renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });

    // Wait for loading to finish
    const nameInput = await screen.findByLabelText(/name/i);
    const editor = await screen.findByTestId('mock-editor');

    expect(nameInput).toBeInTheDocument();
    expect(editor).toBeInTheDocument();
    expect(nameInput).toHaveValue(INITIAL_CHAR_NAME);
    expect(editor).toHaveValue(INITIAL_CHAR_DESC);
    expect(screen.queryByText(/loading character editor.../i)).not.toBeInTheDocument();
    expect(getCharacter).toHaveBeenCalledTimes(1);
    expect(getCharacter).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHARACTER_ID);
  });

  it('displays an error message if fetching fails', async () => {
    const errorMessage = 'Network Error fetching character';
    getCharacter.mockRejectedValue(new Error(errorMessage));
    renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });

    expect(await screen.findByText(/failed to load character/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading character editor.../i)).not.toBeInTheDocument();
    expect(screen.queryByLabelText(/name/i)).not.toBeInTheDocument();
    expect(screen.queryByTestId('mock-editor')).not.toBeInTheDocument();
  });

  it('allows editing the name and description via inputs', async () => {
    const user = userEvent.setup();
    renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });

    const nameInput = await screen.findByLabelText(/name/i);
    const editor = await screen.findByTestId('mock-editor');
    expect(nameInput).toHaveValue(INITIAL_CHAR_NAME);
    expect(editor).toHaveValue(INITIAL_CHAR_DESC);

    // Edit name
    await user.clear(nameInput);
    await user.type(nameInput, UPDATED_CHAR_NAME);
    expect(nameInput).toHaveValue(UPDATED_CHAR_NAME);

    // Edit description
    await user.clear(editor);
    await user.type(editor, UPDATED_CHAR_DESC);
    expect(editor).toHaveValue(UPDATED_CHAR_DESC);
  });

  it('calls updateCharacter API on save button click with updated data', async () => {
    const user = userEvent.setup();
    renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });

    const nameInput = await screen.findByLabelText(/name/i);
    const editor = await screen.findByTestId('mock-editor');

    // Edit both fields
    await user.clear(nameInput);
    await user.type(nameInput, UPDATED_CHAR_NAME);
    await user.clear(editor);
    await user.type(editor, UPDATED_CHAR_DESC);

    const saveButton = screen.getByRole('button', { name: /save character/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(updateCharacter).toHaveBeenCalledTimes(1);
      // Verify both updated name and description are sent
      expect(updateCharacter).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHARACTER_ID, {
        name: UPDATED_CHAR_NAME,
        description: UPDATED_CHAR_DESC
      });
    });

    // Check for success message
    expect(await screen.findByText(/character saved successfully!/i)).toBeInTheDocument();
    expect(screen.queryByText(/saving.../i)).not.toBeInTheDocument();
    // Check if displayed title updates (originalName state)
    expect(screen.getByRole('heading', { name: `Edit Character: ${UPDATED_CHAR_NAME}`})).toBeInTheDocument();
  });

   it('prevents saving if name is empty', async () => {
    const user = userEvent.setup();
    renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });

    const nameInput = await screen.findByLabelText(/name/i);
    await user.clear(nameInput); // Make name empty

    const saveButton = screen.getByRole('button', { name: /save character/i });
    await user.click(saveButton);

    expect(updateCharacter).not.toHaveBeenCalled();
    expect(await screen.findByText(/character name cannot be empty/i)).toBeInTheDocument();
    expect(saveButton).not.toBeDisabled(); // Should not be in saving state
  });

  it('displays an error message if saving fails', async () => {
    const user = userEvent.setup();
    const saveErrorMessage = 'Server error saving character';
    updateCharacter.mockRejectedValue(new Error(saveErrorMessage));
    renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });

    const nameInput = await screen.findByLabelText(/name/i);
    await user.type(nameInput, ' change'); // Make a change

    const saveButton = screen.getByRole('button', { name: /save character/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(updateCharacter).toHaveBeenCalledTimes(1);
    });

    // Check for error message
    expect(await screen.findByText(/failed to save character/i)).toBeInTheDocument();
    expect(screen.queryByText(/character saved successfully!/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/saving.../i)).not.toBeInTheDocument();
  });

  it('disables save button while saving', async () => {
    const user = userEvent.setup();
    // Make updateCharacter take time
    updateCharacter.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
    renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });

    const nameInput = await screen.findByLabelText(/name/i);
    await user.type(nameInput, ' change');

    const saveButton = screen.getByRole('button', { name: /save character/i });
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
     renderWithRouter(<CharacterEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/characters/${TEST_CHARACTER_ID}`] });
     // Wait for loading to finish
     await screen.findByLabelText(/name/i);
     const backLink = screen.getByRole('link', { name: /back to project overview/i });
     expect(backLink).toBeInTheDocument();
     expect(backLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}`);
   });

});