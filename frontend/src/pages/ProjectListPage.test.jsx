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
import { BrowserRouter } from 'react-router-dom'; // Needed because component uses <Link>
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the API module
vi.mock('../api/codexApi', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    listProjects: vi.fn(),
    createProject: vi.fn(),
    deleteProject: vi.fn(),
  };
});

// Import the component *after* mocking
import ProjectListPage from './ProjectListPage';
// Import the mocked functions to configure them
import { listProjects, createProject, deleteProject } from '../api/codexApi';

// Helper to render with Router context
const renderWithRouter = (ui, { route = '/' } = {}) => {
  window.history.pushState({}, 'Test page', route);
  return render(ui, { wrapper: BrowserRouter });
};

describe('ProjectListPage', () => {
  // Reset mocks before each test
  beforeEach(() => {
    vi.resetAllMocks();
    // Provide default mock implementations
    listProjects.mockResolvedValue({ data: { projects: [] } });
    createProject.mockResolvedValue({ data: { id: 'new-proj-id', name: 'New Project' } });
    deleteProject.mockResolvedValue({}); // Simulate successful delete

    // Mock window.confirm used by the delete handler
    window.confirm = vi.fn(() => true); // Assume user confirms deletion by default
  });

  it('renders loading state initially', () => {
    renderWithRouter(<ProjectListPage />);
    expect(screen.getByText(/loading projects.../i)).toBeInTheDocument();
  });

  it('renders project list when data is fetched successfully', async () => {
    const mockProjects = [
      { id: 'proj-1', name: 'Project Alpha' },
      { id: 'proj-2', name: 'Project Beta' },
    ];
    listProjects.mockResolvedValue({ data: { projects: mockProjects } });

    renderWithRouter(<ProjectListPage />);

    expect(await screen.findByText('Project Alpha')).toBeInTheDocument();
    expect(screen.getByText('Project Beta')).toBeInTheDocument();
    expect(screen.queryByText(/loading projects.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(/failed to load projects/i)).not.toBeInTheDocument();
  });

  it('renders empty state when no projects are fetched', async () => {
    listProjects.mockResolvedValue({ data: { projects: [] } });
    renderWithRouter(<ProjectListPage />);
    expect(await screen.findByText(/no projects found/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading projects.../i)).not.toBeInTheDocument();
  });

  it('renders error state when fetching projects fails', async () => {
    const errorMessage = 'Network Error';
    listProjects.mockRejectedValue(new Error(errorMessage));
    renderWithRouter(<ProjectListPage />);
    expect(await screen.findByText(/failed to load projects/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading projects.../i)).not.toBeInTheDocument();
  });

  it('calls createProject API when form is submitted with valid name', async () => {
    const user = userEvent.setup();
    const newProjectName = 'My Test Project';
    listProjects
        .mockResolvedValueOnce({ data: { projects: [] } }) // Initial load
        .mockResolvedValueOnce({ data: { projects: [{ id: 'new-proj-id', name: newProjectName }] } }); // After create

    renderWithRouter(<ProjectListPage />);
    await screen.findByText(/no projects found/i);

    const input = screen.getByPlaceholderText(/new project name/i);
    const button = screen.getByRole('button', { name: /create project/i });

    await user.type(input, newProjectName);
    await user.click(button);

    await waitFor(() => {
      expect(createProject).toHaveBeenCalledTimes(1);
      expect(createProject).toHaveBeenCalledWith({ name: newProjectName });
    });
    expect(await screen.findByText(newProjectName)).toBeInTheDocument();
  });

   it('does not call createProject API when form is submitted with empty name', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ProjectListPage />);
    await screen.findByText(/no projects found/i);

    const button = screen.getByRole('button', { name: /create project/i });
    await user.click(button);

    expect(createProject).not.toHaveBeenCalled();
    expect(await screen.findByText(/project name cannot be empty/i)).toBeInTheDocument();
  });

  // --- NEW TEST FOR DELETE ---
  it('calls deleteProject API when delete button is clicked and confirmed', async () => {
    const user = userEvent.setup();
    const mockProjects = [{ id: 'proj-to-delete', name: 'Delete Me' }];
    // Simulate initial load with one project, then empty list after delete
    listProjects
        .mockResolvedValueOnce({ data: { projects: mockProjects } })
        .mockResolvedValueOnce({ data: { projects: [] } }); // After delete

    renderWithRouter(<ProjectListPage />);

    // Wait for the project to appear
    const deleteButton = await screen.findByRole('button', { name: /delete/i });
    expect(screen.getByText('Delete Me')).toBeInTheDocument();

    // Simulate clicking delete and confirming
    await user.click(deleteButton);

    // Verify window.confirm was called
    expect(window.confirm).toHaveBeenCalledTimes(1);
    expect(window.confirm).toHaveBeenCalledWith('Are you sure you want to delete project "Delete Me"? This cannot be undone.');

    // Verify deleteProject API call
    await waitFor(() => {
        expect(deleteProject).toHaveBeenCalledTimes(1);
        expect(deleteProject).toHaveBeenCalledWith('proj-to-delete');
    });

    // Verify the list refreshed and the project is gone
    expect(await screen.findByText(/no projects found/i)).toBeInTheDocument();
    expect(screen.queryByText('Delete Me')).not.toBeInTheDocument();
  });

  it('does not call deleteProject API when delete confirmation is cancelled', async () => {
    const user = userEvent.setup();
    const mockProjects = [{ id: 'proj-keep', name: 'Keep Me' }];
    listProjects.mockResolvedValue({ data: { projects: mockProjects } });
    window.confirm = vi.fn(() => false); // Simulate user clicking Cancel

    renderWithRouter(<ProjectListPage />);

    const deleteButton = await screen.findByRole('button', { name: /delete/i });
    await user.click(deleteButton);

    expect(window.confirm).toHaveBeenCalledTimes(1);
    expect(deleteProject).not.toHaveBeenCalled(); // API should not be called
    expect(screen.getByText('Keep Me')).toBeInTheDocument(); // Project should still be there
  });
  // --- END NEW TEST ---
});