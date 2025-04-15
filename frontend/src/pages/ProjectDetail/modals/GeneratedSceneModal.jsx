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
import PropTypes from 'prop-types';
import Modal from '../../../components/Modal';

// Styles for the modal components
const styles = {
    sourcesSection: {
        marginTop: '15px',
        marginBottom: '15px',
        backgroundColor: '#f5f5f5',
        padding: '10px',
        borderRadius: '4px',
        border: '1px solid #e0e0e0',
    },
    sourceItem: {
        marginBottom: '5px',
        borderLeft: '3px solid #ddd',
        paddingLeft: '10px',
    },
    sourceList: {
        margin: '10px 0',
        paddingLeft: '20px',
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
        fontFamily: 'monospace',
        fontSize: '0.85em',
    },
    detailsSummary: {
        cursor: 'pointer',
        fontWeight: 'bold',
        marginBottom: '10px',
        userSelect: 'none',
    },
    detailsContent: {
        marginLeft: '15px',
    },
    input: {
        width: '100%',
        padding: '10px',
        marginBottom: '15px',
        fontSize: '1em',
        borderRadius: '4px',
        border: '1px solid #ccc'
    },
    textarea: {
        width: '100%',
        height: '300px',
        padding: '10px',
        marginBottom: '15px',
        fontSize: '1em',
        borderRadius: '4px',
        border: '1px solid #ccc',
        resize: 'vertical',
        fontFamily: 'inherit'
    },
    buttonContainer: {
        display: 'flex',
        justifyContent: 'space-between'
    },
    saveButton: {
        padding: '10px 15px',
        backgroundColor: '#0f9d58',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em'
    },
    cancelButton: {
        padding: '10px 15px',
        backgroundColor: '#db4437',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em'
    },
    disabledButton: {
        opacity: 0.6,
        cursor: 'not-allowed'
    },
    errorMessage: {
        color: 'red',
        marginBottom: '15px'
    }
};

/**
 * Modal component for creating a scene from AI-generated content
 */
function GeneratedSceneModal({
    sceneTitle,
    sceneContent,
    onTitleChange,
    onContentChange,
    onSave,
    onClose,
    isCreating,
    error,
    sources = { source_nodes: [], direct_sources: [] }
}) {
    return (
        <Modal title="Create Scene from Generated Draft" onClose={onClose}>
            <div>
                <h3>Edit the scene draft before saving</h3>
                
                {error && (
                    <div style={styles.errorMessage} data-testid="create-scene-error">
                        {error}
                    </div>
                )}
                
                <label htmlFor="scene-title">Scene Title:</label>
                <input
                    id="scene-title"
                    type="text"
                    value={sceneTitle}
                    onChange={(e) => onTitleChange(e.target.value)}
                    style={styles.input}
                    data-testid="generated-scene-title-input"
                />
                
                <label htmlFor="scene-content">Scene Content:</label>
                <textarea
                    id="scene-content"
                    value={sceneContent}
                    onChange={(e) => onContentChange(e.target.value)}
                    style={styles.textarea}
                    data-testid="generated-scene-content-input"
                />
                
                {/* Sources Section - always display the section */}
                <div style={styles.sourcesSection}>
                    <h4 style={{ marginTop: 0 }}>Scene Generation Sources</h4>
                    
                    {/* Log all source information for debugging */}
                    {console.log('GeneratedSceneModal - ALL sources:', sources)}
                    {console.log('GeneratedSceneModal - Direct sources object type:', typeof sources.direct_sources)}
                    {console.log('GeneratedSceneModal - Is direct_sources array?', Array.isArray(sources.direct_sources))}
                    
                    {/* EMERGENCY FIX: Check for direct sources in our global variable */}
                    {console.log('GeneratedSceneModal - Checking global sources:', window.__LATEST_SELECTED_SOURCES || [])}
                    
                    {/* Direct Sources - ALWAYS SHOW THIS SECTION */}
                    <div>
                        <p style={{ fontWeight: 'bold', marginBottom: '5px' }}>
                            Direct Sources Used:
                        </p>
                        {(() => {
                            // EMERGENCY FIX: Try several approaches to find direct sources
                            // Option 1: Check if we have direct_sources in the sources prop
                            if (Array.isArray(sources.direct_sources) && sources.direct_sources.length > 0) {
                                return (
                                    <ul style={styles.sourceList}>
                                        {sources.direct_sources.map((source, index) => (
                                            <li key={index}>
                                                {typeof source === 'string' 
                                                    ? source 
                                                    : `${source.type || 'Item'}: "${source.name || source.title || 'Unknown'}"`}
                                            </li>
                                        ))}
                                    </ul>
                                );
                            }
                            
                            // Option 2: Check our global variable as a last resort
                            const globalSources = window.__LATEST_SELECTED_SOURCES || [];
                            if (globalSources.length > 0) {
                                return (
                                    <ul style={styles.sourceList}>
                                        {globalSources.map((source, index) => (
                                            <li key={index}>{source}</li>
                                        ))}
                                    </ul>
                                );
                            }
                            
                            // If all else fails, show the empty message
                            return <p style={{ fontStyle: 'italic' }}>No direct sources were used for this generation.</p>;
                        })()} {/* Execute the function immediately */}
                    </div>
                        
                        {/* Retrieved Sources */}
                        {Array.isArray(sources.source_nodes) && sources.source_nodes.length > 0 && (
                            <details>
                                <summary style={styles.detailsSummary}>
                                    Retrieved Context Snippets ({sources.source_nodes.length})
                                </summary>
                                <div style={styles.detailsContent}>
                                    {sources.source_nodes.map((node, index) => (
                                        <div key={index} style={styles.sourceItem}>
                                            <strong>Source:</strong> {node.metadata?.document_title || node.metadata?.document_type || node.metadata?.file_path?.split('/').pop() || 'Unknown'}
                                            {node.score !== undefined && ` (Score: ${node.score.toFixed(3)})`}
                                            <pre style={styles.sourceNodeText}><code>{node.text}</code></pre>
                                        </div>
                                    ))}
                                </div>
                            </details>
                        )}
                </div>
                
                <div style={styles.buttonContainer}>
                    <button
                        onClick={onSave}
                        disabled={!sceneTitle.trim() || isCreating}
                        style={{
                            ...styles.saveButton,
                            ...((!sceneTitle.trim() || isCreating) ? styles.disabledButton : {})
                        }}
                        data-testid="save-generated-scene-button"
                    >
                        {isCreating ? 'Creating Scene...' : 'Create Scene'}
                    </button>
                    
                    <button
                        onClick={onClose}
                        disabled={isCreating}
                        style={{
                            ...styles.cancelButton,
                            ...(isCreating ? styles.disabledButton : {})
                        }}
                        data-testid="cancel-generated-scene-button"
                    >
                        Cancel
                    </button>
                </div>
            </div>
        </Modal>
    );
}

GeneratedSceneModal.propTypes = {
    sceneTitle: PropTypes.string.isRequired,
    sceneContent: PropTypes.string.isRequired,
    onTitleChange: PropTypes.func.isRequired,
    onContentChange: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired,
    onClose: PropTypes.func.isRequired,
    isCreating: PropTypes.bool.isRequired,
    error: PropTypes.string,
    sources: PropTypes.shape({
        source_nodes: PropTypes.array,
        direct_sources: PropTypes.array
    })
};

export default GeneratedSceneModal;
