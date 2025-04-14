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
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

import ProjectNotesPage from './ProjectNotesPage';
import * as api from '../api/codexApi';

// --- Mocks ---
vi.mock('../api/codexApi');
vi.mock('uuid', () => ({
    v4: vi.fn(() => 'mock-temp-uuid-123'),
}));

// Mock the NoteTreeViewer component - UPDATED for Move button
vi.mock('../components/NoteTreeViewer', () => ({
  default: vi.fn(({ projectId, treeData, handlers, isBusy }) => {
    if (!treeData || treeData.length === 0) {
      return <div data-testid="mock-note-tree-viewer">No notes or folders found.</div>;
    }
    const renderMockNode = (node) => (
        <div key={node.id} data-testid={`node-${node.id}`}>
            <span>{node.type === 'folder' ? '📁' : '📄'} {node.name} ({node.path})</span>
            {/* Action Buttons */}
            {node.type === 'folder' && (
                <>
                    <button data-testid={`create-folder-${node.id}`} onClick={() => handlers.onCreateFolder(node.path)} disabled={isBusy}>+ Folder in {node.name}</button>
                    <button data-testid={`create-note-${node.id}`} onClick={() => handlers.onCreateNote(node.path)} disabled={isBusy}>+ Note in {node.name}</button>
                    {node.path !== '/' && (
                         <button data-testid={`rename-folder-${node.id}`} onClick={() => handlers.onRenameFolder(node.path, node.name)} disabled={isBusy}>Rename Folder {node.name}</button>
                    )}
                    {node.path !== '/' && (
                        <button data-testid={`delete-folder-${node.id}`} onClick={() => handlers.onDeleteFolder(node.path)} disabled={isBusy}>Delete Folder {node.name}</button>
                    )}
                </>
            )}
            {node.type === 'note' && (
                 <>
                    {/* Add Move Button Mock */}
                    <button data-testid={`move-note-${node.note_id}`} onClick={() => handlers.onMoveNote(node.note_id, node.path)} disabled={isBusy}>Move Note {node.name}</button>
                    <button data-testid={`delete-note-${node.note_id}`} onClick={() => handlers.onDeleteNote(node.note_id, node.name)} disabled={isBusy}>Delete Note {node.name}</button>
                 </>
            )}
            {/* Render children */}
            {node.children && node.children.length > 0 && (
                <div style={{ marginLeft: '20px' }}>
                    {node.children.map(renderMockNode)}
                </div>
            )}
        </div>
    );

    return (
        <div data-testid="mock-note-tree-viewer">
            <p>Project ID: {projectId}</p>
            <p data-testid="is-busy-prop">Is Busy: {String(isBusy)}</p>
            <p data-testid="tree-node-count">Tree Nodes: {treeData.length}</p>
            {treeData.map(renderMockNode)}
            {/* Root Action Buttons */}
            <button data-testid="create-note-root" onClick={() => handlers.onCreateNote('/')} disabled={isBusy}>+ Note in Root</button>
            <button data-testid="create-folder-root" onClick={() => handlers.onCreateFolder('/')} disabled={isBusy}>+ Folder in Root</button>
        </div>
    );
  }),
}));

import NoteTreeViewer from '../components/NoteTreeViewer';


// --- Test Data ---
const TEST_PROJECT_ID = 'proj-notes-tree-123';
const MOCK_PROJECT = { id: TEST_PROJECT_ID, name: 'Notes Tree Test Project' };
const MOCK_TREE_DATA_INITIAL = [
    { id: '/FolderA', name: 'FolderA', type: 'folder', path: '/FolderA', children: [
        { id: 'note-a1', name: 'Note A1', type: 'note', path: '/FolderA', note_id: 'note-a1', last_modified: Date.now()/1000 - 100, children: [] }
    ]},
    { id: '/FolderB', name: 'FolderB', type: 'folder', path: '/FolderB', children: []}, // Add another folder for moving
    { id: 'note-root', name: 'Root Note', type: 'note', path: '/', note_id: 'note-root', last_modified: Date.now()/1000 - 200, children: [] }
];
const NEW_NOTE_TITLE = 'My Awesome New Note';
const NEW_NOTE_RESPONSE = { id: 'note-new', title: NEW_NOTE_TITLE, folder_path: '/', last_modified: Date.now()/1000 };


// --- Test Setup ---
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

const originalPrompt = window.prompt;
const originalConfirm = window.confirm;

describe('ProjectNotesPage (Tree View)', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        api.getProject.mockResolvedValue({ data: MOCK_PROJECT });
        api.getNoteTree.mockResolvedValue({ data: { tree: structuredClone(MOCK_TREE_DATA_INITIAL) } });
        api.createNote.mockResolvedValue({ data: NEW_NOTE_RESPONSE });
        api.deleteNote.mockResolvedValue({ data: { message: 'Note deleted' } });
        api.deleteFolder.mockResolvedValue({ data: { message: 'Folder deleted' } });
        api.renameFolder.mockResolvedValue({ data: { message: 'Folder renamed' } });
        api.updateNote.mockResolvedValue({ data: {} }); // Mock updateNote for moving
        window.prompt = vi.fn(() => NEW_NOTE_TITLE);
        window.confirm = vi.fn(() => true);
    });

    afterEach(() => {
        window.prompt = originalPrompt;
        window.confirm = originalConfirm;
    });


    // --- Basic Rendering and Fetching Tests ---
    // ... (keep as before) ...
    it('renders loading state initially', async () => {
        api.getNoteTree.mockImplementationOnce(() => new Promise(() => {}));
        renderComponent();
        expect(screen.getByText(/Loading notes structure.../i)).toBeInTheDocument();
    });

    it('fetches project name and note tree on mount and passes data to NoteTreeViewer', async () => {
        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        await waitFor(() => {
             expect(api.getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
             expect(api.getNoteTree).toHaveBeenCalledWith(TEST_PROJECT_ID);
        });
        expect(NoteTreeViewer).toHaveBeenCalledWith(
            expect.objectContaining({ treeData: MOCK_TREE_DATA_INITIAL }),
            expect.anything()
        );
        expect(screen.getByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${MOCK_TREE_DATA_INITIAL.length}`);
        expect(screen.getByText(/📁 FolderA \(\/FolderA\)/)).toBeInTheDocument();
        expect(screen.getByText(/📁 FolderB \(\/FolderB\)/)).toBeInTheDocument();
        expect(screen.getByText(/📄 Root Note \(\/\)/)).toBeInTheDocument();
        expect(screen.getByText(/📄 Note A1 \(\/FolderA\)/)).toBeInTheDocument();
    });

     it('displays message when API returns empty tree', async () => {
        api.getNoteTree.mockResolvedValue({ data: { tree: [] } });
        renderComponent();
        expect(await screen.findByText(/No notes or folders found./i)).toBeInTheDocument();
     });

     it('displays error message if fetching tree fails', async () => {
        api.getNoteTree.mockRejectedValue(new Error('Failed to load tree'));
        renderComponent();
        expect(await screen.findByText(/Failed to load note structure. Please try again./i)).toBeInTheDocument();
    });

    // --- Create Note Tests ---
    // ... (keep as before) ...
     it('handles creating a note in the root folder via button', async () => {
        const user = userEvent.setup();
        const refreshedTree = [...MOCK_TREE_DATA_INITIAL, { ...NEW_NOTE_RESPONSE, type: 'note', name: NEW_NOTE_TITLE, path: '/', id: NEW_NOTE_RESPONSE.id, children: [] }];
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: structuredClone(MOCK_TREE_DATA_INITIAL) } })
            .mockResolvedValueOnce({ data: { tree: refreshedTree } });

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const createRootNoteButton = screen.getByTestId('create-note-root');

        await user.click(createRootNoteButton);

        expect(window.prompt).toHaveBeenCalledWith('Enter title for new note in "/":');
        await waitFor(() => {
            expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, { title: NEW_NOTE_TITLE, folder_path: "/" });
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
        expect(await screen.findByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${refreshedTree.length}`);
        expect(await screen.findByText(`📄 ${NEW_NOTE_TITLE} (/)`)).toBeInTheDocument();
    });

    // --- Create Folder Tests ---
    // ... (keep as before) ...
    it('handles creating a new folder at the root (optimistic update)', async () => {
        const user = userEvent.setup();
        const newFolderName = "Optimistic Folder";
        window.prompt = vi.fn(() => newFolderName);

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const createRootFolderButton = screen.getByTestId('create-folder-root');

        await act(async () => { await user.click(createRootFolderButton); });

        expect(window.prompt).toHaveBeenCalledWith('Enter name for new folder under "/":');
        expect(api.createNote).not.toHaveBeenCalled();
        expect(api.getNoteTree).toHaveBeenCalledTimes(1);

        await waitFor(() => {
            const lastCallArgs = NoteTreeViewer.mock.lastCall[0];
            expect(lastCallArgs.treeData).toHaveLength(MOCK_TREE_DATA_INITIAL.length + 1);
            const newFolder = lastCallArgs.treeData.find(node => node.name === newFolderName);
            expect(newFolder).toBeDefined();
            expect(newFolder.path).toBe(`/${newFolderName}`);
            expect(newFolder.id).toContain('temp-folder-');
        });
        expect(screen.getByText(`📁 ${newFolderName} (/${newFolderName})`)).toBeInTheDocument();
        expect(screen.getByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${MOCK_TREE_DATA_INITIAL.length + 1}`);
    });

     it('handles creating a new folder nested inside another (optimistic update)', async () => {
        const user = userEvent.setup();
        const parentFolder = MOCK_TREE_DATA_INITIAL[0]; // FolderA
        const newFolderName = "Nested Optimistic";
        window.prompt = vi.fn(() => newFolderName);

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const createNestedFolderButton = screen.getByTestId(`create-folder-${parentFolder.id}`);

        await act(async () => { await user.click(createNestedFolderButton); });

        expect(window.prompt).toHaveBeenCalledWith(`Enter name for new folder under "${parentFolder.path}":`);
        expect(api.createNote).not.toHaveBeenCalled();
        expect(api.getNoteTree).toHaveBeenCalledTimes(1);

        await waitFor(() => {
            const lastCallArgs = NoteTreeViewer.mock.lastCall[0];
            const updatedParent = lastCallArgs.treeData.find(node => node.id === parentFolder.id);
            expect(updatedParent.children).toHaveLength(parentFolder.children.length + 1);
            const newFolder = updatedParent.children.find(node => node.name === newFolderName);
            expect(newFolder).toBeDefined();
            expect(newFolder.path).toBe(`${parentFolder.path}/${newFolderName}`);
        });
         expect(screen.getByText(`📁 ${newFolderName} (${parentFolder.path}/${newFolderName})`)).toBeInTheDocument();
    });

    it('prevents creating folder with empty or slash-containing name', async () => {
        const user = userEvent.setup();
        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const createRootFolderButton = screen.getByTestId('create-folder-root');

        window.prompt = vi.fn(() => "  ");
        await act(async () => { await user.click(createRootFolderButton); });
        expect(await screen.findByText(/Folder name cannot be empty./i)).toBeInTheDocument();
        expect(api.getNoteTree).toHaveBeenCalledTimes(1);

        window.prompt = vi.fn(() => "invalid/name");
        await act(async () => { await user.click(createRootFolderButton); });
        expect(await screen.findByText(/Folder name cannot contain slashes./i)).toBeInTheDocument();
        expect(api.getNoteTree).toHaveBeenCalledTimes(1);
    });

     it('prevents creating folder with duplicate name at the same level', async () => {
        const user = userEvent.setup();
        const existingFolderName = MOCK_TREE_DATA_INITIAL[0].name; // "FolderA"
        window.prompt = vi.fn(() => existingFolderName);

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const createRootFolderButton = screen.getByTestId('create-folder-root');

        await act(async () => { await user.click(createRootFolderButton); });

        expect(window.prompt).toHaveBeenCalledWith('Enter name for new folder under "/":');
        expect(await screen.findByText(`A folder named "${existingFolderName}" already exists in "/".`)).toBeInTheDocument();
        expect(api.getNoteTree).toHaveBeenCalledTimes(1);
        const lastCallArgs = NoteTreeViewer.mock.lastCall[0];
        expect(lastCallArgs.treeData).toHaveLength(MOCK_TREE_DATA_INITIAL.length);
    });


    // --- Rename Folder Tests ---
    // ... (keep as before) ...
    it('handles renaming a folder successfully', async () => {
        const user = userEvent.setup();
        const folderToRename = MOCK_TREE_DATA_INITIAL[0]; // FolderA
        const oldPath = folderToRename.path;
        const oldName = folderToRename.name;
        const newName = "Renamed Folder";
        const newPath = `/${newName}`;
        window.prompt = vi.fn(() => newName);

        const renamedFolder = { ...folderToRename, name: newName, path: newPath, id: newPath };
        renamedFolder.children = renamedFolder.children.map(child => ({...child, path: newPath}));
        const refreshedTree = [renamedFolder, MOCK_TREE_DATA_INITIAL[1], MOCK_TREE_DATA_INITIAL[2]]; // Include FolderB
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: structuredClone(MOCK_TREE_DATA_INITIAL) } })
            .mockResolvedValueOnce({ data: { tree: refreshedTree } });

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const renameButton = screen.getByTestId(`rename-folder-${folderToRename.id}`);

        await act(async () => { await user.click(renameButton); });

        expect(window.prompt).toHaveBeenCalledWith(`Enter new name for folder "${oldName}":`, oldName);

        await waitFor(() => {
            expect(api.renameFolder).toHaveBeenCalledTimes(1);
            expect(api.renameFolder).toHaveBeenCalledWith(TEST_PROJECT_ID, { old_path: oldPath, new_path: newPath });
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });

        expect(await screen.findByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${refreshedTree.length}`);
        expect(screen.getByText(`📁 ${newName} (${newPath})`)).toBeInTheDocument();
        expect(screen.queryByText(`📁 ${oldName} (${oldPath})`)).not.toBeInTheDocument();
    });

    // --- Delete Note/Folder Tests ---
    // ... (keep as before) ...
    it('handles deleting a note via button', async () => {
        const user = userEvent.setup();
        const noteToDelete = MOCK_TREE_DATA_INITIAL[2]; // Root Note
        const remainingTree = [MOCK_TREE_DATA_INITIAL[0], MOCK_TREE_DATA_INITIAL[1]];
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: structuredClone(MOCK_TREE_DATA_INITIAL) } })
            .mockResolvedValueOnce({ data: { tree: remainingTree } });

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const deleteButton = screen.getByTestId(`delete-note-${noteToDelete.note_id}`);

        await user.click(deleteButton);

        expect(window.confirm).toHaveBeenCalledWith(`Are you sure you want to delete the note "${noteToDelete.name}"?`);
        await waitFor(() => {
            expect(api.deleteNote).toHaveBeenCalledWith(TEST_PROJECT_ID, noteToDelete.note_id);
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
        expect(await screen.findByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${remainingTree.length}`);
        expect(screen.queryByText(`📄 ${noteToDelete.name} (${noteToDelete.path})`)).not.toBeInTheDocument();
    });

     it('handles deleting a folder recursively via button', async () => {
        const user = userEvent.setup();
        const folderToDelete = MOCK_TREE_DATA_INITIAL[0]; // FolderA
        const remainingTree = [MOCK_TREE_DATA_INITIAL[1], MOCK_TREE_DATA_INITIAL[2]]; // FolderB and Root Note remain
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: structuredClone(MOCK_TREE_DATA_INITIAL) } })
            .mockResolvedValueOnce({ data: { tree: remainingTree } });

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const deleteButton = screen.getByTestId(`delete-folder-${folderToDelete.id}`);

        await user.click(deleteButton);

        expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining(`Delete folder "${folderToDelete.path}"?`));
        await waitFor(() => {
            expect(api.deleteFolder).toHaveBeenCalledWith(TEST_PROJECT_ID, { path: folderToDelete.path, recursive: true });
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
        expect(await screen.findByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${remainingTree.length}`);
        expect(screen.queryByText(`📁 ${folderToDelete.name} (${folderToDelete.path})`)).not.toBeInTheDocument();
    });

    // --- Move Note Tests (NEW) ---
    it('handles moving a note successfully', async () => {
        const user = userEvent.setup();
        const noteToMove = MOCK_TREE_DATA_INITIAL[0].children[0]; // Note A1 in FolderA
        const targetFolder = MOCK_TREE_DATA_INITIAL[1]; // FolderB
        const targetPath = targetFolder.path; // "/FolderB"
        window.prompt = vi.fn(() => targetPath); // Mock prompt to return target path

        // Mock the tree refresh call to show the moved note
        const movedNote = { ...noteToMove, path: targetPath };
        const updatedFolderA = { ...MOCK_TREE_DATA_INITIAL[0], children: [] }; // FolderA is now empty
        const updatedFolderB = { ...targetFolder, children: [movedNote] }; // FolderB now contains the note
        const refreshedTree = [updatedFolderA, updatedFolderB, MOCK_TREE_DATA_INITIAL[2]]; // FolderA, FolderB, Root Note
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: structuredClone(MOCK_TREE_DATA_INITIAL) } }) // Initial load
            .mockResolvedValueOnce({ data: { tree: refreshedTree } }); // After move

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();

        // Find the move button within the mock viewer's rendering
        const moveButton = screen.getByTestId(`move-note-${noteToMove.note_id}`);

        // Wrap state update in act
        await act(async () => {
            await user.click(moveButton);
        });

        // Verify prompt shows current path and available folders
        expect(window.prompt).toHaveBeenCalledWith(
            expect.stringContaining(`Current path: ${noteToMove.path}`), // Check current path shown
            noteToMove.path // Check default value
        );
        expect(window.prompt).toHaveBeenCalledWith(
            expect.stringContaining(`Available folders:\n/\n/FolderA\n/FolderB`), // Check available folders listed
            noteToMove.path
        );


        // Verify API call (updateNote with only folder_path) and tree refresh
        await waitFor(() => {
            expect(api.updateNote).toHaveBeenCalledTimes(1);
            expect(api.updateNote).toHaveBeenCalledWith(
                TEST_PROJECT_ID,
                noteToMove.note_id,
                { folder_path: targetPath } // Only send folder_path
            );
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial load + refresh
        });

        // Verify the mock viewer received updated data
        expect(await screen.findByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${refreshedTree.length}`);
        // Check the note is now rendered with the new path (within the mock's rendering)
        expect(screen.getByText(`📄 ${noteToMove.name} (${targetPath})`)).toBeInTheDocument();
        // Check it's gone from the old path rendering
        expect(screen.queryByText(`📄 ${noteToMove.name} (${noteToMove.path})`)).not.toBeInTheDocument();
    });

     it('prevents moving note if prompt cancelled, empty, or same path', async () => {
        const user = userEvent.setup();
        const noteToMove = MOCK_TREE_DATA_INITIAL[0].children[0]; // Note A1
        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const moveButton = screen.getByTestId(`move-note-${noteToMove.note_id}`);

        // Test cancellation
        window.prompt = vi.fn(() => null);
        await act(async () => { await user.click(moveButton); });
        expect(api.updateNote).not.toHaveBeenCalled();
        expect(screen.queryByText(/Invalid target folder path/i)).not.toBeInTheDocument();

        // Test empty path
        window.prompt = vi.fn(() => "  ");
        await act(async () => { await user.click(moveButton); });
        expect(api.updateNote).not.toHaveBeenCalled();
        // Prompt returns empty string which is != current path, so no error shown, just returns

        // Test same path
        window.prompt = vi.fn(() => noteToMove.path); // Return same path
        await act(async () => { await user.click(moveButton); });
        expect(api.updateNote).not.toHaveBeenCalled();

        expect(api.getNoteTree).toHaveBeenCalledTimes(1); // No refresh occurred
    });

     it('prevents moving note with invalid path', async () => {
        const user = userEvent.setup();
        const noteToMove = MOCK_TREE_DATA_INITIAL[0].children[0]; // Note A1
        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const moveButton = screen.getByTestId(`move-note-${noteToMove.note_id}`);

        // Test no leading slash
        window.prompt = vi.fn(() => "no-slash");
        await act(async () => { await user.click(moveButton); });
        expect(await screen.findByText(/Target path must start with \//i)).toBeInTheDocument();
        expect(api.updateNote).not.toHaveBeenCalled();

         // Test double slash
        window.prompt = vi.fn(() => "/double//slash");
        await act(async () => { await user.click(moveButton); });
        expect(await screen.findByText(/Target path cannot contain \/\//i)).toBeInTheDocument();
        expect(api.updateNote).not.toHaveBeenCalled();

        expect(api.getNoteTree).toHaveBeenCalledTimes(1); // No refresh occurred
    });


    // --- Busy State Test ---
    // ... (keep as before, maybe update to use move action) ...
    it('passes isBusy=true to NoteTreeViewer during API calls', async () => {
        const user = userEvent.setup();
        let resolveInitialGetTree;
        let resolveUpdateNote; // Use updateNote for move test
        api.getNoteTree.mockImplementationOnce(() => new Promise(res => { resolveInitialGetTree = res; }));
        api.updateNote.mockImplementationOnce(() => new Promise(res => { resolveUpdateNote = res; })); // Mock move to hang

        renderComponent();
        expect(screen.getByText(/Loading notes structure.../i)).toBeInTheDocument();

        await act(async () => { resolveInitialGetTree({ data: { tree: structuredClone(MOCK_TREE_DATA_INITIAL) } }); });
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        expect(screen.getByTestId('is-busy-prop')).toHaveTextContent('Is Busy: false');

        const noteToMove = MOCK_TREE_DATA_INITIAL[0].children[0]; // Note A1
        const moveButton = screen.getByTestId(`move-note-${noteToMove.note_id}`);
        window.prompt = vi.fn(() => "/FolderB"); // Ensure prompt returns valid target

        // Wrap the click and subsequent state update in act
        await act(async () => {
            await user.click(moveButton);
        });

        // Now check the busy state *after* the click has been processed
        expect(screen.getByTestId('is-busy-prop')).toHaveTextContent('Is Busy: true');

        // Mock the refresh call after move resolves
        api.getNoteTree.mockResolvedValueOnce({ data: { tree: [ MOCK_TREE_DATA_INITIAL[1] ] } }); // Dummy refreshed data

        // Resolve move
        await act(async () => {
            resolveUpdateNote({ data: { message: 'moved' } }); // Simulate API success
        });

        // Not busy after move and refresh completes
        await waitFor(() => {
            expect(api.getNoteTree).toHaveBeenCalledTimes(2);
            expect(screen.getByTestId('is-busy-prop')).toHaveTextContent('Is Busy: false');
        });
    });

});