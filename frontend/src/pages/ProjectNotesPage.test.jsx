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
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach } from 'vitest';

import ProjectNotesPage from './ProjectNotesPage';
import * as api from '../api/codexApi';

// Mock the API module
vi.mock('../api/codexApi');


const TEST_PROJECT_ID = 'proj-notes-123';
const MOCK_PROJECT = { id: TEST_PROJECT_ID, name: 'Notes Test Project' };
const MOCK_NOTES = [
    { id: 'note-abc', title: 'First Note', last_modified: '2024-01-01T10:00:00Z' },
    { id: 'note-def', title: 'Second Note', last_modified: '2024-01-02T11:00:00Z' },
];
const NEW_NOTE_TITLE = 'My Awesome New Note';
const NEW_NOTE_RESPONSE = { id: 'note-new', title: NEW_NOTE_TITLE, last_modified: '...' };

const renderComponent = () => {
    return render(
        <MemoryRouter initialEntries={[`/projects/${TEST_PROJECT_ID}/notes`]}>
            <Routes>
                <Route path="/projects/:projectId/notes" element={<ProjectNotesPage />} />
                <Route path="/projects/:projectId/notes/:noteId" element={<div>Note Edit Page Mock</div>} />
            </Routes>
        </MemoryRouter>
    );
};

describe('ProjectNotesPage', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        api.getProject.mockResolvedValue({ data: MOCK_PROJECT });
        api.listNotes.mockResolvedValue({ data: { notes: [...MOCK_NOTES] } });
        api.createNote.mockResolvedValue({ data: NEW_NOTE_RESPONSE });
        api.deleteNote.mockResolvedValue({ data: { message: 'Note deleted' } });
        global.confirm = vi.fn(() => true);
    });

    // --- Basic Rendering and Fetching Tests (Unchanged) ---
    it('renders loading state initially', async () => {
        api.listNotes.mockImplementation(() => new Promise(() => {}));
        renderComponent();
        expect(screen.getByText(/Loading notes.../i)).toBeInTheDocument();
        api.listNotes.mockResolvedValue({ data: { notes: [] } }); // Cleanup hanging promise
    });

    it('fetches project name and notes on mount and displays them', async () => {
        renderComponent();
        expect(await screen.findByRole('heading', { name: /Project Notes for "Notes Test Project"/i })).toBeInTheDocument();
        expect(await screen.findByText(MOCK_NOTES[0].title)).toBeInTheDocument();
        expect(screen.getByText(MOCK_NOTES[1].title)).toBeInTheDocument();
        await waitFor(() => {
             expect(api.getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
             expect(api.listNotes).toHaveBeenCalledWith(TEST_PROJECT_ID);
        });
        expect(screen.getByRole('link', { name: MOCK_NOTES[0].title })).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/notes/${MOCK_NOTES[0].id}`);
        expect(screen.getByRole('link', { name: MOCK_NOTES[1].title })).toHaveAttribute('href', `/projects/${TEST_PROJECT_ID}/notes/${MOCK_NOTES[1].id}`);
    });

     it('displays "No notes found" message when API returns empty list', async () => {
        api.listNotes.mockResolvedValue({ data: { notes: [] } });
        renderComponent();
        expect(await screen.findByRole('heading', { name: /Project Notes for "Notes Test Project"/i })).toBeInTheDocument();
        expect(await screen.findByText(/No notes found for this project./i)).toBeInTheDocument();
        expect(screen.queryByText(MOCK_NOTES[0].title)).not.toBeInTheDocument();
     });

     it('displays error message if fetching notes fails', async () => {
        const errorMsg = 'Failed to load notes';
        api.listNotes.mockRejectedValue(new Error(errorMsg));
        renderComponent();
        expect(await screen.findByRole('heading', { name: /Project Notes for "Notes Test Project"/i })).toBeInTheDocument();
        expect(await screen.findByText(/Failed to load notes. Please try again./i)).toBeInTheDocument();
    });

    // --- Create Note Tests (Refocused) ---
    it('allows creating a new note with Enter key: verifies form submission', async () => {
        const user = userEvent.setup();
        const refreshedNotes = [...MOCK_NOTES, NEW_NOTE_RESPONSE];
        api.listNotes
            .mockResolvedValueOnce({ data: { notes: [...MOCK_NOTES] } })
            .mockResolvedValueOnce({ data: { notes: refreshedNotes } });

        renderComponent();
        expect(await screen.findByText(MOCK_NOTES[0].title)).toBeInTheDocument();

        const input = screen.getByRole('textbox', { name: /new note title/i });

        await user.type(input, NEW_NOTE_TITLE + '{Enter}');

        await waitFor(() => {
            expect(api.createNote).toHaveBeenCalledTimes(1);
            expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, { title: NEW_NOTE_TITLE });
        });
        await waitFor(() => {
             expect(api.listNotes).toHaveBeenCalledTimes(2);
        });
        await waitFor(() => {
             expect(input).toHaveValue('');
             expect(screen.getByText(NEW_NOTE_TITLE)).toBeInTheDocument();
        });
    });

    it('allows creating a new note with button click: verifies API call and final UI state', async () => {
        const user = userEvent.setup();
        const refreshedNotes = [...MOCK_NOTES, NEW_NOTE_RESPONSE];
        api.listNotes
            .mockResolvedValueOnce({ data: { notes: [...MOCK_NOTES] } })
            .mockResolvedValueOnce({ data: { notes: refreshedNotes } });

        renderComponent();
        expect(await screen.findByText(MOCK_NOTES[0].title)).toBeInTheDocument();

        const input = screen.getByRole('textbox', { name: /new note title/i });
        const createButton = screen.getByRole('button', { name: /create note/i });

        await user.type(input, NEW_NOTE_TITLE);
        await user.click(createButton);

        await waitFor(() => {
            expect(api.createNote).toHaveBeenCalledTimes(1);
            expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, { title: NEW_NOTE_TITLE });
        });
        await waitFor(() => {
             expect(api.listNotes).toHaveBeenCalledTimes(2);
        });
        await waitFor(() => {
             expect(input).toHaveValue('');
             expect(screen.getByText(NEW_NOTE_TITLE)).toBeInTheDocument();
             expect(createButton).toBeDisabled(); // Correct: Disabled because input is empty
             expect(createButton).toHaveTextContent('Create Note');
        });
    });

    it('displays error message if creating note fails and resets UI', async () => {
        const user = userEvent.setup();
        const errorMsg = 'Server error on create';
        api.createNote.mockRejectedValue(new Error(errorMsg));

        renderComponent();
        expect(await screen.findByText(MOCK_NOTES[0].title)).toBeInTheDocument();

        const input = screen.getByRole('textbox', { name: /new note title/i });
        const createButton = screen.getByRole('button', { name: /create note/i });
        const noteTitle = 'Will Fail Note';
        await user.type(input, noteTitle);
        await user.click(createButton);

        await waitFor(() => {
             expect(api.createNote).toHaveBeenCalledTimes(1);
        });

        expect(await screen.findByText(/Failed to create note. Please try again./i)).toBeInTheDocument();
        await waitFor(() => {
             expect(input).toHaveValue(noteTitle);
             expect(createButton).not.toBeDisabled();
        });
        expect(api.listNotes).toHaveBeenCalledTimes(1);
    });

    // --- FIX: Renamed test and changed assertion ---
    it('disables create button when title input is empty or whitespace', async () => {
        const user = userEvent.setup();
        renderComponent();
        expect(await screen.findByText(MOCK_NOTES[0].title)).toBeInTheDocument(); // Wait for load

        const createButton = screen.getByRole('button', { name: /create note/i });
        const input = screen.getByRole('textbox', { name: /new note title/i });

        // 1. Initially disabled
        expect(createButton).toBeDisabled();

        // 2. Disabled with whitespace
        await user.type(input, '   ');
        expect(createButton).toBeDisabled();

        // 3. Enabled with text
        await user.type(input, 'Valid Title');
        expect(createButton).not.toBeDisabled();

        // 4. Disabled again when cleared
        await user.clear(input);
        expect(createButton).toBeDisabled();

        // Verify no API call happened during these checks
        expect(api.createNote).not.toHaveBeenCalled();
        // Verify no error message was displayed
        expect(screen.queryByText(/Note title cannot be empty./i)).not.toBeInTheDocument();
    });

    // --- Delete Note Tests (Refocused - Keep as before) ---
    it('allows deleting a note: verifies API call and final UI state', async () => {
        const user = userEvent.setup();
        const noteToDelete = MOCK_NOTES[0];
        const remainingNotes = MOCK_NOTES.filter(n => n.id !== noteToDelete.id);
        api.listNotes
            .mockResolvedValueOnce({ data: { notes: [...MOCK_NOTES] } })
            .mockResolvedValueOnce({ data: { notes: remainingNotes } });

        renderComponent();
        expect(await screen.findByText(noteToDelete.title)).toBeInTheDocument();

        const deleteButton = screen.getByRole('button', { name: `Delete note ${noteToDelete.title}` });

        await user.click(deleteButton);

        expect(global.confirm).toHaveBeenCalledWith(`Are you sure you want to delete the note "${noteToDelete.title}"?`);

        await waitFor(() => {
            expect(api.deleteNote).toHaveBeenCalledTimes(1);
            expect(api.deleteNote).toHaveBeenCalledWith(TEST_PROJECT_ID, noteToDelete.id);
        });

        await waitFor(() => {
            expect(api.listNotes).toHaveBeenCalledTimes(2);
        });

        await waitFor(() => {
             expect(screen.queryByText(noteToDelete.title)).not.toBeInTheDocument();
             expect(screen.queryByRole('button', { name: `Delete note ${noteToDelete.title}` })).not.toBeInTheDocument();
        });
        expect(screen.getByRole('button', { name: `Delete note ${MOCK_NOTES[1].title}` })).not.toBeDisabled();
    });

    it('does not delete note if confirmation is cancelled', async () => {
        const user = userEvent.setup();
        global.confirm = vi.fn(() => false);
        renderComponent();
        expect(await screen.findByText(MOCK_NOTES[0].title)).toBeInTheDocument();

        const noteToDelete = MOCK_NOTES[0];
        const deleteButton = screen.getByRole('button', { name: `Delete note ${noteToDelete.title}` });

        await user.click(deleteButton);

        expect(global.confirm).toHaveBeenCalledWith(`Are you sure you want to delete the note "${noteToDelete.title}"?`);
        expect(api.deleteNote).not.toHaveBeenCalled();
        expect(api.listNotes).toHaveBeenCalledTimes(1);
        expect(deleteButton).toHaveTextContent('Delete');
        expect(deleteButton).not.toBeDisabled();
    });

    it('displays error message if deleting note fails and resets UI', async () => {
        const user = userEvent.setup();
        const errorMsg = 'Server error on delete';
        api.deleteNote.mockRejectedValue(new Error(errorMsg));
        global.confirm = vi.fn(() => true);

        renderComponent();
        const noteToDelete = MOCK_NOTES[0];
        expect(await screen.findByText(noteToDelete.title)).toBeInTheDocument();

        const deleteButton = screen.getByRole('button', { name: `Delete note ${noteToDelete.title}` });

        await user.click(deleteButton);

        await waitFor(() => {
             expect(api.deleteNote).toHaveBeenCalledWith(TEST_PROJECT_ID, noteToDelete.id);
        });

        expect(await screen.findByText(/Failed to delete note. Please try again./i)).toBeInTheDocument();
        await waitFor(() => {
             const buttonAfterError = screen.getByRole('button', { name: `Delete note ${noteToDelete.title}` });
             expect(buttonAfterError).not.toBeDisabled();
             expect(buttonAfterError).toHaveTextContent('Delete');
        });
        expect(api.listNotes).toHaveBeenCalledTimes(1);
    });

    // --- Busy State Tests (Simplified - Keep as before) ---
     it('disables create button momentarily during create operation', async () => {
        const user = userEvent.setup();
        let resolveCreate;
        api.createNote.mockImplementation(() => new Promise(res => { resolveCreate = res; }));
        api.listNotes
            .mockResolvedValueOnce({ data: { notes: [...MOCK_NOTES] } })
            .mockResolvedValueOnce({ data: { notes: [...MOCK_NOTES] } });

        renderComponent();
        expect(await screen.findByText(MOCK_NOTES[0].title)).toBeInTheDocument();

        const input = screen.getByRole('textbox', { name: /new note title/i });
        const createButton = screen.getByRole('button', { name: /create note/i });

        await user.type(input, 'Busy Note');
        await user.click(createButton);

        await waitFor(() => {
             expect(screen.getByRole('button', { name: /creating.../i })).toBeDisabled();
        });

        resolveCreate({ data: { id: 'new' } });
        await waitFor(() => {
            // Button is disabled because input is empty after successful creation
            expect(screen.getByRole('button', { name: /create note/i })).toBeDisabled();
        });
     });

     it('disables delete button momentarily during delete operation', async () => {
        const user = userEvent.setup();
         let resolveDelete;
        api.deleteNote.mockImplementation(() => new Promise(res => { resolveDelete = res; }));
         global.confirm = vi.fn(() => true);
         api.listNotes
             .mockResolvedValueOnce({ data: { notes: [...MOCK_NOTES] } })
             .mockResolvedValueOnce({ data: { notes: [...MOCK_NOTES] } });

        renderComponent();
        const noteToDelete = MOCK_NOTES[0];
        expect(await screen.findByText(noteToDelete.title)).toBeInTheDocument();

        const deleteButton1 = screen.getByRole('button', { name: `Delete note ${noteToDelete.title}` });

        await user.click(deleteButton1);

        await waitFor(() => {
             const deletingButton = screen.getByRole('button', { name: `Delete note ${noteToDelete.title}` });
             expect(deletingButton).toBeDisabled();
             expect(deletingButton).toHaveTextContent(/Deleting.../i);
        });

        resolveDelete({ data: { message: 'ok' } });
        await waitFor(() => {
            expect(screen.queryByRole('button', { name: /deleting.../i })).not.toBeInTheDocument();
        });
     });
});