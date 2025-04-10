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

import React, { useState, useRef, useEffect, useCallback } from 'react'; // Added useCallback
import PropTypes from 'prop-types';
import { queryProjectContext } from '../api/codexApi';

// Basic styling (can be moved to CSS file)
const styles = {
    container: {
        border: '1px solid #ccc',
        borderRadius: '5px',
        padding: '15px',
        marginTop: '20px',
        backgroundColor: '#f9f9f9',
    },
    historyArea: {
        maxHeight: '400px',
        overflowY: 'auto',
        marginBottom: '15px',
        padding: '10px',
        border: '1px solid #e0e0e0',
        backgroundColor: '#fff',
        borderRadius: '4px',
    },
    historyEntry: {
        marginBottom: '15px',
        paddingBottom: '10px',
        borderBottom: '1px dashed #eee',
    },
    queryText: {
        fontWeight: 'bold',
        color: '#333',
        marginBottom: '5px',
    },
    textarea: {
        width: '95%',
        minHeight: '60px',
        marginBottom: '10px',
        padding: '8px',
        border: '1px solid #ccc',
        borderRadius: '3px',
    },
    button: {
        padding: '8px 15px',
        cursor: 'pointer',
        backgroundColor: '#007bff',
        color: 'white',
        border: 'none',
        borderRadius: '3px',
        marginRight: '10px',
    },
    buttonDisabled: {
        backgroundColor: '#aaa',
        cursor: 'not-allowed',
    },
    newChatButton: {
        padding: '8px 15px',
        cursor: 'pointer',
        backgroundColor: '#6c757d',
        color: 'white',
        border: 'none',
        borderRadius: '3px',
    },
    responseArea: {
        padding: '10px',
        backgroundColor: 'white',
        whiteSpace: 'pre-wrap',
        wordWrap: 'break-word',
    },
    // --- MODIFIED: Source Nodes Area Style ---
    sourceNodesArea: {
        // marginTop: '10px', // Removed margin, handled by details element
        fontSize: '0.9em',
        color: '#555',
    },
    // --- ADDED: Details/Summary Styles ---
    detailsSummary: {
        cursor: 'pointer',
        fontWeight: 'bold',
        marginTop: '10px',
        color: '#444',
    },
    detailsContent: {
        paddingTop: '5px', // Add some space below the summary
    },
    // --- END ADDED ---
    sourceNode: {
        borderLeft: '3px solid #ddd',
        paddingLeft: '8px',
        marginBottom: '8px',
        backgroundColor: '#f0f0f0',
        padding: '5px',
        borderRadius: '3px',
    },
    sourceNodeText: {
        whiteSpace: 'pre-wrap',
        wordWrap: 'break-word',
        maxHeight: '100px',
        overflowY: 'auto',
        display: 'block',
        marginTop: '5px',
        padding: '5px',
        backgroundColor: '#e9e9e9',
        border: '1px solid #ccc',
        borderRadius: '3px',
    },
    error: {
        color: 'red',
        fontWeight: 'bold',
    },
    loading: {
        fontStyle: 'italic',
        color: '#555',
    }
};

// --- Helper Component for Rendering a Single History Entry ---
const HistoryEntry = ({ entry }) => {
    const getFilename = (filePath) => {
        if (!filePath) return 'Unknown Source';
        return filePath.split(/[\\/]/).pop();
    }

    return (
        <div style={styles.historyEntry} data-entry-id={entry.id}>
            <div style={styles.queryText}>You: {entry.query}</div>
            <div style={styles.responseArea} data-testid={`response-area-${entry.id}`}>
                {entry.isLoading && <p style={styles.loading}>Waiting for AI response...</p>}
                {entry.error && <p style={styles.error} data-testid={`query-error-${entry.id}`}>{entry.error}</p>}
                {entry.response && !entry.error && (
                    <>
                        <p>AI: {entry.response.answer}</p>
                        {/* --- MODIFIED: Wrap source nodes in <details> --- */}
                        {entry.response.source_nodes && entry.response.source_nodes.length > 0 && (
                            <details style={styles.sourceNodesArea}>
                                <summary style={styles.detailsSummary}>Sources Used ({entry.response.source_nodes.length})</summary>
                                <div style={styles.detailsContent}>
                                    {entry.response.source_nodes.map((node) => (
                                        <div key={node.id} style={styles.sourceNode}>
                                            <strong>Source:</strong> {getFilename(node.metadata?.file_path)} (Score: {node.score?.toFixed(3) ?? 'N/A'})
                                            <pre style={styles.sourceNodeText}><code>{node.text}</code></pre>
                                        </div>
                                    ))}
                                </div>
                            </details>
                        )}
                        {/* --- END MODIFIED --- */}
                        {entry.response.source_nodes && entry.response.source_nodes.length === 0 && (
                            <p style={styles.sourceNodesArea}><em>(No specific sources retrieved for this answer)</em></p>
                        )}
                    </>
                )}
            </div>
        </div>
    );
};

HistoryEntry.propTypes = {
    entry: PropTypes.shape({
        id: PropTypes.number.isRequired,
        query: PropTypes.string.isRequired,
        response: PropTypes.object, // AIQueryResponse structure
        error: PropTypes.string,
        isLoading: PropTypes.bool,
    }).isRequired,
};
// --- End Helper Component ---


function QueryInterface({ projectId }) {
    const [currentQuery, setCurrentQuery] = useState('');
    const [history, setHistory] = useState([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const nextId = useRef(0);
    const historyEndRef = useRef(null);
    const formRef = useRef(null); // Ref for the form

    useEffect(() => {
        historyEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history]);

    // --- MODIFIED: Extracted submission logic ---
    const processQuery = useCallback(async () => {
        if (!currentQuery.trim() || isProcessing) return;

        const queryText = currentQuery;
        const entryId = nextId.current++;
        const newEntry = {
            id: entryId,
            query: queryText,
            response: null,
            error: null,
            isLoading: true,
        };

        setHistory(prev => [...prev, newEntry]);
        setCurrentQuery('');
        setIsProcessing(true);

        try {
            console.log(`Sending query for project ${projectId}: "${queryText}"`);
            const apiResponse = await queryProjectContext(projectId, { query: queryText });
            console.log("[QueryInterface] Raw API Response:", apiResponse);

            const answerText = apiResponse.data?.answer;
            const isString = typeof answerText === 'string';
            const startsWithError = isString && answerText.trim().startsWith("Error:");

            if (isString && startsWithError) {
                console.warn(`[QueryInterface] Query returned an error message in the answer field.`);
                setHistory(prev => prev.map(entry =>
                    entry.id === entryId ? { ...entry, error: answerText, isLoading: false } : entry
                ));
            } else {
                console.log(`[QueryInterface] Setting response state for entry ${entryId}.`);
                setHistory(prev => prev.map(entry =>
                    entry.id === entryId ? { ...entry, response: apiResponse.data, isLoading: false } : entry
                ));
            }

        } catch (err) {
            console.error("[QueryInterface] Error in API call catch block:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to get response from AI.';
            console.log(`[QueryInterface] Setting error state for entry ${entryId}: "${errorMsg}"`);
            setHistory(prev => prev.map(entry =>
                entry.id === entryId ? { ...entry, error: errorMsg, isLoading: false } : entry
            ));
        } finally {
            console.log("[QueryInterface] Setting isProcessing to false.");
            setIsProcessing(false);
        }
    }, [currentQuery, isProcessing, projectId]); // Dependencies for the callback
    // --- END MODIFIED ---

    // --- Form submit handler ---
    const handleSubmitForm = (e) => {
        e.preventDefault(); // Prevent default form submission
        processQuery(); // Call the extracted logic
    };
    // --- End Form submit handler ---

    // --- ADDED: Ctrl+Enter handler ---
    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && e.ctrlKey && !isProcessing && currentQuery.trim()) {
            e.preventDefault(); // Prevent default Enter behavior (newline)
            processQuery(); // Trigger submission logic
        }
    };
    // --- END ADDED ---

    const handleNewChat = () => {
        setHistory([]);
        setCurrentQuery('');
        setIsProcessing(false);
        nextId.current = 0;
    };

    const historyAreaId = "query-history";
    const isProcessingId = "is-processing";

    return (
        <div style={styles.container}>
        {/* Hidden element to track processing state */}
        <div data-testid={isProcessingId} style={{ display: 'none' }} data-processing={isProcessing ? 'true' : 'false'}></div>
            {history.length > 0 && (
                <div style={styles.historyArea} data-testid={historyAreaId}>
                    {history.map(entry => (
                        <HistoryEntry key={entry.id} entry={entry} />
                    ))}
                    <div ref={historyEndRef} />
                </div>
            )}

            {/* --- MODIFIED: Added ref and onSubmit --- */}
            <form ref={formRef} onSubmit={handleSubmitForm}>
            {/* --- END MODIFIED --- */}
                <textarea
                    style={styles.textarea}
                    value={currentQuery}
                    onChange={(e) => setCurrentQuery(e.target.value)}
                    onKeyDown={handleKeyDown} // Added keydown handler
                    placeholder="Ask a question about your project plan, characters, scenes... (Ctrl+Enter to submit)"
                    disabled={isProcessing}
                    rows={3}
                    aria-label="AI Query Input"
                />
                <br />
                <button
                    type="submit"
                    data-testid="submit-query-button"
                    style={{ ...styles.button, ...(isProcessing && styles.buttonDisabled) }}
                    disabled={isProcessing || !currentQuery.trim()}
                >
                    {isProcessing ? 'Asking AI...' : 'Submit Query'}
                </button>
                <button
                    type="button"
                    data-testid="new-chat-button"
                    onClick={handleNewChat}
                    style={styles.newChatButton}
                    disabled={isProcessing}
                >
                    New Chat
                </button>
            </form>
        </div>
    );
}

QueryInterface.propTypes = {
  projectId: PropTypes.string.isRequired,
};

export default QueryInterface;