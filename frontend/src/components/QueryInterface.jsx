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
import { queryProjectContext, getChatHistory, updateChatHistory } from '../api/codexApi';

// Basic styling
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
        resize: 'vertical', // Allow vertical resize
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
        backgroundColor: 'white', // Changed from #f0f0f0 for better contrast
        whiteSpace: 'pre-wrap',
        wordWrap: 'break-word',
        borderRadius: '3px', // Added border radius
        // border: '1px solid #eee', // Optional: add subtle border
        marginTop: '5px', // Add some space below query
    },
    sourceNodesArea: {
        fontSize: '0.9em',
        color: '#555',
        marginTop: '10px', // Ensure space above details
    },
    detailsSummary: {
        cursor: 'pointer',
        fontWeight: 'bold',
        // marginTop: '10px', // Removed, handled by sourceNodesArea margin
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
        fontFamily: 'monospace', // Use monospace for code-like text
        fontSize: '0.85em', // Slightly smaller font
    },
    error: {
        color: 'red',
        fontWeight: 'bold',
    },
    loading: {
        fontStyle: 'italic',
        color: '#555',
    },
    directSourceInfo: {
        fontStyle: 'italic',
        color: '#444',
        marginTop: '10px',
        fontSize: '0.9em',
        borderTop: '1px dotted #ccc',
        paddingTop: '8px',
    },
    directSourceList: { // Style for the list itself
        margin: '0',
        paddingLeft: '20px',
        listStyleType: 'disc', // Use standard bullets
    }
};

// --- Helper Component for Rendering a Single History Entry ---
const HistoryEntry = ({ entry }) => {
    // --- MODIFIED: Helper to get display title/filename ---
    const getSourceDisplay = (metadata) => {
        if (!metadata) return 'Unknown Source';
        const sceneTitle = metadata.document_title; // Scene title or fallback ID
        const filePath = metadata.file_path;
        const filename = filePath ? filePath.split(/[\\/]/).pop() : 'Unknown File';
        const type = metadata.document_type || 'Unknown';
        const chapterTitle = metadata.chapter_title; // Get chapter title
        const chapterId = metadata.chapter_id; // Get chapter ID

        // Prioritize title if it exists and isn't just the scene ID (UUID format check)
        const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
        const titleIsLikelyId = sceneTitle && uuidRegex.test(sceneTitle);
        const displaySceneTitle = (sceneTitle && !titleIsLikelyId) ? `"${sceneTitle}"` : filename;

        // Construct display string based on type
        if (type === 'Scene') {
            const displayChapterTitle = chapterTitle && chapterTitle !== chapterId ? `"${chapterTitle}"` : `Chapter ${chapterId || 'Unknown'}`;
            return `Scene in ${displayChapterTitle}: ${displaySceneTitle}`;
        } else if (type === 'Character') {
            return `Character: "${sceneTitle}"`; // Character title is the name
        } else if (type === 'Plan' || type === 'Synopsis' || type === 'World') {
            return sceneTitle; // Use the predefined titles like 'Project Plan'
        } else if (type === 'Note') {
            return `Note: "${sceneTitle}"`; // Note title is the filename stem
        } else {
            // Fallback for Unknown or other types
            return `${type}: ${displaySceneTitle}`;
        }
    };
    // --- END MODIFIED ---

    const directSources = entry.response?.direct_sources; // Use plural
    const hasDirectSources = directSources && Array.isArray(directSources) && directSources.length > 0;
    const retrievedSources = entry.response?.source_nodes;
    const hasRetrievedSources = retrievedSources && Array.isArray(retrievedSources) && retrievedSources.length > 0;

    return (
        <div style={styles.historyEntry} data-entry-id={entry.id}>
            <div style={styles.queryText}>You: {entry.query}</div>
            <div style={styles.responseArea} data-testid={`response-area-${entry.id}`}>
                {entry.isLoading && <p style={styles.loading}>Waiting for AI response...</p>}
                {entry.error && <p style={styles.error} data-testid={`query-error-${entry.id}`}>{entry.error}</p>}
                {entry.response && !entry.error && (
                    <>
                        {/* AI Answer */}
                        <p style={{ marginTop: 0 }}>AI: {entry.response.answer}</p>

                        {/* Direct Sources Section */}
                        {hasDirectSources && (
                            <div style={styles.directSourceInfo} data-testid={`direct-source-info-${entry.id}`}>
                                <p style={{ margin: '0 0 5px 0', fontWeight: 'bold' }}>
                                    Answer primarily based on directly requested content:
                                </p>
                                <ul style={styles.directSourceList}>
                                    {directSources.map((source, index) => (
                                        <li key={index}>{source.type}: "{source.name}"</li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        {/* Retrieved Sources Section */}
                        {hasRetrievedSources && (
                            <details style={styles.sourceNodesArea}>
                                <summary style={styles.detailsSummary}>
                                    Retrieved Context Snippets ({retrievedSources.length})
                                </summary>
                                <div style={styles.detailsContent}>
                                    {retrievedSources.map((node) => (
                                        <div key={node.id} style={styles.sourceNode}>
                                            {/* --- MODIFIED: Use getSourceDisplay --- */}
                                            <strong>Source:</strong> {getSourceDisplay(node.metadata)} (Score: {node.score?.toFixed(3) ?? 'N/A'})
                                            {/* --- END MODIFIED --- */}
                                            <pre style={styles.sourceNodeText}><code>{node.text}</code></pre>
                                        </div>
                                    ))}
                                </div>
                            </details>
                        )}

                        {/* No Sources Message */}
                        {!hasRetrievedSources && !hasDirectSources && (
                            <p style={styles.sourceNodesArea}><em>(No specific sources retrieved or directly requested for this answer)</em></p>
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
        response: PropTypes.shape({
            answer: PropTypes.string,
            source_nodes: PropTypes.arrayOf(PropTypes.object),
            direct_sources: PropTypes.arrayOf(PropTypes.shape({ // Use plural
                type: PropTypes.string,
                name: PropTypes.string,
            }))
        }),
        error: PropTypes.string,
        isLoading: PropTypes.bool,
    }).isRequired,
};
// --- End Helper Component ---


function QueryInterface({ projectId, activeSessionId }) {
    const [currentQuery, setCurrentQuery] = useState('');
    const [history, setHistory] = useState([]);
    const [isProcessing, setIsProcessing] = useState(false);
    const [isLoadingHistory, setIsLoadingHistory] = useState(true);
    const [historyError, setHistoryError] = useState(null);
    const nextId = useRef(0);
    const historyEndRef = useRef(null);
    const formRef = useRef(null);

    // Updated to include activeSessionId in dependency array and API call
    useEffect(() => {
        if (!projectId || !activeSessionId) return;
        let isMounted = true;
        setIsLoadingHistory(true);
        setHistoryError(null);
        setHistory([]);
        console.log(`[QueryInterface] Load Effect: Fetching history for project: ${projectId}, session: ${activeSessionId}`);
        getChatHistory(projectId, activeSessionId)
            .then(response => {
                if (isMounted) {
                    const loadedHistory = response.data?.history || [];
                    const historyWithLoadingState = loadedHistory.map(entry => ({ ...entry, isLoading: false }));
                    setHistory(historyWithLoadingState);
                    const maxId = historyWithLoadingState.reduce((max, entry) => Math.max(max, entry.id), -1);
                    nextId.current = maxId + 1;
                    console.log(`[QueryInterface] Load Effect: Loaded ${historyWithLoadingState.length} entries. Next ID: ${nextId.current}`);
                }
            })
            .catch(error => {
                console.error("[QueryInterface] Load Effect: Error fetching history:", error);
                if (isMounted) { setHistoryError(`Failed to load chat history for this session: ${error.response?.data?.detail || error.message}`); }
            })
            .finally(() => { if (isMounted) { setIsLoadingHistory(false); } });
        return () => { isMounted = false; };
    }, [projectId, activeSessionId]);

    // Updated to include activeSessionId in dependency array and API call
    const saveHistory = useCallback(async (currentHistory) => {
        if (!projectId || !activeSessionId || isLoadingHistory || historyError) {
            console.log("[QueryInterface] Save Effect: Skipping save.");
            return;
        }
        console.log(`[QueryInterface] Save Effect: Saving ${currentHistory.length} history entries for project: ${projectId}, session: ${activeSessionId}`);
        const historyToSave = currentHistory.map(({ isLoading, ...entry }) => entry);
        try {
            await updateChatHistory(projectId, activeSessionId, { history: historyToSave });
            console.log(`[QueryInterface] Save Effect: History saved successfully.`);
        }
        catch (error) {
            console.error("[QueryInterface] Save Effect: Error saving history:", error);
        }
    }, [projectId, activeSessionId, isLoadingHistory, historyError]);

    // (useEffect for scrolling remains unchanged)
    useEffect(() => { if (history.length > 0) { historyEndRef.current?.scrollIntoView({ behavior: "smooth" }); } }, [history]);

    // (processQuery remains unchanged - it already stores the whole responseData)
    const processQuery = useCallback(async () => {
        if (!currentQuery.trim() || isProcessing) return;
        const queryText = currentQuery;
        const entryId = nextId.current++;
        const newEntry = { id: entryId, query: queryText, response: null, error: null, isLoading: true };
        const updatedHistory = [...history, newEntry];
        setHistory(updatedHistory);
        setCurrentQuery('');
        setIsProcessing(true);
        let finalHistoryState = updatedHistory;
        try {
            console.log(`Sending query for project ${projectId}: "${queryText}"`);
            const apiResponse = await queryProjectContext(projectId, { query: queryText });
            console.log("[QueryInterface] Raw API Response:", apiResponse);
            const responseData = apiResponse.data; // Includes answer, source_nodes, direct_sources
            const answerText = responseData?.answer;
            const isString = typeof answerText === 'string';
            const startsWithError = isString && answerText.trim().startsWith("Error:");
            if (isString && startsWithError) {
                console.warn(`[QueryInterface] Query returned an error message in the answer field.`);
                finalHistoryState = updatedHistory.map(entry => entry.id === entryId ? { ...entry, error: answerText, isLoading: false } : entry);
                setHistory(finalHistoryState);
            } else {
                console.log(`[QueryInterface] Setting response state for entry ${entryId}.`);
                finalHistoryState = updatedHistory.map(entry => entry.id === entryId ? { ...entry, response: responseData, isLoading: false } : entry);
                setHistory(finalHistoryState);
            }
        } catch (err) {
            console.error("[QueryInterface] Error in API call catch block:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to get response from AI.';
            console.log(`[QueryInterface] Setting error state for entry ${entryId}: "${errorMsg}"`);
            finalHistoryState = updatedHistory.map(entry => entry.id === entryId ? { ...entry, error: errorMsg, isLoading: false } : entry);
            setHistory(finalHistoryState);
        } finally {
            console.log("[QueryInterface] Setting isProcessing to false.");
            setIsProcessing(false);
            await saveHistory(finalHistoryState);
        }
    }, [currentQuery, isProcessing, projectId, history, saveHistory]);

    // (Event handlers handleSubmitForm, handleKeyDown, handleNewChat remain unchanged)
    const handleSubmitForm = (e) => { e.preventDefault(); processQuery(); };
    const handleKeyDown = (e) => { if (e.key === 'Enter' && e.ctrlKey && !isProcessing && currentQuery.trim()) { e.preventDefault(); processQuery(); } };
    const handleClearChat = async () => { const newHistoryState = []; setHistory(newHistoryState); setCurrentQuery(''); setIsProcessing(false); nextId.current = 0; await saveHistory(newHistoryState); };

    const historyAreaId = "query-history";
    const isProcessingId = "is-processing";

    // --- Main Return JSX ---
    return (
        <div style={styles.container}>
            {/* Hidden element to track processing state */}
            <div data-testid={isProcessingId} style={{ display: 'none' }} data-processing={isProcessing ? 'true' : 'false'}></div>

            {/* Display loading/error for initial history fetch */}
            {isLoadingHistory && <p style={styles.loading}>Loading chat history...</p>}
            {historyError && <p style={styles.error}>{historyError}</p>}

            {/* History Area */}
            {!isLoadingHistory && !historyError && history.length > 0 && (
                <div style={styles.historyArea} data-testid={historyAreaId}>
                    {history.map(entry => (
                        <HistoryEntry key={entry.id} entry={entry} />
                    ))}
                    <div ref={historyEndRef} /> {/* For scrolling */}
                </div>
            )}
            {/* Empty History Message */}
             {!isLoadingHistory && !historyError && history.length === 0 && (
                 <p>No chat history for this session yet. Ask a question below!</p>
             )}

            {/* Input Form */}
            <form ref={formRef} onSubmit={handleSubmitForm}>
                <textarea
                    style={styles.textarea}
                    value={currentQuery}
                    onChange={(e) => setCurrentQuery(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={activeSessionId ? "Ask a question about your project" : "Select a chat session first"}
                    disabled={isProcessing || isLoadingHistory || !!historyError || !activeSessionId}
                    rows={3}
                    aria-label="AI Query Input"
                />
                <br />
                <button
                    type="submit"
                    data-testid="submit-query-button"
                    style={{ ...styles.button, ...((isProcessing || isLoadingHistory || !!historyError || !currentQuery.trim()) && styles.buttonDisabled) }} // Combined disabled condition
                    disabled={isProcessing || isLoadingHistory || !!historyError || !currentQuery.trim()}
                >
                    {isProcessing ? 'Asking AI...' : 'Submit Query'}
                </button>
                <button
                    type="button"
                    data-testid="clear-chat-button"
                    onClick={handleClearChat}
                    style={{...styles.newChatButton, ...((isProcessing || isLoadingHistory || historyError) && styles.buttonDisabled)}} // Apply disabled style
                    disabled={isProcessing || isLoadingHistory || historyError}
                >
                    Clear Chat
                </button>
            </form>
        </div>
    );
}

QueryInterface.propTypes = {
  projectId: PropTypes.string.isRequired,
  activeSessionId: PropTypes.string,
};

export default QueryInterface;