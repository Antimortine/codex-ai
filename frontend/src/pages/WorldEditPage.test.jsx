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
    getWorldInfo: vi.fn(),
    updateWorldInfo: vi.fn(),
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
      aria-label="World Info Content" // Add accessible name
    />
  ),
}));


// Import the component *after* mocks
import WorldEditPage from './WorldEditPage';
// Import mocked functions
import { getWorldInfo, updateWorldInfo } from '../api/codexApi';

const TEST_PROJECT_ID = 'world-proj-789';
const INITIAL_WORLD_CONTENT = '## World Details\n\nMagic system basics.';
const UPDATED_WORLD_CONTENT = '## Updated World\n\nExpanded magic system.';

// Helper to render with Router context and params
const renderWithRouter = (ui, { initialEntries = ['/'] } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        {/* Define the route that WorldEditPage expects */}
        <Route path="/projects/:projectId/world" element={ui} />
        {/* Add other routes if needed for navigation links */}
        <Route path="/projects/:projectId" element={<div>Project Overview Mock</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('WorldEditPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Default mocks for successful operations
    getWorldInfo.mockResolvedValue({ data: { project_id: TEST_PROJECT_ID, content: INITIAL_WORLD_CONTENT } });
    updateWorldInfo.mockResolvedValue({}); // Simulate successful save
  });

  it('renders loading state initially', () => {
    getWorldInfo.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderWithRouter(<WorldEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/world`] });
    expect(screen.getByText(/loading world info editor.../i)).toBeInTheDocument();
  });

  it('fetches and displays world info content after loading', async () => {
    renderWithRouter(<WorldEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/world`] });

    // Wait for loading to finish and editor to appear
    const editor = await screen.findByTestId('mock-editor');
    expect(editor).toBeInTheDocument();
    expect(editor).toHaveValue(INITIAL_WORLD_CONTENT);
    expect(screen.queryByText(/loading world info editor.../i)).not.toBeInTheDocument();
    expect(getWorldInfo).toHaveBeenCalledTimes(1);
    expect(getWorldInfo).toHaveBeenCalledWith(TEST_PROJECT_ID);
  });

  it('displays an error message if fetching fails', async () => {
    const errorMessage = 'Network Error fetching world info';
    getWorldInfo.mockRejectedValue(new Error(errorMessage));
    renderWithRouter(<WorldEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/world`] });

    expect(await screen.findByText(/failed to load world info/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading world info editor.../i)).not.toBeInTheDocument();
    expect(screen.queryByTestId('mock-editor')).not.toBeInTheDocument();
  });

  it('allows editing the content via the mocked editor', async () => {
    const user = userEvent.setup();
    renderWithRouter(<WorldEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/world`] });

    const editor = await screen.findByTestId('mock-editor');
    expect(editor).toHaveValue(INITIAL_WORLD_CONTENT);

    await user.clear(editor);
    await user.type(editor, UPDATED_WORLD_CONTENT);

    expect(editor).toHaveValue(UPDATED_WORLD_CONTENT);
  });

  it('calls updateWorldInfo API on save button click', async () => {
    const user = userEvent.setup();
    renderWithRouter(<WorldEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/world`] });

    const editor = await screen.findByTestId('mock-editor');
    await user.clear(editor);
    await user.type(editor, UPDATED_WORLD_CONTENT);

    const saveButton = screen.getByRole('button', { name: /save world info/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(updateWorldInfo).toHaveBeenCalledTimes(1);
      expect(updateWorldInfo).toHaveBeenCalledWith(TEST_PROJECT_ID, { content: UPDATED_WORLD_CONTENT });
    });

    // Check for success message
    expect(await screen.findByText(/world info saved successfully!/i)).toBeInTheDocument();
    expect(screen.queryByText(/saving.../i)).not.toBeInTheDocument();
  });

  it('displays an error message if saving fails', async () => {
    const user = userEvent.setup();
    const saveErrorMessage = 'Server error saving world info';
    updateWorldInfo.mockRejectedValue(new Error(saveErrorMessage));
    renderWithRouter(<WorldEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/world`] });

    const editor = await screen.findByTestId('mock-editor');
    await user.type(editor, ' some new text'); // Make a change

    const saveButton = screen.getByRole('button', { name: /save world info/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(updateWorldInfo).toHaveBeenCalledTimes(1);
    });

    // Check for error message
    expect(await screen.findByText(/failed to save world info/i)).toBeInTheDocument();
    expect(screen.queryByText(/world info saved successfully!/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/saving.../i)).not.toBeInTheDocument();
  });

  it('disables save button while saving', async () => {
    const user = userEvent.setup();
    // Make updateWorldInfo take time
    updateWorldInfo.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 100)));
    renderWithRouter(<WorldEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/world`] });

    const editor = await screen.findByTestId('mock-editor');
    await user.type(editor, ' change');

    const saveButton = screen.getByRole('button', { name: /save world info/i });
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
     renderWithRouter(<WorldEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/world`] });
     // Wait for loading to finish
     await screen.findByTestId('mock-editor');
     const backLink = screen.getByRole('link', { name: /back to project overview/i });
     expect(backLink).toBeInTheDocument();
     expect(backLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}`);
   });

});