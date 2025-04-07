import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
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
    generateSceneDraft: vi.fn(),
  };
});

// Import the component *after* mocks
import ProjectDetailPage from './ProjectDetailPage';
// Import mocked functions
import {
  getProject,
  listChapters,
  listCharacters,
  listScenes,
} from '../api/codexApi';

// Helper to render with Router context and params
const renderWithRouterAndParams = (ui, { initialEntries = ['/'] } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/projects/:projectId" element={ui} />
        <Route path="/" element={<div>Home Page Mock</div>} />
      </Routes>
    </MemoryRouter>
  );
};

const TEST_PROJECT_ID = 'proj-detail-123';
const TEST_PROJECT_NAME = 'Detailed Project';

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });
  });

  it('renders loading state initially', () => {
    // Mock getProject to be pending initially to see loading state
    getProject.mockImplementation(() => new Promise(() => {})); // Never resolves

    renderWithRouterAndParams(<ProjectDetailPage />, {
      initialEntries: [`/projects/${TEST_PROJECT_ID}`],
    });

    // Check only for the initial project loading indicator
    expect(screen.getByText(/loading project.../i)).toBeInTheDocument();
    // Do NOT check for chapter/character loading here, as project hasn't loaded yet
    expect(screen.queryByText(/loading chapters.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(/loading characters.../i)).not.toBeInTheDocument();
  });

  it('renders project details after successful fetch', async () => {
    renderWithRouterAndParams(<ProjectDetailPage />, {
      initialEntries: [`/projects/${TEST_PROJECT_ID}`],
    });

    expect(await screen.findByText(`Project: ${TEST_PROJECT_NAME}`)).toBeInTheDocument();
    expect(screen.getByText(`ID: ${TEST_PROJECT_ID}`)).toBeInTheDocument();

    // Now that project is loaded, lists might show loading briefly before resolving empty
    // Use waitFor to ensure loading states disappear eventually
    await waitFor(() => {
        expect(screen.queryByText(/loading project.../i)).not.toBeInTheDocument();
        expect(screen.queryByText(/loading chapters.../i)).not.toBeInTheDocument();
        expect(screen.queryByText(/loading characters.../i)).not.toBeInTheDocument();
    });

    expect(screen.getByText(/no chapters yet/i)).toBeInTheDocument();
    expect(screen.getByText(/no characters yet/i)).toBeInTheDocument();
  });

  it('renders error state if fetching project details fails', async () => {
    const errorMessage = 'Failed to fetch project';
    getProject.mockRejectedValue(new Error(errorMessage));
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, {
      initialEntries: [`/projects/${TEST_PROJECT_ID}`],
    });

    expect(await screen.findByText(/failed to load project data/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading project.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(`Project: ${TEST_PROJECT_NAME}`)).not.toBeInTheDocument();
    expect(screen.queryByText(`ID: ${TEST_PROJECT_ID}`)).not.toBeInTheDocument();
  });

  // Add more tests later
});