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

import React, { useState, useCallback, useEffect, useRef } from 'react';
import PropTypes from 'prop-types';
import MDEditor, { commands } from '@uiw/react-md-editor';
import { rephraseText } from '../api/codexApi';

// --- Suggestion Popup Component ---
// (SuggestionPopup component code remains unchanged)
export const SuggestionPopup = ({ suggestions, isLoading, error, onSelect, onClose, top, left }) => {
    const [highlightedIndex, setHighlightedIndex] = useState(-1);
    const popupRef = useRef(null);

    useEffect(() => {
        if (popupRef.current) {
            popupRef.current.focus();
            setHighlightedIndex(-1);
        }
    }, [isLoading, error, suggestions]);

     useEffect(() => {
        setHighlightedIndex(-1);
    }, [suggestions]);

    const handleKeyDown = useCallback((event) => {
        // Handle Escape separately, it should always work
        if (event.key === 'Escape') {
            event.preventDefault();
            onClose();
            return; // Stop further processing for Escape
        }

        // Prevent other navigation if loading, error, or no suggestions
        if (isLoading || error || !suggestions || suggestions.length === 0) {
            return;
        }

        // Handle other keys only if not loading/error and suggestions exist
        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault();
                setHighlightedIndex(prevIndex =>
                    prevIndex === suggestions.length - 1 ? 0 : prevIndex + 1
                );
                break;
            case 'ArrowUp':
                event.preventDefault();
                setHighlightedIndex(prevIndex =>
                    prevIndex <= 0 ? suggestions.length - 1 : prevIndex - 1
                );
                break;
            case 'Enter':
                event.preventDefault();
                if (highlightedIndex >= 0 && highlightedIndex < suggestions.length) {
                    onSelect(suggestions[highlightedIndex]);
                }
                break;
            // Escape is handled above
            default:
                break;
        }
    }, [suggestions, highlightedIndex, isLoading, error, onSelect, onClose]); // Keep dependencies

    useEffect(() => {
        if (highlightedIndex !== -1 && popupRef.current) {
            const highlightedElement = popupRef.current.querySelector(`[data-index="${highlightedIndex}"]`);
            if (highlightedElement && typeof highlightedElement.scrollIntoView === 'function') { // Check if function exists
                highlightedElement.scrollIntoView({ block: 'nearest', inline: 'nearest' });
            }
        }
    }, [highlightedIndex]);


    if (!isLoading && !error && (!suggestions || suggestions.length === 0)) {
        return null;
    }

    // --- Styles defined inline for simplicity in this example ---
    const popupBaseStyles = {
        position: 'absolute',
        zIndex: 1010,
        backgroundColor: 'white',
        border: '1px solid #ccc',
        borderRadius: '4px',
        boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
        padding: '5px',
        minWidth: '200px',
        maxWidth: '400px',
        maxHeight: '300px',
        overflowY: 'auto',
        marginTop: '5px',
        outline: 'none',
    };

    const suggestionBaseStyles = {
        cursor: 'pointer',
        padding: '5px 10px',
        borderBottom: '1px solid #eee',
        fontSize: '0.9em',
        whiteSpace: 'nowrap',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
    };

    const suggestionHighlightedStyles = {
        ...suggestionBaseStyles,
        backgroundColor: '#e0e0e0',
    };

    const errorStyles = {
        color: 'red',
        fontSize: '0.8em',
        padding: '5px',
    };
    // --- End Styles ---


    const dynamicPopupStyles = {
        ...popupBaseStyles,
        top: `${top}px`,
        left: `${left}px`,
    };

    return (
        <div
            ref={popupRef}
            style={dynamicPopupStyles}
            tabIndex={-1}
            onKeyDown={handleKeyDown}
            data-testid="suggestion-popup"
        >
             <button data-testid="popup-close" onClick={onClose} style={{ float: 'right', border:'none', background:'none', cursor:'pointer', fontSize:'1.1em', padding:'0 5px' }}>×</button>
             {isLoading && <div data-testid="popup-loading">Loading...</div>}
             {error && <div data-testid="popup-error" style={errorStyles}>Error: {error}</div>}
             {!isLoading && !error && suggestions && suggestions.length > 0 && (
                 <>
                    <div style={{fontWeight: 'bold', marginBottom: '5px', fontSize:'0.9em'}}>Rephrase Suggestions:</div>
                    {suggestions.map((s, index) => (
                        <div
                            key={index}
                            data-index={index}
                            data-testid={`suggestion-${index}`}
                            style={index === highlightedIndex ? suggestionHighlightedStyles : suggestionBaseStyles}
                            className="suggestion-item"
                            onClick={() => onSelect(s)}
                            onMouseEnter={() => setHighlightedIndex(index)}
                            role="button"
                        >
                            {s}
                        </div>
                    ))}
                 </>
             )}
        </div>
    );
};

SuggestionPopup.propTypes = {
    suggestions: PropTypes.array,
    isLoading: PropTypes.bool,
    error: PropTypes.string,
    onSelect: PropTypes.func.isRequired,
    onClose: PropTypes.func.isRequired,
    top: PropTypes.number.isRequired,
    left: PropTypes.number.isRequired,
};


// --- Main Wrapper ---

function AIEditorWrapper({ value, onChange, height = 300, projectId, ...restProps }) {
    const [popupState, setPopupState] = useState({
        visible: false,
        suggestions: [],
        isLoading: false,
        error: null,
        top: 50,
        left: null,
    });
    const [activeSelection, setActiveSelection] = useState({ start: -1, end: -1, text: '' });
    const editorRef = useRef(null);

    // --- Custom Rephrase Command ---
    const rephraseCommand = {
        name: 'rephrase',
        keyCommand: 'rephrase',
        buttonProps: { 'aria-label': 'Rephrase selected text', title: 'Rephrase selected text (AI)' },
        icon: (
            <svg width="12" height="12" viewBox="0 0 24 24">
                <path fill="currentColor" d="m12.16 6.84l-1.76 1.76l4.6 4.6l-4.6 4.6l1.76 1.76l6.36-6.36zM8.4 6.84l-6.36 6.36l6.36 6.36l1.76-1.76l-4.6-4.6l4.6-4.6z"/>
            </svg>
        ),
        execute: async (state, api) => {
            console.log("[AIEditorWrapper] Rephrase command executed.");
            const selection = state?.selection;
            const selectedText = selection ? state.text.substring(selection.start, selection.end) : '';

            if (!selectedText || selectedText.trim().length === 0 || !selection) {
                console.log("[AIEditorWrapper] No text selected for rephrasing.");
                setPopupState(prev => ({ ...prev, visible: false }));
                return;
            }

            console.log(`[AIEditorWrapper] Selected: "${selectedText}", Start: ${selection.start}, End: ${selection.end}`);
            setActiveSelection({ start: selection.start, end: selection.end, text: selectedText });

            let popupTop = 50;
            let popupLeft = null;
            if (editorRef.current) {
                const editorRect = editorRef.current.getBoundingClientRect();
                popupTop = 45; // Position below toolbar
                // Try to position towards the right, but not off-screen
                popupLeft = Math.max(10, editorRect.width - 420); // 400 width + padding/margin
            }

            // Reset state before API call
            setPopupState({
                visible: true,
                isLoading: true,
                error: null,
                suggestions: [],
                top: popupTop,
                left: popupLeft
            });

            const contextBefore = state.text.substring(Math.max(0, selection.start - 50), selection.start);
            const contextAfter = state.text.substring(selection.end, Math.min(state.text.length, selection.end + 50));

            const requestData = {
                selected_text: selectedText,
                context_before: contextBefore,
                context_after: contextAfter,
            };

            try {
                console.log("[AIEditorWrapper] Sending rephrase request:", requestData);
                const response = await rephraseText(projectId, requestData);
                console.log("[AIEditorWrapper] Rephrase response received:", response.data);

                const suggestionsData = response.data?.suggestions;

                // --- ADDED: Check if the first suggestion is an error message ---
                if (Array.isArray(suggestionsData) && suggestionsData.length > 0 && typeof suggestionsData[0] === 'string' && suggestionsData[0].trim().startsWith("Error:")) {
                    const errorMessage = suggestionsData[0];
                    console.warn(`[AIEditorWrapper] Rephrase API returned an error message: ${errorMessage}`);
                    setPopupState(prev => ({
                        ...prev,
                        isLoading: false,
                        error: errorMessage, // Display the error from the suggestions
                        suggestions: []      // Clear suggestions
                    }));
                } else {
                // --- END ADDED ---
                    // Original success path
                    console.log("[AIEditorWrapper] Rephrase successful, setting suggestions.");
                    setPopupState(prev => ({
                        ...prev,
                        isLoading: false,
                        error: null, // Clear error on success
                        suggestions: suggestionsData || [] // Use suggestions or empty array
                    }));
                }
            } catch (err) {
                console.error("[AIEditorWrapper] Error calling rephrase API:", err);
                const errorMsg = err.response?.data?.detail || err.message || 'Failed to get suggestions.';
                setPopupState(prev => ({
                    ...prev,
                    isLoading: false,
                    error: errorMsg, // Set error from catch block
                    suggestions: []   // Clear suggestions on API error
                }));
            }
        },
    };
    // --- End Custom Command ---


    // --- Handle Suggestion Selection from Popup ---
    const handleSuggestionSelect = useCallback((suggestion) => {
        if (activeSelection.start !== -1 && activeSelection.end !== -1) {
            const newValue =
                value.substring(0, activeSelection.start) +
                suggestion +
                value.substring(activeSelection.end);
            onChange(newValue);
        } else {
            console.error("[AIEditorWrapper] Cannot apply suggestion, stored selection indices are invalid.");
             navigator.clipboard.writeText(suggestion)
                .then(() => setPopupState(prev => ({...prev, error:"Could not apply suggestion. Copied."})))
                .catch(err => {
                    console.error("[AIEditorWrapper] Clipboard write failed:", err);
                    setPopupState(prev => ({...prev, error:"Could not apply suggestion or copy."}));
                });
             return;
        }
        setPopupState(prev => ({ ...prev, visible: false }));
        setActiveSelection({ start: -1, end: -1, text: '' });
    }, [activeSelection, onChange, value]);

    // --- Handle Popup Close ---
    const handlePopupClose = useCallback(() => {
        setPopupState(prev => ({ ...prev, visible: false, error: null }));
        setActiveSelection({ start: -1, end: -1, text: '' });
    }, []);


    return (
        <div ref={editorRef} style={{ position: 'relative' }}>
            <MDEditor
                value={value}
                onChange={onChange}
                height={height}
                commands={[
                    commands.bold, commands.italic, commands.strikethrough, commands.hr, commands.title, commands.divider,
                    commands.link, commands.quote, commands.code, commands.codeBlock, commands.image, commands.divider,
                    commands.unorderedListCommand, commands.orderedListCommand, commands.checkedListCommand, commands.divider,
                    rephraseCommand,
                    commands.divider,
                    commands.help,
                ]}
                {...restProps}
            />

            {popupState.visible && (
                 <SuggestionPopup
                    suggestions={popupState.suggestions}
                    isLoading={popupState.isLoading}
                    error={popupState.error}
                    onSelect={handleSuggestionSelect}
                    onClose={handlePopupClose}
                    top={popupState.top}
                    left={popupState.left}
                 />
            )}
        </div>
    );
}

AIEditorWrapper.propTypes = {
    value: PropTypes.string.isRequired,
    onChange: PropTypes.func.isRequired,
    height: PropTypes.number,
    projectId: PropTypes.string.isRequired,
};

export default AIEditorWrapper;