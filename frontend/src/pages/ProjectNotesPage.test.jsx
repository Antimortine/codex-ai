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
import { vi, describe, it, expect, beforeEach } from 'vitest';

import ProjectNotesPage from './ProjectNotesPage';
import * as api from '../api/codexApi';

// --- Mocks ---
// Mock the API module
vi.mock('../api/codexApi');

// Mock the NoteTreeViewer component
vi.mock('../components/NoteTreeViewer', () => ({
  // Use default export because the component is likely exported as default
  default: vi.fn(({ projectId, treeData, handlers, isBusy }) => {
    // Conditional rendering for empty tree
    if (!treeData || treeData.length === 0) {
      return <div data-testid="mock-note-tree-viewer">No notes or folders found.</div>;
    }
    // Render tree if not empty
    return (
        <div data-testid="mock-note-tree-viewer">
            <p>Project ID: {projectId}</p>
            <p data-testid="is-busy-prop">Is Busy: {String(isBusy)}</p>
            {/* Render basic info about the tree */}
            <p data-testid="tree-node-count">Tree Nodes: {treeData.length}</p>
            {treeData.map(node => (
                <div key={node.id} data-testid={`node-${node.id}`}>
                <span>{node.type === 'folder' ? '📁' : '📄'} {node.name} ({node.path})</span>
                {/* Add buttons to trigger handlers */}
                {node.type === 'folder' && (
                    <button onClick={() => handlers.onCreateNote(node.path)} disabled={isBusy}>+ Note in {node.name}</button>
                )}
                {node.type === 'folder' && node.path !== '/' && (
                    <button data-testid={`delete-folder-${node.id}`} onClick={() => handlers.onDeleteFolder(node.path)} disabled={isBusy}>Delete Folder {node.name}</button>
                )}
                {node.type === 'note' && (
                    <button data-testid={`delete-note-${node.note_id}`} onClick={() => handlers.onDeleteNote(node.note_id, node.name)} disabled={isBusy}>Delete Note {node.name}</button>
                )}
                {/* Render children recursively for testing nested scenarios if needed */}
                {node.children && node.children.length > 0 && (
                     <div style={{ marginLeft: '20px' }}>
                         {node.children.map(child => (
                             <div key={child.id} data-testid={`node-${child.id}`}>
                                 <span>{child.type === 'folder' ? '📁' : '📄'} {child.name} ({child.path})</span>
                                  {/* Add buttons for children if needed for tests */}
                                  {child.type === 'note' && (
                                     <button data-testid={`delete-note-${child.note_id}`} onClick={() => handlers.onDeleteNote(child.note_id, child.name)} disabled={isBusy}>Delete Note {child.name}</button>
                                  )}
                             </div>
                         ))}
                     </div>
                 )}
                </div>
            ))}
            {/* Add a root create button */}
            <button onClick={() => handlers.onCreateNote('/')} disabled={isBusy}>+ Note in Root</button>
            {/* Add a root create folder button */}
            <button onClick={() => handlers.onCreateFolder('/')} disabled={isBusy}>+ Folder in Root</button>
        </div>
    );
  }),
}));

// Mock NoteTreeViewer component import after vi.mock
import NoteTreeViewer from '../components/NoteTreeViewer';


// --- Test Data ---
const TEST_PROJECT_ID = 'proj-notes-tree-123';
const MOCK_PROJECT = { id: TEST_PROJECT_ID, name: 'Notes Tree Test Project' };
// Define MOCK_TREE_DATA with nested structure for better testing
const MOCK_TREE_DATA = [
    { id: '/FolderA', name: 'FolderA', type: 'folder', path: '/FolderA', children: [
        { id: 'note-a1', name: 'Note A1', type: 'note', path: '/FolderA', note_id: 'note-a1', last_modified: Date.now()/1000 - 100, children: [] }
    ]},
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
                {/* Keep the NoteEditPage route for Link testing if needed */}
                <Route path="/projects/:projectId/notes/:noteId" element={<div>Note Edit Page Mock</div>} />
            </Routes>
        </MemoryRouter>
    );
};

describe('ProjectNotesPage (Tree View)', () => {
    beforeEach(() => {
        vi.resetAllMocks();
        // Setup default successful mocks
        api.getProject.mockResolvedValue({ data: MOCK_PROJECT });
        api.getNoteTree.mockResolvedValue({ data: { tree: [...MOCK_TREE_DATA] } });
        api.createNote.mockResolvedValue({ data: NEW_NOTE_RESPONSE });
        api.deleteNote.mockResolvedValue({ data: { message: 'Note deleted' } });
        api.deleteFolder.mockResolvedValue({ data: { message: 'Folder deleted' } });
        // Mock window.prompt and window.confirm
        window.prompt = vi.fn(() => NEW_NOTE_TITLE); // Default prompt returns a title
        window.confirm = vi.fn(() => true); // Default confirm returns true
    });

    // --- Basic Rendering and Fetching Tests ---
    it('renders loading state initially', async () => {
        api.getNoteTree.mockImplementation(() => new Promise(() => {})); // Make it hang
        renderComponent();
        expect(screen.getByText(/Loading notes structure.../i)).toBeInTheDocument();
        // Clean up hanging promise after test if necessary, though not strictly required here
        // as the test finishes before resolution matters.
    });

    it('fetches project name and note tree on mount and passes data to NoteTreeViewer', async () => {
        renderComponent();
        expect(await screen.findByRole('heading', { name: /Project Notes/i })).toBeInTheDocument();
        expect(screen.getByText(`For "${MOCK_PROJECT.name}"`)).toBeInTheDocument();

        // Wait for the mock tree viewer to render with data
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();

        // Verify API calls
        await waitFor(() => {
             expect(api.getProject).toHaveBeenCalledWith(TEST_PROJECT_ID);
             expect(api.getNoteTree).toHaveBeenCalledWith(TEST_PROJECT_ID);
        });

        // Verify props passed to the mocked NoteTreeViewer
        expect(NoteTreeViewer).toHaveBeenCalledWith(
            expect.objectContaining({
                projectId: TEST_PROJECT_ID,
                treeData: MOCK_TREE_DATA,
                isBusy: false,
                handlers: expect.any(Object), // Check handlers exist
            }),
            expect.anything() // Context argument
        );

        // Check some content rendered by the mock viewer based on passed data
        expect(screen.getByText(`Project ID: ${TEST_PROJECT_ID}`)).toBeInTheDocument();
        // Use test-id for node count check
        expect(screen.getByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${MOCK_TREE_DATA.length}`);
        expect(screen.getByText(/📁 FolderA \(\/FolderA\)/)).toBeInTheDocument();
        expect(screen.getByText(/📄 Root Note \(\/\)/)).toBeInTheDocument();
        // Check nested node rendered by mock
        expect(screen.getByText(/📄 Note A1 \(\/FolderA\)/)).toBeInTheDocument();
    });

     it('displays message when API returns empty tree', async () => {
        api.getNoteTree.mockResolvedValue({ data: { tree: [] } });
        renderComponent();
        expect(await screen.findByRole('heading', { name: /Project Notes/i })).toBeInTheDocument();
        // Wait for loading to finish
        await waitFor(() => expect(screen.queryByText(/Loading notes structure.../i)).not.toBeInTheDocument());
        // Check the message rendered by the *mock* NoteTreeViewer when treeData is empty
        // This relies on the mock's conditional rendering logic.
        expect(await screen.findByText(/No notes or folders found./i)).toBeInTheDocument();
     });

     it('displays error message if fetching tree fails', async () => {
        const errorMsg = 'Failed to load tree';
        api.getNoteTree.mockRejectedValue(new Error(errorMsg));
        renderComponent();
        expect(await screen.findByRole('heading', { name: /Project Notes/i })).toBeInTheDocument();
        expect(await screen.findByText(/Failed to load note structure. Please try again./i)).toBeInTheDocument();
    });

    // --- Create Note Tests ---
    it('handles creating a note in the root folder via button', async () => {
        const user = userEvent.setup();
        // Mock the tree refresh call
        const refreshedTree = [...MOCK_TREE_DATA, { ...NEW_NOTE_RESPONSE, type: 'note', name: NEW_NOTE_TITLE, path: '/', id: NEW_NOTE_RESPONSE.id, children: [] }];
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: [...MOCK_TREE_DATA] } }) // Initial load
            .mockResolvedValueOnce({ data: { tree: refreshedTree } }); // After create

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();

        // Find the button rendered by the mock viewer to trigger the handler
        const createRootNoteButton = screen.getByRole('button', { name: /\+ Note in Root/i });

        await user.click(createRootNoteButton);

        // Verify prompt was called (implicitly via the handler)
        expect(window.prompt).toHaveBeenCalledWith('Enter title for new note in "/":');

        // Verify API call and tree refresh
        await waitFor(() => {
            expect(api.createNote).toHaveBeenCalledTimes(1);
            expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, { title: NEW_NOTE_TITLE, folder_path: "/" });
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial load + refresh
        });

        // Verify the mock viewer received updated data (implicitly checks state update)
        // Use findByTestId to wait for the updated count
        expect(await screen.findByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${refreshedTree.length}`);
        // Use findByText to wait for the new node text
        expect(await screen.findByText(`📄 ${NEW_NOTE_TITLE} (/)`)).toBeInTheDocument();
    });

    it('handles creating a note in a specific folder via button', async () => {
        const user = userEvent.setup();
        const targetFolder = MOCK_TREE_DATA[0]; // FolderA
        const targetPath = targetFolder.path;
        const specificNoteTitle = "Note In Folder";
        window.prompt = vi.fn(() => specificNoteTitle); // Specific title for this test

        // Mock the tree refresh call
        const newNoteInFolder = { id: 'new-in-folder', name: specificNoteTitle, type: 'note', path: targetPath, note_id: 'new-in-folder', last_modified: Date.now()/1000, children: [] };
        const updatedFolderA = {
            ...targetFolder,
            children: [ ...targetFolder.children, newNoteInFolder ]
        };
        const refreshedTree = [updatedFolderA, MOCK_TREE_DATA[1]];
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: [...MOCK_TREE_DATA] } }) // Initial load
            .mockResolvedValueOnce({ data: { tree: refreshedTree } }); // After create

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();

        // Find the button rendered by the mock viewer for FolderA
        const createNoteInFolderAButton = screen.getByRole('button', { name: `+ Note in ${targetFolder.name}` });

        await user.click(createNoteInFolderAButton);

        expect(window.prompt).toHaveBeenCalledWith(`Enter title for new note in "${targetPath}":`);

        await waitFor(() => {
            expect(api.createNote).toHaveBeenCalledTimes(1);
            expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, { title: specificNoteTitle, folder_path: targetPath });
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
         // Verify the mock viewer received updated data and the new node is rendered
        expect(await screen.findByText(`📄 ${specificNoteTitle} (${targetPath})`)).toBeInTheDocument();
        // Also check the node count updated
        expect(screen.getByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${refreshedTree.length}`);
    });

    it('does not create note if prompt is cancelled or empty', async () => {
        const user = userEvent.setup();
        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        const createRootNoteButton = screen.getByRole('button', { name: /\+ Note in Root/i });

        // Test cancellation
        window.prompt = vi.fn(() => null);
        await user.click(createRootNoteButton);
        expect(api.createNote).not.toHaveBeenCalled();
        expect(screen.queryByText(/Note title cannot be empty./i)).not.toBeInTheDocument(); // No error on cancel

        // Test empty title
        window.prompt = vi.fn(() => "   ");
        await user.click(createRootNoteButton);
        expect(api.createNote).not.toHaveBeenCalled();
        expect(screen.getByText(/Note title cannot be empty./i)).toBeInTheDocument(); // Error shown

        expect(api.getNoteTree).toHaveBeenCalledTimes(1); // No refresh occurred
    });

    // --- Delete Note Tests ---
    it('handles deleting a note via button', async () => {
        const user = userEvent.setup();
        const noteToDelete = MOCK_TREE_DATA[1]; // Root Note
        const remainingTree = [MOCK_TREE_DATA[0]]; // Only FolderA remains
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: [...MOCK_TREE_DATA] } }) // Initial load
            .mockResolvedValueOnce({ data: { tree: remainingTree } }); // After delete

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();

        // Find the delete button for the specific note within the mock viewer
        const deleteButton = screen.getByTestId(`delete-note-${noteToDelete.note_id}`);

        await user.click(deleteButton);

        expect(window.confirm).toHaveBeenCalledWith(`Are you sure you want to delete the note "${noteToDelete.name}"?`);

        await waitFor(() => {
            expect(api.deleteNote).toHaveBeenCalledTimes(1);
            expect(api.deleteNote).toHaveBeenCalledWith(TEST_PROJECT_ID, noteToDelete.note_id);
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial load + refresh
        });
        // Verify the mock viewer received updated data
        expect(await screen.findByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${remainingTree.length}`);
        expect(screen.queryByText(`📄 ${noteToDelete.name} (${noteToDelete.path})`)).not.toBeInTheDocument();
    });

    // --- Delete Folder Tests ---
     it('handles deleting a folder recursively via button', async () => {
        const user = userEvent.setup();
        const folderToDelete = MOCK_TREE_DATA[0]; // FolderA
        const remainingTree = [MOCK_TREE_DATA[1]]; // Only Root Note remains
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: [...MOCK_TREE_DATA] } }) // Initial load
            .mockResolvedValueOnce({ data: { tree: remainingTree } }); // After delete

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();

        // Find the delete button for the specific folder within the mock viewer
        const deleteButton = screen.getByTestId(`delete-folder-${folderToDelete.id}`);

        await user.click(deleteButton);

        // Check the specific confirmation message used in the handler
        expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining(`Delete folder "${folderToDelete.path}"?`));
        expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining(`permanently delete all notes and subfolders`));


        await waitFor(() => {
            expect(api.deleteFolder).toHaveBeenCalledTimes(1);
            // Verify it was called recursively
            expect(api.deleteFolder).toHaveBeenCalledWith(TEST_PROJECT_ID, { path: folderToDelete.path, recursive: true });
        });
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial load + refresh
        });
        // Verify the mock viewer received updated data
        expect(await screen.findByTestId('tree-node-count')).toHaveTextContent(`Tree Nodes: ${remainingTree.length}`);
        expect(screen.queryByText(`📁 ${folderToDelete.name} (${folderToDelete.path})`)).not.toBeInTheDocument();
    });

    // --- Busy State Tests ---
    it('passes isBusy=true to NoteTreeViewer during API calls', async () => {
        const user = userEvent.setup();
        let resolveInitialGetTree;
        let resolveDeleteFolder;

        // Make initial load hang
        api.getNoteTree.mockImplementationOnce(() => new Promise(res => { resolveInitialGetTree = res; }));
        // Make delete hang
        api.deleteFolder.mockImplementationOnce(() => new Promise(res => { resolveDeleteFolder = res; }));

        renderComponent();

        // 1. Check for loading text initially, NoteTreeViewer not rendered yet
        expect(screen.getByText(/Loading notes structure.../i)).toBeInTheDocument();
        expect(screen.queryByTestId('mock-note-tree-viewer')).not.toBeInTheDocument();

        // Resolve initial load
        await act(async () => {
            resolveInitialGetTree({ data: { tree: [...MOCK_TREE_DATA] } });
        });

        // 2. Not busy after load, TreeViewer is rendered
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        expect(screen.queryByText(/Loading notes structure.../i)).not.toBeInTheDocument();
        expect(screen.getByTestId('is-busy-prop')).toHaveTextContent('Is Busy: false');


        // Trigger delete folder
        const folderToDelete = MOCK_TREE_DATA[0];
        const deleteButton = screen.getByTestId(`delete-folder-${folderToDelete.id}`);
        // Need act because clicking updates state (isProcessing)
        await act(async () => {
             await user.click(deleteButton);
        });


        // 3. Busy during delete
        // Use findByTestId to wait for the prop update
        expect(await screen.findByTestId('is-busy-prop')).toHaveTextContent('Is Busy: true');

         // Mock the refresh call after delete resolves
         api.getNoteTree.mockResolvedValueOnce({ data: { tree: [MOCK_TREE_DATA[1]] } }); // After delete

        // Resolve delete
        await act(async () => {
            resolveDeleteFolder({ data: { message: 'deleted' } });
        });

        // 4. Not busy after delete and refresh completes
        await waitFor(() => {
            // Check refresh call happened
            expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial + refresh
            // Check busy state is false again
            expect(screen.getByTestId('is-busy-prop')).toHaveTextContent('Is Busy: false');
        });
    });

     // --- Placeholder Handler Test ---
     it('calls placeholder alert for create folder', async () => {
        const user = userEvent.setup();
        window.alert = vi.fn(); // Mock alert

        renderComponent();
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();

        // Button rendered by the mock viewer
        const createRootFolderButton = screen.getByRole('button', { name: /\+ Folder in Root/i });
        await user.click(createRootFolderButton);

        expect(window.alert).toHaveBeenCalledWith('Placeholder: Create folder under "/"');
        expect(api.createNote).not.toHaveBeenCalled(); // Ensure wrong API wasn't called
        window.alert.mockRestore(); // Clean up mock
     });

});