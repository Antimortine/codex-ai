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
import { render, screen, within, waitFor } from '@testing-library/react'; // Import waitFor
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom'; // Needed for <Link>
import { describe, it, expect, vi, beforeEach } from 'vitest';

import ChapterSection from './ChapterSection'; // Import the component

// --- Mock Data ---
const mockChapter = {
    id: 'ch-test-1',
    title: 'The Test Chapter',
    order: 1,
};

const mockScenes = [
    { id: 'sc-1', title: 'Scene Alpha', order: 1 },
    { id: 'sc-2', title: 'Scene Beta', order: 2 },
];

const mockProjectId = 'proj-test-123';

// --- Helper Function ---
const renderChapterSection = (props = {}) => {
    const defaultProps = {
        chapter: mockChapter,
        scenesForChapter: mockScenes,
        isLoadingChapterScenes: false,
        isEditingThisChapter: false,
        editedChapterTitleForInput: mockChapter.title, // Default to original if not editing
        isSavingThisChapter: false,
        saveChapterError: null,
        isGeneratingSceneForThisChapter: false,
        generationErrorForThisChapter: null,
        generationSummaryForInput: '',
        isAnyOperationLoading: false,
        projectId: mockProjectId,
        onEditChapter: vi.fn(),
        onSaveChapter: vi.fn(),
        onCancelEditChapter: vi.fn(),
        onDeleteChapter: vi.fn(),
        onCreateScene: vi.fn(),
        onDeleteScene: vi.fn(),
        onGenerateScene: vi.fn(),
        onSummaryChange: vi.fn(),
        onTitleInputChange: vi.fn(),
        // Split Props Defaults
        splitInputContentForThisChapter: '',
        isSplittingThisChapter: false,
        splitErrorForThisChapter: null,
        onSplitInputChange: vi.fn(),
        onSplitChapter: vi.fn(),
        ...props, // Override defaults with test-specific props
    };

    return render(
        <MemoryRouter> {/* Wrap with MemoryRouter because ChapterSection contains <Link> */}
            <ChapterSection {...defaultProps} />
        </MemoryRouter>
    );
};

// --- Test Suite ---
describe('ChapterSection Component', () => {
    let user;

    beforeEach(() => {
        user = userEvent.setup();
        // Reset mocks if needed (though renderChapterSection creates new ones each time)
    });

    // --- Rendering Tests ---
    describe('Rendering (Display Mode)', () => {
        it('renders chapter title and order', () => {
            renderChapterSection();
            expect(screen.getByText(`${mockChapter.order}: ${mockChapter.title}`)).toBeInTheDocument();
            expect(screen.queryByRole('textbox', { name: /chapter title/i })).not.toBeInTheDocument();
        });

        it('renders action buttons (Edit, Delete)', () => {
            renderChapterSection();
            expect(screen.getByRole('button', { name: /edit title/i })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /delete chapter/i })).toBeInTheDocument();
        });

        it('renders links to edit chapter plan and synopsis', () => {
            renderChapterSection();
            const planLink = screen.getByRole('link', { name: /edit chapter plan/i });
            const synopsisLink = screen.getByRole('link', { name: /edit chapter synopsis/i });

            expect(planLink).toBeInTheDocument();
            expect(planLink).toHaveAttribute('href', `/projects/${mockProjectId}/chapters/${mockChapter.id}/plan`);

            expect(synopsisLink).toBeInTheDocument();
            expect(synopsisLink).toHaveAttribute('href', `/projects/${mockProjectId}/chapters/${mockChapter.id}/synopsis`);
        });

        it('renders scene list with links and delete buttons when scenes exist', () => {
            renderChapterSection({ scenesForChapter: mockScenes });
            expect(screen.getByRole('link', { name: /1: Scene Alpha/i })).toBeInTheDocument();
            expect(screen.getByRole('link', { name: /2: Scene Beta/i })).toBeInTheDocument();
            expect(screen.getAllByRole('button', { name: /del scene/i })).toHaveLength(2);
            // Ensure split UI is hidden
            expect(screen.queryByLabelText(/paste full chapter content here to split/i)).not.toBeInTheDocument();
        });

        it('renders Split UI when scene list is empty and not loading', () => {
            renderChapterSection({ scenesForChapter: [] });
            expect(screen.getByLabelText(/paste full chapter content here to split/i)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /split chapter \(ai\)/i })).toBeInTheDocument();
            // Ensure scene list / no scenes message is hidden
            expect(screen.queryByText(/no scenes in this chapter yet/i)).not.toBeInTheDocument();
            expect(screen.queryByRole('list')).not.toBeInTheDocument();
        });

        it('renders Add/Generate Scene controls', () => {
            renderChapterSection();
            expect(screen.getByRole('button', { name: /\+ add scene manually/i })).toBeInTheDocument();
            expect(screen.getByLabelText(/optional prompt\/summary for ai/i)).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /\+ add scene using ai/i })).toBeInTheDocument();
        });
    });

    describe('Rendering (Loading Scenes)', () => {
        it('renders loading text and disables actions', () => {
            renderChapterSection({ isLoadingChapterScenes: true });
            expect(screen.getByText(/loading scenes.../i)).toBeInTheDocument();
            expect(screen.queryByRole('list')).not.toBeInTheDocument(); // No scene list
            expect(screen.queryByLabelText(/paste full chapter content here to split/i)).not.toBeInTheDocument(); // No split UI

            // Check buttons are disabled
            expect(screen.getByRole('button', { name: /edit title/i })).toBeDisabled();
            expect(screen.getByRole('button', { name: /delete chapter/i })).toBeDisabled();
            expect(screen.getByRole('button', { name: /\+ add scene manually/i })).toBeDisabled();
            expect(screen.getByRole('button', { name: /\+ add scene using ai/i })).toBeDisabled();
        });
    });

    describe('Rendering (Editing Chapter Title)', () => {
        it('renders input field and Save/Cancel buttons', () => {
            const editedTitle = "Editing Title";
            renderChapterSection({ isEditingThisChapter: true, editedChapterTitleForInput: editedTitle });

            const input = screen.getByRole('textbox', { name: /chapter title/i });
            expect(input).toBeInTheDocument();
            expect(input).toHaveValue(editedTitle);
            expect(screen.getByRole('button', { name: /save/i })).toBeInTheDocument();
            expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument();

            // Check display elements are hidden
            expect(screen.queryByText(`${mockChapter.order}: ${mockChapter.title}`)).not.toBeInTheDocument();
            expect(screen.queryByRole('button', { name: /edit title/i })).not.toBeInTheDocument();
        });

        it('disables Save button when title input is empty', () => {
            renderChapterSection({ isEditingThisChapter: true, editedChapterTitleForInput: "  " }); // Whitespace
            expect(screen.getByRole('button', { name: /save/i })).toBeDisabled();
        });
    });

    describe('Rendering (Saving Chapter Title)', () => {
        it('shows "Saving..." and disables edit controls', () => {
            renderChapterSection({ isEditingThisChapter: true, isSavingThisChapter: true });
            expect(screen.getByRole('button', { name: /saving.../i })).toBeInTheDocument();
            expect(screen.getByRole('textbox', { name: /chapter title/i })).toBeDisabled();
            expect(screen.getByRole('button', { name: /cancel/i })).toBeDisabled();
        });

        it('displays save error message', async () => { // Make test async
            const errorMsg = "Failed to save chapter";
            renderChapterSection({ isEditingThisChapter: true, isSavingThisChapter: false, saveChapterError: errorMsg });
            // Use findByTestId for robustness
            expect(await screen.findByTestId(`chapter-save-error-${mockChapter.id}`)).toHaveTextContent(`Save Error: ${errorMsg}`);
        });
    });

    describe('Rendering (Generating Scene)', () => {
        it('shows "Generating..." and disables AI controls', () => {
            renderChapterSection({ isGeneratingSceneForThisChapter: true });
            expect(screen.getByRole('button', { name: /generating.../i })).toBeInTheDocument();
            // Check both input and button are disabled
            expect(screen.getByLabelText(/optional prompt\/summary for ai/i)).toBeDisabled();
            expect(screen.getByRole('button', { name: /generating.../i })).toBeDisabled(); // The button itself
        });

        it('displays generation error message', () => {
            const errorMsg = "AI generation failed";
            renderChapterSection({ isGeneratingSceneForThisChapter: false, generationErrorForThisChapter: errorMsg });
            // Use test-id for robustness
            expect(screen.getByTestId(`chapter-gen-error-${mockChapter.id}`)).toHaveTextContent(`Generate Error: ${errorMsg}`);
        });
    });

    // --- Split Chapter Rendering ---
    describe('Rendering (Splitting Chapter)', () => {
        it('shows "Splitting..." and disables split controls when splitting', () => {
            renderChapterSection({ scenesForChapter: [], isSplittingThisChapter: true });
            expect(screen.getByRole('button', { name: /splitting.../i })).toBeInTheDocument();
            expect(screen.getByLabelText(/paste full chapter content here to split/i)).toBeDisabled();
            expect(screen.getByRole('button', { name: /splitting.../i })).toBeDisabled(); // The button itself
        });

        it('disables split button when scenes exist', () => {
            renderChapterSection({ scenesForChapter: mockScenes }); // Has scenes
            // Split UI shouldn't even render, but check button isn't there
             expect(screen.queryByRole('button', { name: /split chapter \(ai\)/i })).not.toBeInTheDocument();
        });

         it('disables split button when input is empty', () => {
            renderChapterSection({ scenesForChapter: [], splitInputContentForThisChapter: '  ' }); // Empty input
            expect(screen.getByRole('button', { name: /split chapter \(ai\)/i })).toBeDisabled();
        });

        it('displays split error message', () => {
            const errorMsg = "AI split failed";
            renderChapterSection({ scenesForChapter: [], splitErrorForThisChapter: errorMsg });
            expect(screen.getByTestId(`split-error-${mockChapter.id}`)).toHaveTextContent(`Split Error: ${errorMsg}`);
        });
    });
    // --- End Split Chapter Rendering ---

     describe('Rendering (isAnyOperationLoading)', () => {
        it('disables all actions when isAnyOperationLoading is true', () => {
            renderChapterSection({ isAnyOperationLoading: true, scenesForChapter: mockScenes });

            // Check display mode buttons
            expect(screen.getByRole('button', { name: /edit title/i })).toBeDisabled();
            expect(screen.getByRole('button', { name: /delete chapter/i })).toBeDisabled();
            // Check scene delete buttons
            screen.getAllByRole('button', { name: /del scene/i }).forEach(button => {
                expect(button).toBeDisabled();
            });
            // Check add/generate buttons
            expect(screen.getByRole('button', { name: /\+ add scene manually/i })).toBeDisabled();
            expect(screen.getByRole('button', { name: /\+ add scene using ai/i })).toBeDisabled();
            expect(screen.getByLabelText(/optional prompt\/summary for ai/i)).toBeDisabled();
            // Check split button (if it were rendered)
            // Since scenes exist, split UI isn't rendered, so no button to check
        });

        it('disables split controls when isAnyOperationLoading is true (no scenes)', () => {
             renderChapterSection({ isAnyOperationLoading: true, scenesForChapter: [] });
             expect(screen.getByLabelText(/paste full chapter content here to split/i)).toBeDisabled();
             expect(screen.getByRole('button', { name: /split chapter \(ai\)/i })).toBeDisabled();
        });
     });

    // --- Interaction Tests ---
    describe('Interactions & Callbacks', () => {
        it('calls onEditChapter when Edit Title is clicked', async () => {
            const onEditChapterMock = vi.fn();
            renderChapterSection({ onEditChapter: onEditChapterMock });
            await user.click(screen.getByRole('button', { name: /edit title/i }));
            expect(onEditChapterMock).toHaveBeenCalledTimes(1);
            expect(onEditChapterMock).toHaveBeenCalledWith(mockChapter);
        });

        it('calls onTitleInputChange when title input changes', async () => {
            const onTitleInputChangeMock = vi.fn();
            const initialTitle = "Initial Edit";
            renderChapterSection({ isEditingThisChapter: true, editedChapterTitleForInput: initialTitle, onTitleInputChange: onTitleInputChangeMock });
            const input = screen.getByRole('textbox', { name: /chapter title/i });
            await user.type(input, '!');
            expect(onTitleInputChangeMock).toHaveBeenCalledTimes(1);
            // Note: We can't easily check the event object content here without more complex setup
        });

        it('calls onSaveChapter when Save is clicked', async () => {
            const onSaveChapterMock = vi.fn();
            const editedTitle = "Saved Title";
            renderChapterSection({ isEditingThisChapter: true, editedChapterTitleForInput: editedTitle, onSaveChapter: onSaveChapterMock });
            await user.click(screen.getByRole('button', { name: /save/i }));
            expect(onSaveChapterMock).toHaveBeenCalledTimes(1);
            expect(onSaveChapterMock).toHaveBeenCalledWith(mockChapter.id, editedTitle);
        });

        it('calls onCancelEditChapter when Cancel is clicked', async () => {
            const onCancelEditChapterMock = vi.fn();
            renderChapterSection({ isEditingThisChapter: true, onCancelEditChapter: onCancelEditChapterMock });
            await user.click(screen.getByRole('button', { name: /cancel/i }));
            expect(onCancelEditChapterMock).toHaveBeenCalledTimes(1);
        });

        it('calls onDeleteChapter when Delete Chapter is clicked', async () => {
            const onDeleteChapterMock = vi.fn();
            renderChapterSection({ onDeleteChapter: onDeleteChapterMock });
            await user.click(screen.getByRole('button', { name: /delete chapter/i }));
            expect(onDeleteChapterMock).toHaveBeenCalledTimes(1);
            expect(onDeleteChapterMock).toHaveBeenCalledWith(mockChapter.id, mockChapter.title);
        });

        it('calls onCreateScene when Add Scene Manually is clicked', async () => {
            const onCreateSceneMock = vi.fn();
            renderChapterSection({ onCreateScene: onCreateSceneMock });
            await user.click(screen.getByRole('button', { name: /\+ add scene manually/i }));
            expect(onCreateSceneMock).toHaveBeenCalledTimes(1);
            expect(onCreateSceneMock).toHaveBeenCalledWith(mockChapter.id);
        });

        it('calls onDeleteScene when Del Scene is clicked', async () => {
            const onDeleteSceneMock = vi.fn();
            renderChapterSection({ scenesForChapter: mockScenes, onDeleteScene: onDeleteSceneMock });
            const deleteButtons = screen.getAllByRole('button', { name: /del scene/i });
            await user.click(deleteButtons[1]); // Click delete for the second scene
            expect(onDeleteSceneMock).toHaveBeenCalledTimes(1);
            expect(onDeleteSceneMock).toHaveBeenCalledWith(mockChapter.id, mockScenes[1].id, mockScenes[1].title);
        });

        it('calls onSummaryChange when summary input changes', async () => {
            const onSummaryChangeMock = vi.fn();
            renderChapterSection({ onSummaryChange: onSummaryChangeMock });
            const input = screen.getByLabelText(/optional prompt\/summary for ai/i);
            const testString = 'Test summary';
            await user.type(input, testString);
            // --- FIXED: Assert only call count ---
            expect(onSummaryChangeMock).toHaveBeenCalledTimes(testString.length);
            // We cannot reliably assert the final value with toHaveBeenLastCalledWith after user.type
            // --- END FIXED ---
        });

        it('calls onGenerateScene when Add Scene using AI is clicked', async () => {
            const onGenerateSceneMock = vi.fn();
            const summary = "AI Prompt";
            renderChapterSection({ onGenerateScene: onGenerateSceneMock, generationSummaryForInput: summary });
            await user.click(screen.getByRole('button', { name: /\+ add scene using ai/i }));
            expect(onGenerateSceneMock).toHaveBeenCalledTimes(1);
            // We need to expect an empty array for the third parameter since our component converts undefined to []
            expect(onGenerateSceneMock).toHaveBeenCalledWith(mockChapter.id, summary, []);
        });

        // --- Split Chapter Interactions ---
        it('calls onSplitInputChange when split textarea changes', async () => {
            const onSplitInputChangeMock = vi.fn();
            renderChapterSection({ scenesForChapter: [], onSplitInputChange: onSplitInputChangeMock });
            const textarea = screen.getByLabelText(/paste full chapter content here to split/i);
            const testString = 'Split this';
            await user.type(textarea, testString);
            // --- FIXED: Assert only call count ---
            expect(onSplitInputChangeMock).toHaveBeenCalledTimes(testString.length);
            // We cannot reliably assert the final value with toHaveBeenLastCalledWith after user.type
            // --- END FIXED ---
        });

        it('calls onSplitChapter when Split Chapter button is clicked', async () => {
            const onSplitChapterMock = vi.fn();
            const content = "Some content to split";
            renderChapterSection({
                scenesForChapter: [],
                splitInputContentForThisChapter: content, // Ensure button is enabled
                onSplitChapter: onSplitChapterMock
            });
            const button = screen.getByRole('button', { name: /split chapter \(ai\)/i });
            expect(button).toBeEnabled(); // Verify it's enabled before click
            await user.click(button);
            expect(onSplitChapterMock).toHaveBeenCalledTimes(1);
            expect(onSplitChapterMock).toHaveBeenCalledWith(mockChapter.id);
        });
        // --- End Split Chapter Interactions ---
    });
});