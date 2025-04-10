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
import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock API calls
vi.mock('../api/codexApi', () => ({
  queryProjectContext: vi.fn(),
}));

// Import the component *after* mocks
import QueryInterface from './QueryInterface';
// Import mocked API function
import { queryProjectContext } from '../api/codexApi';

const TEST_PROJECT_ID = 'query-proj-1';

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


describe('QueryInterface Component with History', () => {
  let user;

  beforeEach(() => {
    vi.resetAllMocks();
    user = userEvent.setup();
    // Default successful response
    queryProjectContext.mockResolvedValue({
      data: { answer: 'Default AI answer.', source_nodes: [] },
    });
    // Mock localStorage
    Storage.prototype.getItem = vi.fn();
    Storage.prototype.setItem = vi.fn();
    Storage.prototype.removeItem = vi.fn();
  });

  it('renders the query input, submit button, and new chat button', () => {
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit query/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /new chat/i })).toBeInTheDocument();
    expect(screen.queryByTestId('query-history')).not.toBeInTheDocument(); // No history initially
  });

  it('disables submit button when query is empty', async () => {
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    expect(submitButton).toBeDisabled(); // Initially empty
    await user.type(queryInput, 'Test query');
    expect(submitButton).not.toBeDisabled(); // After typing
    await user.clear(queryInput);
    expect(submitButton).toBeDisabled(); // Empty again
  });

  // Let's test one thing at a time to make it more reliable
  it('calls API and displays query/response in history', async () => {
    const queryText = 'What is the plan?';
    const answerText = 'The plan is to test.';
    
    // Mock the API response
    queryProjectContext.mockResolvedValue({
      data: { answer: answerText, source_nodes: [] }
    });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    
    // Get initial form elements
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const submitButton = screen.getByTestId('submit-query-button');
    
    // Submit the query
    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for the user query to appear in history
    await screen.findByText(new RegExp(`You: ${queryText}`));
    
    // Wait for AI response to appear in history
    await screen.findByText(new RegExp(`AI: ${answerText}`));
    
    // Verify the input is cleared
    expect(queryInput).toHaveValue('');
  });
  
  it('shows processing state and disables controls while processing', async () => {
    // Create manually resolvable promise 
    let resolveApi;
    const apiPromise = new Promise(resolve => {
      resolveApi = () => resolve({ data: { answer: 'Test answer', source_nodes: [] } });
    });
    queryProjectContext.mockReturnValue(apiPromise);

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    
    // Get initial elements
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const submitButton = screen.getByTestId('submit-query-button');
    const newChatButton = screen.getByTestId('new-chat-button');
    
    // Submit a query
    await user.type(queryInput, 'Test query');
    await user.click(submitButton);
    
    // Verify processing state is active
    expect(screen.getByTestId('is-processing')).toHaveAttribute('data-processing', 'true');
    
    // Verify controls are disabled
    expect(submitButton).toBeDisabled();
    expect(newChatButton).toBeDisabled();
    expect(queryInput).toBeDisabled();
    
    // Resolve the API call
    resolveApi();
  });
  
  it('shows processing state while API call is in progress and resets after completion', async () => {
    // Create a manually controlled promise
    let resolveApi;
    const apiPromise = new Promise(resolve => {
      resolveApi = resolve;
    });
    
    // Use the manually controlled promise in our mock
    queryProjectContext.mockImplementation(() => apiPromise);

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    
    // Get input and submit button
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const submitButton = screen.getByTestId('submit-query-button');
    
    // Submit a query
    await user.type(queryInput, 'Test query');
    await user.click(submitButton);
    
    // Immediately after clicking, check that processing state is active
    // Should be able to catch it because our API promise is still pending
    await waitFor(() => {
      expect(screen.getByTestId('is-processing')).toHaveAttribute('data-processing', 'true');
    });
    
    // Now resolve the API promise
    resolveApi({ data: { answer: 'Test response', source_nodes: [] } });
    
    // Wait for the response to appear in the UI
    await screen.findByText(/AI: Test response/i);
    
    // After the response appears, verify the processing state is reset to false
    await waitFor(() => {
      expect(screen.getByTestId('is-processing')).toHaveAttribute('data-processing', 'false');
    });
  });

  it('adds multiple entries to history', async () => {
    const query1 = 'First query';
    const answer1 = 'Answer one';
    const query2 = 'Second query';
    const answer2 = 'Answer two';

    queryProjectContext
      .mockResolvedValueOnce({ data: { answer: answer1, source_nodes: [] } })
      .mockResolvedValueOnce({ data: { answer: answer2, source_nodes: [] } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    // Submit first query
    await user.type(queryInput, query1);
    await user.click(submitButton);
    await waitFor(() => expect(screen.getByText(`AI: ${answer1}`)).toBeInTheDocument());

    // Submit second query
    await user.type(queryInput, query2);
    await user.click(submitButton);
    await waitFor(() => expect(screen.getByText(`AI: ${answer2}`)).toBeInTheDocument());

    // Check history
    const historyArea = screen.getByTestId('query-history');
    expect(within(historyArea).getByText(`You: ${query1}`)).toBeInTheDocument();
    expect(within(historyArea).getByText(`AI: ${answer1}`)).toBeInTheDocument();
    expect(within(historyArea).getByText(`You: ${query2}`)).toBeInTheDocument();
    expect(within(historyArea).getByText(`AI: ${answer2}`)).toBeInTheDocument();
  });

  it('handles API error and displays it in the correct history entry', async () => {
    const queryText = 'Query that fails';
    const errorMessage = 'AI service unavailable';
    queryProjectContext.mockRejectedValue({ response: { data: { detail: errorMessage } } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for error to appear in the history entry
    await waitFor(() => {
        const latestEntry = getLatestHistoryEntry();
        expect(latestEntry).toBeInTheDocument();
        expect(within(latestEntry).getByTestId(/query-error-\d+/)).toHaveTextContent(errorMessage);
        expect(within(latestEntry).queryByText(/AI:/)).not.toBeInTheDocument(); // No answer
    });
  });

  it('handles API response with "Error:" prefix as an error in history', async () => {
    const queryText = 'Query returning error string';
    const errorMessageInAnswer = 'Error: Rate limit exceeded.';
    queryProjectContext.mockResolvedValue({ data: { answer: errorMessageInAnswer, source_nodes: [] } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for error to appear in the history entry
    await waitFor(() => {
        const latestEntry = getLatestHistoryEntry();
        expect(latestEntry).toBeInTheDocument();
        expect(within(latestEntry).getByTestId(/query-error-\d+/)).toHaveTextContent(errorMessageInAnswer);
        expect(within(latestEntry).queryByText(/AI:/)).not.toBeInTheDocument(); // No answer
    });
  });

  it('clears history when "New Chat" button is clicked', async () => {
    const queryText = 'Some query';
    const answerText = 'Some answer';
    queryProjectContext.mockResolvedValue({ data: { answer: answerText, source_nodes: [] } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);
    const newChatButton = screen.getByRole('button', { name: /new chat/i });

    // Add an entry to history
    await user.type(queryInput, queryText);
    await user.click(submitButton);
    await waitFor(() => expect(screen.getByTestId('query-history')).toBeInTheDocument());
    expect(screen.getByText(`AI: ${answerText}`)).toBeInTheDocument();

    // Click New Chat
    await user.click(newChatButton);

    // Verify history is gone
    expect(screen.queryByTestId('query-history')).not.toBeInTheDocument();
    expect(queryInput).toHaveValue(''); // Input should also be cleared
  });

  it('hides and shows source nodes using the details spoiler', async () => {
    const queryText = 'Query with sources';
    const answerText = 'Answer based on sources.';
    const sourceNodes = [
      { id: 'n1', text: 'Source snippet one.', score: 0.9, metadata: { file_path: 'plan.md' } },
    ];
    queryProjectContext.mockResolvedValue({ data: { answer: answerText, source_nodes: sourceNodes } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for response
    const latestEntry = await waitFor(() => getLatestHistoryEntry());
    expect(within(latestEntry).getByText(`AI: ${answerText}`)).toBeInTheDocument();

    // Find the summary element
    const summary = within(latestEntry).getByText(/sources used \(1\)/i);
    expect(summary).toBeInTheDocument();

    // Source content should NOT be visible initially
    const detailsContent = summary.closest('details').querySelector('div');
    expect(detailsContent).not.toBeVisible();


    // Click the summary to expand
    await user.click(summary);

    // Source content SHOULD now be visible
    expect(within(latestEntry).getByText('Source snippet one.')).toBeVisible();
    expect(within(latestEntry).getByText('plan.md (Score: 0.900)')).toBeVisible();

    // Click again to collapse
    await user.click(summary);
    await waitFor(() => {
        const updatedDetailsContent = summary.closest('details').querySelector('div');
        expect(updatedDetailsContent).not.toBeVisible();
    });
  });

  it('submits query on Ctrl+Enter in textarea', async () => {
    const queryText = 'Submit with ctrl enter';
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    // Simulate Ctrl+Enter press
    fireEvent.keyDown(queryInput, { key: 'Enter', ctrlKey: true });

    // Check if API was called
    await waitFor(() => {
      expect(queryProjectContext).toHaveBeenCalledTimes(1);
      expect(queryProjectContext).toHaveBeenCalledWith(TEST_PROJECT_ID, { query: queryText });
    });

    // Check if history updated (basic check)
    expect(await screen.findByTestId('query-history')).toBeInTheDocument();
    expect(screen.getByText(`You: ${queryText}`)).toBeInTheDocument();
  });

  it('does not submit query on Enter only in textarea', async () => {
    const queryText = 'Do not submit';
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    // Simulate Enter press only
    await user.keyboard('{Enter}'); // userEvent simulates Enter press correctly

    // Check API was NOT called
    expect(queryProjectContext).not.toHaveBeenCalled();
    // Input should contain newline potentially, but not be cleared
    expect(queryInput.value).toContain(queryText);
  });



});