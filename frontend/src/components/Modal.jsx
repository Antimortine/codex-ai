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

import React, { useEffect } from 'react';
import PropTypes from 'prop-types';

const styles = {
  overlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(0, 0, 0, 0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  content: {
    backgroundColor: '#fff',
    padding: '20px',
    borderRadius: '5px',
    maxWidth: '80%',
    width: '700px',
    maxHeight: '85vh',
    overflowY: 'auto',
    position: 'relative',
  },
  title: {
    marginTop: 0,
    marginBottom: '20px',
    borderBottom: '1px solid #eee',
    paddingBottom: '10px',
  },
  closeButton: {
    position: 'absolute',
    top: '10px',
    right: '10px',
    cursor: 'pointer',
    border: 'none',
    background: 'transparent',
    fontSize: '1.5rem',
    fontWeight: 'bold',
  }
};

/**
 * Reusable modal component
 */
function Modal({ title, children, onClose }) {
  // Add event listener for escape key
  useEffect(() => {
    const handleEscapeKey = (event) => {
      if (event.key === 'Escape') {
        onClose();
      }
    };
    
    document.addEventListener('keydown', handleEscapeKey);
    
    // Prevent scrolling on the body when modal is open
    document.body.style.overflow = 'hidden';
    
    return () => {
      document.removeEventListener('keydown', handleEscapeKey);
      document.body.style.overflow = 'auto';
    };
  }, [onClose]);

  // Handle click outside of modal content to close
  const handleOverlayClick = (event) => {
    if (event.target === event.currentTarget) {
      onClose();
    }
  };

  return (
    <div 
      style={styles.overlay} 
      onClick={handleOverlayClick}
      data-testid="modal-overlay"
    >
      <div style={styles.content}>
        <h2 style={styles.title}>{title}</h2>
        
        <button 
          onClick={onClose} 
          style={styles.closeButton}
          aria-label="Close"
          data-testid="modal-close-button"
        >
          &times;
        </button>
        
        {children}
      </div>
    </div>
  );
}

Modal.propTypes = {
  title: PropTypes.string.isRequired,
  children: PropTypes.node.isRequired,
  onClose: PropTypes.func.isRequired
};

export default Modal;
