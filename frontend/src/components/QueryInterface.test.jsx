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
import { render, screen, waitFor, within, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock API calls
vi.mock('../api/codexApi', () => ({
  queryProjectContext: vi.fn(),
  getChatHistory: vi.fn(),
  updateChatHistory: vi.fn(),
}));

// Import the component *after* mocks
import QueryInterface from './QueryInterface';
// Import mocked API function
import { queryProjectContext, getChatHistory, updateChatHistory } from '../api/codexApi';

const TEST_PROJECT_ID = 'query-proj-1';
const TEST_SESSION_ID = 'session-abc'; // Default active session for tests

// Constants matching those in QueryInterface component
const IS_PROCESSING_ID = 'is-processing';

// Helper function (no changes)
const getLatestHistoryEntry = () => {
    const historyContainer = screen.queryByTestId('query-history');
    if (!historyContainer) return null;
    const entries = historyContainer.querySelectorAll('div[data-entry-id]');
    if (!entries || entries.length === 0) return null;
    let latestEntry = null; let maxId = -1;
    entries.forEach(entry => { const id = parseInt(entry.getAttribute('data-entry-id'), 10); if (id > maxId) { maxId = id; latestEntry = entry; } });
    return latestEntry;
};


describe('QueryInterface Component with History & Sessions', () => {
  let user;

  // Helper to render with props
  const renderQueryInterface = (props = {}) => {
      const defaultProps = {
          projectId: TEST_PROJECT_ID,
          activeSessionId: TEST_SESSION_ID, // Default to having an active session
      };
      return render(<QueryInterface {...defaultProps} {...props} />);
  }

  beforeEach(() => {
    vi.resetAllMocks();
    user = userEvent.setup({ delay: null });

    // Default successful responses
    queryProjectContext.mockResolvedValue({ data: { answer: 'Default AI answer.', source_nodes: [], direct_sources: null } });
    getChatHistory.mockResolvedValue({ data: { history: [] } });
    updateChatHistory.mockResolvedValue({ data: {} });
  });

  // --- Tests for initial load (updated) ---
  it('shows loading history state initially if activeSessionId is provided', async () => {
    getChatHistory.mockImplementation(() => new Promise(() => {})); // Never resolves
    renderQueryInterface();
    expect(screen.getByText(/loading chat history.../i)).toBeInTheDocument();
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit query/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /clear chat/i })).toBeDisabled();
      expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeDisabled();
    });
  });

  it('does not show loading and disables input if activeSessionId is null', () => {
      renderQueryInterface({ activeSessionId: null });
      // We shouldn't see the loading text or make API calls when activeSessionId is null
      expect(getChatHistory).not.toHaveBeenCalled();

      // Check for disabled controls
      expect(screen.getByRole('button', { name: /submit query/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /clear chat/i })).toBeDisabled();

      // Check for correct placeholder
      const input = screen.getByRole('textbox', { name: /ai query input/i });
      expect(input).toBeDisabled();
      expect(input).toHaveAttribute('placeholder', 'Select a chat session first');
  });

  it('loads and displays existing history for the active session', async () => {
    const existingHistory = [
        { id: 0, query: 'Old query', response: { answer: 'Old answer', source_nodes: [], direct_sources: null }, error: null },
        { id: 1, query: 'Another old query', response: null, error: 'Old error' },
    ];
    getChatHistory.mockResolvedValue({ data: { history: existingHistory } });

    renderQueryInterface();

    // Wait for history content to appear
    await screen.findByText('You: Old query');

    // Verify mock call after content is present
    expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID);

    // Check that loading state is gone
    expect(screen.queryByText(/loading chat history.../i)).not.toBeInTheDocument();

    // Check that history content is displayed correctly
    const historyArea = screen.getByTestId('query-history');
    expect(within(historyArea).getByText('AI: Old answer')).toBeInTheDocument();
    expect(within(historyArea).getByTestId('query-error-1')).toHaveTextContent('Old error');

    // Verify UI state after history loads
    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit query/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /clear chat/i })).toBeEnabled(); // Should be enabled now
      expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeEnabled();
    });
  });

  it('displays error if loading history fails for active session', async () => {
    const loadErrorMsg = 'Failed to fetch history for session';
    getChatHistory.mockRejectedValue({ message: loadErrorMsg });

    renderQueryInterface();

    // Wait for the error message itself
    await screen.findByText(`Failed to load chat history for this session: ${loadErrorMsg}`);

    // Verify mock call after error is present
    expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID);

    // Verify UI state after error
    expect(screen.queryByText(/loading chat history.../i)).not.toBeInTheDocument();

    await waitFor(() => {
      expect(screen.getByRole('button', { name: /submit query/i })).toBeDisabled();
      expect(screen.getByRole('button', { name: /clear chat/i })).toBeDisabled();
      expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeDisabled();
    });

    expect(screen.queryByTestId('query-history')).not.toBeInTheDocument();
  });
  // --- End Initial Load Tests ---


  it('renders the query input, submit button, and clear chat button', async () => {
    renderQueryInterface();

    // Wait for the "no history" message which appears after successful empty load
    await screen.findByText(/no chat history for this session yet/i);

    // Verify mock call after message is present
    expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID);

    // Check that UI elements are rendered correctly
    expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit query/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /clear chat/i })).toBeInTheDocument();
    expect(screen.queryByTestId('query-history')).not.toBeInTheDocument(); // Initially empty
  });

  // --- Submit flow tests (updated) ---
  it('calls API, displays history, clears input, and saves history for active session', async () => {
    const queryText = 'What is the plan?';
    const answerText = 'The plan is to test.';
    const expectedResponse = { answer: answerText, source_nodes: [], direct_sources: null };
    queryProjectContext.mockResolvedValue({ data: expectedResponse });

    renderQueryInterface();

    // Wait for initial load to complete
    await screen.findByText(/no chat history for this session yet/i);
    expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID);

    // Get UI elements
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const submitButton = screen.getByRole('button', { name: /submit query/i });

    // Type and submit query
    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for update to be saved
    await waitFor(() => {
      expect(updateChatHistory).toHaveBeenCalledTimes(1);
    }, { timeout: 2000 });

    // Verify history was updated in UI
    const historyArea = screen.getByTestId('query-history');
    const latestEntry = getLatestHistoryEntry();

    await waitFor(() => {
      expect(within(latestEntry).getByText(`You: ${queryText}`)).toBeInTheDocument();
      expect(within(latestEntry).getByText(`AI: ${answerText}`)).toBeInTheDocument();
      expect(queryInput).toHaveValue('');
    });

    // Verify API was called with correct parameters
    const expectedHistoryToSave = [
      { id: 0, query: queryText, response: expectedResponse, error: null }
    ];
    expect(updateChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID, { history: expectedHistoryToSave });
  });

  it('handles API error, displays it, and saves history with error for active session', async () => {
    const queryText = 'Query that fails';
    const errorMessage = 'AI service unavailable';
    queryProjectContext.mockRejectedValue({ response: { data: { detail: errorMessage } } });

    renderQueryInterface();

    // Wait for initial load to complete
    await screen.findByText(/no chat history for this session yet/i);
    expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID);

    // Get UI elements
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const submitButton = screen.getByRole('button', { name: /submit query/i });

    // Type and submit query
    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for history to be saved
    await waitFor(() => {
      expect(updateChatHistory).toHaveBeenCalledTimes(1);
    }, { timeout: 2000 });

    // Verify error is displayed in UI
    const historyArea = screen.getByTestId('query-history');
    const latestEntry = getLatestHistoryEntry();

    await waitFor(() => {
      expect(within(latestEntry).getByText(`You: ${queryText}`)).toBeInTheDocument();
      expect(screen.getByTestId(`query-error-0`)).toHaveTextContent(errorMessage);
      expect(queryInput).toHaveValue('');
    });

    // Verify API was called with correct parameters
    const expectedHistoryToSave = [
      { id: 0, query: queryText, response: null, error: errorMessage }
    ];
    expect(updateChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID, { history: expectedHistoryToSave });
  });
  // --- End Submit flow tests ---

  // --- Clear Chat test (updated) ---
  it('clears history for active session and saves empty history on "Clear Chat" click', async () => {
    const queryText = 'Some query';
    const answerText = 'Some answer';
    queryProjectContext.mockResolvedValue({ data: { answer: answerText, source_nodes: [], direct_sources: null } });

    renderQueryInterface();
    // --- Wait for load ---
    await screen.findByText(/no chat history for this session yet/i);
    expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID);
    // --- End Wait ---

    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const clearChatButton = screen.getByRole('button', { name: /clear chat/i });

    await user.type(queryInput, queryText);
    await user.click(submitButton);
    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(1));

    expect(screen.getByTestId('query-history')).toBeInTheDocument();

    await user.click(clearChatButton);

    expect(screen.queryByTestId('query-history')).not.toBeInTheDocument();
    expect(queryInput).toHaveValue('');

    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(2));
    expect(updateChatHistory).toHaveBeenLastCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID, { history: [] });
  });
  // --- End Clear Chat test ---

  // --- Added test for switching sessions ---
  it('reloads history when activeSessionId prop changes', async () => {
      const session1Id = 'session-1';
      const session2Id = 'session-2';
      const history1 = [{ id: 0, query: 'Query in Session 1', response: { answer: 'Answer 1', source_nodes: [], direct_sources: null }, error: null }];
      const history2 = [{ id: 0, query: 'Query in Session 2', response: { answer: 'Answer 2', source_nodes: [], direct_sources: null }, error: null }];

      getChatHistory.mockImplementation((projId, sessId) => {
          expect(projId).toBe(TEST_PROJECT_ID);
          if (sessId === session1Id) return Promise.resolve({ data: { history: history1 } });
          if (sessId === session2Id) return Promise.resolve({ data: { history: history2 } });
          return Promise.resolve({ data: { history: [] } });
      });

      // Initial render with session 1
      const { rerender } = renderQueryInterface({ activeSessionId: session1Id });

      // Wait for session 1 history
      await waitFor(() => {
          expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, session1Id);
          expect(screen.getByText('You: Query in Session 1')).toBeInTheDocument();
      });
      expect(screen.queryByText('You: Query in Session 2')).not.toBeInTheDocument();

      // Rerender with session 2
      rerender(<QueryInterface projectId={TEST_PROJECT_ID} activeSessionId={session2Id} />);

      // Wait for session 2 history
      await waitFor(() => {
          expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, session2Id);
          expect(screen.getByText('You: Query in Session 2')).toBeInTheDocument();
      });
      expect(screen.queryByText('You: Query in Session 1')).not.toBeInTheDocument();

      // Check total calls
      expect(getChatHistory).toHaveBeenCalledTimes(2);
  });
  // --- End Added test ---

  it('submits query on Ctrl+Enter in textarea', async () => {
    const queryText = 'Submit with ctrl enter';
    renderQueryInterface();
    // --- Wait for load ---
    await screen.findByText(/no chat history for this session yet/i);
    expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID);
    // --- End Wait ---

    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    await user.type(queryInput, queryText);
    fireEvent.keyDown(queryInput, { key: 'Enter', ctrlKey: true });

    await waitFor(() => {
      expect(queryProjectContext).toHaveBeenCalledTimes(1);
      expect(queryProjectContext).toHaveBeenCalledWith(TEST_PROJECT_ID, { query: queryText });
    });
    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(1));
    expect(screen.getByText(`You: ${queryText}`)).toBeInTheDocument();
  });

  it('disables UI controls during processing', async () => {
    let resolveApi;
    const apiPromise = new Promise(resolve => { resolveApi = resolve; });
    queryProjectContext.mockImplementation(() => apiPromise);
    getChatHistory.mockResolvedValue({ data: { history: [] } });

    renderQueryInterface();
    // --- Wait for load ---
    await screen.findByText(/no chat history for this session yet/i);
    expect(getChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, TEST_SESSION_ID);
    // --- End Wait ---

    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    // --- FIXED: Button name ---
    const clearChatButton = screen.getByRole('button', { name: /clear chat/i });
    // --- END FIXED ---

    expect(clearChatButton).not.toBeDisabled();

    await user.type(queryInput, 'Test disabling');
    await user.click(screen.getByRole('button', { name: /submit query/i }));

    expect(queryInput).toBeDisabled();
    expect(clearChatButton).toBeDisabled();
    expect(screen.getByRole('button', { name: /asking ai/i })).toBeDisabled();

    act(() => {
      resolveApi({ data: { answer: 'Done', source_nodes: [], direct_sources: null } });
    });
    await waitFor(() => {
        expect(screen.getByRole('button', { name: /submit query/i})).toBeDisabled();
        expect(clearChatButton).toBeEnabled();
        expect(queryInput).toBeEnabled();
    });
  });

  // --- ADDED: Test for displaying chapter title in source nodes ---
  it('displays chapter title for scene source nodes', async () => {
    const queryText = 'Tell me about the first scene';
    const answerText = 'The first scene is about the beginning.';
    const mockSourceNodes = [
      {
        id: 'scene-node-1',
        text: 'Scene content snippet.',
        score: 0.9,
        metadata: {
          file_path: 'user_projects/query-proj-1/chapters/ch-abc/sc-xyz.md',
          project_id: TEST_PROJECT_ID,
          document_type: 'Scene',
          document_title: 'The Beginning Scene', // Scene title
          chapter_id: 'ch-abc',
          chapter_title: 'Chapter One Title' // Chapter title
        }
      },
      {
        id: 'char-node-1',
        text: 'Character description snippet.',
        score: 0.8,
        metadata: {
          file_path: 'user_projects/query-proj-1/characters/char-123.md',
          project_id: TEST_PROJECT_ID,
          document_type: 'Character',
          document_title: 'Gandalf' // Character name
        }
      }
    ];
    const expectedResponse = { answer: answerText, source_nodes: mockSourceNodes, direct_sources: null };
    queryProjectContext.mockResolvedValue({ data: expectedResponse });

    renderQueryInterface();
    await screen.findByText(/no chat history for this session yet/i); // Wait for load

    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const submitButton = screen.getByRole('button', { name: /submit query/i });

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for the response to appear
    await screen.findByText(`AI: ${answerText}`);

    // Open the details spoiler
    const detailsSummary = screen.getByText(/retrieved context snippets/i);
    await user.click(detailsSummary);

    // Verify the source node display format
    const sceneSourceText = await screen.findByText(/Scene in "Chapter One Title": "The Beginning Scene"/i);
    expect(sceneSourceText).toBeInTheDocument();
    const characterSourceText = screen.getByText(/Character: "Gandalf"/i);
    expect(characterSourceText).toBeInTheDocument();
  });
  // --- END ADDED ---

});