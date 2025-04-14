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
import { render, screen, waitFor, act, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import * as ReactRouterDom from 'react-router-dom';
import { vi, describe, it, expect, beforeEach, afterEach } from 'vitest';

import ProjectNotesPage from './ProjectNotesPage';
import * as api from '../api/codexApi';

// --- Mocks ---
vi.mock('../api/codexApi');
vi.mock('uuid', () => ({ v4: vi.fn(() => 'mock-temp-uuid-123') }));

// Create a properly scoped mock for react-router-dom
vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom');
  return {
    ...actual,
    useParams: vi.fn().mockReturnValue({ projectId: 'test-project-id' })
  };
});

let mockTreeViewerHandlers = {};
// --- Fix NoteTreeViewer Mock Export ---
vi.mock('../components/NoteTreeViewer', () => ({
  // Provide the mock function as the default export
  default: vi.fn(({ projectId, treeData, handlers, isBusy }) => {
    mockTreeViewerHandlers = handlers;
    if (!treeData || treeData.length === 0) {
      return <div data-testid="mock-note-tree-viewer">No notes or folders found.</div>;
    }
    const renderMockNode = (node) => {
        // Create testId based on node type (folder or note)
        const nodeId = node.type === 'folder' ? node.id : node.note_id;
        const testId = `node-${nodeId}`;
        
        return (
            <div key={nodeId} data-testid={testId}>
                <span>{node.type === 'folder' ? '📁' : '📄'} {node.name} ({node.path})</span>
                {node.type === 'folder' && (
                    <>
                        <button data-testid={`create-folder-${nodeId}`} onClick={() => handlers.onCreateFolder(node.path)} disabled={isBusy}>+ Folder</button>
                        <button data-testid={`create-note-${nodeId}`} onClick={() => handlers.onCreateNote(node.path)} disabled={isBusy}>+ Note</button>
                        {node.path !== '/' && (
                             <button data-testid={`rename-folder-${nodeId}`} onClick={() => handlers.onRenameFolder(node.path, node.name)} disabled={isBusy}>Rename</button>
                        )}
                        {node.path !== '/' && (
                            <button data-testid={`delete-folder-${nodeId}`} onClick={() => handlers.onDeleteFolder(node.path)} disabled={isBusy}>Delete Folder</button>
                        )}
                    </>
                )}
                {node.type === 'note' && (
                     <>
                        <button data-testid={`move-note-${nodeId}`} onClick={() => handlers.onMoveNote(nodeId, node.folder_path)} disabled={isBusy}>Move</button>
                        <button data-testid={`delete-note-${nodeId}`} onClick={() => handlers.onDeleteNote(nodeId, node.name)} disabled={isBusy}>Delete Note</button>
                     </>
                )}
                {node.children && node.children.length > 0 && (
                    <div style={{ marginLeft: '20px' }}>{node.children.map(renderMockNode)}</div>
                )}
            </div>
        );
    };
    return (
        <div data-testid="mock-note-tree-viewer">
            <p data-testid="tree-node-count">Nodes: {treeData?.length ?? 0}</p>
            {treeData?.map(renderMockNode)}
            <button data-testid="create-note-root" onClick={() => handlers.onCreateNote('/')} disabled={isBusy}>+ Note Root</button>
            <button data-testid="create-folder-root" onClick={() => handlers.onCreateFolder('/')} disabled={isBusy}>+ Folder Root</button>
            <span data-testid="is-busy-prop" style={{ display: 'none' }}>{String(isBusy)}</span>
        </div>
    );
  }),
}));

vi.mock('../components/Modal', () => ({
    default: vi.fn(({ title, onClose, children }) => {
        return (
            <div data-testid="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()} aria-modal="true" role="dialog">
                <div data-testid="mock-modal">
                    <h2 data-testid="modal-title">{title}</h2>
                    <button data-testid="modal-close-button" onClick={onClose} aria-label="Close">&times;</button>
                    <div data-testid="modal-content">{children}</div>
                </div>
            </div>
        );
    }),
}));


import NoteTreeViewer from '../components/NoteTreeViewer';
import Modal from '../components/Modal';

// --- Test Data ---
describe('ProjectNotesPage (Modal Flow)', () => {
    const TEST_PROJECT_ID = 'proj-notes-modal-123';
    const MOCK_PROJECT = { id: TEST_PROJECT_ID, name: 'Notes Modal Test Project' };
    const MOCK_TREE_DATA_TEMPLATE = [
        {
            id: 'folder-1',
            type: 'folder',
            name: 'Documents',
            path: '/Documents',
            children: [
                {
                    note_id: 'note-1',
                    type: 'note',
                    name: 'Meeting Notes',
                    path: '/Documents/Meeting Notes',
                    folder_path: '/Documents'
                }
            ]
        },
        {
            id: 'folder-2',
            type: 'folder',
            name: 'Projects',
            path: '/Projects',
            children: []
        },
        {
            note_id: 'note-2',
            type: 'note',
            name: 'Root Note',
            path: '/Root Note',
            folder_path: '/'
        }
    ];
    
    const NEW_NOTE_TITLE = 'New Test Note';
    const NEW_FOLDER_NAME = 'New Test Folder';

    // --- Test Setup ---
    const renderComponent = (projectId = TEST_PROJECT_ID) => {
        return render(
            <MemoryRouter initialEntries={[`/projects/${projectId}/notes`]}>
                <Routes>
                    <Route path="/projects/:projectId/notes" element={<ProjectNotesPage />} />
                </Routes>
            </MemoryRouter>
        );
    };
    const originalConfirm = window.confirm;
    // Removed promptMock definition as it's not used

    beforeEach(() => {
        vi.resetAllMocks();
        // Set the mock return value for useParams
        ReactRouterDom.useParams.mockReturnValue({ projectId: TEST_PROJECT_ID });
        const currentMockTreeData = JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE));
        api.getProject.mockResolvedValue({ data: MOCK_PROJECT });
        api.getNoteTree.mockResolvedValue({ data: { tree: currentMockTreeData } });
        api.createNote.mockResolvedValue({ data: { id: 'new-note-id' } });
        api.updateNote.mockResolvedValue({ data: { success: true } });
        api.renameFolder.mockResolvedValue({ data: { success: true } });
        api.deleteNote.mockResolvedValue({ data: { success: true } });
        api.deleteFolder.mockResolvedValue({ data: { success: true } });
        window.confirm = vi.fn(() => true);
        mockTreeViewerHandlers = {};
    });

    afterEach(() => {
        window.confirm = originalConfirm;
    });


    // --- Tests ---
    // ... (rest of tests remain the same) ...
    it('renders loading state initially and does not show modal', async () => {
        api.getNoteTree.mockImplementationOnce(() => new Promise(() => {}));
        renderComponent(TEST_PROJECT_ID);
        expect(screen.getByText(/Loading notes structure.../i)).toBeInTheDocument();
        expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
    });

    it('fetches data and renders tree viewer without modal open', async () => {
        renderComponent(TEST_PROJECT_ID);
        expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
        await waitFor(() => {
             expect(api.getNoteTree).toHaveBeenCalledWith(TEST_PROJECT_ID);
        });
        expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        // Use a more reliable way to check for the rendered node
        const nodeElement = await screen.findByTestId(`node-${MOCK_TREE_DATA_TEMPLATE[0].id}`);
        expect(nodeElement).toBeInTheDocument();
        expect(nodeElement).toHaveTextContent(MOCK_TREE_DATA_TEMPLATE[0].name);
    });

     it('passes correct handlers to NoteTreeViewer', async () => {
         renderComponent(TEST_PROJECT_ID);
         expect(await screen.findByTestId('mock-note-tree-viewer')).toBeInTheDocument();
         await waitFor(() => {
             expect(NoteTreeViewer).toHaveBeenCalled();
             const lastCallArgs = NoteTreeViewer.mock.lastCall[0];
             expect(lastCallArgs.handlers).toBeDefined();
             expect(lastCallArgs.handlers.onCreateNote).toBeDefined();
             expect(lastCallArgs.handlers.onCreateFolder).toBeDefined();
             expect(lastCallArgs.handlers.onRenameFolder).toBeDefined();
             expect(lastCallArgs.handlers.onMoveNote).toBeDefined();
         });
     });

     it('opens create note modal via root button and handles submission', async () => {
        const user = userEvent.setup();
        
        // Mock API responses
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } })
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } });
            
        api.createNote.mockResolvedValue({
            data: { id: 'new-note-id', title: NEW_NOTE_TITLE, folder_path: '/' }
        });

        renderComponent(TEST_PROJECT_ID);
        await screen.findByTestId('mock-note-tree-viewer');
        
        // The actual UI has buttons with specific names
        const createRootNoteButton = screen.getByRole('button', { name: '+ New Note (Root)' });
        await user.click(createRootNoteButton);

        // Check for modal and its contents
        const modalOverlay = await screen.findByTestId('modal-overlay');
        const modal = within(modalOverlay).getByTestId('mock-modal');
        expect(within(modal).getByTestId('modal-title')).toHaveTextContent('Create New Note');
        
        // Get input and save button from modal content
        const modalContent = within(modal).getByTestId('modal-content');
        const input = within(modalContent).getByRole('textbox');
        const saveButton = within(modalContent).getByRole('button', { name: 'Create' });

        // Enter title and submit
        await user.type(input, NEW_NOTE_TITLE);
        await user.click(saveButton);

        // Verify proper API call
        await waitFor(() => {
            expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, expect.objectContaining({
                title: NEW_NOTE_TITLE,
                folder_path: "/"
            }));
        });
        
        // Verify the tree was refreshed
        await waitFor(() => {
            expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
        
        // Modal should be closed after successful submission
        await waitFor(() => {
            expect(screen.queryByTestId('modal-overlay')).not.toBeInTheDocument();
        });
    });

    // --- Modal Opening Tests ---
    it('opens create note modal via root button', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Click the "+ New Note (Root)" button
        const createNoteButton = screen.getByText('+ New Note (Root)');
        await user.click(createNoteButton);
        
        // Verify modal is open with correct title
        const modal = screen.getByTestId('mock-modal');
        expect(modal).toBeInTheDocument();
        expect(screen.getByTestId('modal-title')).toHaveTextContent('Create New Note');
        
        // Verify modal content contains expected elements
        const modalContent = screen.getByTestId('modal-content');
        expect(within(modalContent).getByText('Enter a name for the new note:')).toBeInTheDocument();
        expect(within(modalContent).getByRole('textbox')).toBeInTheDocument();
        expect(within(modalContent).getByRole('button', { name: 'Create' })).toBeInTheDocument();
        expect(within(modalContent).getByRole('button', { name: 'Cancel' })).toBeInTheDocument();
    });
    
    it('opens create note modal via folder button in tree viewer', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find and click the create note button for a specific folder
        const folderNode = await screen.findByTestId('node-folder-1');
        const createNoteButton = within(folderNode).getByTestId('create-note-folder-1');
        await user.click(createNoteButton);
        
        // Verify modal is open with correct title
        expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
        expect(screen.getByTestId('modal-title')).toHaveTextContent('Create New Note');
    });
    
    it('opens create folder modal via root button', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Click the "+ New Folder (Root)" button
        const createFolderButton = screen.getByText('+ New Folder (Root)');
        await user.click(createFolderButton);
        
        // Verify modal is open with correct title
        const modal = screen.getByTestId('mock-modal');
        expect(modal).toBeInTheDocument();
        expect(screen.getByTestId('modal-title')).toHaveTextContent('Create New Folder');
        
        // Verify modal content contains expected elements
        const modalContent = screen.getByTestId('modal-content');
        expect(within(modalContent).getByText('Enter a name for the new folder:')).toBeInTheDocument();
        expect(within(modalContent).getByRole('textbox')).toBeInTheDocument();
        expect(within(modalContent).getByRole('button', { name: 'Create' })).toBeInTheDocument();
    });
    
    it('opens create folder modal via tree viewer button', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find and click the create folder button for a specific folder
        const folderNode = await screen.findByTestId('node-folder-1');
        const createFolderButton = within(folderNode).getByTestId('create-folder-folder-1');
        await user.click(createFolderButton);
        
        // Verify modal is open with correct title
        expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
        expect(screen.getByTestId('modal-title')).toHaveTextContent('Create New Folder');
    });
    
    it('opens rename folder modal via tree viewer button', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find and click the rename folder button
        const folderNode = await screen.findByTestId('node-folder-1');
        const renameFolderButton = within(folderNode).getByTestId('rename-folder-folder-1');
        await user.click(renameFolderButton);
        
        // Verify modal is open with correct title
        expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
        expect(screen.getByTestId('modal-title')).toHaveTextContent('Rename Folder');
        
        // Verify initial value in input is the current folder name
        const modalContent = screen.getByTestId('modal-content');
        const input = within(modalContent).getByRole('textbox');
        expect(input).toHaveValue('Documents'); // The name of folder-1
    });
    
    it('opens move note modal via tree viewer button', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find and click the move note button
        const noteNode = await screen.findByTestId('node-note-1');
        const moveNoteButton = within(noteNode).getByTestId('move-note-note-1');
        await user.click(moveNoteButton);
        
        // Verify modal is open with correct title
        expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
        expect(screen.getByTestId('modal-title')).toHaveTextContent('Move Note');
        
        // Verify dropdown contains folder options
        const modalContent = screen.getByTestId('modal-content');
        const select = within(modalContent).getByRole('combobox');
        expect(select).toBeInTheDocument();
        expect(within(select).getAllByRole('option').length).toBeGreaterThanOrEqual(3); // Root, Documents, Projects
    });
    
    // --- Create Note Modal Tests ---
    it('creates note via modal with valid input', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Open create note modal
        await user.click(screen.getByText('+ New Note (Root)'));
        
        // Type a note title and submit
        const modalContent = screen.getByTestId('modal-content');
        await user.type(within(modalContent).getByRole('textbox'), NEW_NOTE_TITLE);
        await user.click(within(modalContent).getByRole('button', { name: 'Create' }));
        
        // Verify API was called with correct params
        expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, expect.objectContaining({
            title: NEW_NOTE_TITLE,
            folder_path: '/'
        }));
        
        // Verify modal is closed after successful submission
        await waitFor(() => {
            expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        });
        
        // Verify note tree was refreshed
        expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial load + after creation
    });
    
    it('shows error for empty note title and prevents API call', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Open create note modal
        await user.click(screen.getByText('+ New Note (Root)'));
        
        // Submit without typing anything
        const modalContent = screen.getByTestId('modal-content');
        await user.click(within(modalContent).getByRole('button', { name: 'Create' }));
        
        // Verify error message is displayed
        expect(within(modalContent).getByText('Please enter a valid note name')).toBeInTheDocument();
        
        // Verify API was not called
        expect(api.createNote).not.toHaveBeenCalled();
        
        // Verify modal is still open
        expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
    });
    
    // --- Create Folder Modal Tests ---
    it('creates folder via modal with valid input', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Open create folder modal
        await user.click(screen.getByText('+ New Folder (Root)'));
        
        // Type a folder name and submit
        const modalContent = screen.getByTestId('modal-content');
        await user.type(within(modalContent).getByRole('textbox'), NEW_FOLDER_NAME);
        await user.click(within(modalContent).getByRole('button', { name: 'Create' }));
        
        // Verify API was called with correct params - specially check .folder title
        expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, expect.objectContaining({
            title: '.folder',
            folder_path: `/${NEW_FOLDER_NAME}`
        }));
        
        // Verify modal is closed after successful submission
        await waitFor(() => {
            expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        });
        
        // Verify note tree was refreshed
        expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial load + after creation
    });
    
    it('shows error for folder name with slashes and prevents API call', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Open create folder modal
        await user.click(screen.getByText('+ New Folder (Root)'));
        
        // Type a folder name with slashes and submit
        const modalContent = screen.getByTestId('modal-content');
        await user.type(within(modalContent).getByRole('textbox'), 'Invalid/Folder/Name');
        await user.click(within(modalContent).getByRole('button', { name: 'Create' }));
        
        // Verify error message is displayed
        expect(within(modalContent).getByText('Folder names cannot contain "/" characters')).toBeInTheDocument();
        
        // Verify API was not called
        expect(api.createNote).not.toHaveBeenCalled();
        
        // Verify modal is still open
        expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
    });
    
    // --- Rename Folder Modal Tests ---
    it('renames folder via modal with valid input', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find and open rename folder modal
        const folderNode = await screen.findByTestId('node-folder-1');
        await user.click(within(folderNode).getByTestId('rename-folder-folder-1'));
        
        // Clear the input and type a new folder name
        const modalContent = screen.getByTestId('modal-content');
        const input = within(modalContent).getByRole('textbox');
        await user.clear(input);
        await user.type(input, 'Renamed Folder');
        await user.click(within(modalContent).getByRole('button', { name: 'Rename' }));
        
        // Verify API was called with correct params
        expect(api.renameFolder).toHaveBeenCalledWith(TEST_PROJECT_ID, {
            old_path: '/Documents',
            new_path: '/Renamed Folder'
        });
        
        // Verify modal is closed after successful submission
        await waitFor(() => {
            expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        });
        
        // Verify note tree was refreshed
        expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial load + after rename
    });
    
    it('does not call API when folder name is unchanged', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find and open rename folder modal
        const folderNode = await screen.findByTestId('node-folder-1');
        await user.click(within(folderNode).getByTestId('rename-folder-folder-1'));
        
        // Submit without changing the input value
        const modalContent = screen.getByTestId('modal-content');
        await user.click(within(modalContent).getByRole('button', { name: 'Rename' }));
        
        // Verify API was not called
        expect(api.renameFolder).not.toHaveBeenCalled();
        
        // Verify modal is closed
        await waitFor(() => {
            expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        });
    });
    
    // --- Move Note Modal Tests ---
    it('moves note via modal to different folder', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find and open move note modal
        // First verify folder-1 (Documents) exists
        const folderNode = await screen.findByTestId('node-folder-1');
        expect(folderNode).toBeInTheDocument();
        
        // Ensure the note inside the folder can be found
        const noteId = MOCK_TREE_DATA_TEMPLATE[0].children[0].note_id; // note-1
        // Get node based on note_id
        const noteNode = await screen.findByTestId(`node-${noteId}`);
        expect(noteNode).toBeInTheDocument();
        
        // Then click the move button
        await user.click(within(noteNode).getByTestId(`move-note-${noteId}`));
        
        // Select a different folder and submit
        const modalContent = screen.getByTestId('modal-content');
        const select = within(modalContent).getByRole('combobox');
        // Note is currently in /Documents, we'll move it to /Projects
        await user.selectOptions(select, '/Projects');
        await user.click(within(modalContent).getByRole('button', { name: 'Move' }));
        
        // Verify API was called with correct params
        expect(api.updateNote).toHaveBeenCalledWith(TEST_PROJECT_ID, 'note-1', {
            folder_path: '/Projects'
        });
        
        // Verify modal is closed after successful submission
        await waitFor(() => {
            expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        });
        
        // Verify note tree was refreshed
        expect(api.getNoteTree).toHaveBeenCalledTimes(2); // Initial load + after move
    });
    
    it('does not call API when note destination is unchanged', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find and open move note modal
        // First verify folder-1 (Documents) exists
        const folderNode = await screen.findByTestId('node-folder-1');
        expect(folderNode).toBeInTheDocument();
        
        // Ensure the note inside the folder can be found
        const noteId = MOCK_TREE_DATA_TEMPLATE[0].children[0].note_id; // note-1
        // Get node based on note_id
        const noteNode = await screen.findByTestId(`node-${noteId}`);
        expect(noteNode).toBeInTheDocument();
        
        // Then click the move button
        await user.click(within(noteNode).getByTestId(`move-note-${noteId}`));
        
        // Select the same folder and submit
        const modalContent = screen.getByTestId('modal-content');
        const select = within(modalContent).getByRole('combobox');
        await user.selectOptions(select, '/Documents'); // Same as current location
        await user.click(within(modalContent).getByRole('button', { name: 'Move' }));
        
        // Verify API was not called
        expect(api.updateNote).not.toHaveBeenCalled();
        
        // Verify modal is closed
        await waitFor(() => {
            expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        });
    });
    
    // --- Busy State Tests ---
    it('disables buttons during note creation API call', async () => {
        const user = userEvent.setup();
        
        // Mock a delayed API response to test busy state
        api.createNote.mockImplementationOnce(() => new Promise(resolve => {
            setTimeout(() => resolve({ data: { id: 'new-note-id' } }), 100);
        }));
        
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Open create note modal
        await user.click(screen.getByText('+ New Note (Root)'));
        
        // Type a note title and submit
        const modalContent = screen.getByTestId('modal-content');
        await user.type(within(modalContent).getByRole('textbox'), NEW_NOTE_TITLE);
        await user.click(within(modalContent).getByRole('button', { name: 'Create' }));
        
        // Check that buttons are disabled during API call
        expect(within(modalContent).getByRole('button', { name: 'Create' })).toBeDisabled();
        expect(within(modalContent).getByRole('button', { name: 'Cancel' })).toBeDisabled();
        
        // Verify tree viewer shows busy state
        expect(screen.getByTestId('is-busy-prop')).toHaveTextContent('true');
        
        // Wait for API call to complete
        await waitFor(() => {
            expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        });
    });
    
    // --- Error Handling Tests ---
    it('shows error message when API call fails', async () => {
        const user = userEvent.setup();
        
        // Mock API failure
        const errorMessage = 'Server error: Could not create note';
        api.createNote.mockRejectedValueOnce(new Error(errorMessage));
        
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Open create note modal
        await user.click(screen.getByText('+ New Note (Root)'));
        
        // Type a note title and submit
        const modalContent = screen.getByTestId('modal-content');
        await user.type(within(modalContent).getByRole('textbox'), NEW_NOTE_TITLE);
        await user.click(within(modalContent).getByRole('button', { name: 'Create' }));
        
        // Check that error message is displayed
        await waitFor(() => {
            expect(within(modalContent).getByText(`Failed to perform action: ${errorMessage}`)).toBeInTheDocument();
        });
        
        // Verify modal is still open
        expect(screen.getByTestId('mock-modal')).toBeInTheDocument();
        
        // Verify buttons are re-enabled after error
        expect(within(modalContent).getByRole('button', { name: 'Create' })).not.toBeDisabled();
        expect(within(modalContent).getByRole('button', { name: 'Cancel' })).not.toBeDisabled();
    });
    
    it('closes modal when close button is clicked', async () => {
        const user = userEvent.setup();
        renderComponent();
        
        // Wait for component to be fully loaded
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Open create note modal
        await user.click(screen.getByText('+ New Note (Root)'));
        
        // Click the close button
        await user.click(screen.getByTestId('modal-close-button'));
        
        // Verify modal is closed
        await waitFor(() => {
            expect(screen.queryByTestId('mock-modal')).not.toBeInTheDocument();
        });
    });

     it('opens create folder modal via root button and handles submission', async () => {
        const user = userEvent.setup();
        
        // Mock API responses
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } })
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } });
        
        api.createNote.mockResolvedValue({
            data: { id: 'new-folder-note-id', title: '.folder', folder_path: `/${NEW_FOLDER_NAME}` }
        });

        renderComponent(TEST_PROJECT_ID);
        await screen.findByTestId('mock-note-tree-viewer');
        
        // The actual UI has buttons with specific names
        const createRootFolderButton = screen.getByRole('button', { name: '+ New Folder (Root)' });
        await user.click(createRootFolderButton);

        // Check for modal and its contents
        const modalOverlay = await screen.findByTestId('modal-overlay');
        const modal = within(modalOverlay).getByTestId('mock-modal');
        expect(within(modal).getByTestId('modal-title')).toHaveTextContent('Create New Folder');
        
        // Get input and create button from modal content
        const modalContent = within(modal).getByTestId('modal-content');
        const input = within(modalContent).getByRole('textbox');
        const createButton = within(modalContent).getByRole('button', { name: 'Create' });

        // Enter folder name and submit
        await user.type(input, NEW_FOLDER_NAME);
        await user.click(createButton);

        // Verify proper API call - using the hidden .folder note approach
        await waitFor(() => {
            expect(api.createNote).toHaveBeenCalledWith(TEST_PROJECT_ID, expect.objectContaining({
                title: '.folder', // Hidden note that represents a folder
                folder_path: `/${NEW_FOLDER_NAME}`
            }));
        });
        
        // Verify the tree was refreshed
        await waitFor(() => {
            expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
        
        // Modal should be closed after successful submission
        await waitFor(() => {
            expect(screen.queryByTestId('modal-overlay')).not.toBeInTheDocument();
        });
    });

    it('opens rename folder modal via mock button and handles submission', async () => {
        const user = userEvent.setup();
        const folderToRename = MOCK_TREE_DATA_TEMPLATE[0];
        const oldPath = folderToRename.path;
        const oldName = folderToRename.name;
        const newName = 'Renamed Documents';

        // Mock API responses
        api.renameFolder.mockResolvedValue({ data: { message: 'renamed' } });
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } })
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } });

        renderComponent(TEST_PROJECT_ID);
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find rename button for the selected folder
        const renameButton = await screen.findByTestId(`rename-folder-${folderToRename.id}`);
        await user.click(renameButton);

        // Find modal elements
        const modalOverlay = await screen.findByTestId('modal-overlay');
        const modal = within(modalOverlay).getByTestId('mock-modal');
        expect(within(modal).getByTestId('modal-title')).toHaveTextContent('Rename Folder');
        
        // Get input and rename button
        const modalContent = within(modal).getByTestId('modal-content');
        const input = within(modalContent).getByRole('textbox');
        const renameButton2 = within(modalContent).getByRole('button', { name: 'Rename' });

        // Input should have the original folder name
        expect(input).toHaveValue(oldName);
        
        // Clear and type new folder name
        await user.clear(input);
        await user.type(input, newName);
        await user.click(renameButton2);

        // Verify proper API call - matches actual component implementation
        await waitFor(() => {
            // Calculate the expected new path using the same logic as in the component
            const oldPathParts = oldPath.split('/');
            oldPathParts.pop(); // Remove the last part (current folder name)
            const parentPath = oldPathParts.length > 0 ? oldPathParts.join('/') : '';
            
            // Construct the new path by combining parent path with new folder name
            const expectedNewPath = parentPath === '' || parentPath === '/' 
                ? `/${newName}` 
                : `${parentPath}/${newName}`;
                
            expect(api.renameFolder).toHaveBeenCalledWith(TEST_PROJECT_ID, { 
                old_path: oldPath, 
                new_path: expectedNewPath
            });
        });
        
        // Verify tree was refreshed
        await waitFor(() => {
            expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
        
        // Verify modal is closed after successful operation
        await waitFor(() => {
            expect(screen.queryByTestId('modal-overlay')).not.toBeInTheDocument();
        });
    });

    it('opens move note modal via mock button and handles submission', async () => {
        const user = userEvent.setup();
        const noteToMove = MOCK_TREE_DATA_TEMPLATE[0].children[0]; // Meeting Notes from Documents folder
        const targetFolder = MOCK_TREE_DATA_TEMPLATE[1]; // Projects folder
        const targetPath = targetFolder.path;

        // Mock API responses
        api.updateNote.mockResolvedValue({ data: { message: 'updated' } });
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } })
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } });

        renderComponent(TEST_PROJECT_ID);
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find move button for the selected note
        const moveButton = await screen.findByTestId(`move-note-${noteToMove.note_id}`);
        await user.click(moveButton);

        // Find modal elements
        const modalOverlay = await screen.findByTestId('modal-overlay');
        const modal = within(modalOverlay).getByTestId('mock-modal');
        expect(within(modal).getByTestId('modal-title')).toHaveTextContent('Move Note');
        
        // Get select dropdown and move button
        const modalContent = within(modal).getByTestId('modal-content');
        const select = within(modalContent).getByRole('combobox');
        const moveModalButton = within(modalContent).getByRole('button', { name: 'Move' });

        // Select the target folder and click move
        await user.selectOptions(select, targetPath);
        await user.click(moveModalButton);

        // Verify proper API call
        await waitFor(() => {
            expect(api.updateNote).toHaveBeenCalledWith(TEST_PROJECT_ID, noteToMove.note_id, { 
                folder_path: targetPath 
            });
        });
        
        // Verify tree was refreshed
        await waitFor(() => {
            expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
        
        // Verify modal is closed after successful operation
        await waitFor(() => {
            expect(screen.queryByTestId('modal-overlay')).not.toBeInTheDocument();
        });
    });

    it('handles deleting a note via button', async () => {
        const user = userEvent.setup();
        const noteToDelete = MOCK_TREE_DATA_TEMPLATE[2]; // Root note

        // Mock API responses
        api.deleteNote.mockResolvedValue({ data: { success: true } });
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } })
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } });
        
        // Mock window.confirm to return true
        window.confirm = vi.fn().mockReturnValue(true);
        
        // Render component and find button
        renderComponent(TEST_PROJECT_ID);
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find the delete button for our note
        const deleteButton = await screen.findByTestId(`delete-note-${noteToDelete.note_id}`);
        
        // Click delete button
        await user.click(deleteButton);
        
        // Wait for all promises to resolve
        await new Promise(resolve => setTimeout(resolve, 0));
        
        // Verify confirm dialog is shown with correct message
        expect(window.confirm).toHaveBeenCalledWith(`Are you sure you want to delete the note "${noteToDelete.name}"?`);

        // Verify API call is made with correct parameters
        expect(api.deleteNote).toHaveBeenCalledWith(TEST_PROJECT_ID, noteToDelete.note_id);
        
        // Verify the note tree is refreshed after deletion
        await waitFor(() => {
            expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
    });
    
    
    
    it('handles deleting a folder recursively via button', async () => {
        const user = userEvent.setup();
        const folderToDelete = MOCK_TREE_DATA_TEMPLATE[0]; // Documents folder
        
        // Mock API responses
        api.deleteFolder.mockResolvedValue({ data: { success: true } });
        api.getNoteTree
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } })
            .mockResolvedValueOnce({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } });
        
        // Mock window.confirm to return true
        window.confirm = vi.fn().mockReturnValue(true);
        
        // Render component and find button
        renderComponent(TEST_PROJECT_ID);
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Find the delete button for our folder
        const deleteButton = await screen.findByTestId(`delete-folder-${folderToDelete.id}`);
        
        // Click delete button
        await user.click(deleteButton);
        
        // Verify confirm dialog is shown with folder name
        expect(window.confirm).toHaveBeenCalledWith(
            expect.stringMatching(new RegExp(`Are you sure you want to delete the folder.*${folderToDelete.name}.*contents`, 'i'))
        );

        // Verify API call is made with correct parameters - component passes { path, recursive: true }
        await waitFor(() => {
            expect(api.deleteFolder).toHaveBeenCalledWith(TEST_PROJECT_ID, { 
                path: folderToDelete.path, 
                recursive: true 
            });
        });
        
        // Verify the note tree is refreshed after deletion
        await waitFor(() => {
            expect(api.getNoteTree).toHaveBeenCalledTimes(2);
        });
    });

    it('disables modal buttons during API processing', async () => {
        const user = userEvent.setup();
        
        // Setup to capture the resolve function for our manual promise
        let resolveApiCall;
        api.createNote.mockImplementationOnce(() => {
            return new Promise(resolve => {
                resolveApiCall = resolve;
            });
        });
        
        // Set up the component and tree data
        api.getNoteTree.mockResolvedValue({ data: { tree: JSON.parse(JSON.stringify(MOCK_TREE_DATA_TEMPLATE)) } });
        renderComponent(TEST_PROJECT_ID);
        await screen.findByTestId('mock-note-tree-viewer');
        
        // Open create note modal
        const createNoteButton = screen.getByRole('button', { name: '+ New Note (Root)' });
        await user.click(createNoteButton);
        
        // Find the modal and its contents
        const modalOverlay = await screen.findByTestId('modal-overlay');
        const modal = within(modalOverlay).getByTestId('mock-modal');
        const modalContent = within(modal).getByTestId('modal-content');
        
        // Enter note title
        const input = within(modalContent).getByRole('textbox');
        await user.type(input, 'Test Note');
        
        // Get the create button
        const createButton = within(modalContent).getByRole('button', { name: 'Create' });
        const cancelButton = within(modalContent).getByRole('button', { name: 'Cancel' });
        
        // Verify buttons are enabled before submission
        expect(createButton).not.toBeDisabled();
        expect(cancelButton).not.toBeDisabled();
        
        // Click create button to submit
        await user.click(createButton);
        
        // Verify both buttons become disabled during API processing
        await waitFor(() => {
            const disabledCreateButton = within(modalContent).getByRole('button', { name: 'Create' });
            expect(disabledCreateButton).toBeDisabled();
            
            const disabledCancelButton = within(modalContent).getByRole('button', { name: 'Cancel' });
            expect(disabledCancelButton).toBeDisabled();
        });
        
        // Now complete the API call
        act(() => {
            resolveApiCall({ data: { id: 'new-note-id' } });
        });
        
        // Verify modal closes after processing completes
        await waitFor(() => {
            expect(screen.queryByTestId('modal-overlay')).not.toBeInTheDocument();
        });
        
        // Verify the tree was refreshed after completion
        expect(api.getNoteTree).toHaveBeenCalledTimes(2);
    });
});