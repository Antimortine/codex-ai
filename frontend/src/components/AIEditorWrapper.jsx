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

import React, { useState, useCallback } from 'react';
import PropTypes from 'prop-types';
import MDEditor, { commands } from '@uiw/react-md-editor'; // Import commands
import { rephraseText } from '../api/codexApi';

// --- Suggestion Popup Component ---
const popupStyles = {
    position: 'absolute',
    zIndex: 1010,
    backgroundColor: 'white',
    border: '1px solid #ccc',
    borderRadius: '4px',
    boxShadow: '0 2px 10px rgba(0,0,0,0.2)',
    padding: '5px',
    minWidth: '150px',
    marginTop: '5px', // Add some space below toolbar
};

const suggestionStyles = {
    cursor: 'pointer',
    padding: '4px 8px',
    borderBottom: '1px solid #eee',
    fontSize: '0.9em',
};

const errorStyles = {
    color: 'red',
    fontSize: '0.8em',
    padding: '5px',
};

const SuggestionPopup = ({ suggestions, isLoading, error, onSelect, onClose }) => {
    if (!isLoading && !error && (!suggestions || suggestions.length === 0)) {
        return null; // Don't show if nothing to display
    }

    return (
        <div style={popupStyles}>
             <button onClick={onClose} style={{ float: 'right', border:'none', background:'none', cursor:'pointer', fontSize:'1.1em', padding:'0 5px' }}>×</button>
             {isLoading && <div>Loading...</div>}
             {error && <div style={errorStyles}>Error: {error}</div>}
             {!isLoading && !error && suggestions && suggestions.length > 0 && (
                 <>
                    <div style={{fontWeight: 'bold', marginBottom: '5px', fontSize:'0.9em'}}>Rephrase Suggestions:</div>
                    {suggestions.map((s, index) => (
                        <div
                            key={index}
                            style={suggestionStyles}
                            className="suggestion-item" // For potential CSS hover
                            onClick={() => onSelect(s)}
                            role="button"
                            tabIndex={0}
                            onKeyPress={(e) => e.key === 'Enter' && onSelect(s)}
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
};


// --- Main Wrapper ---

function AIEditorWrapper({ value, onChange, height = 300, projectId, ...restProps }) {
    const [popupState, setPopupState] = useState({
        visible: false,
        suggestions: [],
        isLoading: false,
        error: null,
    });
    // Store selection state needed for replacement
    const [activeSelection, setActiveSelection] = useState({ start: -1, end: -1, text: '' });

    // --- Custom Rephrase Command ---
    const rephraseCommand = {
        name: 'rephrase',
        keyCommand: 'rephrase',
        buttonProps: { 'aria-label': 'Rephrase selected text', title: 'Rephrase selected text (AI)' },
        icon: ( // Simple icon placeholder
            <svg width="12" height="12" viewBox="0 0 24 24">
                <path fill="currentColor" d="m12.16 6.84l-1.76 1.76l4.6 4.6l-4.6 4.6l1.76 1.76l6.36-6.36zM8.4 6.84l-6.36 6.36l6.36 6.36l1.76-1.76l-4.6-4.6l4.6-4.6z"/>
            </svg>
        ),
        execute: async (state, api) => {
            console.log("Rephrase command executed.");
            // Use state object which proved reliable
            const selection = state?.selection;
            const selectedText = selection ? state.text.substring(selection.start, selection.end) : '';

            if (!selectedText || selectedText.trim().length === 0 || !selection) {
                console.log("No text selected for rephrasing.");
                setPopupState(prev => ({ ...prev, visible: false })); // Ensure popup is hidden
                return;
            }

            console.log(`Selected: "${selectedText}", Start: ${selection.start}, End: ${selection.end}`);
            // Store selection details from the reliable 'state' object
            setActiveSelection({ start: selection.start, end: selection.end, text: selectedText });
            // Show loading popup
            setPopupState({ visible: true, isLoading: true, error: null, suggestions: [] });

            // Get context
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
                .then(() => setPopupState(prev => ({...prev, error:"Could not apply suggestion. Copied."}))) // Show error briefly in popup
                .catch(err => {
                    console.error("Clipboard write failed:", err);
                    setPopupState(prev => ({...prev, error:"Could not apply suggestion or copy."}));
                });
             // Don't close immediately if there was an error
             return;
        }
        // Close popup after successful application
        setPopupState(prev => ({ ...prev, visible: false }));
        setActiveSelection({ start: -1, end: -1, text: '' });
    }, [activeSelection, onChange, value]);

    // --- Handle Popup Close ---
    const handlePopupClose = useCallback(() => {
        setPopupState(prev => ({ ...prev, visible: false, error: null })); // Hide and clear error
        setActiveSelection({ start: -1, end: -1, text: '' });
    }, []);


    return (
        <div style={{ position: 'relative' }}> {/* Position relative for absolute popup */}
            <MDEditor
                value={value}
                onChange={onChange}
                height={height}
                commands={[
                    // Sensible default command set
                    commands.bold, commands.italic, commands.strikethrough, commands.hr, commands.title, commands.divider,
                    commands.link, commands.quote, commands.code, commands.codeBlock, commands.image, commands.divider,
                    commands.unorderedListCommand, commands.orderedListCommand, commands.checkedListCommand, commands.divider,
                    rephraseCommand, // Add our command
                    commands.divider,
                    commands.help,
                ]}
                {...restProps}
            />

            {/* Render Suggestion Popup Conditionally */}
            {/* Position near top-right, adjust as needed */}
            {popupState.visible && (
                 <div style={{position:'absolute', top: '40px', right:'10px', zIndex:1010}}>
                    <SuggestionPopup
                        suggestions={popupState.suggestions}
                        isLoading={popupState.isLoading}
                        error={popupState.error}
                        onSelect={handleSuggestionSelect}
                        onClose={handlePopupClose}
                    />
                 </div>
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