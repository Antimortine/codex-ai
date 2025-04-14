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

// Basic styles for placeholder
const styles = {
  node: {
    marginLeft: '20px',
    padding: '5px 0',
  },
  folder: {
    fontWeight: 'bold',
    cursor: 'pointer', // Indicate interactivity later
  },
  noteLink: {
    textDecoration: 'none',
    color: '#007bff',
  },
  actions: {
    marginLeft: '10px',
    fontSize: '0.8em',
    display: 'inline-flex', // Keep actions on the same line
    gap: '5px', // Add space between action buttons
  },
  actionButton: {
    padding: '2px 5px',
    cursor: 'pointer',
    border: '1px solid #ccc',
    borderRadius: '3px',
    backgroundColor: '#f8f9fa',
  },
  disabledButton: {
    cursor: 'not-allowed',
    opacity: 0.6,
  },
};

/**
 * Recursive function to render tree nodes.
 * This is a basic placeholder and will be replaced with a proper tree library or implementation.
 */
const renderNode = (node, projectId, handlers, isBusy) => {
  const {
    onCreateNote,
    onCreateFolder, // Placeholder for now
    onRenameFolder, // Placeholder for now
    onDeleteFolder, // Placeholder for now
    onDeleteNote,
    onMoveNote, // Placeholder for now
  } = handlers;

  return (
    <div key={node.id} style={styles.node}>
      {node.type === 'folder' ? (
        <div>
          <span style={styles.folder} title={`Path: ${node.path}`}>
            📁 {node.name}
          </span>
          <span style={styles.actions}>
            <button
              onClick={() => onCreateNote(node.path)} // Pass folder path
              style={{ ...styles.actionButton, ...(isBusy ? styles.disabledButton : {}) }}
              disabled={isBusy}
              title="Create Note Here"
            >
              + Note
            </button>
            {/* Add Folder/Rename/Delete buttons later */}
             <button
               onClick={() => onDeleteFolder(node.path)}
               style={{ ...styles.actionButton, backgroundColor: '#ffdddd', ...(isBusy ? styles.disabledButton : {}) }}
               disabled={isBusy || node.path === '/'} // Cannot delete root
               title="Delete Folder"
             >
               🗑️ Folder
             </button>
          </span>
          {/* Recursively render children */}
          {node.children && node.children.map(child => renderNode(child, projectId, handlers, isBusy))}
        </div>
      ) : (
        <div>
          <span>📄 </span>
          <Link
            to={`/projects/${projectId}/notes/${node.note_id}`}
            style={styles.noteLink}
            title={`Path: ${node.path}\nLast Modified: ${node.last_modified ? new Date(node.last_modified * 1000).toLocaleString() : 'N/A'}`}
          >
            {node.name}
          </Link>
           <span style={styles.actions}>
             <button
               onClick={() => onDeleteNote(node.note_id, node.name)}
               style={{ ...styles.actionButton, backgroundColor: '#ffdddd', ...(isBusy ? styles.disabledButton : {}) }}
               disabled={isBusy}
               title="Delete Note"
             >
                🗑️ Note
             </button>
             {/* Add Move button later */}
           </span>
        </div>
      )}
    </div>
  );
};

/**
 * NoteTreeViewer Component - Renders the hierarchical note structure.
 */
function NoteTreeViewer({ projectId, treeData, handlers, isBusy }) {
  if (!treeData || treeData.length === 0) {
    return <div>No notes or folders found.</div>;
  }

  return (
    <div>
      {/* Render top-level nodes */}
      {treeData.map(node => renderNode(node, projectId, handlers, isBusy))}
    </div>
  );
}

NoteTreeViewer.propTypes = {
  projectId: PropTypes.string.isRequired,
  treeData: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    type: PropTypes.oneOf(['folder', 'note']).isRequired,
    path: PropTypes.string.isRequired,
    children: PropTypes.array, // Recursive definition handled by PropTypes.array
    note_id: PropTypes.string,
    last_modified: PropTypes.number,
  })).isRequired,
  handlers: PropTypes.shape({
      onCreateNote: PropTypes.func.isRequired,
      onCreateFolder: PropTypes.func.isRequired, // Placeholder
      onRenameFolder: PropTypes.func.isRequired, // Placeholder
      onDeleteFolder: PropTypes.func.isRequired,
      onDeleteNote: PropTypes.func.isRequired,
      onMoveNote: PropTypes.func.isRequired, // Placeholder
  }).isRequired,
  isBusy: PropTypes.bool,
};

NoteTreeViewer.defaultProps = {
  isBusy: false,
};


export default NoteTreeViewer;