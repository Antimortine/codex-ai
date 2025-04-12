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
    getChapterSynopsis: vi.fn(),
    updateChapterSynopsis: vi.fn(),
  };
});

// Mock the AIEditorWrapper component
vi.mock('../components/AIEditorWrapper', () => ({
  default: ({ value, onChange }) => (
    <textarea
      data-testid="mock-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Chapter Synopsis Content"
    />
  ),
}));

// Import the component *after* mocks
import ChapterSynopsisEditPage from './ChapterSynopsisEditPage';
// Import mocked functions
import { getChapterSynopsis, updateChapterSynopsis } from '../api/codexApi';

const TEST_PROJECT_ID = 'chap-syn-proj-1';
const TEST_CHAPTER_ID = 'chap-syn-ch-1';
const INITIAL_CONTENT = '## Chapter Synopsis\n\nThis chapter covers...';
const UPDATED_CONTENT = '## Updated Chapter Synopsis\n\nThis chapter now covers...';

// Helper to render with Router context and params
const renderWithRouter = (ui, { initialEntries = ['/'] } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/projects/:projectId/chapters/:chapterId/synopsis" element={ui} />
        <Route path="/projects/:projectId" element={<div>Project Overview Mock</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('ChapterSynopsisEditPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getChapterSynopsis.mockResolvedValue({ data: { project_id: TEST_PROJECT_ID, content: INITIAL_CONTENT } });
    updateChapterSynopsis.mockResolvedValue({});
  });

  it('renders loading state initially', () => {
    getChapterSynopsis.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderWithRouter(<ChapterSynopsisEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/synopsis`] });
    expect(screen.getByText(/loading chapter synopsis editor.../i)).toBeInTheDocument();
  });

  it('fetches and displays chapter synopsis content after loading', async () => {
    renderWithRouter(<ChapterSynopsisEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/synopsis`] });
    const editor = await screen.findByTestId('mock-editor');
    expect(editor).toBeInTheDocument();
    expect(editor).toHaveValue(INITIAL_CONTENT);
    expect(screen.queryByText(/loading chapter synopsis editor.../i)).not.toBeInTheDocument();
    expect(getChapterSynopsis).toHaveBeenCalledTimes(1);
    expect(getChapterSynopsis).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID);
  });

  it('displays an error message if fetching fails', async () => {
    const errorMessage = 'Network Error fetching chapter synopsis';
    getChapterSynopsis.mockRejectedValue(new Error(errorMessage));
    renderWithRouter(<ChapterSynopsisEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/synopsis`] });
    expect(await screen.findByText(/failed to load synopsis for chapter/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading chapter synopsis editor.../i)).not.toBeInTheDocument();
    expect(screen.queryByTestId('mock-editor')).not.toBeInTheDocument();
  });

  it('allows editing the content via the mocked editor', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ChapterSynopsisEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/synopsis`] });
    const editor = await screen.findByTestId('mock-editor');
    await user.clear(editor);
    await user.type(editor, UPDATED_CONTENT);
    expect(editor).toHaveValue(UPDATED_CONTENT);
  });

  it('calls updateChapterSynopsis API on save button click', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ChapterSynopsisEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/synopsis`] });
    const editor = await screen.findByTestId('mock-editor');
    await user.clear(editor);
    await user.type(editor, UPDATED_CONTENT);
    const saveButton = screen.getByRole('button', { name: /save chapter synopsis/i });
    await user.click(saveButton);
    await waitFor(() => {
      expect(updateChapterSynopsis).toHaveBeenCalledTimes(1);
      expect(updateChapterSynopsis).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID, { content: UPDATED_CONTENT });
    });
    expect(await screen.findByText(/chapter synopsis saved successfully!/i)).toBeInTheDocument();
  });

  it('displays an error message if saving fails', async () => {
    const user = userEvent.setup();
    const saveErrorMessage = 'Server error saving chapter synopsis';
    updateChapterSynopsis.mockRejectedValue(new Error(saveErrorMessage));
    renderWithRouter(<ChapterSynopsisEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/synopsis`] });
    const editor = await screen.findByTestId('mock-editor');
    await user.type(editor, ' change');
    const saveButton = screen.getByRole('button', { name: /save chapter synopsis/i });
    await user.click(saveButton);
    await waitFor(() => { expect(updateChapterSynopsis).toHaveBeenCalledTimes(1); });
    expect(await screen.findByText(/failed to save chapter synopsis/i)).toBeInTheDocument();
  });

  it('disables save button while saving', async () => {
    const user = userEvent.setup();
    updateChapterSynopsis.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 50)));
    renderWithRouter(<ChapterSynopsisEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/synopsis`] });
    const editor = await screen.findByTestId('mock-editor');
    await user.type(editor, ' change');
    const saveButton = screen.getByRole('button', { name: /save chapter synopsis/i });
    await user.click(saveButton);
    expect(saveButton).toBeDisabled();
    expect(screen.getByText(/saving.../i)).toBeInTheDocument();
    await waitFor(() => { expect(saveButton).not.toBeDisabled(); });
  });

  it('renders a link back to the project overview', async () => {
     renderWithRouter(<ChapterSynopsisEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/synopsis`] });
     await screen.findByTestId('mock-editor');
     const backLink = screen.getByRole('link', { name: /back to project overview/i });
     expect(backLink).toBeInTheDocument();
     expect(backLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}`);
   });
});