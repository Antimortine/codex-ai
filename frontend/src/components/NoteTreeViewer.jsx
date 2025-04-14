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

import React, { useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { Tree } from 'react-arborist';
import { useNavigate } from 'react-router-dom';

// --- Icons ---
const FolderIcon = ({ isOpen }) => <span style={{ marginRight: '5px' }}>{isOpen ? '📂' : '📁'}</span>;
const NoteIcon = () => <span style={{ marginRight: '5px' }}>📄</span>;
const MoveIcon = () => <span>➔</span>; // Simple move icon

// --- Custom Node Renderer ---
function Node({ node, style, dragHandle, tree }) {
  const navigate = useNavigate();
  const { handlers, projectId, isBusy } = tree.props;
  const [isHovering, setIsHovering] = useState(false);

  const handleClick = (event) => {
    if (event.target.closest('button.action-button')) {
      event.stopPropagation();
      return;
    }
    if (node.data.type === 'folder') {
      node.toggle();
    } else if (node.data.type === 'note') {
      navigate(`/projects/${projectId}/notes/${node.data.note_id}`);
    }
  };

  const outerStyle = {
    ...style,
    cursor: 'pointer',
    position: 'relative',
    backgroundColor: isHovering ? '#f0f0f0' : 'transparent',
  };

  const nodeContentStyle = {
    display: 'flex',
    alignItems: 'center',
    width: '100%',
    padding: '2px 5px',
    backgroundColor: node.state.isSelected ? '#e0e0e0' : 'transparent',
    borderRadius: '3px',
    position: 'relative',
    zIndex: 1,
  };

  const textStyle = {
    flexGrow: 1,
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    marginLeft: '4px',
  };

  const actionsStyle = {
    position: 'absolute',
    right: '5px',
    top: '50%',
    transform: 'translateY(-50%)',
    display: 'flex',
    alignItems: 'center',
    gap: '5px',
    backgroundColor: 'inherit',
    padding: '2px 4px',
    borderRadius: '3px',
    opacity: isHovering ? 1 : 0,
    visibility: isHovering ? 'visible' : 'hidden',
    transition: 'opacity 0.1s ease-in-out, visibility 0.1s ease-in-out',
    zIndex: 2,
  };


  const buttonStyle = {
    padding: '2px 5px',
    cursor: 'pointer',
    border: '1px solid #ccc',
    borderRadius: '3px',
    backgroundColor: '#f8f9fa',
    fontSize: '0.8em',
    lineHeight: '1',
    display: 'inline-flex', // Align icon and text
    alignItems: 'center',
    gap: '3px',
  };

   const renameButtonStyle = {
       ...buttonStyle,
       backgroundColor: '#e2e6ea',
       color: '#495057',
       borderColor: '#dae0e5',
   };

   const moveButtonStyle = { // Style for move button
       ...buttonStyle,
       backgroundColor: '#d1ecf1', // Light blue
       color: '#0c5460',
       borderColor: '#bee5eb',
   };

  const deleteButtonStyle = {
    ...buttonStyle,
    backgroundColor: '#ffdddd',
    color: '#dc3545',
    borderColor: '#f5c6cb',
  };

  const disabledButtonStyle = {
    cursor: 'not-allowed',
    opacity: 0.6,
  };

  return (
    <div
      ref={dragHandle}
      style={outerStyle}
      onClick={handleClick}
      onMouseEnter={() => setIsHovering(true)}
      onMouseLeave={() => setIsHovering(false)}
      title={`Path: ${node.data.path}${node.data.type === 'note' ? `\nLast Modified: ${node.data.last_modified ? new Date(node.data.last_modified * 1000).toLocaleString() : 'N/A'}` : ''}`}
    >
      <div style={nodeContentStyle}>
        {node.data.type === 'folder' ? <FolderIcon isOpen={node.isOpen} /> : <NoteIcon />}
        <span style={textStyle}>{node.data.name}</span>
      </div>

      <div style={actionsStyle}>
        {/* Folder Actions */}
        {node.data.type === 'folder' && (
            <>
                <button
                    className="action-button"
                    onClick={(e) => { e.stopPropagation(); handlers.onCreateFolder(node.data.path); }}
                    style={{ ...buttonStyle, ...(isBusy ? disabledButtonStyle : {}) }}
                    disabled={isBusy}
                    title="Create Folder Here"
                >
                    + Folder
                </button>
                <button
                    className="action-button"
                    onClick={(e) => { e.stopPropagation(); handlers.onCreateNote(node.data.path); }}
                    style={{ ...buttonStyle, ...(isBusy ? disabledButtonStyle : {}) }}
                    disabled={isBusy}
                    title="Create Note Here"
                >
                    + Note
                </button>
                {node.data.path !== '/' && (
                    <>
                        <button
                            className="action-button"
                            onClick={(e) => { e.stopPropagation(); handlers.onRenameFolder(node.data.path, node.data.name); }}
                            style={{ ...renameButtonStyle, ...(isBusy ? disabledButtonStyle : {}) }}
                            disabled={isBusy}
                            title="Rename Folder"
                        >
                            ✏️ Rename
                        </button>
                        <button
                            className="action-button"
                            onClick={(e) => { e.stopPropagation(); handlers.onDeleteFolder(node.data.path); }}
                            style={{ ...deleteButtonStyle, ...(isBusy ? disabledButtonStyle : {}) }}
                            disabled={isBusy}
                            title="Delete Folder (Recursive)"
                        >
                            🗑️ Delete
                        </button>
                    </>
                )}
            </>
        )}
        {/* Note Actions */}
        {node.data.type === 'note' && (
            <>
                {/* Move Note Button - NEW */}
                <button
                    className="action-button"
                    onClick={(e) => { e.stopPropagation(); handlers.onMoveNote(node.data.note_id, node.data.path); }}
                    style={{ ...moveButtonStyle, ...(isBusy ? disabledButtonStyle : {}) }}
                    disabled={isBusy}
                    title="Move Note"
                >
                    <MoveIcon /> Move
                </button>
                {/* Delete Note Button */}
                <button
                    className="action-button"
                    onClick={(e) => { e.stopPropagation(); handlers.onDeleteNote(node.data.note_id, node.data.name); }}
                    style={{ ...deleteButtonStyle, ...(isBusy ? disabledButtonStyle : {}) }}
                    disabled={isBusy}
                    title="Delete Note"
                >
                    🗑️ Delete
                </button>
            </>
        )}
      </div>
    </div>
  );
}

Node.propTypes = {
    node: PropTypes.object.isRequired,
    style: PropTypes.object,
    dragHandle: PropTypes.func,
    tree: PropTypes.object.isRequired,
};


/**
 * NoteTreeViewer Component - Renders the hierarchical note structure using react-arborist.
 */
function NoteTreeViewer({
    projectId,
    treeData,
    handlers,
    isBusy = false
}) {
  const treeRef = useRef(null);

  if (!treeData) {
    return <div>Loading tree structure...</div>;
  }

  return (
    <Tree
      ref={treeRef}
      data={treeData}
      openByDefault={false}
      width="100%"
      height={600}
      indent={24}
      rowHeight={30}
      paddingTop={10}
      paddingBottom={10}
      handlers={handlers}
      projectId={projectId}
      isBusy={isBusy}
    >
      {Node}
    </Tree>
  );
}

NoteTreeViewer.propTypes = {
  projectId: PropTypes.string.isRequired,
  treeData: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.string.isRequired,
    name: PropTypes.string.isRequired,
    type: PropTypes.oneOf(['folder', 'note']).isRequired,
    path: PropTypes.string.isRequired,
    children: PropTypes.array,
    note_id: PropTypes.string,
    last_modified: PropTypes.number,
  })).isRequired,
  handlers: PropTypes.shape({
      onCreateNote: PropTypes.func.isRequired,
      onCreateFolder: PropTypes.func.isRequired,
      onRenameFolder: PropTypes.func.isRequired,
      onDeleteFolder: PropTypes.func.isRequired,
      onDeleteNote: PropTypes.func.isRequired,
      onMoveNote: PropTypes.func.isRequired, // Now required
  }).isRequired,
  isBusy: PropTypes.bool,
};

// Default prop handled in function signature

export default NoteTreeViewer;