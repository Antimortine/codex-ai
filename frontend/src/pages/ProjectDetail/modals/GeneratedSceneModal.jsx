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
    error
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
    error: PropTypes.string
};

export default GeneratedSceneModal;
