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

// Styles for the project header components
const styles = {
    container: {
        display: 'flex',
        flexDirection: 'column',
        marginBottom: '20px'
    },
    titleContainer: {
        display: 'flex',
        alignItems: 'center',
        marginBottom: '10px'
    },
    title: {
        margin: 0,
        padding: 0,
        fontSize: '2em'
    },
    editButton: {
        marginLeft: '15px',
        padding: '5px 10px',
        backgroundColor: '#4285f4',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer'
    },
    inputContainer: {
        display: 'flex',
        alignItems: 'center',
        marginBottom: '10px'
    },
    input: {
        padding: '8px',
        fontSize: '1.2em',
        width: '300px',
        marginRight: '10px'
    },
    saveButton: {
        marginRight: '10px',
        padding: '8px 15px',
        backgroundColor: '#0f9d58',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer'
    },
    cancelButton: {
        padding: '8px 15px',
        backgroundColor: '#db4437',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer'
    },
    disabledButton: {
        opacity: 0.6,
        cursor: 'not-allowed'
    },
    errorMessage: {
        color: 'red',
        marginTop: '5px'
    },
    successMessage: {
        color: 'green',
        marginTop: '5px'
    }
};

/**
 * ProjectHeader component that displays the project title and handles title editing
 */
function ProjectHeader({
    project,
    isLoading,
    isEditingName,
    editedProjectName,
    isSavingName,
    saveNameError,
    saveNameSuccess,
    setEditedProjectName,
    onEditClick,
    onCancelEdit,
    onSave
}) {
    if (isLoading) {
        return <div style={styles.container}><h1 style={styles.title}>Loading project...</h1></div>;
    }

    if (!project) {
        return <div style={styles.container}><h1 style={styles.title}>Project not found</h1></div>;
    }

    return (
        <div style={styles.container}>
            {!isEditingName ? (
                <div style={styles.titleContainer}>
                    <h1 style={styles.title} data-testid="project-title">{project.name}</h1>
                    <button 
                        onClick={onEditClick} 
                        style={styles.editButton}
                        data-testid="edit-project-name-button"
                    >
                        Edit
                    </button>
                </div>
            ) : (
                <div>
                    <div style={styles.inputContainer}>
                        <input
                            type="text"
                            value={editedProjectName}
                            onChange={(e) => setEditedProjectName(e.target.value)}
                            style={styles.input}
                            autoFocus
                            data-testid="project-name-input"
                        />
                        <button
                            onClick={onSave}
                            disabled={!editedProjectName.trim() || isSavingName}
                            style={{
                                ...styles.saveButton,
                                ...((!editedProjectName.trim() || isSavingName) ? styles.disabledButton : {})
                            }}
                            data-testid="save-project-name-button"
                        >
                            {isSavingName ? 'Saving...' : 'Save'}
                        </button>
                        <button
                            onClick={onCancelEdit}
                            disabled={isSavingName}
                            style={{
                                ...styles.cancelButton,
                                ...(isSavingName ? styles.disabledButton : {})
                            }}
                            data-testid="cancel-project-name-edit-button"
                        >
                            Cancel
                        </button>
                    </div>
                    {saveNameError && (
                        <div style={styles.errorMessage} data-testid="save-name-error">
                            {saveNameError}
                        </div>
                    )}
                </div>
            )}
            {saveNameSuccess && (
                <div style={styles.successMessage} data-testid="save-name-success">
                    {saveNameSuccess}
                </div>
            )}
        </div>
    );
}

ProjectHeader.propTypes = {
    project: PropTypes.shape({
        id: PropTypes.string.isRequired,
        name: PropTypes.string.isRequired
    }),
    isLoading: PropTypes.bool.isRequired,
    isEditingName: PropTypes.bool.isRequired,
    editedProjectName: PropTypes.string.isRequired,
    isSavingName: PropTypes.bool.isRequired,
    saveNameError: PropTypes.string,
    saveNameSuccess: PropTypes.string,
    setEditedProjectName: PropTypes.func.isRequired,
    onEditClick: PropTypes.func.isRequired,
    onCancelEdit: PropTypes.func.isRequired,
    onSave: PropTypes.func.isRequired
};

export default ProjectHeader;
