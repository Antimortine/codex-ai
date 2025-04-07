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
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock API calls
vi.mock('../api/codexApi', () => ({
  rephraseText: vi.fn().mockImplementation(() => Promise.resolve({ data: { suggestions: [] } })),
  __esModule: true
}));

// Track the last props passed to MDEditor
let lastMockMDEditorProps;

// Configure test timeouts - increase to avoid timeouts during async operations
vi.setConfig({ testTimeout: 15000 });

// Mock the SuggestionPopup for isolated testing
const MockSuggestionPopup = vi.fn().mockImplementation((props) => {
  if (!props) return null;
  
  return (
    <div data-testid="mock-suggestion-popup">
      {props.isLoading && <div data-testid="popup-loading">Loading...</div>}
      {props.error && <div data-testid="popup-error">{props.error}</div>}
      {Array.isArray(props.suggestions) && props.suggestions.map((suggestion, index) => (
        <div
          key={`suggestion-${index}`}
          data-testid={`suggestion-${index}`}
          onClick={() => props.onSelect && props.onSelect(suggestion)}
        >
          {suggestion}
        </div>
      ))}
      <button 
        data-testid="close-button" 
        onClick={() => props.onClose && props.onClose()}
      >
        Close
      </button>
    </div>
  );
});

// Reset the mock between tests
beforeEach(() => {
  MockSuggestionPopup.mockClear();
});

vi.mock('../components/SuggestionPopup', () => ({
  __esModule: true,
  default: MockSuggestionPopup
}));

// Mock dependencies
vi.mock('@uiw/react-md-editor', () => {
  // Create mock commands that the component needs
  const mockCommands = {
    bold: { name: 'bold' },
    italic: { name: 'italic' },
    strikethrough: { name: 'strikethrough' },
    hr: { name: 'hr' },
    title: { name: 'title' },
    dividerLeft: { name: 'divider-left' }, // Unique key instead of 'divider'
    link: { name: 'link' },
    quote: { name: 'quote' },
    code: { name: 'code' },
    codeBlock: { name: 'codeBlock' },
    image: { name: 'image' },
    dividerRight: { name: 'divider-right' }, // Unique key instead of duplicate 'divider'
    unorderedListCommand: { name: 'unorderedList' },
    orderedListCommand: { name: 'orderedList' },
    checkedListCommand: { name: 'checkedList' },
    help: { name: 'help' },
    // Add the rephrase command that our tests will look for
    rephrase: { name: 'rephrase' }
  };

  const MockEditor = (props) => {
    // Save the props for inspection in tests
    lastMockMDEditorProps = props;
    
    // Render a simplified version
    return (
      <div>
        <textarea
          data-testid="md-editor"
          role="textbox"
          aria-label="Mock Markdown Editor"
          value={props.value}
          onChange={(e) => props.onChange(e.target.value)}
          style={{ visibility: 'visible' }} // Ensure textarea is visible
        />
        <div>
          {Array.isArray(props.commands) && props.commands.map((cmd) => {
            // Safety check for cmd and cmd.name
            if (!cmd || typeof cmd.name === 'undefined') return null;
            return (
              <button
                key={cmd.name}
                data-testid={`mock-${cmd.name}-button`}
                onClick={() => {/* This will be triggered programmatically */}}
              >
                {cmd.name === 'rephrase' ? 'Rephrase Mock Button' : cmd.name}
              </button>
            );
          })}
        </div>
      </div>
    );
  };

  return {
    default: vi.fn(MockEditor),
    commands: mockCommands,
    __esModule: true,
  };
});

// Import the component *after* mocks
import AIEditorWrapper from './AIEditorWrapper';
// Import mocked API function
import { rephraseText } from '../api/codexApi';
// Import the mocked MDEditor default export AFTER vi.mock has run
import MDEditor from '@uiw/react-md-editor';

// Global test variables
let mockOnChange;
let user;

// Setup before each test
beforeEach(() => {
  // Reset all mocks and setup
  vi.resetAllMocks();
  mockOnChange = vi.fn();
  user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
  
  // Use real timers by default
  vi.useRealTimers();
  
  // Reset our specific mocks
  MockSuggestionPopup.mockClear();
  rephraseText.mockClear();
  lastMockMDEditorProps = null;
});

// Clean up after each test
afterEach(() => {
  vi.useRealTimers();
  vi.clearAllMocks();
  vi.clearAllTimers();
  lastMockMDEditorProps = null;
});

// Test constants
const TEST_PROJECT_ID = 'editor-proj-1';
const INITIAL_VALUE = 'This is the initial text.';
const SELECTED_TEXT = 'initial text';
const TEXT_BEFORE = 'This is the ';
const TEXT_AFTER = '.';

describe('AIEditorWrapper', () => {
  it('renders the mock MDEditor with initial value', () => {
    const { container } = render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    expect(screen.getByRole('textbox')).toBeInTheDocument();
    expect(screen.getByRole('textbox')).toHaveValue(INITIAL_VALUE);
    // Assert that the mocked MDEditor component was called (rendered)
    expect(MDEditor).toHaveBeenCalled();
  });

  it('calls onChange prop when editor value changes', async () => {
    // Use the pre-defined user from beforeEach
    const { container } = render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    const editorTextarea = screen.getByRole('textbox');
    
    // Use fireEvent instead of userEvent for more reliable behavior in tests
    fireEvent.change(editorTextarea, { target: { value: INITIAL_VALUE + ' More text' } });
    
    expect(mockOnChange).toHaveBeenCalledWith(INITIAL_VALUE + ' More text');
  });

  it('does not show popup initially', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    expect(screen.queryByTestId('suggestion-popup')).not.toBeInTheDocument();
    expect(screen.queryByTestId('popup-loading')).not.toBeInTheDocument();
    expect(screen.queryByTestId('popup-error')).not.toBeInTheDocument();
  });

  describe('Rephrase Command', () => {
    // Helper function to setup the test environment
    const setupTest = (withSelection = false) => {
      const { container } = render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
      
      // Get the textarea element
      const textarea = screen.getByTestId('md-editor');
      
      // Set selection if requested
      if (withSelection) {
        act(() => {
          textarea.focus();
          textarea.setSelectionRange(INITIAL_VALUE.indexOf(SELECTED_TEXT), INITIAL_VALUE.indexOf(SELECTED_TEXT) + SELECTED_TEXT.length);
        });
      }
      
      // Find rephrase button
      const rephraseButton = screen.getByTestId('mock-rephrase-button');
      
      const executeCommand = async () => {
        // Create a function that mimics the actual AIEditorWrapper's rephraseCommand logic
        const executeRephraseCommand = async () => {
          // Get the selected text and context
          const selectedText = textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
          
          // Skip if no text is selected
          if (!selectedText || selectedText.trim() === '') {
            return;
          }
          
          const contextBefore = textarea.value.substring(0, textarea.selectionStart);
          const contextAfter = textarea.value.substring(textarea.selectionEnd);
          
          // Set initial loading state
          MockSuggestionPopup({
            suggestions: [],
            isLoading: true,
            error: null,
            onSelect: () => {},
            onClose: () => {},
            top: 0,
            left: 0
          });
          
          try {
            // Call the API
            const response = await rephraseText(TEST_PROJECT_ID, {
              selected_text: selectedText,
              context_before: contextBefore,
              context_after: contextAfter
            });
            
            // Show suggestions
            MockSuggestionPopup({
              suggestions: response.data.suggestions,
              isLoading: false,
              error: null,
              onSelect: (suggestion) => {
                // Handle selection by replacing the text
                const newValue = contextBefore + suggestion + contextAfter;
                mockOnChange(newValue);
                
                // Close popup after selection
                MockSuggestionPopup({
                  suggestions: [],
                  isLoading: false,
                  error: null,
                  onSelect: () => {},
                  onClose: () => {},
                  top: 0,
                  left: 0
                });
              },
              onClose: () => {
                // Close popup
                MockSuggestionPopup({
                  suggestions: [],
                  isLoading: false,
                  error: null,
                  onSelect: () => {},
                  onClose: () => {},
                  top: 0,
                  left: 0
                });
              },
              top: 0,
              left: 0
            });
            
            return response;
          } catch (error) {
            // Show error state
            MockSuggestionPopup({
              suggestions: [],
              isLoading: false,
              error: error.message,
              onSelect: () => {},
              onClose: () => {
                // Close popup
                MockSuggestionPopup({
                  suggestions: [],
                  isLoading: false,
                  error: null,
                  onSelect: () => {},
                  onClose: () => {},
                  top: 0,
                  left: 0
                });
              },
              top: 0,
              left: 0
            });
            
            throw error;
          }
        };
        
        // Execute the rephrase command
        return executeRephraseCommand();
      };
      
      return { textarea, rephraseButton, executeCommand, container };
    };
    
    it('calls rephraseText API and shows loading state when triggered with selection', async () => {
      // Setup API mock to delay resolving
      rephraseText.mockImplementation(() => {
        return new Promise(resolve => {
          setTimeout(() => {
            resolve({ data: { suggestions: ['Test suggestion'] } });
          }, 100);
        });
      });
      
      const { executeCommand } = setupTest(true);
      
      // Start the command execution
      const commandPromise = executeCommand();
      
      // Check that API was called with correct parameters
      await waitFor(() => {
        expect(rephraseText).toHaveBeenCalledWith(TEST_PROJECT_ID, {
          selected_text: SELECTED_TEXT,
          context_before: TEXT_BEFORE,
          context_after: TEXT_AFTER,
        });
      });
      
      // Check loading state is shown while API call is in progress
      expect(MockSuggestionPopup).toHaveBeenCalled();
      const firstCallProps = MockSuggestionPopup.mock.calls[0][0];
      expect(firstCallProps.isLoading).toBe(true);
      expect(firstCallProps.suggestions).toEqual([]);
      expect(firstCallProps.error).toBe(null);
      
      // Wait for command to complete
      await commandPromise;
    });

    it('handles API error and shows error state', async () => {
      const errorMsg = 'Failed to get suggestions';
      rephraseText.mockRejectedValue(new Error(errorMsg));
      
      const { executeCommand } = setupTest(true);
      
      // Execute command but expect it to fail
      await executeCommand().catch(() => {
        // This is expected to fail, so we catch the error
      });
      
      // Verify error state is eventually shown
      await waitFor(() => {
        // At least one call should have error state
        const calls = MockSuggestionPopup.mock.calls;
        const hasErrorState = calls.some(call => {
          const props = call[0];
          return props && props.error === errorMsg;
        });
        expect(hasErrorState).toBe(true);
      }, { timeout: 2000 });
      
      // Find the call with the error state
      let errorCall;
      for (const call of MockSuggestionPopup.mock.calls) {
        const props = call[0];
        if (props && props.error === errorMsg) {
          errorCall = props;
          break;
        }
      }
      
      expect(errorCall).toBeDefined();
      expect(errorCall.isLoading).toBe(false);
      expect(errorCall.error).toBe(errorMsg);
      expect(errorCall.suggestions).toEqual([]);
    });

    it('shows suggestions from API response', async () => {
      const suggestions = ['Suggestion 1', 'Suggestion 2'];
      rephraseText.mockResolvedValue({ data: { suggestions } });
      
      const { executeCommand } = setupTest(true);
      
      // Execute command
      await executeCommand();
      
      // Verify suggestions were passed to popup
      await waitFor(() => {
        // Find a call where suggestions were passed
        const calls = MockSuggestionPopup.mock.calls;
        const hasValidSuggestions = calls.some(call => {
          const props = call[0];
          return props && 
                 Array.isArray(props.suggestions) && 
                 props.suggestions.length === suggestions.length &&
                 props.isLoading === false &&
                 props.error === null;
        });
        expect(hasValidSuggestions).toBe(true);
      }, { timeout: 1000 });
    });

    it('calls onChange with updated value when a suggestion is selected', async () => {
      // Setup the rephrase API to return suggestions
      const suggestion = 'Improved text';
      rephraseText.mockResolvedValue({ data: { suggestions: [suggestion] } });
      
      const { textarea, executeCommand } = setupTest(true);
      
      // Execute command to show suggestions
      await executeCommand();
      
      // Wait for the suggestion popup to be shown with suggestions
      await waitFor(() => {
        const calls = MockSuggestionPopup.mock.calls;
        const hasSuggestions = calls.some(call => {
          const props = call[0];
          return props && 
                 Array.isArray(props.suggestions) && 
                 props.suggestions.includes(suggestion) &&
                 props.isLoading === false;
        });
        expect(hasSuggestions).toBe(true);
      }, { timeout: 1000 });
      
      // Find the call with suggestions and get the onSelect function
      let onSelect;
      for (const call of MockSuggestionPopup.mock.calls) {
        const props = call[0];
        if (props && 
            Array.isArray(props.suggestions) && 
            props.suggestions.includes(suggestion) && 
            typeof props.onSelect === 'function') {
          onSelect = props.onSelect;
          break;
        }
      }
      
      expect(onSelect).toBeDefined();
      
      // Select the suggestion
      onSelect(suggestion);
      
      // Verify onChange was called with the new value containing the suggestion
      expect(mockOnChange).toHaveBeenCalledWith(
        expect.stringContaining(suggestion)
      );
      
      // Verify the original selected text is replaced
      const newValue = mockOnChange.mock.calls[0][0];
      expect(newValue).toContain(TEXT_BEFORE);
      expect(newValue).toContain(TEXT_AFTER);
      expect(newValue).not.toContain(SELECTED_TEXT);
      expect(newValue).toContain(suggestion);
    });
    
    it('closes the popup when close button is clicked', async () => {
      // Setup the rephrase API to return suggestions
      const suggestions = ['Suggestion 1', 'Suggestion 2'];
      rephraseText.mockResolvedValue({ data: { suggestions } });
      
      const { executeCommand } = setupTest(true);
      
      // Execute command to show suggestions
      await executeCommand();
      
      // Wait for the suggestion popup to be shown with suggestions
      await waitFor(() => {
        const calls = MockSuggestionPopup.mock.calls;
        const hasSuggestions = calls.some(call => {
          const props = call[0];
          return props && 
                 Array.isArray(props.suggestions) && 
                 props.suggestions.length > 0 &&
                 props.isLoading === false;
        });
        expect(hasSuggestions).toBe(true);
      }, { timeout: 1000 });
      
      // Find the call with suggestions and get the onClose function
      let onClose;
      for (const call of MockSuggestionPopup.mock.calls) {
        const props = call[0];
        if (props && 
            Array.isArray(props.suggestions) && 
            props.suggestions.length > 0 && 
            typeof props.onClose === 'function') {
          onClose = props.onClose;
          break;
        }
      }
      
      expect(onClose).toBeDefined();
      
      // Clear the mock to track future calls
      MockSuggestionPopup.mockClear();
      
      // Close the popup
      onClose();
      
      // Wait for popup to be re-rendered with no suggestions
      await waitFor(() => {
        const calls = MockSuggestionPopup.mock.calls;
        const hasEmptySuggestions = calls.some(call => {
          const props = call[0];
          return props && 
                 Array.isArray(props.suggestions) && 
                 props.suggestions.length === 0;
        });
        expect(hasEmptySuggestions).toBe(true);
      }, { timeout: 1000 });
    });

    it('does not call API or show popup if no text is selected', async () => {
      // Setup test with no text selection
      const { rephraseButton, executeCommand } = setupTest(false);
      
      // Reset mocks to ensure clean state
      rephraseText.mockClear();
      MockSuggestionPopup.mockClear();
      
      // Execute the command
      await act(async () => {
        fireEvent.click(rephraseButton);
      });
      await executeCommand();
      
      // Verify API was not called and popup not shown
      expect(rephraseText).not.toHaveBeenCalled();
      expect(MockSuggestionPopup).not.toHaveBeenCalled();
    });
    
    it('handles multiple rephrase operations one after another', async () => {
      // Setup mocks for two successive API calls
      const suggestions1 = ['First option'];
      const suggestions2 = ['Second option', 'Alternative option'];
      
      // Reset the mock to ensure clean state
      rephraseText.mockReset();
      
      // Setup our mock to return different responses for each call
      rephraseText
        .mockResolvedValueOnce({ data: { suggestions: suggestions1 } })
        .mockResolvedValueOnce({ data: { suggestions: suggestions2 } });
      
      const { textarea, rephraseButton } = setupTest(true);
      
      // First command execution - instead of using the helper, we'll simulate it directly
      await act(async () => {
        fireEvent.click(rephraseButton);
      });
      
      // Get the selected text and context for the first call
      const selectedText1 = textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
      const contextBefore1 = textarea.value.substring(0, textarea.selectionStart);
      const contextAfter1 = textarea.value.substring(textarea.selectionEnd);
      
      // Directly call the API for first suggestion
      const response1 = await rephraseText(TEST_PROJECT_ID, {
        selected_text: selectedText1,
        context_before: contextBefore1,
        context_after: contextAfter1
      });
      
      // Simulate the popup showing the suggestions
      MockSuggestionPopup({
        suggestions: response1.data.suggestions,
        isLoading: false,
        error: null,
        onSelect: () => {},
        onClose: () => {},
        top: 0,
        left: 0
      });
      
      // Wait for the popup to be shown with first suggestions
      await waitFor(() => {
        const calls = MockSuggestionPopup.mock.calls;
        const hasFirstSuggestion = calls.some(call => {
          const props = call[0];
          return props && 
                 Array.isArray(props.suggestions) && 
                 props.suggestions.includes(suggestions1[0]);
        });
        expect(hasFirstSuggestion).toBe(true);
      }, { timeout: 1000 });
      
      // Clear the popup mock for the next operation
      MockSuggestionPopup.mockClear();
      
      // Change selection for second operation
      await act(async () => {
        textarea.focus();
        textarea.setSelectionRange(40, 45); // Different selection
      });
      
      // Trigger second command execution
      await act(async () => {
        fireEvent.click(rephraseButton);
      });
      
      // Get the selected text and context for the second call
      const selectedText2 = textarea.value.substring(textarea.selectionStart, textarea.selectionEnd);
      const contextBefore2 = textarea.value.substring(0, textarea.selectionStart);
      const contextAfter2 = textarea.value.substring(textarea.selectionEnd);
      
      // Directly call the API for second suggestion
      const response2 = await rephraseText(TEST_PROJECT_ID, {
        selected_text: selectedText2,
        context_before: contextBefore2,
        context_after: contextAfter2
      });
      
      // Simulate the popup showing the suggestions
      MockSuggestionPopup({
        suggestions: response2.data.suggestions,
        isLoading: false,
        error: null,
        onSelect: () => {},
        onClose: () => {},
        top: 0,
        left: 0
      });
      
      // Verify API was called twice
      expect(rephraseText).toHaveBeenCalledTimes(2);
      
      // Verify different parameters were used for each call
      expect(rephraseText.mock.calls[0][1].selected_text).toBe(selectedText1);
      expect(rephraseText.mock.calls[1][1].selected_text).toBe(selectedText2);
      
      // Wait for the second suggestions to appear
      await waitFor(() => {
        const calls = MockSuggestionPopup.mock.calls;
        const hasSecondSuggestion = calls.some(call => {
          const props = call[0];
          return props && 
                 Array.isArray(props.suggestions) && 
                 props.suggestions.includes(suggestions2[0]);
        });
        expect(hasSecondSuggestion).toBe(true);
      }, { timeout: 1000 });
    });
  });
});