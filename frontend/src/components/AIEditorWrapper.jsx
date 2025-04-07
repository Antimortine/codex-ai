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

import React, { useState, useCallback, useEffect, useRef } from 'react'; // Added useEffect, useRef
import PropTypes from 'prop-types';
import MDEditor, { commands } from '@uiw/react-md-editor';
import { rephraseText } from '../api/codexApi';

// --- Suggestion Popup Component ---
const popupBaseStyles = {
    position: 'absolute',
    zIndex: 1010,
    backgroundColor: 'white',
    border: '1px solid #ccc',
    borderRadius: '4px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
    padding: '5px',
    minWidth: '200px', // Increased minWidth
    maxWidth: '400px', // Added maxWidth
    maxHeight: '300px', // Added maxHeight
    overflowY: 'auto', // Allow scrolling for many suggestions
    marginTop: '5px',
    outline: 'none', // Remove default focus outline
};

const suggestionBaseStyles = {
    cursor: 'pointer',
    padding: '5px 10px', // Increased padding
    borderBottom: '1px solid #eee',
    fontSize: '0.9em',
    whiteSpace: 'nowrap', // Prevent wrapping
    overflow: 'hidden',
    textOverflow: 'ellipsis', // Add ellipsis if too long
};

const suggestionHighlightedStyles = {
    ...suggestionBaseStyles,
    backgroundColor: '#e0e0e0', // Highlight color
};

const errorStyles = {
    color: 'red',
    fontSize: '0.8em',
    padding: '5px',
};

const SuggestionPopup = ({ suggestions, isLoading, error, onSelect, onClose, top, left }) => {
    const [highlightedIndex, setHighlightedIndex] = useState(-1); // -1 means nothing highlighted
    const popupRef = useRef(null); // Ref for the popup container

    // Focus the popup when it becomes visible to capture key events
    useEffect(() => {
        if (popupRef.current) {
            popupRef.current.focus();
            setHighlightedIndex(-1); // Reset highlight when popup appears/changes
        }
    }, [isLoading, error, suggestions]); // Re-run if loading/error/suggestions change

    // Reset highlight index if suggestions list changes
     useEffect(() => {
        setHighlightedIndex(-1);
    }, [suggestions]);

    const handleKeyDown = useCallback((event) => {
        if (isLoading || error || !suggestions || suggestions.length === 0) return;

        switch (event.key) {
            case 'ArrowDown':
                event.preventDefault(); // Prevent page scroll
                setHighlightedIndex(prevIndex =>
                    prevIndex === suggestions.length - 1 ? 0 : prevIndex + 1
                );
                break;
            case 'ArrowUp':
                event.preventDefault(); // Prevent page scroll
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
            case 'Escape':
                event.preventDefault();
                onClose();
                break;
            default:
                break;
        }
    }, [suggestions, highlightedIndex, isLoading, error, onSelect, onClose]);

    // Scroll highlighted item into view
    useEffect(() => {
        if (highlightedIndex !== -1 && popupRef.current) {
            const highlightedElement = popupRef.current.querySelector(`[data-index="${highlightedIndex}"]`);
            if (highlightedElement) {
                highlightedElement.scrollIntoView({ block: 'nearest', inline: 'nearest' });
            }
        }
    }, [highlightedIndex]);


    if (!isLoading && !error && (!suggestions || suggestions.length === 0)) {
        return null;
    }

    // Combine base styles with dynamic top/left
    const dynamicPopupStyles = {
        ...popupBaseStyles,
        top: `${top}px`,
        left: `${left}px`,
    };

    return (
        // Added ref and tabIndex for focus, onKeyDown handler
        <div
            ref={popupRef}
            style={dynamicPopupStyles}
            tabIndex={-1} // Make it focusable
            onKeyDown={handleKeyDown}
        >
             <button onClick={onClose} style={{ float: 'right', border:'none', background:'none', cursor:'pointer', fontSize:'1.1em', padding:'0 5px' }}>×</button>
             {isLoading && <div>Loading...</div>}
             {error && <div style={errorStyles}>Error: {error}</div>}
             {!isLoading && !error && suggestions && suggestions.length > 0 && (
                 <>
                    <div style={{fontWeight: 'bold', marginBottom: '5px', fontSize:'0.9em'}}>Rephrase Suggestions:</div>
                    {suggestions.map((s, index) => (
                        <div
                            key={index}
                            data-index={index} // Add data-index for querySelector
                            style={index === highlightedIndex ? suggestionHighlightedStyles : suggestionBaseStyles}
                            className="suggestion-item"
                            onClick={() => onSelect(s)}
                            onMouseEnter={() => setHighlightedIndex(index)} // Highlight on hover
                            role="button"
                            // Removed tabIndex and onKeyPress as container handles keys
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
    top: PropTypes.number.isRequired, // Position prop
    left: PropTypes.number.isRequired, // Position prop
};


// --- Main Wrapper ---

function AIEditorWrapper({ value, onChange, height = 300, projectId, ...restProps }) {
    const [popupState, setPopupState] = useState({
        visible: false,
        suggestions: [],
        isLoading: false,
        error: null,
        // --- ADDED: Popup position ---
        top: 50, // Default position
        left: null, // Default to right alignment later
    });
    const [activeSelection, setActiveSelection] = useState({ start: -1, end: -1, text: '' });
    const editorRef = useRef(null); // Ref for the editor container div

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
            console.log("Rephrase command executed.");
            const selection = state?.selection;
            const selectedText = selection ? state.text.substring(selection.start, selection.end) : '';

            if (!selectedText || selectedText.trim().length === 0 || !selection) {
                console.log("No text selected for rephrasing.");
                setPopupState(prev => ({ ...prev, visible: false }));
                return;
            }

            console.log(`Selected: "${selectedText}", Start: ${selection.start}, End: ${selection.end}`);
            setActiveSelection({ start: selection.start, end: selection.end, text: selectedText });

            // --- Calculate Popup Position ---
            let popupTop = 50; // Default below toolbar
            let popupLeft = null; // Default right alignment
            if (editorRef.current) {
                const editorRect = editorRef.current.getBoundingClientRect();
                // Position near top-right corner of the editor container
                popupTop = 45; // Adjust as needed based on toolbar height
                popupLeft = editorRect.width - 420; // Approx popup width + padding
                if (popupLeft < 10) popupLeft = 10; // Ensure it doesn't go off-screen left
            }
            // -----------------------------

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
                console.log("Sending rephrase request:", requestData);
                const response = await rephraseText(projectId, requestData);
                console.log("Rephrase suggestions received:", response.data.suggestions);

                if (response.data.suggestions && response.data.suggestions[0]?.startsWith("Error:")) {
                     setPopupState(prev => ({ ...prev, isLoading: false, error: response.data.suggestions[0] }));
                } else {
                     setPopupState(prev => ({ ...prev, isLoading: false, suggestions: response.data.suggestions || [] }));
                }
            } catch (err) {
                console.error("Error calling rephrase API:", err);
                const errorMsg = err.response?.data?.detail || err.message || 'Failed to get suggestions.';
                setPopupState(prev => ({ ...prev, isLoading: false, error: errorMsg }));
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
            console.error("Cannot apply suggestion, stored selection indices are invalid.");
             navigator.clipboard.writeText(suggestion)
                .then(() => setPopupState(prev => ({...prev, error:"Could not apply suggestion. Copied."})))
                .catch(err => {
                    console.error("Clipboard write failed:", err);
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
        // Added ref to the container
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

            {/* Render Suggestion Popup Conditionally */}
            {popupState.visible && (
                 // Pass position props
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