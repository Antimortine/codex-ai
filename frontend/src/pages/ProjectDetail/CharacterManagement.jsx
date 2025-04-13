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

// Styles for the character management components
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
    newCharacterForm: {
        display: 'flex',
        marginTop: '10px',
        marginBottom: '20px'
    },
    input: {
        padding: '8px',
        fontSize: '1em',
        width: '250px',
        marginRight: '10px'
    },
    addButton: {
        padding: '8px 15px',
        backgroundColor: '#0f9d58',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer'
    },
    disabledButton: {
        opacity: 0.6,
        cursor: 'not-allowed'
    },
    characterList: {
        listStyle: 'none',
        padding: 0,
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
        gap: '15px'
    },
    characterItem: {
        padding: '15px',
        borderRadius: '4px',
        backgroundColor: '#f5f5f5',
        border: '1px solid #ddd',
        display: 'flex',
        flexDirection: 'column'
    },
    characterName: {
        margin: '0 0 10px 0',
        fontSize: '1.1em'
    },
    deleteButton: {
        marginTop: 'auto',
        padding: '5px 10px',
        backgroundColor: '#db4437',
        color: 'white',
        border: 'none',
        borderRadius: '4px',
        cursor: 'pointer',
        fontSize: '0.9em',
        width: 'fit-content'
    },
    errorMessage: {
        color: 'red',
        marginTop: '5px'
    }
};

/**
 * CharacterManagement component that handles character listing, creation, and deletion
 */
function CharacterManagement({
    projectId,
    characters,
    isLoading,
    newCharacterName,
    setNewCharacterName,
    onCreateCharacter,
    onDeleteCharacter,
    characterError,
    isAnyOperationLoading
}) {
    // Handle new character form submission
    const handleSubmit = (e) => {
        e.preventDefault();
        onCreateCharacter();
    };

    return (
        <section style={styles.container}>
            <div style={styles.header}>
                <h2 style={styles.heading}>Characters</h2>
            </div>
            
            {/* New character form */}
            <form onSubmit={handleSubmit} style={styles.newCharacterForm}>
                <input
                    type="text"
                    value={newCharacterName}
                    onChange={(e) => setNewCharacterName(e.target.value)}
                    placeholder="New character name"
                    style={styles.input}
                    data-testid="new-character-input"
                />
                <button
                    type="submit"
                    disabled={!newCharacterName.trim() || isAnyOperationLoading}
                    style={{
                        ...styles.addButton,
                        ...((!newCharacterName.trim() || isAnyOperationLoading) ? styles.disabledButton : {})
                    }}
                    data-testid="add-character-button"
                >
                    Add Character
                </button>
            </form>
            
            {/* Display any error messages */}
            {characterError && (
                <div style={styles.errorMessage} data-testid="character-error">
                    {characterError}
                </div>
            )}
            
            {/* Character list */}
            {isLoading ? (
                <p>Loading characters...</p>
            ) : characters.length === 0 ? (
                <p>No characters yet. Add your first character to get started.</p>
            ) : (
                <ul style={styles.characterList}>
                    {characters.map(character => (
                        <li key={character.id} style={styles.characterItem}>
                            <h3 style={styles.characterName}>
                                <Link to={`/projects/${projectId}/characters/${character.id}`}>
                                    {character.name}
                                </Link>
                            </h3>
                            <button
                                onClick={() => onDeleteCharacter(character.id)}
                                disabled={isAnyOperationLoading}
                                style={{
                                    ...styles.deleteButton,
                                    ...(isAnyOperationLoading ? styles.disabledButton : {})
                                }}
                                data-testid={`delete-character-button-${character.id}`}
                            >
                                Delete
                            </button>
                        </li>
                    ))}
                </ul>
            )}
        </section>
    );
}

CharacterManagement.propTypes = {
    projectId: PropTypes.string.isRequired,
    characters: PropTypes.array.isRequired,
    isLoading: PropTypes.bool.isRequired,
    newCharacterName: PropTypes.string.isRequired,
    setNewCharacterName: PropTypes.func.isRequired,
    onCreateCharacter: PropTypes.func.isRequired,
    onDeleteCharacter: PropTypes.func.isRequired,
    characterError: PropTypes.string,
    isAnyOperationLoading: PropTypes.bool.isRequired
};

export default CharacterManagement;
