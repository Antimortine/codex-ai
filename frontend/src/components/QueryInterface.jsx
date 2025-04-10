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

import React, { useState, useRef, useEffect, useCallback } from 'react';
import PropTypes from 'prop-types';
// --- MODIFIED: Import new API functions ---
import { queryProjectContext, getChatHistory, updateChatHistory } from '../api/codexApi';
// --- END MODIFIED ---

// --- REMOVED: LocalStorage Key ---
// const getHistoryStorageKey = (projectId) => `codex-ai-chat-${projectId}`;

// Basic styling (remains the same)
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
    sourceNodesArea: {
        fontSize: '0.9em',
        color: '#555',
    },
    detailsSummary: {
        cursor: 'pointer',
        fontWeight: 'bold',
        marginTop: '10px',
        color: '#444',
    },
    detailsContent: {
        paddingTop: '5px',
    },
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

// --- Helper Component for Rendering a Single History Entry (Unchanged) ---
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
        response: PropTypes.object,
        error: PropTypes.string,
        isLoading: PropTypes.bool,
    }).isRequired,
};
// --- End Helper Component ---


function QueryInterface({ projectId }) {
    const [currentQuery, setCurrentQuery] = useState('');
    const [history, setHistory] = useState([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isLoadingHistory, setIsLoadingHistory] = useState(true); // State for initial history load
    const [historyError, setHistoryError] = useState(null); // State for history load error
    const nextId = useRef(0);
    const historyEndRef = useRef(null);
    const formRef = useRef(null);
    // --- REMOVED: isInitialLoad ref ---
    // const isInitialLoad = useRef(true);

    // --- Load history from Backend on mount ---
    useEffect(() => {
        if (!projectId) return;

        let isMounted = true; // Flag to prevent state update on unmounted component
        setIsLoadingHistory(true);
        setHistoryError(null);
        setHistory([]); // Clear existing history before loading

        console.log(`[QueryInterface] Load Effect: Fetching history for project: ${projectId}`);

        getChatHistory(projectId)
            .then(response => {
                if (isMounted) {
                    const loadedHistory = response.data?.history || [];
                    // Add isLoading: false to each loaded entry
                    const historyWithLoadingState = loadedHistory.map(entry => ({
                        ...entry,
                        isLoading: false
                    }));
                    setHistory(historyWithLoadingState);
                    const maxId = historyWithLoadingState.reduce((max, entry) => Math.max(max, entry.id), -1);
                    nextId.current = maxId + 1;
                    console.log(`[QueryInterface] Load Effect: Loaded ${historyWithLoadingState.length} entries. Next ID: ${nextId.current}`);
                }
            })
            .catch(error => {
                console.error("[QueryInterface] Load Effect: Error fetching history:", error);
                if (isMounted) {
                    // Don't set history on error, show specific error message
                    setHistoryError(`Failed to load chat history: ${error.response?.data?.detail || error.message}`);
                }
            })
            .finally(() => {
                if (isMounted) {
                    setIsLoadingHistory(false);
                }
            });

        // Cleanup function
        return () => {
            isMounted = false;
        };
    }, [projectId]); // Depend only on projectId

    // --- Save history to Backend on change ---
    // Debounce this later if needed, for now save after each query completion
    const saveHistory = useCallback(async (currentHistory) => {
        if (!projectId) return;

        // Don't save if history is currently loading or failed to load
        if (isLoadingHistory || historyError) {
             console.log("[QueryInterface] Save Effect: Skipping save due to loading/error state.");
             return;
        }

        console.log(`[QueryInterface] Save Effect: Saving ${currentHistory.length} history entries for project: ${projectId}`);
        // Prepare data for backend (remove isLoading state)
        const historyToSave = currentHistory.map(({ isLoading, ...entry }) => entry);

        try {
            await updateChatHistory(projectId, { history: historyToSave });
            console.log(`[QueryInterface] Save Effect: History saved successfully.`);
        } catch (error) {
            console.error("[QueryInterface] Save Effect: Error saving history:", error);
            // Maybe show a non-blocking error to the user? For now, just log.
            // setHistoryError(`Failed to save chat history: ${error.response?.data?.detail || error.message}`);
        }
    }, [projectId, isLoadingHistory, historyError]); // Dependencies for the save callback

    // --- Scroll to bottom when history updates ---
    useEffect(() => {
        // Only scroll if there's history to scroll to
        if (history.length > 0) {
            historyEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [history]); // Trigger scroll on history change

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

        // Optimistically update UI
        const updatedHistory = [...history, newEntry];
        setHistory(updatedHistory);
        setCurrentQuery('');
        setIsProcessing(true);

        let finalHistoryState = updatedHistory; // Keep track of the state to save

        try {
            console.log(`Sending query for project ${projectId}: "${queryText}"`);
            const apiResponse = await queryProjectContext(projectId, { query: queryText });
            console.log("[QueryInterface] Raw API Response:", apiResponse);

            const answerText = apiResponse.data?.answer;
            const isString = typeof answerText === 'string';
            const startsWithError = isString && answerText.trim().startsWith("Error:");

            if (isString && startsWithError) {
                console.warn(`[QueryInterface] Query returned an error message in the answer field.`);
                finalHistoryState = updatedHistory.map(entry =>
                    entry.id === entryId ? { ...entry, error: answerText, isLoading: false } : entry
                );
                setHistory(finalHistoryState);
            } else {
                console.log(`[QueryInterface] Setting response state for entry ${entryId}.`);
                finalHistoryState = updatedHistory.map(entry =>
                    entry.id === entryId ? { ...entry, response: apiResponse.data, isLoading: false } : entry
                );
                setHistory(finalHistoryState);
            }

        } catch (err) {
            console.error("[QueryInterface] Error in API call catch block:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to get response from AI.';
            console.log(`[QueryInterface] Setting error state for entry ${entryId}: "${errorMsg}"`);
            finalHistoryState = updatedHistory.map(entry =>
                entry.id === entryId ? { ...entry, error: errorMsg, isLoading: false } : entry
            );
            setHistory(finalHistoryState);
        } finally {
            console.log("[QueryInterface] Setting isProcessing to false.");
            setIsProcessing(false);
            // Save history after processing is complete
            await saveHistory(finalHistoryState);
        }
    }, [currentQuery, isProcessing, projectId, history, saveHistory]); // Added history and saveHistory

    const handleSubmitForm = (e) => {
        e.preventDefault();
        processQuery();
    };

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && e.ctrlKey && !isProcessing && currentQuery.trim()) {
            e.preventDefault();
            processQuery();
        }
    };

    // --- MODIFIED: Clear state and save empty history ---
    const handleNewChat = async () => {
        const newHistoryState = [];
        setHistory(newHistoryState);
        setCurrentQuery('');
        setIsProcessing(false);
        nextId.current = 0;
        // Save the cleared history to the backend
        await saveHistory(newHistoryState);
    };
    // --- END MODIFIED ---

    const historyAreaId = "query-history";
    const isProcessingId = "is-processing";

    return (
        <div style={styles.container}>
            {/* Hidden element to track processing state */}
            <div data-testid={isProcessingId} style={{ display: 'none' }} data-processing={isProcessing ? 'true' : 'false'}></div>

            {/* Display loading/error for initial history fetch */}
            {isLoadingHistory && <p style={styles.loading}>Loading chat history...</p>}
            {historyError && <p style={styles.error}>{historyError}</p>}

            {/* Only show history area if not loading and no error */}
            {!isLoadingHistory && !historyError && history.length > 0 && (
                <div style={styles.historyArea} data-testid={historyAreaId}>
                    {history.map(entry => (
                        <HistoryEntry key={entry.id} entry={entry} />
                    ))}
                    <div ref={historyEndRef} />
                </div>
            )}
             {!isLoadingHistory && !historyError && history.length === 0 && (
                 <p>No chat history yet. Ask a question below!</p>
             )}

            <form ref={formRef} onSubmit={handleSubmitForm}>
                <textarea
                    style={styles.textarea}
                    value={currentQuery}
                    onChange={(e) => setCurrentQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask a question about your project plan, characters, scenes... (Ctrl+Enter to submit)"
                    disabled={isProcessing || isLoadingHistory || !!historyError} // Disable if loading history or error occurred
                    rows={3}
                    aria-label="AI Query Input"
                />
                <br />
                <button
                    type="submit"
                    data-testid="submit-query-button"
                    style={{ ...styles.button, ...((isProcessing || isLoadingHistory || !!historyError) && styles.buttonDisabled) }}
                    disabled={isProcessing || isLoadingHistory || !!historyError || !currentQuery.trim()}
                >
                    {isProcessing ? 'Asking AI...' : 'Submit Query'}
                </button>
                <button
                    type="button"
                    data-testid="new-chat-button"
                    onClick={handleNewChat}
                    style={styles.newChatButton}
                    disabled={isProcessing || isLoadingHistory} // Disable while processing or loading history
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