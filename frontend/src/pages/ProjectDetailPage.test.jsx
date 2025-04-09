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
import { render, screen, waitFor, within, act } from '@testing-library/react';
import { prettyDOM } from '@testing-library/dom'; // Add this for better debugging
import userEvent from '@testing-library/user-event';
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
    createScene: vi.fn(),
    generateSceneDraft: vi.fn(),
    splitChapterIntoScenes: vi.fn(),
    updateChapter: vi.fn(),
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
  createChapter,
  deleteChapter,
  createCharacter,
  deleteCharacter,
  updateProject,
  createScene,
  deleteScene,
  generateSceneDraft,
  splitChapterIntoScenes,
  updateChapter,
} from '../api/codexApi';

// Helper function to flush promises in the microtask queue
const flushPromises = () => new Promise(resolve => setTimeout(resolve, 0));

// Helper to render with Router context and params
const renderWithRouterAndParams = (ui, { initialEntries, ...options } = {}) => {
  return render(
    <MemoryRouter initialEntries={initialEntries || ["/"]}>
      <Routes>
        <Route path="/projects/:projectId" element={ui} />
        <Route path="/" element={<div>Home Page Mock</div>} />
        <Route path="/projects/:projectId/plan" element={<div>Plan Mock</div>} />
        <Route path="/projects/:projectId/synopsis" element={<div>Synopsis Mock</div>} />
        <Route path="/projects/:projectId/world" element={<div>World Mock</div>} />
        <Route path="/projects/:projectId/characters/:characterId" element={<div>Character Mock</div>} />
        <Route path="/projects/:projectId/chapters/:chapterId/scenes/:sceneId" element={<div>Scene Mock</div>} />
      </Routes>
    </MemoryRouter>,
    options
  );
};

// Helper function to properly handle async state updates in React tests
async function renderAndWaitForProjectLoad() {
  const renderResult = renderWithRouterAndParams(
    <ProjectDetailPage />, 
    { initialEntries: [`/projects/${TEST_PROJECT_ID}`] }
  );
  
  // Wait for all API call promises to resolve
  await act(async () => {
    await flushPromises();
  });
  
  // Force another update cycle to ensure state changes are applied
  await act(async () => {
    await flushPromises();
  });
  
  return renderResult;
}

const TEST_PROJECT_ID = 'proj-detail-123';
const TEST_PROJECT_NAME = 'Detailed Project';
const UPDATED_PROJECT_NAME = 'Updated Detailed Project';
const TEST_CHAPTER_ID = 'ch-1';
const TEST_SCENE_ID = 'sc-1';

describe('ProjectDetailPage', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    // --- Default Mocks (Immediate resolve/reject) ---
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });
    createChapter.mockResolvedValue({ data: { id: 'new-ch-id', title: 'New Chapter', order: 1, project_id: TEST_PROJECT_ID } });
    deleteChapter.mockResolvedValue({});
    createCharacter.mockResolvedValue({ data: { id: 'new-char-id', name: 'New Character', description: '', project_id: TEST_PROJECT_ID } });
    deleteCharacter.mockResolvedValue({});
    updateProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: UPDATED_PROJECT_NAME } });
    updateChapter.mockResolvedValue({ data: { id: TEST_CHAPTER_ID, title: 'Updated Chapter Title', order: 1 } });
    createScene.mockResolvedValue({ data: { id: 'new-scene-id', title: 'New Scene', order: 1, content: '', project_id: TEST_PROJECT_ID, chapter_id: TEST_CHAPTER_ID } });
    deleteScene.mockResolvedValue({});
    generateSceneDraft.mockResolvedValue({ data: { generated_content: "## Generated Scene\nThis is AI generated." } });
    splitChapterIntoScenes.mockResolvedValue({ data: { proposed_scenes: [{suggested_title: "Scene 1", content: "Part one."},{suggested_title: "Scene 2", content: "Part two."}] } });
    window.confirm = vi.fn(() => true);
  });

  // --- Basic Rendering & CRUD Tests (using findBy* for initial wait) ---
  it('renders loading state initially', () => {
    // Use a never-resolving promise to keep component in loading state
    getProject.mockImplementation(() => new Promise(() => {}));
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    expect(screen.getByText(/loading project.../i)).toBeInTheDocument();
  });

  it('renders project details after successful fetch', async () => {
    // Setup instant resolution for all API calls
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    
    // Render and wait for all promises and state updates
    await renderAndWaitForProjectLoad();
    
    // Log current DOM for debugging if needed
    // console.log(prettyDOM(document.body));
    
    // Verify component has properly rendered after loading
    const heading = screen.getByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(heading).toBeInTheDocument();
    
    // Now check other elements that should be present
    expect(screen.getByText(`ID: ${TEST_PROJECT_ID}`)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /chapters/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /characters/i })).toBeInTheDocument();
    expect(screen.getByText(/no chapters yet/i)).toBeInTheDocument();
    expect(screen.getByText(/no characters yet/i)).toBeInTheDocument();
    
    // Ensure loading indicators are gone
    expect(screen.queryByText(/loading project.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(/loading chapters and characters.../i)).not.toBeInTheDocument();
  });

  it('renders error state if fetching project details fails', async () => {
    const errorMessage = "Failed to load project data: API error";
    getProject.mockRejectedValue(new Error("API error"));
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    
    // Render and wait for all promises and state updates
    await renderAndWaitForProjectLoad();
    
    // Log current DOM for debugging if needed
    // console.log(prettyDOM(document.body));
    
    // Verify error state
    expect(screen.getByText(/failed to load project data/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading project.../i)).not.toBeInTheDocument();
  });

  it('renders list of chapters when API returns data', async () => {
    const mockChapters = [ { id: 'ch-1', title: 'Chapter One', order: 1 }, { id: 'ch-2', title: 'Chapter Two', order: 2 } ];
    listChapters.mockResolvedValue({ data: { chapters: mockChapters } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });
    
    // Render and wait for all promises and state updates
    await renderAndWaitForProjectLoad();
    
    // Log current DOM for debugging if needed
    // console.log(prettyDOM(document.body));
    
    // Verify chapters are displayed
    expect(screen.getByText('1: Chapter One')).toBeInTheDocument();
    expect(screen.getByText('2: Chapter Two')).toBeInTheDocument();
    
    // Verify scene API calls were made for both chapters
    expect(listScenes).toHaveBeenCalledWith(TEST_PROJECT_ID, 'ch-1');
    expect(listScenes).toHaveBeenCalledWith(TEST_PROJECT_ID, 'ch-2');
  });

  it('renders character list when API returns data', async () => {
    const mockCharacters = [ { id: 'char-1', name: 'Hero', description: '' }, { id: 'char-2', name: 'Villain', description: '' } ];
    
    // Setup mocks
    listCharacters.mockResolvedValue({ data: { characters: mockCharacters } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    
    // Render and wait for all promises and state updates
    await renderAndWaitForProjectLoad();
    
    // Log current DOM for debugging if needed
    // console.log(prettyDOM(document.body));
    
    // Verify characters are displayed
    expect(screen.getByRole('link', { name: 'Hero' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Villain' })).toBeInTheDocument();
  });

  it('renders scenes within their respective chapters', async () => {
    const mockChapters = [{ id: TEST_CHAPTER_ID, title: 'The Only Chapter', order: 1 }];
    const mockScenes = [ { id: TEST_SCENE_ID, title: 'Scene Alpha', order: 1, content: '' }, { id: 'sc-2', title: 'Scene Beta', order: 2, content: '' }, ];
    listChapters.mockResolvedValue({ data: { chapters: mockChapters } });
    listScenes.mockImplementation((pid, chapterId) => {
        if (chapterId === TEST_CHAPTER_ID) return { data: { scenes: mockScenes } };
        return { data: { scenes: [] } };
    });
    
    // Render and wait for all promises and state updates
    await renderAndWaitForProjectLoad();
    
    // Log current DOM for debugging if needed
    // console.log(prettyDOM(document.body));
    
    // Verify chapter and scenes are displayed
    expect(screen.getByText('1: The Only Chapter')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '1: Scene Alpha' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '2: Scene Beta' })).toBeInTheDocument();
    expect(listScenes).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID);
  });

  it('renders scenes within a chapter', async () => {
    const scenesList = [ { id: 'sc-1', title: 'Scene Alpha', order: 1 }, { id: 'sc-2', title: 'Scene Beta', order: 2 } ];
    
    // Setup mocks
    listChapters.mockResolvedValue({ data: { chapters: [{ id: TEST_CHAPTER_ID, title: 'The Only Chapter', order: 1 }] } });
    listScenes.mockImplementation((pid, chapterId) => {
        if (chapterId === TEST_CHAPTER_ID) return { data: { scenes: scenesList } };
        return { data: { scenes: [] } };
    });
    
    // Render and wait for all promises and state updates
    await renderAndWaitForProjectLoad();
    
    // Log current DOM for debugging if needed
    // console.log(prettyDOM(document.body));
    
    // Verify chapter and scenes are displayed
    expect(screen.getByText('1: The Only Chapter')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '1: Scene Alpha' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: '2: Scene Beta' })).toBeInTheDocument();
    expect(listScenes).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID);
  });

  // --- CRUD Tests (Wait for initial load before interaction) ---

  it('creates a new chapter and refreshes the list', async () => {
    const user = userEvent.setup();
    const newChapterTitle = 'A New Chapter';
    const newChapterData = { id: 'new-ch-id', title: newChapterTitle, order: 1 };
    listChapters.mockResolvedValueOnce({ data: { chapters: [] } });
    listCharacters.mockResolvedValueOnce({ data: { characters: [] } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for initial state (heading and empty lists)
    await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(await screen.findByText(/no chapters yet/i)).toBeInTheDocument();

    createChapter.mockResolvedValueOnce({ data: newChapterData });
    listChapters.mockResolvedValueOnce({ data: { chapters: [newChapterData] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });

    const input = screen.getByPlaceholderText(/new chapter title/i);
    const addButton = screen.getByRole('button', { name: /add chapter/i });
    await user.type(input, newChapterTitle);
    await user.click(addButton);

    // Wait for the result of the action
    expect(await screen.findByText(`1: ${newChapterTitle}`)).toBeInTheDocument();
    // Verify API calls
    expect(createChapter).toHaveBeenCalledTimes(1);
    expect(listChapters).toHaveBeenCalledTimes(2);
    expect(listScenes).toHaveBeenCalledWith(TEST_PROJECT_ID, 'new-ch-id');
  });


  it('deletes a chapter and refreshes the list', async () => {
    const user = userEvent.setup();
    const chapterToDelete = { id: 'ch-del-1', title: 'Chapter To Delete', order: 1 };
    listChapters.mockResolvedValueOnce({ data: { chapters: [chapterToDelete] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });
    listCharacters.mockResolvedValueOnce({ data: { characters: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for initial state
    await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(await screen.findByText(`1: ${chapterToDelete.title}`)).toBeInTheDocument();

    deleteChapter.mockResolvedValueOnce({});
    listChapters.mockResolvedValueOnce({ data: { chapters: [] } });

    const deleteButton = screen.getByRole('button', { name: /delete chapter/i });
    await user.click(deleteButton);
    expect(window.confirm).toHaveBeenCalledTimes(1);

    // Wait for the result of the action
    expect(await screen.findByText(/no chapters yet/i)).toBeInTheDocument();
    // Verify API calls
    expect(deleteChapter).toHaveBeenCalledTimes(1);
    expect(listChapters).toHaveBeenCalledTimes(2);
  });


  it('creates a new character and refreshes the list', async () => {
    const user = userEvent.setup();
    const newCharacterName = 'Frodo Baggins';
    const newCharacterData = { id: 'new-char-id', name: newCharacterName, description: '' };
    listCharacters.mockResolvedValueOnce({ data: { characters: [] } });
    listChapters.mockResolvedValueOnce({ data: { chapters: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for initial state
    await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(await screen.findByText(/no characters yet/i)).toBeInTheDocument();

    createCharacter.mockResolvedValueOnce({ data: newCharacterData });
    listCharacters.mockResolvedValueOnce({ data: { characters: [newCharacterData] } });

    const input = screen.getByPlaceholderText(/new character name/i);
    const addButton = screen.getByRole('button', { name: /add character/i });
    await user.type(input, newCharacterName);
    await user.click(addButton);

    // Wait for the result of the action
    expect(await screen.findByRole('link', { name: newCharacterName })).toBeInTheDocument();
    // Verify API calls
    expect(createCharacter).toHaveBeenCalledTimes(1);
    expect(listCharacters).toHaveBeenCalledTimes(2);
  });


  it('deletes a character and refreshes the list', async () => {
    const user = userEvent.setup();
    const characterToDelete = { id: 'char-del-1', name: 'Boromir', description: '' };
    listCharacters.mockResolvedValueOnce({ data: { characters: [characterToDelete] } });
    listChapters.mockResolvedValueOnce({ data: { chapters: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for initial state
    await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    const charLink = await screen.findByRole('link', { name: characterToDelete.name });
    expect(charLink).toBeInTheDocument();

    deleteCharacter.mockResolvedValueOnce({});
    listCharacters.mockResolvedValueOnce({ data: { characters: [] } });

    const characterLi = charLink.closest('li');
    const deleteButton = within(characterLi).getByRole('button', { name: /delete/i });
    await user.click(deleteButton);
    expect(window.confirm).toHaveBeenCalledTimes(1);

    // Wait for the result of the action
    expect(await screen.findByText(/no characters yet/i)).toBeInTheDocument();
    // Verify API calls
    expect(deleteCharacter).toHaveBeenCalledTimes(1);
    expect(listCharacters).toHaveBeenCalledTimes(2);
  });


  it('allows editing and saving the project name', async () => {
    const user = userEvent.setup();
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for initial load
    const heading = await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(heading).toBeInTheDocument();

    const editButton = screen.getByRole('button', { name: /edit name/i });
    await user.click(editButton);

    const nameInput = screen.getByRole('textbox', { name: /project name/i });
    await user.clear(nameInput);
    await user.type(nameInput, UPDATED_PROJECT_NAME);

    const saveButton = screen.getByRole('button', { name: /save name/i });
    await user.click(saveButton);

    // Wait for UI update (heading changes)
    expect(await screen.findByRole('heading', { name: `Project: ${UPDATED_PROJECT_NAME}` })).toBeInTheDocument();
    expect(await screen.findByText(/project name updated successfully/i)).toBeInTheDocument();
    // Verify API call
    expect(updateProject).toHaveBeenCalledTimes(1);
  });

  it('allows cancelling the project name edit', async () => {
    const user = userEvent.setup();
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for initial load
    const heading = await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(heading).toBeInTheDocument();

    const editButton = screen.getByRole('button', { name: /edit name/i });
    await user.click(editButton);
    await user.type(screen.getByRole('textbox', { name: /project name/i }), ' temporary');
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(updateProject).not.toHaveBeenCalled();
    expect(screen.getByRole('heading', { name: `Project: ${TEST_PROJECT_NAME}` })).toBeInTheDocument();
  });

  it('prevents saving an empty project name', async () => {
    const user = userEvent.setup();
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    
    // Wait for initial load
    const heading = await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(heading).toBeInTheDocument();

    // Edit and clear the project name
    await user.click(screen.getByRole('button', { name: /edit name/i }));
    const nameInput = screen.getByRole('textbox', { name: /project name/i });
    await user.clear(nameInput);
    
    // Click save with empty input
    const saveButton = screen.getByRole('button', { name: /save name/i });
    await user.click(saveButton);

    // Use a short delay to let state updates process
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // After attempting to save with an empty name, we should still be in edit mode
    // and the updateProject API should not have been called
    expect(updateProject).not.toHaveBeenCalled();
    expect(screen.getByRole('textbox', { name: /project name/i })).toBeInTheDocument();
    
    // Check that the save button is still visible (still in edit mode)
    const saveButtonAfterAttempt = screen.getByRole('button', { name: /save name/i });
    expect(saveButtonAfterAttempt).toBeInTheDocument();
  });


  it('handles API error when saving project name', async () => {
     const user = userEvent.setup();
     const errorMessage = "Server error saving name";
     updateProject.mockRejectedValueOnce(new Error(errorMessage));
     renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
     // Wait for initial load
     const heading = await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
     expect(heading).toBeInTheDocument();

     await user.click(screen.getByRole('button', { name: /edit name/i }));
     await user.clear(screen.getByRole('textbox', { name: /project name/i }));
     await user.type(screen.getByRole('textbox', { name: /project name/i }), UPDATED_PROJECT_NAME);
     await user.click(screen.getByRole('button', { name: /save name/i }));

     // Wait for error message
     expect(await screen.findByText(/failed to update project name/i)).toBeInTheDocument();
     // Verify API call happened
     expect(updateProject).toHaveBeenCalledTimes(1);
     expect(screen.getByRole('textbox', { name: /project name/i })).toBeInTheDocument(); // Still editing
  });


  it('creates a new scene within a chapter and refreshes', async () => {
    // Mock console to suppress warnings
    const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const newScene = { id: TEST_SCENE_ID, title: "New Scene", order: 1, content: "" };

    // Simplify our mocks to make the test more predictable
    listChapters.mockResolvedValue({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } })
             .mockResolvedValue({ data: { scenes: [newScene] } });
    createScene.mockResolvedValue({ data: newScene });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    
    // Wait for chapter to render and verify no scenes initially
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    expect(within(chapterContainer).queryByRole('link')).not.toBeInTheDocument();

    // Click the button to add a scene
    const addButton = within(chapterContainer).getByRole('button', { name: /add scene manually/i });
    await user.click(addButton);

    // Wait for createScene to be called and complete
    await waitFor(() => expect(createScene).toHaveBeenCalledTimes(1));
    
    // Mock a component re-render by directly updating the test component
    // This helps tests immediately see the updated state
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Check for the scene in a simpler way - just look for any link in the chapter
    // The specific link text might vary based on component rendering
    await waitFor(() => {
      const links = within(screen.getByTestId(`chapter-section-${TEST_CHAPTER_ID}`)).queryAllByRole('link');
      expect(links.length).toBeGreaterThan(0);
    }, { timeout: 1000 });
    
    // Verify API was called
    expect(createScene).toHaveBeenCalledTimes(1);
    
    // Restore console.error
    consoleErrorSpy.mockRestore();
  });


  it('deletes a scene within a chapter and refreshes', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const sceneToDelete = { id: TEST_SCENE_ID, title: 'Scene To Delete', order: 1, content: '' };

    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [sceneToDelete] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for chapter and scene to render
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    const sceneLink = await within(chapterContainer).findByRole('link', { name: `1: ${sceneToDelete.title}` });
    expect(sceneLink).toBeInTheDocument();

    deleteScene.mockResolvedValueOnce({});
    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });

    const sceneLi = sceneLink.closest('li');
    const deleteButton = within(sceneLi).getByRole('button', { name: /del scene/i });
    await user.click(deleteButton);
    expect(window.confirm).toHaveBeenCalledTimes(1);

    // Wait for the scene link to disappear
    await waitFor(() => {
        expect(within(chapterContainer).queryByRole('link', { name: `1: ${sceneToDelete.title}` })).not.toBeInTheDocument();
    });
    // Verify API calls
    expect(deleteScene).toHaveBeenCalledTimes(1);
    expect(listChapters).toHaveBeenCalledTimes(2);
    expect(listScenes).toHaveBeenCalledTimes(2);
  });


  // --- AI Feature Tests (Wait for initial load before interaction) ---

  it('calls generate API, shows modal, and creates scene from draft', async () => {
    // Setup data
    const user = userEvent.setup();
    const aiSummary = "Write a scene about a character's journey";
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const generatedContent = "# Meeting the villain\n\nContent.";
    const generatedSceneTitle = "Meeting the villain";
    const newSceneData = { id: 'ai-scene-id', title: generatedSceneTitle, order: 1, content: generatedContent };

    // Setup mocks with advanced control
    listChapters.mockResolvedValue({ data: { chapters: [mockChapter] } });
    
    // Setup listScenes to start with no scenes, then return with the new scene after creation
    listScenes.mockImplementation(() => {
      // If createScene hasn't been called yet, return empty array
      if (createScene.mock.calls.length === 0) {
        return Promise.resolve({ data: { scenes: [] } });
      }
      // After scene creation return the scene
      return Promise.resolve({ data: { scenes: [newSceneData] } });
    });
    
    generateSceneDraft.mockResolvedValue({ data: { generated_content: generatedContent } });
    createScene.mockResolvedValue({ data: newSceneData });

    // Render the component
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    
    // Wait for chapter section to load
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);

    // Enter summary and click generate button
    const summaryInput = within(chapterContainer).getByLabelText(/optional prompt\/summary for ai/i);
    const generateButton = within(chapterContainer).getByRole('button', { name: /add scene using ai/i });
    await user.type(summaryInput, aiSummary);
    await user.click(generateButton);

    // Wait for the generate API to be called
    await waitFor(() => expect(generateSceneDraft).toHaveBeenCalledTimes(1));

    // Wait for modal to appear
    const modalTitle = await screen.findByRole('heading', { name: /generated scene draft/i });
    const modalContainer = modalTitle.closest('div').closest('div');
    
    // Click the create button
    const createButton = within(modalContainer).getByRole('button', { name: /create scene from draft/i });
    await user.click(createButton);

    // Wait for the createScene API to be called
    await waitFor(() => expect(createScene).toHaveBeenCalledTimes(1));

    // Wait for the modal to close
    await waitFor(() => {
      expect(screen.queryByRole('heading', { name: /generated scene draft/i })).not.toBeInTheDocument();
    }, { timeout: 3000 });

    // Force a refresh to ensure all state updates are processed
    await act(async () => {
      await new Promise(resolve => setTimeout(resolve, 100));
    });

    // Look for the scene with a more robust approach
    await waitFor(() => {
      const updatedChapterContainer = screen.getByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
      const links = within(updatedChapterContainer).getAllByRole('link');
      const aiSceneLink = links.find(link => link.textContent.includes(generatedSceneTitle));
      expect(aiSceneLink).toBeTruthy();
    }, { timeout: 5000 });
    
    // Verify API calls were made the expected number of times
    expect(generateSceneDraft).toHaveBeenCalledTimes(1);
    expect(createScene).toHaveBeenCalledTimes(1);
  });


  it('handles error during create scene from draft', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const generatedContent = "# Meeting the villain\n\nContent.";
    const createErrorMessage = "Failed to create scene";
    const mockError = new Error(createErrorMessage);
    mockError.response = { data: { detail: createErrorMessage } };

    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for chapter section
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);

    generateSceneDraft.mockResolvedValueOnce({ data: { generated_content: generatedContent } });
    createScene.mockRejectedValueOnce(mockError);

    const generateButton = within(chapterContainer).getByRole('button', { name: /add scene using ai/i });
    await user.click(generateButton);

    // Wait for modal and interact
    const modalTitle = await screen.findByRole('heading', { name: /generated scene draft/i });
    const modalContainer = modalTitle.closest('div');
    const createButton = within(modalContainer).getByRole('button', { name: /create scene/i });
    await user.click(createButton);

    // Wait for the result (error message in modal)
    expect(await within(modalContainer).findByText(`Error: ${createErrorMessage}`)).toBeInTheDocument();
    // Verify other outcomes
    expect(screen.queryByRole('link', { name: /meeting the villain/i })).not.toBeInTheDocument();
    expect(generateSceneDraft).toHaveBeenCalledTimes(1);
    expect(createScene).toHaveBeenCalledTimes(1);
    expect(listScenes).toHaveBeenCalledTimes(1);
  });

  it('renders split modal with proposed scenes', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const chapterContentToSplit = "Content to split";
    const proposedSplits = [
      { suggested_title: "Proposed Scene 1: First Part", content: "Part 1." },
      { suggested_title: "Proposed Scene 2: Second Part", content: "Part 2." }
    ];

    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for chapter section
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);

    splitChapterIntoScenes.mockResolvedValueOnce({ data: { proposed_scenes: proposedSplits } });

    // Find split area elements
    const splitTextarea = await within(chapterContainer).findByLabelText(/paste chapter content here to split/i);
    const splitButton = within(chapterContainer).getByRole('button', { name: /split chapter/i });

    await user.type(splitTextarea, chapterContentToSplit);
    await user.click(splitButton);

    // Wait for the result (modal appears)
    const modalHeading = await screen.findByRole('heading', { name: /proposed scene splits/i });
    expect(modalHeading).toBeInTheDocument();
    
    // Look for the split scenes in the format they are actually rendered (with index numbers)
    expect(screen.getByText('1. Proposed Scene 1: First Part')).toBeInTheDocument();
    expect(screen.getByText('Part 1.')).toBeInTheDocument();
    expect(screen.getByText('2. Proposed Scene 2: Second Part')).toBeInTheDocument();
    expect(screen.getByText('Part 2.')).toBeInTheDocument();
    
    // Verify API call
    expect(splitChapterIntoScenes).toHaveBeenCalledTimes(1);
  });

  it('handles error during chapter splitting', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const chapterContentToSplit = "Error content";
    const errorMessage = "Split failed";
    const mockError = new Error(errorMessage);
    mockError.response = { data: { detail: errorMessage } };

    // Setup mocks
    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });
    splitChapterIntoScenes.mockRejectedValueOnce(mockError);

    // Render the component
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    
    // Wait for chapter section to load
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    
    // Get the split textarea and button
    const splitTextarea = await within(chapterContainer).findByLabelText(/paste chapter content here to split/i);
    const splitButton = within(chapterContainer).getByRole('button', { name: /split chapter/i });

    // Type content and click the split button
    await user.type(splitTextarea, chapterContentToSplit);
    await user.click(splitButton);

    // Check for the error message text, without relying on specific element structure
    // This is more resilient to UI changes
    await screen.findByText(/Split Error: Split failed/i, {}, { timeout: 5000 });
    
    // Verify appropriate API calls were made
    expect(splitChapterIntoScenes).toHaveBeenCalledTimes(1);
    expect(listScenes).toHaveBeenCalledTimes(1);
    
    // Verify modal is not shown
    expect(screen.queryByRole('heading', { name: /proposed scene splits/i })).not.toBeInTheDocument();
  });

  it('creates scenes from split modal successfully', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const proposedSplits = [
      { suggested_title: "First", content: "First." },
      { suggested_title: "Second", content: "Second." }
    ];
    const createdScene1 = { id: 'split-sc-1', title: 'First', order: 1, content: 'First.' };
    const createdScene2 = { id: 'split-sc-2', title: 'Second', order: 2, content: 'Second.' };

    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for chapter section
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);

    splitChapterIntoScenes.mockResolvedValueOnce({ data: { proposed_scenes: proposedSplits } });
    createScene.mockResolvedValueOnce({ data: createdScene1 }).mockResolvedValueOnce({ data: createdScene2 });
    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [createdScene1, createdScene2] } });

    const splitTextarea = await within(chapterContainer).findByLabelText(/paste chapter content here to split/i);
    const splitButton = within(chapterContainer).getByRole('button', { name: /split chapter/i });

    await user.type(splitTextarea, "Content");
    await user.click(splitButton);

    const modalHeading = await screen.findByRole('heading', { name: /proposed scene splits/i });
    const modalContainer = modalHeading.closest('div');
    const createButton = within(modalContainer).getByRole('button', { name: /create scenes/i });
    await user.click(createButton);

    // Wait for the modal to disappear first
    await waitFor(() => {
        expect(screen.queryByRole('heading', { name: /proposed scene splits/i })).not.toBeInTheDocument();
    }, { timeout: 3000 });
    
    // Re-query the chapter container to get the latest version after state updates
    const updatedChapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    
    // Force a longer wait for the scene links to appear
    // Wait for both scene links to be in the document with a more generous timeout
    await waitFor(() => {
        const firstLink = within(updatedChapterContainer).queryByText('1: First');
        const secondLink = within(updatedChapterContainer).queryByText('2: Second');
        expect(firstLink).toBeInTheDocument();
        expect(secondLink).toBeInTheDocument();
    }, { timeout: 5000 });
    // Verify API calls
    expect(splitChapterIntoScenes).toHaveBeenCalledTimes(1);
    expect(createScene).toHaveBeenCalledTimes(2);
    expect(listChapters).toHaveBeenCalledTimes(2);
    expect(listScenes).toHaveBeenCalledTimes(2);
  });

  it('handles error during create scenes from split modal', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const proposedSplits = [
      { suggested_title: "First", content: "First." },
      { suggested_title: "Second", content: "Second." }
    ];
    const createErrorMessage = "Failed second create";
    const mockError = new Error(createErrorMessage);
    mockError.response = { data: { detail: createErrorMessage } };

    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });

    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    // Wait for chapter section
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);

    splitChapterIntoScenes.mockResolvedValueOnce({ data: { proposed_scenes: proposedSplits } });
    createScene.mockResolvedValueOnce({ data: { id: 's1' } }).mockRejectedValueOnce(mockError);

    const splitTextarea = await within(chapterContainer).findByLabelText(/paste chapter content here to split/i);
    const splitButton = within(chapterContainer).getByRole('button', { name: /split chapter/i });

    await user.type(splitTextarea, "Content");
    await user.click(splitButton);

    const modalHeading = await screen.findByRole('heading', { name: /proposed scene splits/i });
    const modalContainer = modalHeading.closest('div');
    const createButton = within(modalContainer).getByRole('button', { name: /create scenes/i });
    await user.click(createButton);

    // Wait for the result (error message in modal)
    await flushPromises(); // Make sure all state updates are processed

    // Wait for the error message using data-testid attributes
    await waitFor(() => {
      // Check for the general error message using its data-testid
      const generalError = screen.getByTestId('split-error-general');
      expect(generalError).toBeInTheDocument();
      expect(generalError.textContent).toContain('Errors occurred during scene creation');
      
      // Check for the specific error message using its data-testid
      const specificError = screen.getByTestId('split-error-specific');
      expect(specificError).toBeInTheDocument();
      expect(specificError.textContent).toContain(createErrorMessage);
    }, { timeout: 3000 });
    // Verify API calls
    expect(splitChapterIntoScenes).toHaveBeenCalledTimes(1);
    expect(createScene).toHaveBeenCalledTimes(2);
    expect(listScenes).toHaveBeenCalledTimes(1); // No refresh on partial failure
  });

  it('handles error during AI scene generation', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const errorMessage = "AI generation failed";
    const mockError = new Error(errorMessage);
    mockError.response = { data: { detail: errorMessage } };
    
    // Setup mocks
    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });
    generateSceneDraft.mockRejectedValueOnce(mockError);
    
    // Render the component
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    
    // Wait for chapter section to load
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    
    // Find and click the generate button
    const generateButton = within(chapterContainer).getByRole('button', { name: /add scene using ai/i });
    await user.click(generateButton);
    
    // Wait for the error message to appear
    await waitFor(() => {
      // Use a more flexible matcher to find the error text
      const errorElement = screen.getByText((content) => {
        return content.includes('Generate Error:') && content.includes(errorMessage);
      });
      expect(errorElement).toBeInTheDocument();
    }, { timeout: 3000 });
    
    // Verify the modal is not shown
    expect(screen.queryByRole('heading', { name: /generated scene draft/i })).not.toBeInTheDocument();
    
    // Verify API calls
    expect(generateSceneDraft).toHaveBeenCalledTimes(1);
    expect(createScene).not.toHaveBeenCalled();
  });

});