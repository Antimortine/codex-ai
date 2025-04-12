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
    getChapterPlan: vi.fn(),
    updateChapterPlan: vi.fn(),
  };
});

// Mock the AIEditorWrapper component
vi.mock('../components/AIEditorWrapper', () => ({
  default: ({ value, onChange }) => (
    <textarea
      data-testid="mock-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      aria-label="Chapter Plan Content"
    />
  ),
}));

// Import the component *after* mocks
import ChapterPlanEditPage from './ChapterPlanEditPage';
// Import mocked functions
import { getChapterPlan, updateChapterPlan } from '../api/codexApi';

const TEST_PROJECT_ID = 'chap-plan-proj-1';
const TEST_CHAPTER_ID = 'chap-plan-ch-1';
const INITIAL_CONTENT = '# Chapter Plan\n\n- Detail 1';
const UPDATED_CONTENT = '# Updated Chapter Plan\n\n- Detail A';

// Helper to render with Router context and params
const renderWithRouter = (ui, { initialEntries = ['/'] } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/projects/:projectId/chapters/:chapterId/plan" element={ui} />
        <Route path="/projects/:projectId" element={<div>Project Overview Mock</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('ChapterPlanEditPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getChapterPlan.mockResolvedValue({ data: { project_id: TEST_PROJECT_ID, content: INITIAL_CONTENT } });
    updateChapterPlan.mockResolvedValue({});
  });

  it('renders loading state initially', () => {
    getChapterPlan.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderWithRouter(<ChapterPlanEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/plan`] });
    expect(screen.getByText(/loading chapter plan editor.../i)).toBeInTheDocument();
  });

  it('fetches and displays chapter plan content after loading', async () => {
    renderWithRouter(<ChapterPlanEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/plan`] });
    const editor = await screen.findByTestId('mock-editor');
    expect(editor).toBeInTheDocument();
    expect(editor).toHaveValue(INITIAL_CONTENT);
    expect(screen.queryByText(/loading chapter plan editor.../i)).not.toBeInTheDocument();
    expect(getChapterPlan).toHaveBeenCalledTimes(1);
    expect(getChapterPlan).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID);
  });

  it('displays an error message if fetching fails', async () => {
    const errorMessage = 'Network Error fetching chapter plan';
    getChapterPlan.mockRejectedValue(new Error(errorMessage));
    renderWithRouter(<ChapterPlanEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/plan`] });
    expect(await screen.findByText(/failed to load plan for chapter/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading chapter plan editor.../i)).not.toBeInTheDocument();
    expect(screen.queryByTestId('mock-editor')).not.toBeInTheDocument();
  });

  it('allows editing the content via the mocked editor', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ChapterPlanEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/plan`] });
    const editor = await screen.findByTestId('mock-editor');
    await user.clear(editor);
    await user.type(editor, UPDATED_CONTENT);
    expect(editor).toHaveValue(UPDATED_CONTENT);
  });

  it('calls updateChapterPlan API on save button click', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ChapterPlanEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/plan`] });
    const editor = await screen.findByTestId('mock-editor');
    await user.clear(editor);
    await user.type(editor, UPDATED_CONTENT);
    const saveButton = screen.getByRole('button', { name: /save chapter plan/i });
    await user.click(saveButton);
    await waitFor(() => {
      expect(updateChapterPlan).toHaveBeenCalledTimes(1);
      expect(updateChapterPlan).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID, { content: UPDATED_CONTENT });
    });
    expect(await screen.findByText(/chapter plan saved successfully!/i)).toBeInTheDocument();
  });

  it('displays an error message if saving fails', async () => {
    const user = userEvent.setup();
    const saveErrorMessage = 'Server error saving chapter plan';
    updateChapterPlan.mockRejectedValue(new Error(saveErrorMessage));
    renderWithRouter(<ChapterPlanEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/plan`] });
    const editor = await screen.findByTestId('mock-editor');
    await user.type(editor, ' change');
    const saveButton = screen.getByRole('button', { name: /save chapter plan/i });
    await user.click(saveButton);
    await waitFor(() => { expect(updateChapterPlan).toHaveBeenCalledTimes(1); });
    expect(await screen.findByText(/failed to save chapter plan/i)).toBeInTheDocument();
  });

  it('disables save button while saving', async () => {
    const user = userEvent.setup();
    updateChapterPlan.mockImplementation(() => new Promise(resolve => setTimeout(resolve, 50)));
    renderWithRouter(<ChapterPlanEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/plan`] });
    const editor = await screen.findByTestId('mock-editor');
    await user.type(editor, ' change');
    const saveButton = screen.getByRole('button', { name: /save chapter plan/i });
    await user.click(saveButton);
    expect(saveButton).toBeDisabled();
    expect(screen.getByText(/saving.../i)).toBeInTheDocument();
    await waitFor(() => { expect(saveButton).not.toBeDisabled(); });
  });

  it('renders a link back to the project overview', async () => {
     renderWithRouter(<ChapterPlanEditPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/chapters/${TEST_CHAPTER_ID}/plan`] });
     await screen.findByTestId('mock-editor');
     const backLink = screen.getByRole('link', { name: /back to project overview/i });
     expect(backLink).toBeInTheDocument();
     expect(backLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}`);
   });
});