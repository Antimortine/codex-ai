import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter } from 'react-router-dom'; // Needed because component uses <Link>
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock the API module
// Note: Adjust the path based on your actual file structure
vi.mock('../api/codexApi', async (importOriginal) => {
  const actual = await importOriginal(); // Get actual module to preserve other exports if needed
  return {
    ...actual, // Spread actual exports
    listProjects: vi.fn(), // Mock specific functions
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

    // Wait for loading to disappear and projects to appear
    expect(await screen.findByText('Project Alpha')).toBeInTheDocument();
    expect(screen.getByText('Project Beta')).toBeInTheDocument();
    expect(screen.queryByText(/loading projects.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(/failed to load projects/i)).not.toBeInTheDocument();
  });

  it('renders empty state when no projects are fetched', async () => {
    // Default mock already returns empty list, but being explicit
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
    // Mock listProjects to return empty initially, then updated list after create
    listProjects
        .mockResolvedValueOnce({ data: { projects: [] } }) // Initial load
        .mockResolvedValueOnce({ data: { projects: [{ id: 'new-proj-id', name: newProjectName }] } }); // After create

    renderWithRouter(<ProjectListPage />);

    // Wait for initial load
    await screen.findByText(/no projects found/i);

    // Simulate user input and submission
    const input = screen.getByPlaceholderText(/new project name/i);
    const button = screen.getByRole('button', { name: /create project/i });

    await user.type(input, newProjectName);
    await user.click(button);

    // Check if createProject was called correctly
    await waitFor(() => {
      expect(createProject).toHaveBeenCalledTimes(1);
      expect(createProject).toHaveBeenCalledWith({ name: newProjectName });
    });

    // Check if the list refreshed and shows the new project
    expect(await screen.findByText(newProjectName)).toBeInTheDocument();
  });

   it('does not call createProject API when form is submitted with empty name', async () => {
    const user = userEvent.setup();
    renderWithRouter(<ProjectListPage />);
    await screen.findByText(/no projects found/i); // Wait for load

    const button = screen.getByRole('button', { name: /create project/i });
    await user.click(button); // Click without typing

    expect(createProject).not.toHaveBeenCalled();
    // Optionally check if an error message is shown to the user
    expect(await screen.findByText(/project name cannot be empty/i)).toBeInTheDocument();
  });

  // TODO: Add test for deleteProject interaction
});