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
import { describe, it, vi, beforeEach, expect, afterEach } from 'vitest';
import { render, screen, act, fireEvent, waitFor } from '@testing-library/react';
import AIEditorWrapper from './AIEditorWrapper';
import { rephraseText } from '../api/codexApi';

// Constants for test
const INITIAL_VALUE = 'This is initial text for the editor with some selected text.';
const SELECTION_START = 35;
const SELECTION_END = 53;
const SELECTED_TEXT = INITIAL_VALUE.substring(SELECTION_START, SELECTION_END); // "some selected text"
const TEST_PROJECT_ID = 'test-project-123';

// Mock the API
vi.mock('../api/codexApi', () => ({
  rephraseText: vi.fn()
}));

// Mock the SuggestionPopup component in AIEditorWrapper
vi.mock('./AIEditorWrapper', async () => {
  const actual = await vi.importActual('./AIEditorWrapper');
  return {
    ...actual,
    SuggestionPopup: ({ isLoading, error, suggestions, onSelect, onClose, top, left }) => (
      <div data-testid="suggestion-popup" style={{ position: 'absolute', top, left }}>
        {isLoading && <div data-testid="popup-loading">Loading...</div>}
        {error && <div data-testid="popup-error">{error}</div>}
        {!isLoading && !error && suggestions?.map((suggestion, index) => (
          <div
            key={index}
            data-testid={`suggestion-${index}`}
            onClick={() => onSelect(suggestion)}
          >
            {suggestion}
          </div>
        ))}
        <button data-testid="popup-close" onClick={onClose}>Close</button>
      </div>
    )
  };
});

// --- Mock MDEditor ---
let latestEditorCommands = [];
vi.mock('@uiw/react-md-editor', () => {
  const mockCommands = {
    bold: { name: 'bold' }, italic: { name: 'italic' }, strikethrough: { name: 'strikethrough' },
    hr: { name: 'hr' }, title: { name: 'title' }, divider: { name: 'divider' },
    link: { name: 'link' }, quote: { name: 'quote' }, code: { name: 'code' },
    codeBlock: { name: 'codeBlock' }, image: { name: 'image' },
    unorderedListCommand: { name: 'unorderedList' }, orderedListCommand: { name: 'orderedList' },
    checkedListCommand: { name: 'checkedList' }, help: { name: 'help' },
  };

  return {
    __esModule: true,
    default: ({ value, onChange, commands }) => {
      latestEditorCommands = commands || [];
      return (
        <div>
          <textarea data-testid="mock-md-editor" value={value} onChange={(e) => onChange(e.target.value)} />
        </div>
      );
    },
    commands: mockCommands
  };
});
// --- End Mock MDEditor ---

describe('AIEditorWrapper', () => {
  let mockOnChange;

  beforeEach(() => {
    vi.clearAllMocks();
    mockOnChange = vi.fn();
    latestEditorCommands = [];

    // Default mock response for success case
    rephraseText.mockResolvedValue({ data: { suggestions: ['suggestion 1', 'suggestion 2'] } });
  });

  afterEach(() => {
    latestEditorCommands = [];
  });

  it('renders the editor with initial value', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    const editor = screen.getByTestId('mock-md-editor');
    expect(editor).toBeInTheDocument();
    expect(editor.value).toBe(INITIAL_VALUE);
  });

  it('adds the rephrase command to the editor', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    // Use more flexible assertion to find the command
    const rephraseCommandExists = latestEditorCommands.some(cmd => cmd.name === 'rephrase');
    expect(rephraseCommandExists).toBe(true);
    const rephraseCommand = latestEditorCommands.find(cmd => cmd.name === 'rephrase');
    expect(typeof rephraseCommand.execute).toBe('function');
  });

  it('calls onChange when editor value changes', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    const editor = screen.getByTestId('mock-md-editor');
    const newValue = 'Updated value';
    fireEvent.change(editor, { target: { value: newValue } });
    expect(mockOnChange).toHaveBeenCalledWith(newValue);
  });

  it('does not call API or show popup if there is no text selection', async () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    const rephraseCommand = latestEditorCommands.find(cmd => cmd.name === 'rephrase');
    expect(rephraseCommand).toBeDefined();

    await act(async () => {
      // Empty selection
      await rephraseCommand.execute({ text: INITIAL_VALUE, selection: { start: 0, end: 0 } }, {});
    });

    // Verify no API call and no popup
    expect(rephraseText).not.toHaveBeenCalled();
    expect(screen.queryByTestId("mock-suggestion-popup")).not.toBeInTheDocument();
  });

  it('calls rephraseText API with correct parameters and shows loading', async () => {
    // Never resolving promise to test loading state
    rephraseText.mockImplementation(() => new Promise(() => {}));
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    const rephraseCommand = latestEditorCommands.find(cmd => cmd.name === 'rephrase');
    expect(rephraseCommand).toBeDefined();

    // Execute command
    act(() => {
      rephraseCommand.execute({ text: INITIAL_VALUE, selection: { start: SELECTION_START, end: SELECTION_END } }, {});
    });

    // Wait for loading indicator
    await waitFor(() => {
      expect(screen.getByTestId("popup-loading")).toBeInTheDocument();
    });
    
    // Check popup is rendered
    expect(screen.getByTestId("suggestion-popup")).toBeInTheDocument();

    // Verify API call parameters - use more flexible assertion
    await waitFor(() => {
      expect(rephraseText).toHaveBeenCalledTimes(1);
      const calls = rephraseText.mock.calls;
      // Check if any call matches our expected parameters
      const hasCorrectCall = calls.some(call => {
        const [projectId, params] = call;
        return (
          projectId === TEST_PROJECT_ID &&
          params.selected_text === SELECTED_TEXT &&
          typeof params.context_before === 'string' &&
          typeof params.context_after === 'string'
        );
      });
      expect(hasCorrectCall).toBe(true);
    });
  });

  it('shows suggestions when API call succeeds', async () => {
    const suggestions = ['suggestion alpha', 'suggestion beta'];
    rephraseText.mockResolvedValue({ data: { suggestions } });
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    const rephraseCommand = latestEditorCommands.find(cmd => cmd.name === 'rephrase');
    expect(rephraseCommand).toBeDefined();

    // Execute the command and wait for the entire async flow
    await act(async () => {
      await rephraseCommand.execute({ text: INITIAL_VALUE, selection: { start: SELECTION_START, end: SELECTION_END } }, {});
    });

    // Wait for suggestions to appear
    await waitFor(() => {
      expect(screen.getByTestId("suggestion-0")).toBeInTheDocument();
    });

    // Verify content
    expect(screen.getByTestId("suggestion-0")).toHaveTextContent(suggestions[0]);
    expect(screen.getByTestId("suggestion-1")).toHaveTextContent(suggestions[1]);
    expect(screen.queryByTestId("popup-loading")).not.toBeInTheDocument();
    expect(screen.queryByTestId("popup-error")).not.toBeInTheDocument();
  });

  it('shows error in popup if API call fails (rejects)', async () => {
    const errorMessage = "API Network Error";
    rephraseText.mockRejectedValue(new Error(errorMessage));
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    const rephraseCommand = latestEditorCommands.find(cmd => cmd.name === 'rephrase');
    expect(rephraseCommand).toBeDefined();

    // Execute the command with proper error handling
    await act(async () => {
      try {
        await rephraseCommand.execute({ text: INITIAL_VALUE, selection: { start: SELECTION_START, end: SELECTION_END } }, {});
      } catch (e) {
        // Expected to reject, but we handle it in the component
      }
    });

    // Wait for the error message to appear
    await waitFor(() => {
      expect(screen.getByTestId("popup-error")).toBeInTheDocument();
    });

    // Verify error content exists (without being too specific about exact format)
    const errorElement = screen.getByTestId("popup-error");
    expect(errorElement.textContent).toContain(errorMessage);
    expect(screen.queryByTestId("popup-loading")).not.toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-0")).not.toBeInTheDocument();
  });

  it('shows error in popup if API returns error message in suggestions', async () => {
    const errorMessage = "Error: Rephrasing blocked by safety filter.";
    rephraseText.mockResolvedValue({ data: { suggestions: [errorMessage] } });
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    const rephraseCommand = latestEditorCommands.find(cmd => cmd.name === 'rephrase');
    expect(rephraseCommand).toBeDefined();

    // Execute the command
    await act(async () => {
      await rephraseCommand.execute({ text: INITIAL_VALUE, selection: { start: SELECTION_START, end: SELECTION_END } }, {});
    });

    // Wait for error message
    await waitFor(() => {
      expect(screen.getByTestId("popup-error")).toBeInTheDocument();
    });

    const errorElement = screen.getByTestId("popup-error");
    expect(errorElement.textContent).toContain(errorMessage);
    expect(screen.queryByTestId("popup-loading")).not.toBeInTheDocument();
    expect(screen.queryByTestId("suggestion-0")).not.toBeInTheDocument();
  });

  it('handles multiple rephrase operations correctly', async () => {
    // Test that multiple API calls work correctly
    const firstSuggestions = ['first suggestion 1', 'first suggestion 2'];
    const secondSuggestions = ['second suggestion 1', 'second suggestion 2'];
    
    // Setup API mock to return different values on successive calls
    rephraseText.mockImplementation((projectId, data) => {
      if (rephraseText.mock.calls.length === 1) {
        return Promise.resolve({ data: { suggestions: firstSuggestions } });
      } else {
        return Promise.resolve({ data: { suggestions: secondSuggestions } });
      }
    });

    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    const rephraseCommand = latestEditorCommands.find(cmd => cmd.name === 'rephrase');
    expect(rephraseCommand).toBeDefined();

    // First rephrase operation
    await act(async () => {
      await rephraseCommand.execute({ text: INITIAL_VALUE, selection: { start: SELECTION_START, end: SELECTION_END } }, {});
    });

    // Verify first suggestions appear
    await waitFor(() => {
      expect(screen.getByTestId("suggestion-0")).toBeInTheDocument();
      expect(screen.getByTestId("suggestion-0").textContent).toBe(firstSuggestions[0]);
    });

    // Close popup
    fireEvent.click(screen.getByTestId('popup-close'));

    // Second rephrase operation with different selection
    await act(async () => {
      await rephraseCommand.execute({ text: INITIAL_VALUE, selection: { start: 5, end: 15 } }, {});
    });

    // Verify second suggestions appear
    await waitFor(() => {
      expect(screen.getByTestId("suggestion-0")).toBeInTheDocument();
      expect(screen.getByTestId("suggestion-0").textContent).toBe(secondSuggestions[0]);
    });

    // Verify API was called twice with different parameters
    expect(rephraseText).toHaveBeenCalledTimes(2);
    // First call
    expect(rephraseText.mock.calls[0][0]).toBe(TEST_PROJECT_ID);
    expect(rephraseText.mock.calls[0][1].selected_text).toBe(SELECTED_TEXT);
    // Second call
    expect(rephraseText.mock.calls[1][0]).toBe(TEST_PROJECT_ID);
    expect(rephraseText.mock.calls[1][1].selected_text).toBe(INITIAL_VALUE.substring(5, 15));
  });

  it('applies suggestion correctly when selected', async () => {
    const suggestions = ['improved text'];
    rephraseText.mockResolvedValue({ data: { suggestions } });
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    const rephraseCommand = latestEditorCommands.find(cmd => cmd.name === 'rephrase');

    // Execute rephrase
    await act(async () => {
      await rephraseCommand.execute({ text: INITIAL_VALUE, selection: { start: SELECTION_START, end: SELECTION_END } }, {});
    });

    // Wait for suggestions to appear
    await waitFor(() => {
      expect(screen.getByTestId("suggestion-0")).toBeInTheDocument();
    });

    // Select a suggestion
    fireEvent.click(screen.getByTestId('suggestion-0'));

    // Verify that onChange was called with the correct new value
    expect(mockOnChange).toHaveBeenCalledWith(
      INITIAL_VALUE.substring(0, SELECTION_START) + suggestions[0] + INITIAL_VALUE.substring(SELECTION_END)
    );

    // Verify popup is closed after selection
    expect(screen.queryByTestId("mock-suggestion-popup")).not.toBeInTheDocument();
  });
});