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

// Basic tests for the refactored ProjectDetailPage structure

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event'; // <-- IMPORT ADDED
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';

import ProjectDetailPage from './index'; // Import the main component from the directory index
import * as api from '../../api/codexApi';
import ChapterSection from '../../components/ChapterSection'; // Import the actual component

// Mock API functions
vi.mock('../../api/codexApi');

// Mock child components that are complex or make their own API calls
vi.mock('../../components/ChapterSection', () => ({
    // Provide a default mock implementation for ChapterSection
    default: vi.fn((props) => (
        <div data-testid={`chapter-section-${props.chapter.id}`}>
            <h3 data-testid={`chapter-title-${props.chapter.id}`}>
                {props.chapter.order}: {props.chapter.title}
            </h3>
            {/* Simulate scene display */}
            {props.scenes?.map(scene => (
                <div key={scene.id} data-testid={`scene-${scene.id}`}>
                    Scene: {scene.title}
                </div>
            ))}
            {/* Add mock buttons/inputs if needed for interaction tests later */}
            <button onClick={() => props.onDeleteChapter(props.chapter.id)}>Delete Chapter</button>
            <input
                 type="text"
                 aria-label={`Edit chapter title ${props.chapter.id}`}
                 value={props.editedChapterTitleForInput ?? ''} // Use prop value
                 onChange={(e) => props.onTitleInputChange(props.chapter.id, e.target.value)}
            />
             <button onClick={() => props.onSaveChapterTitle(props.chapter.id)}>Save Title</button>
             {/* Add mocks for other required props */}
             <button onClick={() => props.onCreateScene(props.chapter.id, {})}>Create Scene</button>
             <button onClick={() => props.onDeleteScene(props.chapter.id, 'scene-mock-id')}>Delete Scene</button>
             <button onClick={() => props.onGenerateScene(props.chapter.id, {})}>Generate Scene</button>
             <button onClick={() => props.onSplitChapter(props.chapter.id)}>Split Chapter</button>
             <button onClick={() => props.onCompileChapter(props.chapter.id)}>Compile Chapter</button>
             <textarea
                 aria-label={`Scene generation summary ${props.chapter.id}`}
                 value={props.sceneGenerationSummary ?? ''}
                 onChange={(e) => props.onSummaryChange(props.chapter.id, e.target.value)}
             />
              <textarea
                 aria-label={`Split chapter content ${props.chapter.id}`}
                 value={props.splitChapterContent ?? ''}
                 onChange={(e) => props.onSplitInputChange(props.chapter.id, e.target.value)}
              />
        </div>
    ))
}));


const TEST_PROJECT_ID = 'proj-detail-refactor';
const MOCK_PROJECT = { id: TEST_PROJECT_ID, name: 'Refactor Test Project' };
const MOCK_CHAPTERS = [
    { id: 'ch1', title: 'Chapter One', order: 1 },
    { id: 'ch2', title: 'Chapter Two', order: 2 },
];
const MOCK_SCENES_CH1 = [
    { id: 's1', chapter_id: 'ch1', title: 'Scene 1.1', order: 1, content: 'Content 1.1' },
    { id: 's2', chapter_id: 'ch1', title: 'Scene 1.2', order: 2, content: 'Content 1.2' },
];
const MOCK_CHARACTERS = [
    { id: 'char1', name: 'Hero', description: 'The main one' },
];

const renderWithRouter = (initialEntries = [`/projects/${TEST_PROJECT_ID}`]) => {
    // Reset mocks passed to ChapterSection before each render if needed
     vi.mocked(ChapterSection).mockClear(); // Clear previous calls/instances if using vi.fn() directly

     // Re-mock ChapterSection specifically for this render if needed, or rely on the module-level mock
     // vi.mocked(ChapterSection).mockImplementation((props) => { ... }); // If more specific mock needed per test

    return render(
        <MemoryRouter initialEntries={initialEntries}>
            <Routes>
                <Route path="/projects/:projectId" element={<ProjectDetailPage />} />
                {/* Add other routes used by links within the page if necessary */}
                 <Route path="/projects/:projectId/notes" element={<div>Notes Page Mock</div>} />
                 <Route path="/projects/:projectId/query" element={<div>Query Page Mock</div>} />
                 <Route path="/projects/:projectId/plan" element={<div>Plan Edit Mock</div>} />
                 <Route path="/projects/:projectId/synopsis" element={<div>Synopsis Edit Mock</div>} />
                 <Route path="/projects/:projectId/world" element={<div>World Edit Mock</div>} />
                 <Route path="/projects/:projectId/characters/:characterId" element={<div>Character Edit Mock</div>} />
                 <Route path="/projects/:projectId/chapters/:chapterId/plan" element={<div>Chapter Plan Mock</div>} />
                 <Route path="/projects/:projectId/chapters/:chapterId/synopsis" element={<div>Chapter Synopsis Mock</div>} />
                 <Route path="/projects/:projectId/chapters/:chapterId/scenes/:sceneId" element={<div>Scene Edit Mock</div>} />

            </Routes>
        </MemoryRouter>
    );
};


describe('Refactored ProjectDetailPage Tests', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        // Setup default successful API mocks
        api.getProject.mockResolvedValue({ data: MOCK_PROJECT });
        api.listChapters.mockResolvedValue({ data: { chapters: MOCK_CHAPTERS } });
        api.listScenes.mockResolvedValue({ data: { scenes: MOCK_SCENES_CH1 } }); // Default to scenes for ch1
        api.listCharacters.mockResolvedValue({ data: { characters: MOCK_CHARACTERS } });
        api.rebuildProjectIndex.mockResolvedValue({ data: { message: 'Success' } });
        api.deleteChapter.mockResolvedValue({ data: { message: 'Deleted' } });
        api.deleteCharacter.mockResolvedValue({ data: { message: 'Deleted' } });
        api.createChapter.mockResolvedValue({ data: { id: 'ch-new', title: 'New Chapter', order: 3 } });
        api.createCharacter.mockResolvedValue({ data: { id: 'char-new', name: 'New Char', description: '' } });
        api.updateProject.mockResolvedValue({ data: { ...MOCK_PROJECT, name: 'Updated Name' } });
        api.updateChapter.mockResolvedValue({ data: { id: 'ch1', title: 'Updated Chapter', order: 1 } });
         // Mock compile/generate/split if those buttons are tested
         api.compileChapterContent.mockResolvedValue({ data: { filename: 'test.md', content: 'Compiled' } });
         api.generateSceneDraft.mockResolvedValue({ data: { title: 'Generated Scene', content: 'Generated content' } });
         api.splitChapterIntoScenes.mockResolvedValue({ data: { scenes: [] } });

          // Mock ChapterSection with specific implementation for these tests if needed
          // Or ensure the module-level mock includes necessary elements/calls
           vi.mocked(ChapterSection).mockImplementation(props => (
             <div data-testid={`chapter-section-${props.chapter.id}`}>
                <h3 data-testid={`chapter-title-${props.chapter.id}`}>
                    {props.chapter.order}: {props.chapter.title}
                </h3>
                {/* Simplified scene rendering for basic tests */}
                {props.scenes?.map(scene => <div key={scene.id}>Scene: {scene.title}</div>)}

                {/* Include necessary interactive elements with mock handlers */}
                <button onClick={() => props.onDeleteChapter(props.chapter.id)}>Delete Chapter</button>
                <input
                    type="text"
                    aria-label={`Edit chapter title ${props.chapter.id}`}
                    value={props.editingChapterId === props.chapter.id ? props.editedChapterTitleForInput : props.chapter.title} // Reflect edit state
                    onChange={(e) => props.onTitleInputChange(props.chapter.id, e.target.value)}
                    disabled={props.editingChapterId !== null && props.editingChapterId !== props.chapter.id}
                />
                <button onClick={() => props.onToggleEditTitle(props.chapter.id)}>
                    {props.editingChapterId === props.chapter.id ? 'Cancel Edit' : 'Edit Title'}
                 </button>
                <button
                    onClick={() => props.onSaveChapterTitle(props.chapter.id)}
                    disabled={props.editingChapterId !== props.chapter.id || props.isSavingChapterId === props.chapter.id}
                 >
                     {props.isSavingChapterId === props.chapter.id ? 'Saving...' : 'Save Title'}
                 </button>
                <button onClick={() => props.onGenerateScene(props.chapter.id, { summary: props.sceneGenerationSummary })}>Generate Scene</button>
                <button onClick={() => props.onSplitChapter(props.chapter.id, { content: props.splitChapterContent })}>Split Chapter</button>
                 <button onClick={() => props.onCompileChapter(props.chapter.id)}>Compile Chapter</button>
                 {/* Ensure other required props are handled or defaulted if necessary */}
                 <button onClick={() => props.onCreateScene(props.chapter.id, {})}>Add Scene Manually</button>
                 <button onClick={() => props.onDeleteScene(props.chapter.id, 'mockSceneId')}>Delete Scene</button>
                 <textarea
                    aria-label={`Scene generation summary ${props.chapter.id}`}
                    value={props.sceneGenerationSummary ?? ''}
                    onChange={(e) => props.onSummaryChange(props.chapter.id, e.target.value)}
                />
                <textarea
                    aria-label={`Split chapter content ${props.chapter.id}`}
                    value={props.splitChapterContent ?? ''}
                    onChange={(e) => props.onSplitInputChange(props.chapter.id, e.target.value)}
                />
                 {/* Mock links */}
                 <a href={`/projects/${props.projectId}/chapters/${props.chapter.id}/plan`}>Chapter Plan</a>
                 <a href={`/projects/${props.projectId}/chapters/${props.chapter.id}/synopsis`}>Chapter Synopsis</a>
            </div>
           ));

    });

    it('renders the project name correctly', async () => {
        renderWithRouter();
        // Wait for the heading containing the project name
        // The ProjectHeader component should handle displaying this
        expect(await screen.findByRole('heading', { name: new RegExp(MOCK_PROJECT.name, 'i'), level: 1 })).toBeInTheDocument();
        expect(api.getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });

    it('renders chapter sections with titles', async () => {
        renderWithRouter();
        // Wait for chapter titles to appear within the mocked ChapterSection
        expect(await screen.findByTestId('chapter-title-ch1')).toHaveTextContent(`1: ${MOCK_CHAPTERS[0].title}`);
        expect(screen.getByTestId('chapter-title-ch2')).toHaveTextContent(`2: ${MOCK_CHAPTERS[1].title}`);
        expect(api.listChapters).toHaveBeenCalledWith(TEST_PROJECT_ID);
    });

     it('renders character sections', async () => {
         renderWithRouter();
         // Wait for character name to appear
         expect(await screen.findByText(MOCK_CHARACTERS[0].name)).toBeInTheDocument();
         expect(api.listCharacters).toHaveBeenCalledWith(TEST_PROJECT_ID);
     });

     it('renders project tools section with links/buttons', async () => {
        renderWithRouter();
        // Check for key tool elements
        expect(await screen.findByTestId('rebuild-index-button')).toBeInTheDocument();
        expect(screen.getByTestId('query-link')).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/query`);
        expect(screen.getByTestId('notes-link')).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/notes`); // Verify new notes link
    });

     // Add more tests here for interactions handled by the main page
     // (e.g., triggering rebuild index, add chapter/character modals if managed by ProjectDetailPage directly)
      // Example: Test Rebuild Index Button Click
      it('calls rebuildProjectIndex when rebuild button is clicked', async () => {
           const user = userEvent.setup(); // <-- SETUP userEvent
           renderWithRouter();
           const rebuildButton = await screen.findByTestId('rebuild-index-button');
           await user.click(rebuildButton);
           await waitFor(() => {
               expect(api.rebuildProjectIndex).toHaveBeenCalledWith(TEST_PROJECT_ID);
           });
           // Check for success message display
           expect(await screen.findByTestId('rebuild-success')).toBeInTheDocument();
      });


});