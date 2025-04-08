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
import { describe, it, vi, beforeEach, expect } from 'vitest';
import { render, screen, act, fireEvent } from '@testing-library/react';
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

// Mock SuggestionPopup - just need to know it was rendered
vi.mock('../components/SuggestionPopup', () => ({
  __esModule: true,
  default: vi.fn().mockImplementation(props => {
    return (
      <div data-testid="mock-suggestion-popup">
        {props.isLoading && <div data-testid="popup-loading">Loading...</div>}
        {props.error && <div data-testid="popup-error">{props.error.message || JSON.stringify(props.error)}</div>}
        {!props.isLoading && !props.error && props.suggestions?.map((suggestion, index) => (
          <div 
            key={index} 
            data-testid={`suggestion-${index}`} 
            onClick={() => props.onSelect && props.onSelect(suggestion)}
          >
            {suggestion}
          </div>
        ))}
        <button data-testid="popup-close" onClick={props.onClose}>Close</button>
      </div>
    );
  })
}));

// Track MDEditor props to get access to the rephrase command
let editorCommands = [];

// Mock MDEditor with commands export
vi.mock('@uiw/react-md-editor', () => {
  const mockCommands = {
    bold: { name: 'bold' },
    italic: { name: 'italic' },
    strikethrough: { name: 'strikethrough' },
    hr: { name: 'hr' },
    title: { name: 'title' },
    divider: { name: 'divider' },
    link: { name: 'link' },
    quote: { name: 'quote' },
    code: { name: 'code' },
    codeBlock: { name: 'codeBlock' },
    image: { name: 'image' },
    unorderedListCommand: { name: 'unorderedList' },
    orderedListCommand: { name: 'orderedList' },
    checkedListCommand: { name: 'checkedList' },
    help: { name: 'help' },
  };
  
  return {
    __esModule: true,
    default: ({ value, onChange, commands }) => {
      // Store commands for testing
      editorCommands = commands || [];
      
      return (
        <div>
          <textarea 
            data-testid="mock-md-editor"
            value={value} 
            onChange={(e) => onChange(e.target.value)}
          />
          <div data-testid="toolbar">
            {commands?.map((cmd, i) => (
              <button 
                key={i}
                data-testid={`cmd-${cmd.name}`}
              >
                {cmd.name}
              </button>
            ))}
          </div>
        </div>
      );
    },
    commands: mockCommands
  };
});

describe('AIEditorWrapper', () => {
  let mockOnChange;
  
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnChange = vi.fn();
    editorCommands = [];
    
    // Default successful API response
    rephraseText.mockResolvedValue({ data: { suggestions: ['suggestion 1', 'suggestion 2'] } });
  });
  
  it('renders the editor with initial value', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    // Verify editor is rendered with the initial value
    const editor = screen.getByTestId('mock-md-editor');
    expect(editor).toBeInTheDocument();
    expect(editor.value).toBe(INITIAL_VALUE);
  });

  it('adds the rephrase command to the editor', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    // Find the rephrase command in the list of commands
    const rephraseCommand = editorCommands.find(cmd => cmd.name === 'rephrase');
    expect(rephraseCommand).toBeDefined();
    expect(typeof rephraseCommand.execute).toBe('function');
  });
  
  it('calls onChange when editor value changes', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    const editor = screen.getByTestId('mock-md-editor');
    const newValue = 'Updated value';
    
    fireEvent.change(editor, { target: { value: newValue } });
    
    // Verify onChange was called
    expect(mockOnChange).toHaveBeenCalledWith(newValue);
  });
  
  it('does not call API if there is no text selection', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    // Get the rephrase command and execute it with empty selection
    const rephraseCommand = editorCommands.find(cmd => cmd.name === 'rephrase');
    act(() => {
      rephraseCommand.execute({
        text: INITIAL_VALUE,
        selection: { start: 0, end: 0 } // Empty selection
      }, {});
    });
    
    // Verify API was not called
    expect(rephraseText).not.toHaveBeenCalled();
  });
  
  it('calls rephraseText API with correct parameters', () => {
    render(<AIEditorWrapper value={INITIAL_VALUE} onChange={mockOnChange} projectId={TEST_PROJECT_ID} />);
    
    // Get the rephrase command and execute it with selection
    const rephraseCommand = editorCommands.find(cmd => cmd.name === 'rephrase');
    act(() => {
      rephraseCommand.execute({
        text: INITIAL_VALUE,
        selection: { start: SELECTION_START, end: SELECTION_END }
      }, {});
    });
    
    // Verify API was called with correct parameters
    expect(rephraseText).toHaveBeenCalledWith(TEST_PROJECT_ID, {
      selected_text: SELECTED_TEXT,
      context_before: expect.any(String),
      context_after: expect.any(String),
    });
  });
});