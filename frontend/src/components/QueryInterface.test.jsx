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

describe('QueryInterface', () => {
  let user;

  beforeEach(() => {
    vi.resetAllMocks();
    user = userEvent.setup();
    // Default successful response
    queryProjectContext.mockResolvedValue({
      data: { answer: 'Default AI answer.', source_nodes: [] },
    });
  });

  it('renders the query input and submit button', () => {
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    expect(screen.getByPlaceholderText(/ask a question about your project/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /submit query/i })).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /ai answer/i })).not.toBeInTheDocument(); // No response initially
  });

  it('disables submit button when query is empty or loading', async () => {
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    // Initially empty
    expect(submitButton).toBeDisabled();

    // After typing
    await user.type(queryInput, 'Test query');
    expect(submitButton).not.toBeDisabled();

    // While loading (simulate)
    queryProjectContext.mockImplementation(() => new Promise(() => {})); // Never resolves
    await user.click(submitButton);
    expect(submitButton).toBeDisabled();
    expect(screen.getByText(/waiting for AI response.../i)).toBeInTheDocument();
  });

  it('calls queryProjectContext API on submit with correct data', async () => {
    const queryText = 'What is the plan?';
    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    await waitFor(() => {
      expect(queryProjectContext).toHaveBeenCalledTimes(1);
      expect(queryProjectContext).toHaveBeenCalledWith(TEST_PROJECT_ID, { query: queryText });
    });
  });

  it('displays the AI answer when API call succeeds', async () => {
    const queryText = 'Test query';
    const answerText = 'This is the successful answer.';
    queryProjectContext.mockResolvedValue({ data: { answer: answerText, source_nodes: [] } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for the answer to appear
    expect(await screen.findByText(answerText)).toBeInTheDocument();
    expect(screen.getByRole('heading', { name: /ai answer/i })).toBeInTheDocument();
    expect(screen.queryByText(/waiting for AI response.../i)).not.toBeInTheDocument();
    expect(screen.queryByText(/error:/i)).not.toBeInTheDocument();
  });

  it('displays source nodes when API call succeeds and returns nodes', async () => {
    const queryText = 'Query with sources';
    const answerText = 'Answer based on sources.';
    const sourceNodes = [
      { id: 'node1', text: 'Source snippet one.', score: 0.95, metadata: { file_path: 'project/plan.md' } },
      { id: 'node2', text: 'Source snippet two.', score: 0.88, metadata: { file_path: 'project/chapters/ch1/scene1.md' } },
      { id: 'node3', text: 'Source snippet three.', score: null, metadata: { file_path: 'other/file.txt' } }, // Test null score
    ];
    queryProjectContext.mockResolvedValue({ data: { answer: answerText, source_nodes: sourceNodes } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for answer
    await screen.findByText(answerText);

    // Check sources heading
    expect(screen.getByRole('heading', { name: /sources used/i })).toBeInTheDocument();

    // Check individual source nodes
    expect(screen.getByText('plan.md (Score: 0.950)')).toBeInTheDocument();
    expect(screen.getByText('Source snippet one.')).toBeInTheDocument();

    expect(screen.getByText('scene1.md (Score: 0.880)')).toBeInTheDocument();
    expect(screen.getByText('Source snippet two.')).toBeInTheDocument();

    expect(screen.getByText('file.txt (Score: N/A)')).toBeInTheDocument(); // Check null score handling
    expect(screen.getByText('Source snippet three.')).toBeInTheDocument();
  });

   it('displays specific message when API call succeeds but returns no source nodes', async () => {
    const queryText = 'Query with no sources';
    const answerText = 'Answer without sources.';
    queryProjectContext.mockResolvedValue({ data: { answer: answerText, source_nodes: [] } }); // Empty array

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for answer
    await screen.findByText(answerText);

    // Check for the specific message
    expect(screen.getByText('(No specific sources retrieved for this answer)')).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /sources used/i })).not.toBeInTheDocument();
  });

  it('displays an error message if API call fails', async () => {
    const queryText = 'Query that fails';
    const errorMessage = 'AI service unavailable';
    // Simulate API error with a detail message
    queryProjectContext.mockRejectedValue({ response: { data: { detail: errorMessage } } });

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for error message
    expect(await screen.findByText(`Error: ${errorMessage}`)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /ai answer/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/waiting for AI response.../i)).not.toBeInTheDocument();
  });

   it('displays a generic error message if API error has no detail', async () => {
    const queryText = 'Query that fails generically';
    const genericErrorMessage = 'Network Error';
    // Simulate API error without a detail message
    queryProjectContext.mockRejectedValue(new Error(genericErrorMessage));

    render(<QueryInterface projectId={TEST_PROJECT_ID} />);
    const submitButton = screen.getByRole('button', { name: /submit query/i });
    const queryInput = screen.getByPlaceholderText(/ask a question about your project/i);

    await user.type(queryInput, queryText);
    await user.click(submitButton);

    // Wait for generic error message
    expect(await screen.findByText(`Error: ${genericErrorMessage}`)).toBeInTheDocument();
    expect(screen.queryByRole('heading', { name: /ai answer/i })).not.toBeInTheDocument();
  });

});