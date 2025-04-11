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

// --- REMOVED # Comments ---

import React from 'react';
import { render, screen, waitFor, within, fireEvent, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock API calls
vi.mock('../api/codexApi', () => ({
  queryProjectContext: vi.fn(),
  getChatHistory: vi.fn(), // Mock new API
  updateChatHistory: vi.fn(), // Mock new API
}));

// Import the component *after* mocks
import QueryInterface from './QueryInterface';
// Import mocked API function
import { queryProjectContext, getChatHistory, updateChatHistory } from '../api/codexApi';

const TEST_PROJECT_ID = 'query-proj-1';

// Constants matching those in QueryInterface component
const IS_PROCESSING_ID = 'is-processing';

// Helper function to get the latest history entry element
const getLatestHistoryEntry = () => {
    const historyContainer = screen.queryByTestId('query-history');
    if (!historyContainer) return null;
    // Find the div with the highest data-entry-id attribute
    const entries = historyContainer.querySelectorAll('div[data-entry-id]');
    if (!entries || entries.length === 0) return null;
    let latestEntry = null;
    let maxId = -1;
    entries.forEach(entry => {
        const id = parseInt(entry.getAttribute('data-entry-id'), 10);
        if (id > maxId) {
            maxId = id;
            latestEntry = entry;
        }
    });
    return latestEntry;
};


describe('QueryInterface Component with History (API Persistence)', () => {
  let user;

  beforeEach(() => {
    vi.resetAllMocks();
    user = userEvent.setup({ delay: null }); // Use default delay for userEvent

    // Default successful responses
    queryProjectContext.mockResolvedValue({
      data: { answer: 'Default AI answer.', source_nodes: [], direct_sources: null }, // Added direct_sources: null
    });
    getChatHistory.mockResolvedValue({ data: { history: [] } }); // Default empty history
    updateChatHistory.mockResolvedValue({ data: {} }); // Mock successful save
  });

  // --- Tests for initial load ---
  it('shows loading history state initially', async () => {
    getChatHistory.mockImplementation(() => new Promise(() => {})); // Never resolves
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    expect(screen.getByText(/loading chat history.../i)).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: /submit query/i })).toBeDisabled();
    expect(await screen.findByRole('button', { name: /new chat/i })).toBeDisabled();
    expect(await screen.findByPlaceholderText(/ask a question about your project/i)).toBeDisabled();
  });

  it('loads and displays existing history on mount', async () => {
    const existingHistory = [
        { id: 0, query: 'Old query', response: { answer: 'Old answer', source_nodes: [], direct_sources: null }, error: null }, // Added direct_sources
        { id: 1, query: 'Another old query', response: null, error: 'Old error' },
    ];
    getChatHistory.mockResolvedValue({ data: { history: existingHistory } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);

    await waitFor(() => {
        expect(screen.getByText('You: Old query')).toBeInTheDocument();
    });
    expect(screen.queryByText(/loading chat history.../i)).not.toBeInTheDocument();

    const historyArea = screen.getByTestId('query-history');
    expect(historyArea).toBeInTheDocument();
    expect(within(historyArea).getByText('You: Old query')).toBeInTheDocument();
    expect(within(historyArea).getByText('AI: Old answer')).toBeInTheDocument();
    expect(within(historyArea).getByText('You: Another old query')).toBeInTheDocument();
    expect(within(historyArea).getByTestId('query-error-1')).toHaveTextContent('Old error');

    expect(screen.getByRole('button', { name: /submit query/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /new chat/i })).toBeEnabled();
    expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeEnabled();
  });

  it('displays error if loading history fails', async () => {
    const loadErrorMsg = 'Failed to fetch history';
    getChatHistory.mockRejectedValue({ message: loadErrorMsg });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);

    await waitFor(() => {
        expect(screen.queryByText(/loading chat history.../i)).not.toBeInTheDocument();
    });
    expect(await screen.findByText(`Failed to load chat history: ${loadErrorMsg}`)).toBeInTheDocument();

    expect(screen.getByRole('button', { name: /submit query/i })).toBeDisabled();
    expect(screen.getByRole('button', { name: /new chat/i })).toBeEnabled();
    expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeDisabled();
    expect(screen.queryByTestId('query-history')).not.toBeInTheDocument();
  });
  // --- End Initial Load Tests ---


  it('renders the query input, submit button, and new chat button', async () => {
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());
    expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit query/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /new chat/i })).toBeInTheDocument();
    expect(screen.queryByTestId('query-history')).not.toBeInTheDocument();
  });

  it('disables submit button when query is empty', async () => {
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    expect(submitButton).toBeDisabled();
    await user.type(queryInput, 'Test query');
    expect(submitButton).not.toBeDisabled();
    await user.clear(queryInput);
    expect(submitButton).toBeDisabled();
  });

  it('calls API, displays history, clears input, and saves history on submit', async () => {
    const queryText = 'What is the plan?';
    const answerText = 'The plan is to test.';
    const expectedResponse = { answer: answerText, source_nodes: [], direct_sources: null }; // Added direct_sources
    queryProjectContext.mockResolvedValue({ data: expectedResponse });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const submitButton = screen.getByRole('button', { name: /submit query/i });

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    await waitFor(() => {
      expect(updateChatHistory).toHaveBeenCalledTimes(1);
    }, { timeout: 2000 });

    const historyArea = screen.getByTestId('query-history');
    expect(historyArea).toBeInTheDocument();

    const latestEntry = getLatestHistoryEntry();
    expect(latestEntry).toBeInTheDocument();
    expect(within(latestEntry).getByText(`You: ${queryText}`)).toBeInTheDocument();
    expect(within(latestEntry).getByText(`AI: ${answerText}`)).toBeInTheDocument();

    expect(queryInput).toHaveValue('');

    const expectedHistoryToSave = [
      { id: 0, query: queryText, response: expectedResponse, error: null }
    ];
    expect(updateChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, { history: expectedHistoryToSave });
  });

  it('adds multiple entries to history and saves final state', async () => {
    const query1 = 'First query';
    const answer1 = 'Answer one';
    const query2 = 'Second query';
    const answer2 = 'Answer two';
    const response1 = { answer: answer1, source_nodes: [], direct_sources: null }; // Added direct_sources
    const response2 = { answer: answer2, source_nodes: [], direct_sources: null }; // Added direct_sources

    queryProjectContext
      .mockResolvedValueOnce({ data: response1 })
      .mockResolvedValueOnce({ data: response2 });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    // Submit first query
    await user.type(queryInput, query1);
    await user.click(submitButton);
    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(1));

    // Submit second query
    await user.type(queryInput, query2);
    await user.click(submitButton);
    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(2));

    // Check history display
    const historyArea = screen.getByTestId('query-history');
    expect(within(historyArea).getByText(`You: ${query1}`)).toBeInTheDocument();
    expect(within(historyArea).getByText(`AI: ${answer1}`)).toBeInTheDocument();
    expect(within(historyArea).getByText(`You: ${query2}`)).toBeInTheDocument();
    expect(within(historyArea).getByText(`AI: ${answer2}`)).toBeInTheDocument();

    // Check final save call
    const expectedHistoryToSave = [
        { id: 0, query: query1, response: response1, error: null },
        { id: 1, query: query2, response: response2, error: null }
    ];
    expect(updateChatHistory).toHaveBeenLastCalledWith(TEST_PROJECT_ID, { history: expectedHistoryToSave });
  });

  it('handles API error, displays it, and saves history with error', async () => {
    const queryText = 'Query that fails';
    const errorMessage = 'AI service unavailable';
    queryProjectContext.mockRejectedValue({ response: { data: { detail: errorMessage } } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(1));

    const latestEntry = getLatestHistoryEntry();
    expect(latestEntry).toBeInTheDocument();
    expect(within(latestEntry).getByTestId(/query-error-\d+/)).toHaveTextContent(errorMessage);

    const expectedHistoryToSave = [
        { id: 0, query: queryText, response: null, error: errorMessage }
    ];
    expect(updateChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, { history: expectedHistoryToSave });
  });

  it('handles API response with "Error:" prefix and saves history with error', async () => {
    const queryText = 'Query returning error string';
    const errorMessageInAnswer = 'Error: Rate limit exceeded.';
    queryProjectContext.mockResolvedValue({ data: { answer: errorMessageInAnswer, source_nodes: [], direct_sources: null } }); // Added direct_sources

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
     await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(1));

    const latestEntry = getLatestHistoryEntry();
    expect(latestEntry).toBeInTheDocument();
    expect(within(latestEntry).getByTestId(/query-error-\d+/)).toHaveTextContent(errorMessageInAnswer);

    const expectedHistoryToSave = [
        { id: 0, query: queryText, response: null, error: errorMessageInAnswer }
    ];
    expect(updateChatHistory).toHaveBeenCalledWith(TEST_PROJECT_ID, { history: expectedHistoryToSave });
  });

  it('clears history and saves empty history on "New Chat" click', async () => {
    const queryText = 'Some query';
    const answerText = 'Some answer';
    queryProjectContext.mockResolvedValue({ data: { answer: answerText, source_nodes: [], direct_sources: null } }); // Added direct_sources

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const newChatButton = screen.getByRole('button', { name: /new chat/i });

    await user.type(queryInput, queryText);
    await user.click(submitButton);
    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(1));

    await user.click(newChatButton);

    expect(screen.queryByTestId('query-history')).not.toBeInTheDocument();
    expect(queryInput).toHaveValue('');

    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(2));
    expect(updateChatHistory).toHaveBeenLastCalledWith(TEST_PROJECT_ID, { history: [] });
  });

  it('hides and shows source nodes using the details spoiler', async () => {
    const queryText = 'Query with sources';
    const answerText = 'Answer based on sources.';
    const sourceNodes = [
      { id: 'n1', text: 'Source snippet one.', score: 0.9, metadata: { file_path: 'plan.md', document_type: 'Plan', document_title: 'Project Plan' } }, // Added type/title
    ];
    queryProjectContext.mockResolvedValue({ data: { answer: answerText, source_nodes: sourceNodes, direct_sources: null } }); // Added direct_sources

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(1));

    const latestEntry = getLatestHistoryEntry();
    const summary = within(latestEntry).getByText(/retrieved context snippets \(1\)/i);
    expect(summary).toBeInTheDocument();

    const detailsContent = summary.closest('details').querySelector('div');
    expect(detailsContent).not.toBeVisible();

    await user.click(summary);

    expect(within(latestEntry).getByText('Source snippet one.')).toBeVisible();
    // --- MODIFIED: Assert the new display format by parts ---
    const sourceNodeDiv = within(latestEntry).getByText('Source snippet one.').closest('div'); // Find the parent div
    expect(within(sourceNodeDiv).getByText(/Plan: "Project Plan"/)).toBeInTheDocument(); // Check for type/title part
    expect(within(sourceNodeDiv).getByText(/\(Score: 0.900\)/)).toBeInTheDocument(); // Check for score part
    // --- END MODIFIED ---

    await user.click(summary);
    await waitFor(() => {
        const updatedDetailsContent = summary.closest('details').querySelector('div');
        expect(updatedDetailsContent).not.toBeVisible();
    });
  });

  it('submits query on Ctrl+Enter in textarea', async () => {
    const queryText = 'Submit with ctrl enter';
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    fireEvent.keyDown(queryInput, { key: 'Enter', ctrlKey: true });

    await waitFor(() => {
      expect(queryProjectContext).toHaveBeenCalledTimes(1);
      expect(queryProjectContext).toHaveBeenCalledWith(TEST_PROJECT_ID, { query: queryText });
    });

    await waitFor(() => expect(updateChatHistory).toHaveBeenCalledTimes(1));

    expect(await screen.findByTestId('query-history')).toBeInTheDocument();
    expect(screen.getByText(`You: ${queryText}`)).toBeInTheDocument();
  });

  it('does not submit query on Enter only in textarea', async () => {
    const queryText = 'Do not submit';
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.keyboard('{Enter}');

    expect(queryProjectContext).not.toHaveBeenCalled();
    expect(updateChatHistory).not.toHaveBeenCalled();
    expect(queryInput.value).toContain(queryText);
  });

  it('shows loading state during processing', async () => {
    let resolveApi;
    const apiPromise = new Promise(resolve => { resolveApi = resolve; });
    queryProjectContext.mockImplementation(() => apiPromise);
    getChatHistory.mockResolvedValue({ data: { history: [] } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    await user.type(queryInput, 'Test processing');

    const submitButton = screen.getByRole('button', { name: /submit query/i });
    fireEvent.click(submitButton);

    const loadingButton = screen.getByRole('button', { name: /asking ai/i });
    expect(loadingButton).toBeInTheDocument();

    act(() => {
      resolveApi({ data: { answer: 'Done', source_nodes: [], direct_sources: null } }); // Added direct_sources
    });

    await waitFor(() => {
      expect(screen.getByTestId('query-history')).toBeInTheDocument();
    });
  });

  it('disables UI controls during processing', async () => {
    let resolveApi;
    const apiPromise = new Promise(resolve => { resolveApi = resolve; });
    queryProjectContext.mockImplementation(() => apiPromise);
    getChatHistory.mockResolvedValue({ data: { history: [] } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    await waitFor(() => expect(getChatHistory).toHaveBeenCalled());

    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const newChatButton = screen.getByRole('button', { name: /new chat/i });

    expect(newChatButton).not.toBeDisabled();

    await user.type(queryInput, 'Test disabling');
    await user.click(screen.getByRole('button', { name: /submit query/i }));

    expect(queryInput).toBeDisabled();
    expect(newChatButton).toBeDisabled();
    expect(screen.getByRole('button', { name: /asking ai/i })).toBeDisabled();

    act(() => {
      resolveApi({ data: { answer: 'Done', source_nodes: [], direct_sources: null } }); // Added direct_sources
    });
    // No assertions after resolution in this specific test
  });

});