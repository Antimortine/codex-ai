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
    container: {
        maxHeight: '70vh',
        display: 'flex',
        flexDirection: 'column'
    },
    contentContainer: {
        flex: 1,
        overflow: 'auto',
        padding: '15px',
        marginBottom: '15px',
        backgroundColor: '#f9f9f9',
        border: '1px solid #ddd',
        borderRadius: '4px',
        whiteSpace: 'pre-wrap',
        fontSize: '0.95em',
        lineHeight: '1.5'
    },
    buttonContainer: {
        display: 'flex',
        justifyContent: 'space-between'
    },
    closeButton: {
        padding: '10px 15px',
        backgroundColor: '#4285f4',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em'
    },
    copyButton: {
        padding: '10px 15px',
        backgroundColor: '#0f9d58',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em'
    },
    errorMessage: {
        color: 'red',
        marginBottom: '15px'
    },
    copyMessage: {
        color: 'green',
        marginTop: '10px'
    }
};

/**
 * Modal component for showing compiled chapter content
 */
function CompiledContentModal({ content, onClose, error }) {
    const [copySuccess, setCopySuccess] = React.useState('');

    // Handle copying content to clipboard
    const handleCopyToClipboard = () => {
        navigator.clipboard.writeText(content)
            .then(() => {
                setCopySuccess('Content copied to clipboard!');
                // Clear the message after 3 seconds
                setTimeout(() => setCopySuccess(''), 3000);
            })
            .catch(err => {
                console.error('Could not copy text: ', err);
                setCopySuccess('Failed to copy content');
            });
    };

    return (
        <Modal title="Compiled Chapter Content" onClose={onClose}>
            <div style={styles.container}>
                {error && (
                    <div style={styles.errorMessage} data-testid="compile-error">
                        {error}
                    </div>
                )}
                
                <div style={styles.contentContainer} data-testid="compiled-content">
                    {content || 'No content to display'}
                </div>
                
                <div style={styles.buttonContainer}>
                    <button
                        onClick={handleCopyToClipboard}
                        disabled={!content}
                        style={{
                            ...styles.copyButton,
                            ...(!content ? { opacity: 0.6, cursor: 'not-allowed' } : {})
                        }}
                        data-testid="copy-content-button"
                    >
                        Copy to Clipboard
                    </button>
                    
                    <button
                        onClick={onClose}
                        style={styles.closeButton}
                        data-testid="close-modal-button"
                    >
                        Close
                    </button>
                </div>
                
                {copySuccess && (
                    <div style={styles.copyMessage} data-testid="copy-success">
                        {copySuccess}
                    </div>
                )}
            </div>
        </Modal>
    );
}

CompiledContentModal.propTypes = {
    content: PropTypes.string.isRequired,
    onClose: PropTypes.func.isRequired,
    error: PropTypes.string
};

export default CompiledContentModal;
