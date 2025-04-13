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
    textarea: {
        width: '100%',
        height: '200px',
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
        justifyContent: 'space-between',
        marginBottom: '20px'
    },
    actionButton: {
        padding: '10px 15px',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em'
    },
    splitButton: {
        backgroundColor: '#4285f4',
        color: 'white'
    },
    createButton: {
        backgroundColor: '#0f9d58',
        color: 'white'
    },
    cancelButton: {
        backgroundColor: '#db4437',
        color: 'white'
    },
    disabledButton: {
        opacity: 0.6,
        cursor: 'not-allowed'
    },
    errorMessage: {
        color: 'red',
        marginBottom: '15px'
    },
    splitResult: {
        marginTop: '20px',
        borderTop: '1px solid #eee',
        paddingTop: '15px'
    },
    splitItemContainer: {
        marginBottom: '20px',
        padding: '15px',
        borderRadius: '4px',
        backgroundColor: '#f9f9f9',
        border: '1px solid #ddd'
    },
    splitItemTitle: {
        margin: '0 0 10px 0',
        fontSize: '1.2em',
        fontWeight: 'bold'
    },
    splitItemContent: {
        whiteSpace: 'pre-wrap',
        fontSize: '0.95em',
        padding: '10px',
        backgroundColor: 'white',
        border: '1px solid #eee',
        borderRadius: '4px',
        maxHeight: '150px',
        overflow: 'auto'
    }
};

/**
 * Modal component for splitting chapter content into scenes
 */
function SplitChapterModal({
    chapterId,
    inputContent,
    onInputChange,
    proposedSplits,
    onSplit,
    onCreateScenes,
    onClose,
    isSplitting,
    isCreating,
    splitError,
    createError
}) {
    return (
        <Modal title="Split Chapter into Scenes" onClose={onClose}>
            <div>
                <h3>Enter or paste your chapter content to split into scenes</h3>
                
                {splitError && (
                    <div style={styles.errorMessage} data-testid="split-error">
                        {splitError}
                    </div>
                )}
                
                {createError && (
                    <div style={styles.errorMessage} data-testid="create-from-split-error">
                        {createError}
                    </div>
                )}
                
                <textarea
                    value={inputContent}
                    onChange={(e) => onInputChange(e.target.value)}
                    placeholder="Enter chapter content here..."
                    style={styles.textarea}
                    data-testid="split-input-content"
                />
                
                <div style={styles.buttonContainer}>
                    <button
                        onClick={onSplit}
                        disabled={!inputContent.trim() || isSplitting || isCreating}
                        style={{
                            ...styles.actionButton,
                            ...styles.splitButton,
                            ...((!inputContent.trim() || isSplitting || isCreating) ? styles.disabledButton : {})
                        }}
                        data-testid="split-content-button"
                    >
                        {isSplitting ? 'Splitting...' : 'Split Content'}
                    </button>
                    
                    {proposedSplits.length > 0 && (
                        <button
                            onClick={onCreateScenes}
                            disabled={isSplitting || isCreating}
                            style={{
                                ...styles.actionButton,
                                ...styles.createButton,
                                ...((isSplitting || isCreating) ? styles.disabledButton : {})
                            }}
                            data-testid="create-scenes-from-split-button"
                        >
                            {isCreating ? 'Creating Scenes...' : 'Create Scenes'}
                        </button>
                    )}
                    
                    <button
                        onClick={onClose}
                        disabled={isSplitting || isCreating}
                        style={{
                            ...styles.actionButton,
                            ...styles.cancelButton,
                            ...((isSplitting || isCreating) ? styles.disabledButton : {})
                        }}
                        data-testid="cancel-split-button"
                    >
                        Cancel
                    </button>
                </div>
                
                {/* Display proposed splits */}
                {proposedSplits.length > 0 && (
                    <div style={styles.splitResult}>
                        <h3>Proposed Scenes ({proposedSplits.length})</h3>
                        <p>Review the proposed scenes below. Click 'Create Scenes' to add them to your chapter.</p>
                        
                        {proposedSplits.map((split, index) => (
                            <div key={index} style={styles.splitItemContainer}>
                                <h4 style={styles.splitItemTitle}>
                                    {split.title || `Scene ${index + 1}`}
                                </h4>
                                <div style={styles.splitItemContent}>
                                    {split.content || 'No content'}
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </Modal>
    );
}

SplitChapterModal.propTypes = {
    chapterId: PropTypes.string.isRequired,
    inputContent: PropTypes.string.isRequired,
    onInputChange: PropTypes.func.isRequired,
    proposedSplits: PropTypes.array.isRequired,
    onSplit: PropTypes.func.isRequired,
    onCreateScenes: PropTypes.func.isRequired,
    onClose: PropTypes.func.isRequired,
    isSplitting: PropTypes.bool.isRequired,
    isCreating: PropTypes.bool.isRequired,
    splitError: PropTypes.string,
    createError: PropTypes.string
};

export default SplitChapterModal;
