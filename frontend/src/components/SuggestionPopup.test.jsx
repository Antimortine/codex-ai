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
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';

// *** REMOVED vi.mock for AIEditorWrapper ***

// *** ADDED: Direct import of the exported SuggestionPopup ***
import { SuggestionPopup } from '../components/AIEditorWrapper';


// --- Test Suite ---

describe('SuggestionPopup', () => {
  let mockOnSelect;
  let mockOnClose;
  const suggestions = ['suggestion one', 'suggestion two', 'suggestion three'];
  const defaultProps = {
    suggestions: suggestions,
    isLoading: false,
    error: null,
    onSelect: vi.fn(),
    onClose: vi.fn(),
    top: 100,
    left: 150,
  };

  beforeEach(() => {
    vi.resetAllMocks();
    mockOnSelect = vi.fn();
    mockOnClose = vi.fn();
    defaultProps.onSelect = mockOnSelect;
    defaultProps.onClose = mockOnClose;
  });

  // Helper to render with props
  const renderPopup = (props = {}) => {
    // *** Ensure SuggestionPopup is defined here ***
    if (!SuggestionPopup) {
        throw new Error("SuggestionPopup component is not defined/imported correctly for the test.");
    }
    return render(<SuggestionPopup {...defaultProps} {...props} />);
  };

  it('renders nothing when not loading, no error, and no suggestions', () => {
    renderPopup({ suggestions: [] });
    expect(screen.queryByTestId('suggestion-popup')).not.toBeInTheDocument();
  });

  it('renders loading state', () => {
    renderPopup({ isLoading: true, suggestions: [] });
    expect(screen.getByTestId('popup-loading')).toBeInTheDocument();
    expect(screen.getByText('Loading...')).toBeInTheDocument();
    expect(screen.queryByTestId('popup-error')).not.toBeInTheDocument();
    expect(screen.queryByText(/suggestions:/i)).not.toBeInTheDocument();
  });

  it('renders error state', () => {
    const errorMsg = 'Failed to fetch';
    renderPopup({ error: errorMsg, suggestions: [], isLoading: false });
    expect(screen.getByTestId('popup-error')).toBeInTheDocument();
    expect(screen.getByText(`Error: ${errorMsg}`)).toBeInTheDocument();
    expect(screen.queryByTestId('popup-loading')).not.toBeInTheDocument();
    expect(screen.queryByText(/suggestions:/i)).not.toBeInTheDocument();
  });

  it('renders suggestions list', () => {
    renderPopup();
    expect(screen.getByTestId('suggestion-popup')).toBeInTheDocument();
    expect(screen.getByText('Rephrase Suggestions:')).toBeInTheDocument();
    expect(screen.getByText('suggestion one')).toBeInTheDocument();
    expect(screen.getByText('suggestion two')).toBeInTheDocument();
    expect(screen.getByText('suggestion three')).toBeInTheDocument();
    expect(screen.queryByTestId('popup-loading')).not.toBeInTheDocument();
    expect(screen.queryByTestId('popup-error')).not.toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', async () => {
    const user = userEvent.setup();
    renderPopup();
    const closeButton = screen.getByTestId('popup-close');
    await user.click(closeButton);
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  it('calls onSelect with the correct suggestion when an item is clicked', async () => {
    const user = userEvent.setup();
    renderPopup();
    const suggestionItem = screen.getByText('suggestion two'); // Use getByText
    await user.click(suggestionItem);
    expect(mockOnSelect).toHaveBeenCalledTimes(1);
    expect(mockOnSelect).toHaveBeenCalledWith('suggestion two');
  });

  it('calls onClose when Escape key is pressed', async () => {
    const user = userEvent.setup();
    renderPopup();
    const popup = screen.getByTestId('suggestion-popup');
    popup.focus();
    await user.keyboard('{Escape}');
    expect(mockOnClose).toHaveBeenCalledTimes(1);
  });

  describe('Keyboard Navigation', () => {
    let user;

    beforeEach(() => {
        user = userEvent.setup();
    });

    it('highlights next item on ArrowDown, wrapping around', async () => {
      renderPopup();
      const popup = screen.getByTestId('suggestion-popup');
      popup.focus();

      const item0 = screen.getByTestId('suggestion-0');
      const item1 = screen.getByTestId('suggestion-1');
      const item2 = screen.getByTestId('suggestion-2');

      // Initial state: nothing highlighted
      expect(item0).not.toHaveStyle('background-color: rgb(224, 224, 224)');

      // Press Down -> highlight 0
      await user.keyboard('{ArrowDown}');
      expect(item0).toHaveStyle('background-color: rgb(224, 224, 224)');
      expect(item1).not.toHaveStyle('background-color: rgb(224, 224, 224)');

      // Press Down -> highlight 1
      await user.keyboard('{ArrowDown}');
      expect(item0).not.toHaveStyle('background-color: rgb(224, 224, 224)');
      expect(item1).toHaveStyle('background-color: rgb(224, 224, 224)');

      // Press Down -> highlight 2
      await user.keyboard('{ArrowDown}');
      expect(item1).not.toHaveStyle('background-color: rgb(224, 224, 224)');
      expect(item2).toHaveStyle('background-color: rgb(224, 224, 224)');

      // Press Down -> wrap to 0
      await user.keyboard('{ArrowDown}');
      expect(item2).not.toHaveStyle('background-color: rgb(224, 224, 224)');
      expect(item0).toHaveStyle('background-color: rgb(224, 224, 224)');
    });

    it('highlights previous item on ArrowUp, wrapping around', async () => {
      renderPopup();
      const popup = screen.getByTestId('suggestion-popup');
      popup.focus();

      const item0 = screen.getByTestId('suggestion-0');
      const item1 = screen.getByTestId('suggestion-1');
      const item2 = screen.getByTestId('suggestion-2');

      // Initial state: nothing highlighted
      // Press Up -> highlight last item (index 2)
      await user.keyboard('{ArrowUp}');
      expect(item2).toHaveStyle('background-color: rgb(224, 224, 224)');
      expect(item1).not.toHaveStyle('background-color: rgb(224, 224, 224)');

      // Press Up -> highlight 1
      await user.keyboard('{ArrowUp}');
      expect(item2).not.toHaveStyle('background-color: rgb(224, 224, 224)');
      expect(item1).toHaveStyle('background-color: rgb(224, 224, 224)');

      // Press Up -> highlight 0
      await user.keyboard('{ArrowUp}');
      expect(item1).not.toHaveStyle('background-color: rgb(224, 224, 224)');
      expect(item0).toHaveStyle('background-color: rgb(224, 224, 224)');

      // Press Up -> wrap to 2
      await user.keyboard('{ArrowUp}');
      expect(item0).not.toHaveStyle('background-color: rgb(224, 224, 224)');
      expect(item2).toHaveStyle('background-color: rgb(224, 224, 224)');
    });

    it('calls onSelect with highlighted item on Enter', async () => {
      renderPopup();
      const popup = screen.getByTestId('suggestion-popup');
      popup.focus();

      // Highlight 'suggestion two' (index 1)
      await user.keyboard('{ArrowDown}');
      await user.keyboard('{ArrowDown}');
      expect(screen.getByTestId('suggestion-1')).toHaveStyle('background-color: rgb(224, 224, 224)');

      // Press Enter
      await user.keyboard('{Enter}');
      expect(mockOnSelect).toHaveBeenCalledTimes(1);
      expect(mockOnSelect).toHaveBeenCalledWith('suggestion two');
    });

    it('does nothing on Enter if no item is highlighted', async () => {
        renderPopup();
        const popup = screen.getByTestId('suggestion-popup');
        popup.focus();

        // Press Enter without highlighting
        await user.keyboard('{Enter}');
        expect(mockOnSelect).not.toHaveBeenCalled();
    });

    it('ignores keyboard navigation when loading', async () => {
        renderPopup({ isLoading: true, suggestions: [] });
        const popup = screen.getByTestId('suggestion-popup');
        popup.focus();

        await user.keyboard('{ArrowDown}');
        expect(mockOnSelect).not.toHaveBeenCalled();
        expect(mockOnClose).not.toHaveBeenCalled(); // Don't close on ArrowDown

        await user.keyboard('{Enter}');
        expect(mockOnSelect).not.toHaveBeenCalled();

        // Escape should still work
        await user.keyboard('{Escape}');
        expect(mockOnClose).toHaveBeenCalledTimes(1);
    });

     it('ignores keyboard navigation when error', async () => {
        renderPopup({ error: "Some error", suggestions: [] });
        const popup = screen.getByTestId('suggestion-popup');
        popup.focus();

        await user.keyboard('{ArrowDown}');
        expect(mockOnSelect).not.toHaveBeenCalled();
        expect(mockOnClose).not.toHaveBeenCalled(); // Don't close on ArrowDown

        await user.keyboard('{Enter}');
        expect(mockOnSelect).not.toHaveBeenCalled();

        // Escape should still work
        await user.keyboard('{Escape}');
        expect(mockOnClose).toHaveBeenCalledTimes(1);
    });
  });

  it('highlights item on mouse enter', async () => {
    const user = userEvent.setup();
    renderPopup();

    const item0 = screen.getByTestId('suggestion-0');
    const item1 = screen.getByTestId('suggestion-1');

    // Initially nothing highlighted
    expect(item0).not.toHaveStyle('background-color: rgb(224, 224, 224)');
    expect(item1).not.toHaveStyle('background-color: rgb(224, 224, 224)');

    // Hover over item 1
    await user.hover(item1);
    expect(item0).not.toHaveStyle('background-color: rgb(224, 224, 224)');
    expect(item1).toHaveStyle('background-color: rgb(224, 224, 224)');

     // Hover over item 0
    await user.hover(item0);
    expect(item0).toHaveStyle('background-color: rgb(224, 224, 224)');
    expect(item1).not.toHaveStyle('background-color: rgb(224, 224, 224)');
  });

});