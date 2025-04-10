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
import { queryProjectContext } from '../api/codexApi';

// --- LocalStorage Key ---
const getHistoryStorageKey = (projectId) => `codex-ai-chat-${projectId}`;

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
    const nextId = useRef(0);
    const historyEndRef = useRef(null);
    const formRef = useRef(null);
    // --- MODIFIED: Initialize isInitialLoad to true ---
    const isInitialLoad = useRef(true);
    // --- END MODIFIED ---

    // --- Load history from LocalStorage on mount ---
    useEffect(() => {
        if (!projectId) return;

        console.log(`[QueryInterface] Load Effect: Attempting load for project: ${projectId}`);
        const storageKey = getHistoryStorageKey(projectId);
        let loadedHistoryData = []; // Default to empty
        let loadedNextId = 0;

        try {
            const storedHistory = localStorage.getItem(storageKey);
            if (storedHistory) {
                const parsedHistory = JSON.parse(storedHistory);
                if (Array.isArray(parsedHistory)) {
                    loadedHistoryData = parsedHistory.map(entry => ({
                        ...entry,
                        isLoading: false // Ensure loading is false on load
                    }));
                    const maxId = loadedHistoryData.reduce((max, entry) => Math.max(max, entry.id), -1);
                    loadedNextId = maxId + 1;
                    console.log(`[QueryInterface] Load Effect: Loaded ${loadedHistoryData.length} entries. Next ID: ${loadedNextId}`);
                } else {
                    console.warn(`[QueryInterface] Load Effect: Invalid history data found for key ${storageKey}. Resetting.`);
                    localStorage.removeItem(storageKey);
                }
            } else {
                console.log(`[QueryInterface] Load Effect: No history found for key ${storageKey}.`);
            }
        } catch (error) {
            console.error("[QueryInterface] Load Effect: Error loading/parsing history:", error);
        }

        // Set state *after* reading/parsing
        setHistory(loadedHistoryData);
        nextId.current = loadedNextId;

        // --- MODIFIED: Set flag *after* state updates are scheduled ---
        // Use setTimeout to ensure this runs after the current render cycle completes
        const timerId = setTimeout(() => {
            console.log("[QueryInterface] Load Effect: Marking initial load as complete.");
            isInitialLoad.current = false;
        }, 0);

        // Cleanup function for the timeout
        return () => clearTimeout(timerId);
        // --- END MODIFIED ---

    }, [projectId]); // Depend only on projectId

    // --- Save history to LocalStorage on change ---
    useEffect(() => {
        // --- MODIFIED: Check flag *inside* the effect ---
        if (!projectId || isInitialLoad.current) {
            console.log(`[QueryInterface] Save Effect: Skipping save for project ${projectId}, initial load flag: ${isInitialLoad.current}`);
            return; // Don't save during initial load phase or if projectId is missing
        }
        // --- END MODIFIED ---

        console.log(`[QueryInterface] Save Effect: Saving ${history.length} history entries for project: ${projectId}`);
        const storageKey = getHistoryStorageKey(projectId);
        try {
            localStorage.setItem(storageKey, JSON.stringify(history));
        } catch (error) {
            console.error("[QueryInterface] Save Effect: Error saving history:", error);
        }
    }, [history, projectId]); // Depend on history and projectId

    // --- Scroll to bottom when history updates ---
    useEffect(() => {
        historyEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [history]);

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
    }, [currentQuery, isProcessing, projectId]);

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

    const handleNewChat = () => {
        setHistory([]);
        setCurrentQuery('');
        setIsProcessing(false);
        nextId.current = 0;
        if (projectId) {
            const storageKey = getHistoryStorageKey(projectId);
            try {
                localStorage.removeItem(storageKey);
                console.log(`[QueryInterface] Cleared history from LocalStorage for key ${storageKey}.`);
            } catch (error) {
                console.error("[QueryInterface] Error clearing history from LocalStorage:", error);
            }
        }
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

            <form ref={formRef} onSubmit={handleSubmitForm}>
                <textarea
                    style={styles.textarea}
                    value={currentQuery}
                    onChange={(e) => setCurrentQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
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