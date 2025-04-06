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

import React, { useState } from 'react';
import PropTypes from 'prop-types'; // Import PropTypes
import { queryProjectContext } from '../api/codexApi'; // Import the API function

// Basic styling (can be moved to CSS file)
const styles = {
    container: {
        border: '1px solid #ccc',
        borderRadius: '5px',
        padding: '15px',
        marginTop: '20px',
        backgroundColor: '#f9f9f9',
    },
    textarea: {
        width: '95%', // Adjust width as needed
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
    },
    buttonDisabled: {
        backgroundColor: '#aaa',
        cursor: 'not-allowed',
    },
    responseArea: {
        marginTop: '15px',
        padding: '10px',
        border: '1px dashed #eee',
        backgroundColor: 'white',
        whiteSpace: 'pre-wrap', // Preserve whitespace and newlines in answer
        wordWrap: 'break-word', // Break long words
    },
    sourceNodesArea: {
        marginTop: '10px',
        fontSize: '0.9em',
        color: '#555',
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
        maxHeight: '100px', // Limit height of snippet
        overflowY: 'auto', // Add scroll if snippet is long
        display: 'block', // Ensure block display for scroll
        marginTop: '5px',
        padding: '5px',
        backgroundColor: '#e9e9e9',
        border: '1px solid #ccc',
        borderRadius: '3px',
    },
    error: {
        color: 'red',
        marginTop: '10px',
    },
    loading: {
        marginTop: '10px',
        fontStyle: 'italic',
        color: '#555',
    }
};

function QueryInterface({ projectId }) {
    const [query, setQuery] = useState('');
    const [response, setResponse] = useState(null); // Stores { answer: string, source_nodes: [] }
    const [isLoading, setIsLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleSubmitQuery = async (e) => {
        e.preventDefault();
        if (!query.trim() || isLoading) return;

        setIsLoading(true);
        setError(null);
        setResponse(null); // Clear previous response

        try {
            console.log(`Sending query for project ${projectId}: "${query}"`);
            const apiResponse = await queryProjectContext(projectId, { query: query });
            console.log("API Response received:", apiResponse.data);
            setResponse(apiResponse.data); // Expecting { answer: "...", source_nodes: [...] }
        } catch (err) {
            console.error("Error querying project context:", err);
            const errorMsg = err.response?.data?.detail || err.message || 'Failed to get response from AI.';
            setError(errorMsg);
            setResponse(null);
        } finally {
            setIsLoading(false);
        }
    };

    // Helper to extract filename from path
    const getFilename = (filePath) => {
        if (!filePath) return 'Unknown Source';
        // Basic filename extraction, handles both / and \
        return filePath.split(/[\\/]/).pop();
    }

    return (
        <div style={styles.container}>
            <h3>Ask AI about this Project</h3>
            <form onSubmit={handleSubmitQuery}>
                <textarea
                    style={styles.textarea}
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask a question about your project plan, characters, scenes..."
                    disabled={isLoading}
                    rows={3} // Start with 3 rows
                />
                <br />
                <button
                    type="submit"
                    style={{ ...styles.button, ...(isLoading && styles.buttonDisabled) }}
                    disabled={isLoading || !query.trim()}
                >
                    {isLoading ? 'Asking AI...' : 'Submit Query'}
                </button>
            </form>

            {isLoading && <p style={styles.loading}>Waiting for AI response...</p>}
            {error && <p style={styles.error}>Error: {error}</p>}

            {response && (
                <div style={styles.responseArea}>
                    <h4>AI Answer:</h4>
                    <p>{response.answer}</p>

                    {response.source_nodes && response.source_nodes.length > 0 && (
                        <div style={styles.sourceNodesArea}>
                            <h5>Sources Used:</h5>
                            {response.source_nodes.map((node) => (
                                <div key={node.id} style={styles.sourceNode}>
                                    <strong>Source:</strong> {getFilename(node.metadata?.file_path)} (Score: {node.score?.toFixed(3) ?? 'N/A'})
                                    <pre style={styles.sourceNodeText}><code>{node.text}</code></pre>
                                </div>
                            ))}
                        </div>
                    )}
                     {response.source_nodes && response.source_nodes.length === 0 && (
                         <p style={styles.sourceNodesArea}><em>(No specific sources retrieved for this answer)</em></p>
                     )}
                </div>
            )}
        </div>
    );
}

// Add PropTypes for projectId
QueryInterface.propTypes = {
  projectId: PropTypes.string.isRequired,
};

export default QueryInterface;