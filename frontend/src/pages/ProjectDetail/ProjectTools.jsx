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
import { Link } from 'react-router-dom';

// Styles for the project tools components
const styles = {
    container: {
        marginBottom: '20px'
    },
    header: {
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center'
    },
    heading: {
        margin: 0
    },
    buttonContainer: {
        display: 'flex',
        flexWrap: 'wrap',
        gap: '10px',
        marginTop: '15px'
    },
    toolButton: {
        padding: '10px 15px',
        backgroundColor: '#4285f4',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em'
    },
    linkButton: {
        padding: '10px 15px',
        backgroundColor: '#0f9d58', // Green color for links
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '1em',
        textDecoration: 'none',
        display: 'inline-block'
    },
    disabledButton: {
        opacity: 0.6,
        cursor: 'not-allowed'
    },
    errorMessage: {
        color: 'red',
        marginTop: '10px'
    },
    successMessage: {
        color: 'green',
        marginTop: '10px'
    }
};

/**
 * ProjectTools component that provides utilities for project management
 */
function ProjectTools({
    projectId,
    isRebuildingIndex,
    rebuildError,
    rebuildSuccessMessage,
    onRebuildIndex,
    isAnyOperationLoading // Used to disable rebuild if other ops are running
}) {
    return (
        <section style={styles.container}>
            <div style={styles.header}>
                <h2 style={styles.heading}>Project Tools</h2>
            </div>

            <div style={styles.buttonContainer}>
                {/* Rebuild Index Button */}
                <button
                    onClick={onRebuildIndex}
                    disabled={isRebuildingIndex || isAnyOperationLoading}
                    style={{
                        ...styles.toolButton, // Blue color for actions
                        ...(isRebuildingIndex || isAnyOperationLoading ? styles.disabledButton : {})
                    }}
                    data-testid="rebuild-index-button"
                >
                    {isRebuildingIndex ? 'Rebuilding Index...' : 'Rebuild Search Index'}
                </button>

                {/* Query Project AI Link */}
                <Link
                    to={`/projects/${projectId}/query`}
                    style={styles.linkButton}
                    data-testid="query-link"
                >
                    Query Project AI
                </Link>

                {/* Project Notes Link - ADDED */}
                <Link
                    to={`/projects/${projectId}/notes`}
                    style={styles.linkButton}
                    data-testid="notes-link"
                >
                    Project Notes
                </Link>
                {/* END ADDED */}

                {/* Placeholder for Timeline Link (if implemented later) */}
                {/*
                <Link
                    to={`/projects/${projectId}/timeline`}
                    style={styles.linkButton}
                    data-testid="timeline-link"
                >
                    View Timeline
                </Link>
                */}

            </div>

            {/* Display error or success messages for Rebuild Index */}
            {rebuildError && (
                <div style={styles.errorMessage} data-testid="rebuild-error">
                    {rebuildError}
                </div>
            )}

            {rebuildSuccessMessage && (
                <div style={styles.successMessage} data-testid="rebuild-success">
                    {rebuildSuccessMessage}
                </div>
            )}
        </section>
    );
}

ProjectTools.propTypes = {
    projectId: PropTypes.string.isRequired,
    isRebuildingIndex: PropTypes.bool.isRequired,
    rebuildError: PropTypes.string,
    rebuildSuccessMessage: PropTypes.string,
    onRebuildIndex: PropTypes.func.isRequired,
    isAnyOperationLoading: PropTypes.bool.isRequired
};

export default ProjectTools;