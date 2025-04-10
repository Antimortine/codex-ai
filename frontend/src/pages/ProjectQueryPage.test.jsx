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

// Mock API calls used by ProjectQueryPage
vi.mock('../api/codexApi', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getProject: vi.fn(),
    // queryProjectContext is used by QueryInterface, but we mock QueryInterface itself
  };
});

// Mock the QueryInterface component
vi.mock('../components/QueryInterface', () => ({
    default: ({ projectId }) => <div data-testid="mock-query-interface">Query for {projectId}</div>
}));

// Import the component *after* mocks
import ProjectQueryPage from './ProjectQueryPage';
// Import mocked functions
import { getProject } from '../api/codexApi';

const TEST_PROJECT_ID = 'proj-query-xyz';
const TEST_PROJECT_NAME = 'Query Test Project';

// Helper to render with Router context and params
const renderWithRouter = (ui, { initialEntries = ['/'] } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        {/* Define the route that ProjectQueryPage expects */}
        <Route path="/projects/:projectId/query" element={ui} />
        {/* Add other routes if needed for navigation links */}
        <Route path="/projects/:projectId" element={<div>Project Overview Mock</div>} />
      </Routes>
    </MemoryRouter>
  );
};

describe('ProjectQueryPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // Default mock for successful project fetch
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
  });

  it('renders loading state initially', () => {
    getProject.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderWithRouter(<ProjectQueryPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/query`] });
    expect(screen.getByRole('heading', { name: /loading project query interface.../i })).toBeInTheDocument();
    expect(screen.queryByTestId('mock-query-interface')).not.toBeInTheDocument();
  });

  it('fetches and displays project name and renders QueryInterface after loading', async () => {
    renderWithRouter(<ProjectQueryPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/query`] });

    // Wait for loading to finish
    expect(await screen.findByRole('heading', { name: `Chat with AI about Project: ${TEST_PROJECT_NAME}` })).toBeInTheDocument();
    expect(screen.getByText(`Project ID: ${TEST_PROJECT_ID}`)).toBeInTheDocument();

    // Check QueryInterface is rendered with correct prop
    const queryInterface = screen.getByTestId('mock-query-interface');
    expect(queryInterface).toBeInTheDocument();
    expect(queryInterface).toHaveTextContent(`Query for ${TEST_PROJECT_ID}`);

    expect(screen.queryByRole('heading', { name: /loading project query interface.../i })).not.toBeInTheDocument();
    expect(getProject).toHaveBeenCalledTimes(1);
    expect(getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
  });

  it('displays an error message if fetching project fails', async () => {
    const errorMessage = 'Network Error fetching project';
    getProject.mockRejectedValue(new Error(errorMessage));
    renderWithRouter(<ProjectQueryPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/query`] });

    expect(await screen.findByRole('heading', { name: /error loading project query/i })).toBeInTheDocument();
    expect(screen.getByText(`Failed to load project details: ${errorMessage}`)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /loading project query interface.../i })).not.toBeInTheDocument();
    expect(screen.queryByTestId('mock-query-interface')).not.toBeInTheDocument(); // QueryInterface should not render on error
  });

  it('renders a link back to the project overview', async () => {
     renderWithRouter(<ProjectQueryPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/query`] });
     // Wait for loading to finish
     await screen.findByTestId('mock-query-interface');
     const backLink = screen.getByRole('link', { name: /back to project overview/i });
     expect(backLink).toBeInTheDocument();
     expect(backLink).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}`);
   });

});