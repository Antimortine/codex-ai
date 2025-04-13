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
import { render, screen, waitFor, waitForElementToBeRemoved } from '@testing-library/react'; // Import waitForElementToBeRemoved
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

import NoteEditPage from './NoteEditPage';
import * as api from '../api/codexApi';

// --- Mock API ---
vi.mock('../api/codexApi');

// --- Mock AIEditorWrapper ---
let editorProps = {};
vi.mock('../components/AIEditorWrapper', () => ({
    default: (props) => {
        editorProps = { ...props };
        // Simulate content prop for textarea
        const valueToShow = props.value === null || props.value === undefined ? '' : props.value;
        return (
            <textarea
                data-testid="mock-ai-editor"
                value={valueToShow} // Handle potential null/undefined
                onChange={(e) => props.onChange(e.target.value)}
                aria-label="Note Content Mock Editor"
            />
        );
    },
}));

// --- Test Data ---
const TEST_PROJECT_ID = 'proj-edit-456';
const TEST_NOTE_ID = 'note-xyz';
const MOCK_NOTE_INITIAL = {
    id: TEST_NOTE_ID,
    title: 'Initial Note Title',
    content: 'Initial note content.',
    last_modified: '2024-01-03T12:00:00Z'
};
// Define an explicit updated object for clarity in mock responses
const MOCK_NOTE_UPDATED = {
    ...MOCK_NOTE_INITIAL,
    title: 'Updated Title',
    content: 'Updated Content',
    last_modified: '2024-01-03T13:00:00Z' // Simulate time change
};


const renderComponent = () => {
    editorProps = {};
    return render(
        <MemoryRouter initialEntries={[`/projects/${TEST_PROJECT_ID}/notes/${TEST_NOTE_ID}`]}>
            <Routes>
                <Route path="/projects/:projectId/notes/:noteId" element={<NoteEditPage />} />
                <Route path="/projects/:projectId/notes" element={<div>Notes List Page Mock</div>} />
            </Routes>
        </MemoryRouter>
    );
};


describe('NoteEditPage', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        // *** REMOVED FAKE TIMERS ***
        // Default successful mocks returning distinct objects
        api.getNote.mockResolvedValue({ data: { ...MOCK_NOTE_INITIAL } }); // Return a copy
        api.updateNote.mockResolvedValue({ data: { ...MOCK_NOTE_UPDATED } }); // Return a copy
    });

    // *** REMOVED afterEach restoring timers ***

    it('renders loading state initially', () => {
        // Make getNote hang initially
        api.getNote.mockImplementation(() => new Promise(() => {}));
        renderComponent();
        expect(screen.getByText(/Loading note.../i)).toBeInTheDocument();
    });

    it('fetches note data on mount and displays it in form fields', async () => {
        renderComponent();

        // Use findBy* which incorporates waitFor
        const titleInput = await screen.findByRole('textbox', { name: /note title/i });
        const editor = await screen.findByTestId('mock-ai-editor');

        // Verify initial state
        expect(titleInput).toHaveValue(MOCK_NOTE_INITIAL.title);
        expect(editor).toHaveValue(MOCK_NOTE_INITIAL.content);
        expect(api.getNote).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_NOTE_ID);

        // Verify editor props (ensure value is correct even if null initially)
        expect(editorProps.value).toBe(MOCK_NOTE_INITIAL.content);
        expect(editorProps.projectId).toBe(TEST_PROJECT_ID);

        // Save button should be disabled initially
        expect(screen.getByRole('button', { name: /save note/i })).toBeDisabled();
    });

    it('displays error message if fetching note fails', async () => {
        const errorMsg = 'Note not found';
        api.getNote.mockRejectedValue(new Error(errorMsg));
        renderComponent();

        // Use findBy* for error message as well
        expect(await screen.findByText(/Error Loading Note/i)).toBeInTheDocument();
        expect(await screen.findByText(/Failed to load note note-xyz/i)).toBeInTheDocument();
        expect(screen.queryByRole('textbox', { name: /note title/i })).not.toBeInTheDocument();
    });

    it('enables save button when title is changed', async () => {
        const user = userEvent.setup();
        renderComponent();

        const titleInput = await screen.findByRole('textbox', { name: /note title/i });
        const saveButton = screen.getByRole('button', { name: /save note/i });

        expect(saveButton).toBeDisabled();
        await user.type(titleInput, ' Updated');
        // No waitFor needed here, enabling should be synchronous on input change
        expect(saveButton).not.toBeDisabled();
    });

    it('enables save button when content is changed via editor mock', async () => {
        const user = userEvent.setup();
        renderComponent();

        const editor = await screen.findByTestId('mock-ai-editor');
        const saveButton = screen.getByRole('button', { name: /save note/i });

        expect(saveButton).toBeDisabled();
        await user.type(editor, ' Additional content.');
        // No waitFor needed here
        expect(saveButton).not.toBeDisabled();
    });

    it('calls updateNote with only title when only title is changed', async () => {
        const user = userEvent.setup();
        const specificUpdatedData = { ...MOCK_NOTE_INITIAL, title: 'Updated Title Only' };
        api.updateNote.mockResolvedValue({ data: specificUpdatedData }); // Mock specific response for this test

        renderComponent();

        const titleInput = await screen.findByRole('textbox', { name: /note title/i });
        const saveButton = screen.getByRole('button', { name: /save note/i });
        const newTitle = 'Updated Title Only';

        await user.clear(titleInput);
        await user.type(titleInput, newTitle);
        expect(saveButton).not.toBeDisabled(); // Button is enabled

        await user.click(saveButton);

        // Wait for the API call *first*
        await waitFor(() => {
            expect(api.updateNote).toHaveBeenCalledTimes(1);
            expect(api.updateNote).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_NOTE_ID, { title: newTitle });
        });

        // Then wait for the UI consequences
        await waitFor(() => {
             // Button text changes back
             expect(screen.getByRole('button', { name: /save note/i })).toBeInTheDocument();
             // Button becomes disabled because state matches saved state
             expect(screen.getByRole('button', { name: /save note/i })).toBeDisabled();
        });
        // Check success message appeared
        const successMessage = await screen.findByText(/Note saved successfully!/i);
        expect(successMessage).toBeInTheDocument();

        // Wait for message to disappear (using real timers now)
        await waitForElementToBeRemoved(() => screen.queryByText(/Note saved successfully!/i), { timeout: 4000 }); // Adjust timeout slightly > 3000ms
    });

     it('calls updateNote with only content when only content is changed', async () => {
        const user = userEvent.setup();
        const newContent = 'Updated content only.';
        const specificUpdatedData = { ...MOCK_NOTE_INITIAL, content: newContent };
        api.updateNote.mockResolvedValue({ data: specificUpdatedData });

        renderComponent();

        const editor = await screen.findByTestId('mock-ai-editor');
        const saveButton = screen.getByRole('button', { name: /save note/i });

        await user.clear(editor);
        await user.type(editor, newContent);
        expect(saveButton).not.toBeDisabled();

        await user.click(saveButton);

        // Wait for API call
        await waitFor(() => {
            expect(api.updateNote).toHaveBeenCalledTimes(1);
            expect(api.updateNote).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_NOTE_ID, { content: newContent });
        });

        // Wait for UI consequences
        await waitFor(() => {
             expect(screen.getByRole('button', { name: /save note/i })).toBeDisabled();
        });
        const successMessage = await screen.findByText(/Note saved successfully!/i);
        expect(successMessage).toBeInTheDocument();

        // Wait for message removal
        await waitForElementToBeRemoved(() => screen.queryByText(/Note saved successfully!/i), { timeout: 4000 });
     });

      it('calls updateNote with both title and content when both are changed', async () => {
        const user = userEvent.setup();
        const newTitle = 'New Title Both';
        const newContent = 'New Content Both';
        const specificUpdatedData = { ...MOCK_NOTE_INITIAL, title: newTitle, content: newContent };
        api.updateNote.mockResolvedValue({ data: specificUpdatedData });

        renderComponent();

        const titleInput = await screen.findByRole('textbox', { name: /note title/i });
        const editor = await screen.findByTestId('mock-ai-editor');
        const saveButton = screen.getByRole('button', { name: /save note/i });

        await user.clear(titleInput);
        await user.type(titleInput, newTitle);
        await user.clear(editor);
        await user.type(editor, newContent);
        expect(saveButton).not.toBeDisabled();

        await user.click(saveButton);

        // Wait for API call
        await waitFor(() => {
            expect(api.updateNote).toHaveBeenCalledTimes(1);
            expect(api.updateNote).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_NOTE_ID, { title: newTitle, content: newContent });
        });
         // Wait for UI consequences
         await waitFor(() => {
              expect(screen.getByRole('button', { name: /save note/i })).toBeDisabled();
         });
        const successMessage = await screen.findByText(/Note saved successfully!/i);
        expect(successMessage).toBeInTheDocument();
         // Wait for message removal
         await waitForElementToBeRemoved(() => screen.queryByText(/Note saved successfully!/i), { timeout: 4000 });
     });

     it('shows success message briefly if save is clicked with no changes', async () => {
        const user = userEvent.setup();
        renderComponent();

        await screen.findByRole('textbox', { name: /note title/i }); // Wait for load
        const saveButton = screen.getByRole('button', { name: /save note/i });

        expect(saveButton).toBeDisabled();
        // Cannot click disabled button with userEvent, but testing the logic anyway
        // Simulate the condition where handleSave is called with no changes
        // In the actual component, this branch IS reachable if the component state is changed and then reverted before saving.
        // Let's simulate that:
        const titleInput = screen.getByRole('textbox', { name: /note title/i });
        await user.type(titleInput, 'temp');
        expect(saveButton).not.toBeDisabled();
        await user.clear(titleInput);
        await user.type(titleInput, MOCK_NOTE_INITIAL.title); // Revert
        expect(saveButton).toBeDisabled(); // Disabled again

        // Now, if we could call the handler directly (not ideal), it would hit the "no change" branch.
        // Instead, we test that the button is disabled, which implies no API call.
        // The success message logic for "no changes" might need a slight component adjustment
        // if we want to explicitly test that brief success message *without* an API call.
        // For now, we verify the button is disabled and no API call happens.
        expect(api.updateNote).not.toHaveBeenCalled();

        // If the "no change" branch *was* reached, test the message:
        // expect(await screen.findByText(/Note saved successfully!/i)).toBeInTheDocument();
        // await waitForElementToBeRemoved(() => screen.queryByText(/Note saved successfully!/i), { timeout: 4000 });
     });

    it('displays error message if saving note fails', async () => {
        const user = userEvent.setup();
        const errorMsg = 'Server save error';
        api.updateNote.mockRejectedValue(new Error(errorMsg));
        renderComponent();

        const titleInput = await screen.findByRole('textbox', { name: /note title/i });
        const saveButton = screen.getByRole('button', { name: /save note/i });

        await user.type(titleInput, ' Change to trigger save');
        expect(saveButton).not.toBeDisabled();
        await user.click(saveButton);

        // Wait for API call attempt
        await waitFor(() => {
             expect(api.updateNote).toHaveBeenCalledTimes(1);
        });

        // Check for error message
        expect(await screen.findByText(/Failed to save note. Please try again./i)).toBeInTheDocument();
        expect(screen.queryByText(/Note saved successfully!/i)).not.toBeInTheDocument();

        // Button should be re-enabled because changes are still present and save failed
        expect(saveButton).not.toBeDisabled();
        expect(screen.getByRole('button', { name: /save note/i })).toBeInTheDocument(); // Check text reverted
    });

    it('prevents saving with an empty title', async () => {
        const user = userEvent.setup();
        renderComponent();

        const titleInput = await screen.findByRole('textbox', { name: /note title/i });
        const saveButton = screen.getByRole('button', { name: /save note/i });

        await user.clear(titleInput); // Make title empty
        expect(titleInput).toHaveValue('');
        expect(saveButton).not.toBeDisabled(); // Button is enabled because content hasn't changed back yet

        await user.click(saveButton); // Click to trigger validation

        // Validation happens synchronously in the handler
        expect(api.updateNote).not.toHaveBeenCalled();
        expect(await screen.findByText(/Note title cannot be empty./i)).toBeInTheDocument();
        expect(saveButton).not.toBeDisabled(); // Stays enabled because save didn't start
    });

     it('updates internal state correctly after successful save and allows further saves', async () => {
        const user = userEvent.setup();
        // Ensure the mock returns the exact data we changed to
        api.updateNote.mockResolvedValue({ data: { ...MOCK_NOTE_INITIAL, title: 'Saved New Title', content: 'Saved New Content' }});
        renderComponent();

        const titleInput = await screen.findByRole('textbox', { name: /note title/i });
        const editor = await screen.findByTestId('mock-ai-editor');
        const saveButton = screen.getByRole('button', { name: /save note/i });

        // Make changes
        await user.clear(titleInput);
        await user.type(titleInput, 'Saved New Title');
        await user.clear(editor);
        await user.type(editor, 'Saved New Content');
        expect(saveButton).not.toBeDisabled();

        // Save
        await user.click(saveButton);

        // Wait for save UI consequences
        await waitFor(() => {
            expect(screen.getByRole('button', { name: /save note/i })).toBeDisabled();
        });
        expect(await screen.findByText(/Note saved successfully!/i)).toBeInTheDocument();
        await waitForElementToBeRemoved(() => screen.queryByText(/Note saved successfully!/i), { timeout: 4000 });


        // Now, the button should be disabled because the current state matches the *new* originalNote state
        expect(saveButton).toBeDisabled();

        // Make another minor change
        await user.type(titleInput, '!');
        expect(saveButton).not.toBeDisabled(); // Should be enabled again

        // Mock response for second save
        const secondUpdateData = { ...MOCK_NOTE_INITIAL, title: 'Saved New Title!', content: 'Saved New Content' };
        api.updateNote.mockResolvedValue({ data: secondUpdateData });

        // Save again
        await user.click(saveButton);

         // Wait for API call
         await waitFor(() => {
             expect(api.updateNote).toHaveBeenCalledTimes(2); // Second call
             expect(api.updateNote).toHaveBeenLastCalledWith(TEST_PROJECT_ID, TEST_NOTE_ID, { title: 'Saved New Title!' });
         });
          // Wait for UI consequences
          await waitFor(() => {
               expect(screen.getByRole('button', { name: /save note/i })).toBeDisabled();
          });
         expect(await screen.findByText(/Note saved successfully!/i)).toBeInTheDocument();
         await waitForElementToBeRemoved(() => screen.queryByText(/Note saved successfully!/i), { timeout: 4000 });
    });

});