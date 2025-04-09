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
    splitChapterIntoScenes: vi.fn(), // Keep mock
    updateChapter: vi.fn(),
  };
});

// Mock the ChapterSection component - ACCURATE MOCK
vi.mock('../components/ChapterSection', () => ({
    default: (props) => {
        // Determine if scenes exist for conditional rendering
        const hasScenes = props.scenesForChapter && props.scenesForChapter.length > 0;

        return (
            <div data-testid={`chapter-section-${props.chapter.id}`}>
                {/* Title/Edit */}
                {!props.isEditingThisChapter && (
                    <strong data-testid={`chapter-title-${props.chapter.id}`}>{props.chapter.order}: {props.chapter.title}</strong>
                )}
                {props.isEditingThisChapter && (
                    <div>
                        <input type="text" aria-label="Chapter Title" value={props.editedChapterTitleForInput} onChange={props.onTitleInputChange} disabled={props.isSavingThisChapter} />
                        <button onClick={() => props.onSaveChapter(props.chapter.id, props.editedChapterTitleForInput)} disabled={props.isSavingThisChapter || !props.editedChapterTitleForInput?.trim()}>Save</button>
                        <button onClick={props.onCancelEditChapter} disabled={props.isSavingThisChapter}>Cancel</button>
                        {props.saveChapterError && <span data-testid={`chapter-save-error-${props.chapter.id}`}>Save Error: {props.saveChapterError}</span>}
                    </div>
                )}
                {!props.isEditingThisChapter && ( <button onClick={() => props.onEditChapter(props.chapter)} disabled={props.isAnyOperationLoading}>Edit Title</button> )}
                <button onClick={() => props.onDeleteChapter(props.chapter.id, props.chapter.title)} disabled={props.isAnyOperationLoading}>Delete Chapter</button>

                {/* Scene List OR Split UI - Correct Conditional Logic */}
                {props.isLoadingChapterScenes ? <p>Loading scenes...</p> : (
                    hasScenes ? ( // Use the calculated boolean
                        // Simulate Scene List if scenes exist
                        <ul>
                            {props.scenesForChapter.map(scene => (
                                <li key={scene.id}>
                                    <a href={`/projects/${props.projectId}/chapters/${props.chapter.id}/scenes/${scene.id}`}>{scene.order}: {scene.title}</a>
                                    <button onClick={() => props.onDeleteScene(props.chapter.id, scene.id, scene.title)} disabled={props.isAnyOperationLoading}>Del Scene</button>
                                </li>
                            ))}
                        </ul>
                    ) : (
                        // Simulate Split UI if no scenes
                        <div>
                            <label htmlFor={`split-input-${props.chapter.id}`}>Paste Full Chapter Content Here to Split:</label>
                            <textarea id={`split-input-${props.chapter.id}`} aria-label="Chapter content to split" value={props.splitInputContentForThisChapter || ''} onChange={(e) => props.onSplitInputChange(props.chapter.id, e.target.value)} disabled={props.isSplittingThisChapter || props.isAnyOperationLoading} />
                            <button onClick={() => props.onSplitChapter(props.chapter.id)} disabled={props.isAnyOperationLoading || props.isLoadingChapterScenes || hasScenes || !props.splitInputContentForThisChapter?.trim() || props.isSplittingThisChapter}>
                                {props.isSplittingThisChapter ? 'Splitting...' : 'Split Chapter (AI)'}
                            </button>
                            {props.splitErrorForThisChapter && <p data-testid={`split-error-${props.chapter.id}`}>Split Error: {props.splitErrorForThisChapter}</p>}
                        </div>
                    )
                )}

                {/* Add/Generate Scene Area */}
                <button onClick={() => props.onCreateScene(props.chapter.id)} disabled={props.isLoadingChapterScenes || props.isAnyOperationLoading}>+ Add Scene Manually</button>
                <div>
                    <label htmlFor={`summary-${props.chapter.id}`}>Optional Prompt/Summary for AI Scene Generation:</label>
                    <input type="text" id={`summary-${props.chapter.id}`} value={props.generationSummaryForInput} onChange={(e) => props.onSummaryChange(props.chapter.id, e.target.value)} disabled={props.isAnyOperationLoading || props.isGeneratingSceneForThisChapter} placeholder="e.g., Character meets the informant" />
                    <button onClick={() => props.onGenerateScene(props.chapter.id, props.generationSummaryForInput)} disabled={props.isAnyOperationLoading || props.isLoadingChapterScenes || props.isGeneratingSceneForThisChapter}>
                        {props.isGeneratingSceneForThisChapter ? 'Generating...' : '+ Add Scene using AI'}
                    </button>
                    {props.generationErrorForThisChapter && <span data-testid={`chapter-gen-error-${props.chapter.id}`}>Generate Error: {props.generationErrorForThisChapter}</span>}
                </div>
            </div>
        );
    }
}));


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
async function renderAndWaitForLoad(initialEntries) {
  const { rerender } = renderWithRouterAndParams( // Get rerender function
    <ProjectDetailPage />,
    { initialEntries }
  );

  // Wait for the main project loading indicator to disappear
  await waitFor(() => {
      expect(screen.queryByText(/loading project.../i)).not.toBeInTheDocument();
  }, { timeout: 5000 });

  // Wait for chapters/characters loading state to potentially resolve
  await waitFor(() => {
      expect(screen.queryByText(/loading chapters and characters.../i)).not.toBeInTheDocument();
  }, { timeout: 5000 });


  // Force another update cycle to ensure state changes are applied
  await act(async () => {
    await flushPromises();
  });

  return { rerender }; // Return rerender
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
  it('renders loading state initially', async () => {
    getProject.mockImplementation(() => new Promise(() => {}));
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    expect(screen.getByText(/loading project.../i)).toBeInTheDocument();
  });

  it('renders project details after successful fetch', async () => {
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const heading = screen.getByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(heading).toBeInTheDocument();
    expect(screen.getByText(`ID: ${TEST_PROJECT_ID}`)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /chapters/i })).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /characters/i })).toBeInTheDocument();
    expect(screen.getByText(/no chapters yet/i)).toBeInTheDocument();
    expect(screen.getByText(/no characters yet/i)).toBeInTheDocument();
    expect(screen.queryByText(/loading project.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(/loading chapters and characters.../i)).not.toBeInTheDocument();
  });

  it('renders error state if fetching project details fails', async () => {
    const errorMessage = "API error";
    getProject.mockRejectedValue(new Error(errorMessage));
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    listCharacters.mockResolvedValue({ data: { characters: [] } });
    renderWithRouterAndParams(<ProjectDetailPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}`] });
    expect(await screen.findByText(`Error: Failed to load project data: ${errorMessage}`)).toBeInTheDocument();
    expect(screen.queryByText(/loading project.../i)).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') })).not.toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /chapters/i })).not.toBeInTheDocument();
  });


  it('renders list of chapters using ChapterSection component', async () => {
    const mockChapters = [ { id: 'ch-1', title: 'Chapter One', order: 1 }, { id: 'ch-2', title: 'Chapter Two', order: 2 } ];
    listChapters.mockResolvedValue({ data: { chapters: mockChapters } });
    listScenes.mockResolvedValue({ data: { scenes: [] } });
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const chapterSection1 = await screen.findByTestId('chapter-section-ch-1');
    const chapterSection2 = await screen.findByTestId('chapter-section-ch-2');
    expect(chapterSection1).toBeInTheDocument();
    expect(chapterSection2).toBeInTheDocument();
    expect(within(chapterSection1).getByText('1: Chapter One')).toBeInTheDocument();
    expect(within(chapterSection2).getByText('2: Chapter Two')).toBeInTheDocument();
    expect(listScenes).toHaveBeenCalledWith(TEST_PROJECT_ID, 'ch-1');
    expect(listScenes).toHaveBeenCalledWith(TEST_PROJECT_ID, 'ch-2');
  });


  it('renders character list when API returns data', async () => {
    const mockCharacters = [ { id: 'char-1', name: 'Hero', description: '' }, { id: 'char-2', name: 'Villain', description: '' } ];
    listCharacters.mockResolvedValue({ data: { characters: mockCharacters } });
    listChapters.mockResolvedValue({ data: { chapters: [] } });
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    expect(screen.getByRole('link', { name: 'Hero' })).toBeInTheDocument();
    expect(screen.getByRole('link', { name: 'Villain' })).toBeInTheDocument();
  });

  it('renders scenes within their respective ChapterSection components', async () => {
    const mockChapters = [{ id: TEST_CHAPTER_ID, title: 'The Only Chapter', order: 1 }];
    const mockScenes = [ { id: TEST_SCENE_ID, title: 'Scene Alpha', order: 1, content: '' }, { id: 'sc-2', title: 'Scene Beta', order: 2, content: '' }, ];
    listChapters.mockResolvedValue({ data: { chapters: mockChapters } });
    listScenes.mockImplementation((pid, chapterId) => {
        if (chapterId === TEST_CHAPTER_ID) return Promise.resolve({ data: { scenes: mockScenes } });
        return Promise.resolve({ data: { scenes: [] } });
    });
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const chapterSection = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    expect(within(chapterSection).getByText('1: The Only Chapter')).toBeInTheDocument();
    expect(within(chapterSection).getByRole('link', { name: '1: Scene Alpha' })).toBeInTheDocument();
    expect(within(chapterSection).getByRole('link', { name: '2: Scene Beta' })).toBeInTheDocument();
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

    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    expect(await screen.findByText(/no chapters yet/i)).toBeInTheDocument();

    createChapter.mockResolvedValueOnce({ data: newChapterData });
    listChapters.mockResolvedValueOnce({ data: { chapters: [newChapterData] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });

    const input = screen.getByPlaceholderText(/new chapter title/i);
    const addButton = screen.getByRole('button', { name: /add chapter/i });

    // Type first, then check enablement
    await user.type(input, newChapterTitle);
    expect(addButton).toBeEnabled(); // Button should be enabled now
    await user.click(addButton);

    const newChapterSection = await screen.findByTestId('chapter-section-new-ch-id');
    expect(within(newChapterSection).getByText(`1: ${newChapterTitle}`)).toBeInTheDocument();
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

    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const chapterSection = await screen.findByTestId('chapter-section-ch-del-1');
    expect(within(chapterSection).getByText(`1: ${chapterToDelete.title}`)).toBeInTheDocument();

    deleteChapter.mockResolvedValueOnce({});
    listChapters.mockResolvedValueOnce({ data: { chapters: [] } });

    const deleteButton = within(chapterSection).getByRole('button', { name: /delete chapter/i });
    await user.click(deleteButton);
    expect(window.confirm).toHaveBeenCalledTimes(1);

    expect(await screen.findByText(/no chapters yet/i)).toBeInTheDocument();
    expect(screen.queryByTestId('chapter-section-ch-del-1')).not.toBeInTheDocument();
    expect(deleteChapter).toHaveBeenCalledTimes(1);
    expect(listChapters).toHaveBeenCalledTimes(2);
  });


  it('creates a new character and refreshes the list', async () => {
    const user = userEvent.setup();
    const newCharacterName = 'Frodo Baggins';
    const newCharacterData = { id: 'new-char-id', name: newCharacterName, description: '' };
    listCharacters.mockResolvedValueOnce({ data: { characters: [] } });
    listChapters.mockResolvedValueOnce({ data: { chapters: [] } });

    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    expect(await screen.findByText(/no characters yet/i)).toBeInTheDocument();

    createCharacter.mockResolvedValueOnce({ data: newCharacterData });
    listCharacters.mockResolvedValueOnce({ data: { characters: [newCharacterData] } });

    const input = screen.getByPlaceholderText(/new character name/i);
    const addButton = screen.getByRole('button', { name: /add character/i });

    // Type first, then check enablement
    await user.type(input, newCharacterName);
    expect(addButton).toBeEnabled(); // Button should be enabled now
    await user.click(addButton);

    expect(await screen.findByRole('link', { name: newCharacterName })).toBeInTheDocument();
    expect(createCharacter).toHaveBeenCalledTimes(1);
    expect(listCharacters).toHaveBeenCalledTimes(2);
  });


  it('deletes a character and refreshes the list', async () => {
    const user = userEvent.setup();
    const characterToDelete = { id: 'char-del-1', name: 'Boromir', description: '' };
    listCharacters.mockResolvedValueOnce({ data: { characters: [characterToDelete] } });
    listChapters.mockResolvedValueOnce({ data: { chapters: [] } });

    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const charLink = await screen.findByRole('link', { name: characterToDelete.name });
    expect(charLink).toBeInTheDocument();

    deleteCharacter.mockResolvedValueOnce({});
    listCharacters.mockResolvedValueOnce({ data: { characters: [] } });

    const characterLi = charLink.closest('li');
    const deleteButton = within(characterLi).getByRole('button', { name: /delete/i });
    await user.click(deleteButton);
    expect(window.confirm).toHaveBeenCalledTimes(1);

    expect(await screen.findByText(/no characters yet/i)).toBeInTheDocument();
    expect(deleteCharacter).toHaveBeenCalledTimes(1);
    expect(listCharacters).toHaveBeenCalledTimes(2);
  });


  it('allows editing and saving the project name', async () => {
    const user = userEvent.setup();
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const heading = await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(heading).toBeInTheDocument();
    const editButton = screen.getByRole('button', { name: /edit name/i });
    await user.click(editButton);
    const nameInput = screen.getByRole('textbox', { name: /project name/i });
    await user.clear(nameInput);
    await user.type(nameInput, UPDATED_PROJECT_NAME);
    const saveButton = screen.getByRole('button', { name: /save name/i });
    await user.click(saveButton);
    expect(await screen.findByRole('heading', { name: `Project: ${UPDATED_PROJECT_NAME}` })).toBeInTheDocument();
    expect(await screen.findByText(/project name updated successfully/i)).toBeInTheDocument();
    expect(updateProject).toHaveBeenCalledTimes(1);
  });

  it('allows cancelling the project name edit', async () => {
    const user = userEvent.setup();
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
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

  // --- REVISED TEST ---
  it('disables save button when project name is empty', async () => {
    const user = userEvent.setup();
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);

    const heading = await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
    expect(heading).toBeInTheDocument();

    // Enter edit mode
    await user.click(screen.getByRole('button', { name: /edit name/i }));
    const nameInput = screen.getByRole('textbox', { name: /project name/i });
    const saveButton = screen.getByRole('button', { name: /save name/i });

    // Check button is enabled initially (or with non-empty value)
    expect(saveButton).toBeEnabled();

    // Clear the input
    await user.clear(nameInput);

    // Assert button is now disabled
    expect(saveButton).toBeDisabled();

    // (Optional) Type something back in and check if enabled
    await user.type(nameInput, 'Valid Name');
    expect(saveButton).toBeEnabled();

    // Ensure API was not called because save wasn't possible with empty input
    expect(updateProject).not.toHaveBeenCalled();
    // Ensure error message is NOT displayed
    expect(screen.queryByTestId('save-name-error')).not.toBeInTheDocument();
  });


  it('handles API error when saving project name', async () => {
     const user = userEvent.setup();
     const errorMessage = "Server error saving name";
     updateProject.mockRejectedValueOnce(new Error(errorMessage));
     await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
     const heading = await screen.findByRole('heading', { name: new RegExp(`Project: ${TEST_PROJECT_NAME}`, 'i') });
     expect(heading).toBeInTheDocument();
     await user.click(screen.getByRole('button', { name: /edit name/i }));
     await user.clear(screen.getByRole('textbox', { name: /project name/i }));
     await user.type(screen.getByRole('textbox', { name: /project name/i }), UPDATED_PROJECT_NAME);
     await user.click(screen.getByRole('button', { name: /save name/i }));
     expect(await screen.findByTestId('save-name-error')).toHaveTextContent(/failed to update project name/i);
     expect(updateProject).toHaveBeenCalledTimes(1);
     expect(screen.getByRole('textbox', { name: /project name/i })).toBeInTheDocument();
  });


  it('creates a new scene within a chapter and refreshes', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const newScene = { id: TEST_SCENE_ID, title: "New Scene", order: 1, content: "" };
    listChapters.mockResolvedValue({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } })
             .mockResolvedValue({ data: { scenes: [newScene] } });
    createScene.mockResolvedValue({ data: newScene });
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    expect(within(chapterContainer).queryByRole('link')).not.toBeInTheDocument();
    const addButton = within(chapterContainer).getByRole('button', { name: /add scene manually/i });
    await user.click(addButton);
    await waitFor(() => expect(createScene).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(listScenes).toHaveBeenCalledTimes(2));
    const updatedChapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    expect(await within(updatedChapterContainer).findByRole('link', { name: /1: New Scene/i })).toBeInTheDocument();
    expect(createScene).toHaveBeenCalledTimes(1);
  });


  it('deletes a scene within a chapter and refreshes', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const sceneToDelete = { id: TEST_SCENE_ID, title: 'Scene To Delete', order: 1, content: '' };
    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [sceneToDelete] } });
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    const sceneLink = await within(chapterContainer).findByRole('link', { name: `1: ${sceneToDelete.title}` });
    expect(sceneLink).toBeInTheDocument();
    deleteScene.mockResolvedValueOnce({});
    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });
    const deleteButton = within(chapterContainer).getByRole('button', { name: /del scene/i });
    await user.click(deleteButton);
    expect(window.confirm).toHaveBeenCalledTimes(1);
    await waitFor(() => { expect(within(chapterContainer).queryByRole('link', { name: `1: ${sceneToDelete.title}` })).not.toBeInTheDocument(); });
    expect(deleteScene).toHaveBeenCalledTimes(1);
    expect(listChapters).toHaveBeenCalledTimes(2);
    expect(listScenes).toHaveBeenCalledTimes(2);
  });


  // --- AI Feature Tests (Wait for initial load before interaction) ---

  it('calls generate API, shows modal, and creates scene from draft', async () => {
    const user = userEvent.setup();
    const aiSummary = "Write a scene about a character's journey";
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const generatedContent = "# Meeting the villain\n\nContent.";
    const generatedSceneTitle = "Meeting the villain";
    const newSceneData = { id: 'ai-scene-id', title: generatedSceneTitle, order: 1, content: generatedContent };
    listChapters.mockResolvedValue({ data: { chapters: [mockChapter] } });
    listScenes.mockImplementation((pid, chId) => { if (chId === TEST_CHAPTER_ID) { return createScene.mock.calls.length > 0 ? Promise.resolve({ data: { scenes: [newSceneData] } }) : Promise.resolve({ data: { scenes: [] } }); } return Promise.resolve({ data: { scenes: [] } }); });
    generateSceneDraft.mockResolvedValue({ data: { generated_content: generatedContent } });
    createScene.mockResolvedValue({ data: newSceneData });
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    const summaryInput = within(chapterContainer).getByLabelText(/optional prompt\/summary for ai/i);
    const generateButton = within(chapterContainer).getByRole('button', { name: /add scene using ai/i });
    await user.type(summaryInput, aiSummary);

    await waitFor(async () => {
        await user.click(generateButton);
        expect(generateSceneDraft).toHaveBeenCalledTimes(1);
        expect(await screen.findByTestId('generated-scene-modal')).toBeInTheDocument();
    });

    const modal = screen.getByTestId('generated-scene-modal');
    const createButton = within(modal).getByRole('button', { name: /create scene from draft/i });
    await user.click(createButton);
    await waitFor(() => expect(createScene).toHaveBeenCalledTimes(1));
    await waitFor(() => { expect(screen.queryByTestId('generated-scene-modal')).not.toBeInTheDocument(); });
    const updatedChapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    expect(await within(updatedChapterContainer).findByRole('link', { name: `1: ${generatedSceneTitle}` })).toBeInTheDocument();
    expect(generateSceneDraft).toHaveBeenCalledTimes(1);
    expect(createScene).toHaveBeenCalledTimes(1);
  });


  it('handles error during create scene from draft', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const generatedContent = "# Meeting the villain\n\nContent.";
    const createErrorMessage = "Failed to create scene";
    const mockError = new Error(createErrorMessage); mockError.response = { data: { detail: createErrorMessage } };
    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    generateSceneDraft.mockResolvedValueOnce({ data: { generated_content: generatedContent } });
    createScene.mockRejectedValueOnce(mockError);
    const generateButton = within(chapterContainer).getByRole('button', { name: /add scene using ai/i });

    await waitFor(async () => {
        await user.click(generateButton);
        expect(generateSceneDraft).toHaveBeenCalledTimes(1);
        expect(await screen.findByTestId('generated-scene-modal')).toBeInTheDocument();
    });

    const modal = screen.getByTestId('generated-scene-modal');
    const createButton = within(modal).getByRole('button', { name: /create scene/i });
    await user.click(createButton);
    expect(await within(modal).findByText(`Error: ${createErrorMessage}`)).toBeInTheDocument();
    expect(within(chapterContainer).queryByRole('link', { name: /meeting the villain/i })).not.toBeInTheDocument();
    expect(generateSceneDraft).toHaveBeenCalledTimes(1);
    expect(createScene).toHaveBeenCalledTimes(1);
    expect(listScenes).toHaveBeenCalledTimes(1);
  });

  // --- REMOVE Split Chapter Tests ---


  it('handles error during AI scene generation', async () => {
    const user = userEvent.setup();
    const mockChapter = { id: TEST_CHAPTER_ID, title: 'Test Chapter', order: 1 };
    const errorMessage = "AI generation failed";
    const mockError = new Error(errorMessage); mockError.response = { data: { detail: errorMessage } };
    listChapters.mockResolvedValueOnce({ data: { chapters: [mockChapter] } });
    listScenes.mockResolvedValueOnce({ data: { scenes: [] } });
    generateSceneDraft.mockRejectedValueOnce(mockError);
    await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
    const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
    const generateButton = within(chapterContainer).getByRole('button', { name: /add scene using ai/i });
    await user.click(generateButton);
    expect(await within(chapterContainer).findByTestId(`chapter-gen-error-${TEST_CHAPTER_ID}`)).toHaveTextContent(`Generate Error: ${errorMessage}`);
    expect(screen.queryByTestId('generated-scene-modal')).not.toBeInTheDocument();
    expect(generateSceneDraft).toHaveBeenCalledTimes(1);
    expect(createScene).not.toHaveBeenCalled();
  });

  // --- Test Chapter Title Editing Integration ---
  it('allows editing chapter title via ChapterSection', async () => {
      const user = userEvent.setup();
      const mockChapter = { id: TEST_CHAPTER_ID, title: 'Original Title', order: 1 };
      const updatedTitle = 'Updated Chapter Title';
      listChapters.mockResolvedValue({ data: { chapters: [mockChapter] } });
      listScenes.mockResolvedValue({ data: { scenes: [] } });
      updateChapter.mockImplementation(async () => { await new Promise(res => setTimeout(res, 10)); return { data: { ...mockChapter, title: updatedTitle } }; });

      await renderAndWaitForLoad([`/projects/${TEST_PROJECT_ID}`]);
      const chapterContainer = await screen.findByTestId(`chapter-section-${TEST_CHAPTER_ID}`);
      const editButton = within(chapterContainer).getByRole('button', { name: /edit title/i });

      await act(async () => { await user.click(editButton); });

      const titleInput = within(chapterContainer).getByRole('textbox', { name: /chapter title/i });
      await act(async () => {
          await user.clear(titleInput);
          await user.type(titleInput, updatedTitle);
      });

      const saveButton = within(chapterContainer).getByRole('button', { name: /save/i });

      // Mock the refresh call data *before* the save click finishes
      listChapters.mockResolvedValueOnce({ data: { chapters: [{ ...mockChapter, title: updatedTitle }] } });
      listScenes.mockResolvedValueOnce({ data: { scenes: [] } });

      await act(async () => {
          await user.click(saveButton);
          await flushPromises(); // Allow save handler and refresh to potentially start
      });

      // Wait for API call
      await waitFor(() => { expect(updateChapter).toHaveBeenCalledTimes(1); });
      expect(updateChapter).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_CHAPTER_ID, { title: updatedTitle });

      // Force another flush to process state updates from refresh
      await act(async () => { await flushPromises(); });

      // Wait for the component to re-render and exit edit mode
      await waitFor(() => {
          expect(within(chapterContainer).queryByRole('textbox', { name: /chapter title/i })).not.toBeInTheDocument();
      });

      // Now assert the title is updated using findByTestId
      expect(await within(chapterContainer).findByTestId(`chapter-title-${TEST_CHAPTER_ID}`)).toHaveTextContent(`1: ${updatedTitle}`);
  });


});