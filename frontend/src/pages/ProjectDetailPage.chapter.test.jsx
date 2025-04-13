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
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import ProjectDetailPage from './ProjectDetail';
import * as api from '../api/codexApi'; // Path relative to this file
// Import shared testing utilities
import { 
  renderWithRouter, 
  flushPromises, 
  TEST_PROJECT_ID,
  TEST_CHAPTER_ID,
  TEST_SCENE_ID,
  MOCK_PROJECT 
} from '../utils/testing';

// Use the imported test constants for consistent testing
const mockProject = {
  ...MOCK_PROJECT,
  // Add any test-specific overrides here if needed
};

const mockChaptersData = [
  { id: 'ch-1', title: 'Chapter One', order: 1, project_id: TEST_PROJECT_ID },
  { id: 'ch-2', title: 'Chapter Two', order: 2, project_id: TEST_PROJECT_ID }
];

const mockCharacters = [
  { id: 'char-1', name: 'Character One', description: 'Main protagonist', project_id: TEST_PROJECT_ID },
  { id: 'char-2', name: 'Character Two', description: 'Antagonist', project_id: TEST_PROJECT_ID }
];

const mockScenes = [
  { id: 'scene-1', title: 'Scene One', content: 'Scene content here', chapter_id: 'ch-1' },
  { id: 'scene-2', title: 'Scene Two', content: 'Another scene', chapter_id: 'ch-1' }
];

// Mock dependencies
vi.mock('../api/codexApi');

// Explicitly mock file-saver
vi.mock('file-saver', () => ({
  saveAs: vi.fn(),
  __esModule: true,
  default: { saveAs: vi.fn() }
}));

// Mock child components
vi.mock('../components/ChapterSection', () => ({ // Path relative to this file
    default: ({
        chapter,
        onDeleteChapter,
        onEditChapter,
        isEditingThisChapter,
        editedChapterTitleForInput,
        onTitleInputChange,
        onSaveChapter,
        onCancelEditChapter,
        isSavingThisChapter,
        saveChapterError,
        onGenerateScene,
        onSplitChapter,
        onCompileChapter,
        onCreateScene,
        onDeleteScene,
        onSummaryChange,
        onSplitInputChange,
    }) => (
        // ... (mock implementation remains the same)
        <div data-testid={`chapter-section-${chapter.id}`}>
            <strong data-testid={`chapter-title-${chapter.id}`}>{chapter.order}: {chapter.title}</strong>
            {isEditingThisChapter ? (
                <div>
                    <input type="text" aria-label="Chapter Title" value={editedChapterTitleForInput} onChange={onTitleInputChange} data-testid={`edit-chapter-input-${chapter.id}`} />
                    <button onClick={onSaveChapter} data-testid={`save-chapter-button-${chapter.id}`}>Save</button>
                    <button onClick={onCancelEditChapter} data-testid={`cancel-edit-button-${chapter.id}`}>Cancel</button>
                    {saveChapterError && <p data-testid={`chapter-save-error-${chapter.id}`}>{saveChapterError}</p>}
                </div>
            ) : ( <button onClick={() => onEditChapter(chapter)} data-testid={`edit-chapter-button-${chapter.id}`}>Edit Title</button> )}
            <button onClick={() => onDeleteChapter(chapter.id, chapter.title)} data-testid={`delete-chapter-button-${chapter.id}`}>Delete Chapter</button>
            <button onClick={() => onGenerateScene(chapter.id)} data-testid={`generate-scene-ai-button-${chapter.id}`}>+ Add Scene using AI</button>
            <button onClick={() => onCreateScene(chapter.id)} data-testid={`add-scene-manual-button-${chapter.id}`}>+ Add Scene Manually</button>
            <button onClick={() => onCompileChapter(chapter.id)} data-testid={`compile-chapter-button-${chapter.id}`}>Compile Chapter</button>
            <button onClick={() => onSplitChapter(chapter.id)} data-testid={`split-chapter-button-${chapter.id}`}>Split Chapter (AI)</button>
            <input data-testid={`summary-input-${chapter.id}`} onChange={(e) => onSummaryChange(chapter.id, e.target.value)} placeholder="Summary" />
            <textarea data-testid={`split-input-${chapter.id}`} onChange={(e) => onSplitInputChange(chapter.id, e.target.value)} placeholder="Split Content" />
        </div>
    )
}));


// --- Test Suite for Chapter Operations ---
describe('ProjectDetailPage Chapter Tests', () => {
    const user = userEvent.setup();
    let currentMockChapters;

    beforeEach(() => {
        vi.resetAllMocks();

        // Now we've defined mock data directly, so we can use it safely
        currentMockChapters = [...mockChaptersData]; 

        // Mock API calls using the initialized data
        api.getProject.mockResolvedValue({ data: mockProject });
        api.listChapters.mockResolvedValue({ data: { chapters: currentMockChapters } });
        api.listCharacters.mockResolvedValue({ data: { characters: mockCharacters } });
        api.listScenes.mockImplementation((projectId, chapterId) => {
            const chapter = currentMockChapters.find(c => c.id === chapterId);
            if (chapter) {
                 return Promise.resolve({ data: { scenes: mockScenes.filter(s => s.chapter_id === chapterId) } });
            }
            return Promise.resolve({ data: { scenes: [] } });
        });
        vi.spyOn(window, 'confirm').mockImplementation(() => true);
    });

    afterEach(() => {
        vi.restoreAllMocks();
    });

    // Helper to wait for initial data load
    const waitForInitialLoad = async () => {
        // Wait for API calls to be made - this is more reliable than looking for text
        await waitFor(() => {
            expect(api.getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
            expect(api.listChapters).toHaveBeenCalledWith(TEST_PROJECT_ID);
        });
        
        // Ensure there's time for the component to render
        await act(async () => { await flushPromises(); });
        
        // Wait for chapters to load if we have any
        if (currentMockChapters.length > 0) {
            try {
                await screen.findByTestId(`chapter-section-${currentMockChapters[0].id}`, {}, { timeout: 2000 });
            } catch (error) {
                // If we can't find the chapter section, just continue - the test will fail later if needed
                console.log('Chapter section not found, continuing with test');
            }
        }
        
        // Make sure character data is loaded
        if (mockCharacters.length > 0) {
            // Wait for the characters section to be displayed
            await screen.findByText(/Characters/i);
        }
        
        // Allow additional time for all async operations to settle
        await act(async () => {
            await flushPromises(50); // Use our imported utility
        });
    };


    it('creates a new chapter and refreshes the list', async () => {
        const newChapterTitle = 'Chapter Three';
        const nextOrder = currentMockChapters.length > 0 ? Math.max(0, ...currentMockChapters.map(c => Number(c.order) || 0)) + 1 : 1;
        const createdChapter = { id: 'ch-3', title: newChapterTitle, order: nextOrder, project_id: TEST_PROJECT_ID };
        api.createChapter.mockResolvedValue({ data: createdChapter });

        renderWithRouter(<ProjectDetailPage />, `/projects/${TEST_PROJECT_ID}`);
        await waitForInitialLoad();

        const input = screen.getByTestId('new-chapter-input');
        const addButton = screen.getByTestId('add-chapter-button');

        await user.type(input, newChapterTitle);
        await user.click(addButton);

        await waitFor(() => {
            expect(api.createChapter).toHaveBeenCalledTimes(1);
            expect(api.createChapter).toHaveBeenCalledWith(TEST_PROJECT_ID, {
                title: newChapterTitle,
                order: nextOrder
            });
        });

        expect(await screen.findByText(/Chapter Three/i)).toBeInTheDocument();
        expect(input).toHaveValue('');
    });

    it('handles error during chapter creation', async () => {
        const newChapterTitle = 'Chapter Error';
        const errorMessage = 'Failed to create chapter - Network Error';
        const nextOrder = currentMockChapters.length > 0 ? Math.max(0, ...currentMockChapters.map(c => Number(c.order) || 0)) + 1 : 1;
        api.createChapter.mockRejectedValue(new Error(errorMessage));

        renderWithRouter(<ProjectDetailPage />, `/projects/${TEST_PROJECT_ID}`);
        await waitForInitialLoad();

        const input = screen.getByTestId('new-chapter-input');
        const addButton = screen.getByTestId('add-chapter-button');

        await user.type(input, newChapterTitle);
        await user.click(addButton);

        await waitFor(() => {
            expect(api.createChapter).toHaveBeenCalledTimes(1);
            expect(api.createChapter).toHaveBeenCalledWith(TEST_PROJECT_ID, {
                title: newChapterTitle,
                order: nextOrder
            });
        });
        if (currentMockChapters && currentMockChapters.length > 0) { // Add check
             expect(screen.getByText(new RegExp(currentMockChapters[0].title, 'i'))).toBeInTheDocument();
        }
    });


    it('allows editing a chapter title', async () => {
        // We've defined mockChaptersData directly, so this should always pass
        expect(currentMockChapters.length).toBeGreaterThan(0);
        const chapterToEdit = currentMockChapters[0];
        const updatedTitle = 'Chapter One Revised';
        const updatedChapterData = { ...chapterToEdit, title: updatedTitle };
        api.updateChapter.mockResolvedValue({ data: updatedChapterData });

        renderWithRouter(<ProjectDetailPage />, `/projects/${TEST_PROJECT_ID}`);
        await waitForInitialLoad();

        const editButton = screen.getByTestId(`edit-chapter-button-${chapterToEdit.id}`);
        await user.click(editButton);

        const editInput = await screen.findByTestId(`edit-chapter-input-${chapterToEdit.id}`);
        expect(editInput).toHaveValue(chapterToEdit.title);

        await user.clear(editInput);
        await user.type(editInput, updatedTitle);
        expect(editInput).toHaveValue(updatedTitle);

        const saveButton = screen.getByTestId(`save-chapter-button-${chapterToEdit.id}`);
        await user.click(saveButton);

        await waitFor(() => {
            expect(api.updateChapter).toHaveBeenCalledTimes(1);
            expect(api.updateChapter).toHaveBeenCalledWith(TEST_PROJECT_ID, chapterToEdit.id, {
                title: updatedTitle,
                order: chapterToEdit.order
            });
        });

        expect(await screen.findByTestId(`chapter-title-${chapterToEdit.id}`)).toHaveTextContent(`${chapterToEdit.order}: ${updatedTitle}`);
        expect(screen.queryByTestId(`edit-chapter-input-${chapterToEdit.id}`)).not.toBeInTheDocument();
    });

     it('allows cancelling chapter title edit', async () => {
        expect(currentMockChapters.length).toBeGreaterThan(0);
        const chapterToEdit = currentMockChapters[0];

        renderWithRouter(<ProjectDetailPage />, `/projects/${TEST_PROJECT_ID}`);
        await waitForInitialLoad();

        const editButton = screen.getByTestId(`edit-chapter-button-${chapterToEdit.id}`);
        await user.click(editButton);

        const editInput = await screen.findByTestId(`edit-chapter-input-${chapterToEdit.id}`);
        await user.type(editInput, ' - temporary edit');

        const cancelButton = screen.getByTestId(`cancel-edit-button-${chapterToEdit.id}`);
        await user.click(cancelButton);

        expect(api.updateChapter).not.toHaveBeenCalled();

        expect(await screen.findByTestId(`chapter-title-${chapterToEdit.id}`)).toHaveTextContent(`${chapterToEdit.order}: ${chapterToEdit.title}`);
        expect(screen.queryByTestId(`edit-chapter-input-${chapterToEdit.id}`)).not.toBeInTheDocument();
    });

    it('handles error during chapter title update', async () => {
        expect(currentMockChapters.length).toBeGreaterThan(0);
        const chapterToEdit = currentMockChapters[0];
        const updatedTitle = 'Chapter With Error';
        const errorMessage = 'Failed to update chapter - Network Error';
        api.updateChapter.mockRejectedValue(new Error(errorMessage));

        renderWithRouter(<ProjectDetailPage />, `/projects/${TEST_PROJECT_ID}`);
        await waitForInitialLoad();

        const editButton = screen.getByTestId(`edit-chapter-button-${chapterToEdit.id}`);
        await user.click(editButton);

        const editInput = await screen.findByTestId(`edit-chapter-input-${chapterToEdit.id}`);
        expect(editInput).toHaveValue(chapterToEdit.title);

        await user.clear(editInput);
        await user.type(editInput, updatedTitle);
        expect(editInput).toHaveValue(updatedTitle);

        const saveButton = screen.getByTestId(`save-chapter-button-${chapterToEdit.id}`);
        await user.click(saveButton);

        await waitFor(() => {
            expect(api.updateChapter).toHaveBeenCalledTimes(1);
            expect(api.updateChapter).toHaveBeenCalledWith(TEST_PROJECT_ID, chapterToEdit.id, {
                title: updatedTitle,
                order: chapterToEdit.order
            });
        });

        expect(screen.getByTestId(`edit-chapter-input-${chapterToEdit.id}`)).toBeInTheDocument();
        expect(screen.getByTestId(`edit-chapter-input-${chapterToEdit.id}`)).toHaveValue(updatedTitle);
    });


    it('deletes a chapter and refreshes the list', async () => {
        expect(currentMockChapters.length).toBeGreaterThan(0);
        const chapterToDelete = currentMockChapters[0];
        const remainingChapters = currentMockChapters.slice(1).map((ch, index) => ({ ...ch, order: index + 1 }));

        api.deleteChapter.mockResolvedValue({ data: { message: 'Chapter deleted' } });

        const confirmSpy = window.confirm;

        renderWithRouter(<ProjectDetailPage />, `/projects/${TEST_PROJECT_ID}`);
        await waitForInitialLoad();

        const deleteButton = screen.getByTestId(`delete-chapter-button-${chapterToDelete.id}`);
        await user.click(deleteButton);

        expect(confirmSpy).toHaveBeenCalledTimes(1);
        expect(confirmSpy).toHaveBeenCalledWith(expect.stringContaining(chapterToDelete.title));

        await waitFor(() => {
            expect(api.deleteChapter).toHaveBeenCalledTimes(1);
            expect(api.deleteChapter).toHaveBeenCalledWith(TEST_PROJECT_ID, chapterToDelete.id);
        });

        await waitFor(() => {
            expect(screen.queryByText(new RegExp(chapterToDelete.title, 'i'))).not.toBeInTheDocument();
        });

        if (remainingChapters.length > 0) {
            const remainingChapterTitle = await screen.findByText(new RegExp(remainingChapters[0].title, 'i'));
            expect(remainingChapterTitle).toBeInTheDocument();
            expect(screen.getByTestId(`chapter-title-${remainingChapters[0].id}`)).toHaveTextContent(`1: ${remainingChapters[0].title}`);
        }
    });

     it('cancels chapter deletion', async () => {
        expect(currentMockChapters.length).toBeGreaterThan(0);
        const chapterToDelete = currentMockChapters[0];
        const confirmSpy = vi.spyOn(window, 'confirm').mockImplementationOnce(() => false);

        renderWithRouter(<ProjectDetailPage />, `/projects/${TEST_PROJECT_ID}`);
        await waitForInitialLoad();

        const deleteButton = screen.getByTestId(`delete-chapter-button-${chapterToDelete.id}`);
        await user.click(deleteButton);

        expect(confirmSpy).toHaveBeenCalledTimes(1);
        expect(api.deleteChapter).not.toHaveBeenCalled();
        expect(screen.getByText(new RegExp(chapterToDelete.title, 'i'))).toBeInTheDocument();

        confirmSpy.mockRestore();
    });

     it('handles error during chapter deletion', async () => {
        expect(currentMockChapters.length).toBeGreaterThan(0);
        const chapterToDelete = currentMockChapters[0];
        const errorMessage = 'Deletion failed!';
        api.deleteChapter.mockRejectedValue(new Error(errorMessage));

        const confirmSpy = window.confirm;

        renderWithRouter(<ProjectDetailPage />, `/projects/${TEST_PROJECT_ID}`);
        await waitForInitialLoad();

        const deleteButton = screen.getByTestId(`delete-chapter-button-${chapterToDelete.id}`);
        await user.click(deleteButton);

        await waitFor(() => {
            expect(api.deleteChapter).toHaveBeenCalledTimes(1);
            expect(api.deleteChapter).toHaveBeenCalledWith(TEST_PROJECT_ID, chapterToDelete.id);
        });

        expect(screen.getByText(new RegExp(chapterToDelete.title, 'i'))).toBeInTheDocument();
    });


});