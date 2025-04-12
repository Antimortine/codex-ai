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
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock API calls used by ProjectQueryPage AND QueryInterface (for verification)
vi.mock('../api/codexApi', async (importOriginal) => {
  const actual = await importOriginal();
  return {
    ...actual,
    getProject: vi.fn(),
    listChatSessions: vi.fn(),
    createChatSession: vi.fn(),
    renameChatSession: vi.fn(),
    deleteChatSession: vi.fn(),
    getChatHistory: vi.fn(), // Needed by QueryInterface (mocked child)
    updateChatHistory: vi.fn(), // Needed by QueryInterface (mocked child)
  };
});

// Mock the QueryInterface component and track props
let lastQueryInterfaceProps = {};
vi.mock('../components/QueryInterface', () => ({
    default: (props) => {
        lastQueryInterfaceProps = props; // Store props for assertion
        // Render null if activeSessionId is null/undefined to mimic conditional rendering
        if (!props.activeSessionId) return null;
        return (
            <div data-testid="mock-query-interface">
                Query for {props.projectId}, Session: {props.activeSessionId}
            </div>
        );
    }
}));

// Import the component *after* mocks
import ProjectQueryPage from './ProjectQueryPage';
// Import mocked functions
import {
    getProject,
    listChatSessions,
    createChatSession,
    renameChatSession,
    deleteChatSession,
} from '../api/codexApi';

const TEST_PROJECT_ID = 'proj-query-xyz';
const TEST_PROJECT_NAME = 'Query Test Project';
const SESSION_1 = { id: 'session-abc', name: 'Main Chat', project_id: TEST_PROJECT_ID };
const SESSION_2 = { id: 'session-def', name: 'Second Chat', project_id: TEST_PROJECT_ID };
const NEW_SESSION = { id: 'session-new', name: 'Newly Created', project_id: TEST_PROJECT_ID };

// Helper to render with Router context and params
const renderWithRouter = (ui, { initialEntries = ['/'] } = {}) => {
  lastQueryInterfaceProps = {}; // Reset tracked props
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/projects/:projectId/query" element={ui} />
        <Route path="/projects/:projectId" element={<div>Project Overview Mock</div>} />
      </Routes>
    </MemoryRouter>
  );
};

// Helper to wait for initial loads
async function waitForInitialLoad(expectSessions = true) {
    await waitFor(() => {
        expect(screen.queryByRole('heading', { name: /loading project query interface.../i })).not.toBeInTheDocument();
    });
     if (expectSessions) {
        await screen.findByLabelText('Select Chat Session');
        expect(screen.queryByText(/loading sessions.../i)).not.toBeInTheDocument();
    }
}


describe('ProjectQueryPage', () => {
  let user;

  beforeEach(() => {
    vi.resetAllMocks();
    user = userEvent.setup();
    // Default mocks
    getProject.mockResolvedValue({ data: { id: TEST_PROJECT_ID, name: TEST_PROJECT_NAME } });
    listChatSessions.mockResolvedValue({ data: { sessions: [SESSION_1, SESSION_2] } });
    createChatSession.mockResolvedValue({ data: NEW_SESSION });
    renameChatSession.mockResolvedValue({ data: { ...SESSION_1, name: 'Renamed Session' } });
    deleteChatSession.mockResolvedValue({ data: { message: "Deleted" } });
    window.prompt = vi.fn();
    window.confirm = vi.fn(() => true);
  });

  afterEach(() => {
      vi.restoreAllMocks();
  });

  // --- Tests remain the same up to the failing one ---
  it('renders project/session loading states initially', () => { /* ... */ });
  it('fetches project name and sessions, displays dropdown, and renders QueryInterface', async () => { /* ... */ });
  it('creates a default session if none exist on load', async () => { /* ... */ });
  it('handles error fetching sessions', async () => { /* ... */ });
  it('changes active session and reloads QueryInterface history', async () => { /* ... */ });
  it('handles "New Session" button click', async () => { /* ... */ });
  it('handles "Rename Session" button click', async () => { /* ... */ });

  // --- REVISED Failing Test ---
  it('handles "Delete Session" button click', async () => {
      // Mock the sequence of list calls
      listChatSessions
          .mockResolvedValueOnce({ data: { sessions: [SESSION_1, SESSION_2] }}) // Initial load
          .mockResolvedValueOnce({ data: { sessions: [SESSION_2] }}); // After delete

      renderWithRouter(<ProjectQueryPage />, { initialEntries: [`/projects/${TEST_PROJECT_ID}/query`] });
      await waitForInitialLoad();

      const select = screen.getByLabelText('Select Chat Session');

      // Wait specifically for the options to be populated
      await waitFor(() => {
          expect(within(select).getByRole('option', { name: /Main Chat/ })).toBeInTheDocument();
      });

      // Select session 1 to delete it
      await user.selectOptions(select, SESSION_1.id);
      await waitFor(() => expect(lastQueryInterfaceProps.activeSessionId).toBe(SESSION_1.id));

      const deleteButton = screen.getByRole('button', { name: 'Delete' });
      await user.click(deleteButton);

      // Verify confirmation and API call
      expect(window.confirm).toHaveBeenCalledWith(expect.stringContaining(`"${SESSION_1.name}"`));
      await waitFor(() => {
          expect(deleteChatSession).toHaveBeenCalledTimes(1);
          expect(deleteChatSession).toHaveBeenCalledWith(TEST_PROJECT_ID, SESSION_1.id);
          // --- REVISED: Wait for listChatSessions to have been called TWICE ---
          expect(listChatSessions).toHaveBeenCalledTimes(2);
          // --- END REVISED ---
      });

      // Wait specifically for the activeSessionId prop to update
      await waitFor(() => {
          expect(lastQueryInterfaceProps.activeSessionId).toBe(SESSION_2.id);
      });

      // Also check dropdown content after the state update
      const updatedSelect = screen.getByLabelText('Select Chat Session');
      expect(within(updatedSelect).queryByRole('option', { name: /Main Chat/ })).not.toBeInTheDocument();
      expect(within(updatedSelect).getByRole('option', { name: /Second Chat/ })).toBeInTheDocument();
      expect(updatedSelect).toHaveValue(SESSION_2.id);
  });
  // --- END REVISED ---

   it('prevents deleting the last session', async () => { /* ... */ });

});