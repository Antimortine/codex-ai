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

import React, { useState, useEffect, useCallback, useRef } from 'react'; // Import useRef
import { useParams, Link } from 'react-router-dom';
import QueryInterface from '../components/QueryInterface';
import {
    getProject,
    listChatSessions,
    createChatSession,
    renameChatSession,
    deleteChatSession
} from '../api/codexApi';

const sessionStyles = {
    container: {
        display: 'flex',
        alignItems: 'center',
        gap: '10px',
        marginBottom: '1rem',
        flexWrap: 'wrap',
    },
    select: {
        padding: '5px',
        minWidth: '200px',
        flexGrow: 1,
    },
    button: {
        padding: '5px 10px',
        cursor: 'pointer',
        border: '1px solid #ccc',
        borderRadius: '3px',
    },
    buttonDisabled: {
        cursor: 'not-allowed',
        opacity: 0.6,
    },
    error: {
        color: 'red',
        fontSize: '0.9em',
        marginTop: '5px',
        width: '100%',
    },
    loading: {
        fontStyle: 'italic',
        color: '#555',
    },
};

function ProjectQueryPage() {
    const { projectId } = useParams();
    const [projectName, setProjectName] = useState('...');
    const [isLoadingProject, setIsLoadingProject] = useState(true);
    const [projectError, setProjectError] = useState(null);

    const [sessions, setSessions] = useState([]);
    const [activeSessionId, setActiveSessionId] = useState(null);
    const [isLoadingSessions, setIsLoadingSessions] = useState(true);
    const [sessionError, setSessionError] = useState(null);
    const [isProcessingSessionAction, setIsProcessingSessionAction] = useState(false);
    // --- Use a ref to track if the initial session load/check is done ---
    const initialSessionCheckDone = useRef(false);
    // ---

    // Fetch project name (no changes)
    useEffect(() => {
        let isMounted = true;
        setIsLoadingProject(true);
        setProjectError(null);
        initialSessionCheckDone.current = false; // Reset check when project changes
        if (!projectId) { if (isMounted) { setProjectError("Project ID not found in URL."); setIsLoadingProject(false); } return; }
        getProject(projectId)
            .then(response => { if (isMounted) { setProjectName(response.data.name || 'Unknown Project'); } })
            .catch(err => { console.error("[ProjectQueryPage] getProject FAILED:", err); if (isMounted) { setProjectError(`Failed to load project details: ${err.message}`); setProjectName('Error Loading Project'); } })
            .finally(() => { if (isMounted) { setIsLoadingProject(false); } });
        return () => { isMounted = false; };
    }, [projectId]);

    // --- REVISED: fetchSessions focuses only on fetching and setting state ---
    const fetchSessions = useCallback(async (selectSessionId = null) => {
        if (!projectId) return Promise.resolve([]);
        // Don't reset loading if already processing an action that will call fetch again
        if (!isProcessingSessionAction) {
            setIsLoadingSessions(true);
        }
        setSessionError(null);
        let fetchedSessions = [];
        try {
            const response = await listChatSessions(projectId);
            fetchedSessions = response.data?.sessions || [];
            setSessions(fetchedSessions); // Update sessions list
            console.log("[ProjectQueryPage] Fetched sessions:", fetchedSessions);

            // Determine the session to activate
            let sessionToActivate = null;
            if (selectSessionId && fetchedSessions.some(s => s.id === selectSessionId)) {
                sessionToActivate = selectSessionId; // Activate the requested one if valid
            } else if (fetchedSessions.length > 0) {
                 // Keep current active session if it still exists in the fetched list
                const currentActiveStillExists = activeSessionId && fetchedSessions.some(s => s.id === activeSessionId);
                sessionToActivate = currentActiveStillExists ? activeSessionId : fetchedSessions[0].id;
            }

            setActiveSessionId(sessionToActivate); // Set to null if no sessions
            console.log(`[ProjectQueryPage] Set active session to: ${sessionToActivate}`);
            return fetchedSessions; // Return the fetched sessions

        } catch (err) {
            console.error("[ProjectQueryPage] Error fetching sessions:", err);
            setSessionError(`Failed to load chat sessions: ${err.response?.data?.detail || err.message}`);
            setActiveSessionId(null);
            setSessions([]);
            return []; // Return empty array on error
        } finally {
            setIsLoadingSessions(false); // Ensure loading is set to false
            // Mark initial check done AFTER the first successful/failed fetch
            if (!initialSessionCheckDone.current) {
                initialSessionCheckDone.current = true;
            }
        }
    // --- REMOVED activeSessionId from dependency array ---
    }, [projectId, isProcessingSessionAction]); // Depend on projectId and processing flag
    // --- END REVISED ---

    // --- REVISED: useEffect for initial fetch ---
    useEffect(() => {
        // Fetch initially when project is ready
        if (projectId && !isLoadingProject && !projectError) {
            fetchSessions();
        }
    }, [projectId, isLoadingProject, projectError, fetchSessions]);
    // --- END REVISED ---

    // --- Session Action Handlers ---
    // --- REVISED: handleCreateSession simplified ---
    const handleCreateSession = useCallback(async (defaultName = null) => {
        const newSessionName = defaultName || window.prompt("Enter name for the new chat session:");
        if (!newSessionName || !newSessionName.trim()) return;

        setIsProcessingSessionAction(true);
        setSessionError(null);
        let newSessionId = null;
        try {
            const response = await createChatSession(projectId, { name: newSessionName.trim() });
            newSessionId = response.data.id;
            console.log("[ProjectQueryPage] Created new session:", response.data);
            // Fetch sessions again, activating the new one
            await fetchSessions(newSessionId);
        } catch (err) {
            console.error("[ProjectQueryPage] Error creating session:", err);
            setSessionError(`Failed to create session: ${err.response?.data?.detail || err.message}`);
            setIsProcessingSessionAction(false); // Ensure flag is reset on error
        } finally {
            // setIsLoadingProcessing(false) is handled by fetchSessions if successful
        }
    }, [projectId, fetchSessions]); // Depends on fetchSessions

    // --- REVISED: Separate useEffect for default creation ---
    useEffect(() => {
        // Only run this check *after* the initial load is marked complete
        // and if no sessions were found/activated and no error occurred.
        if (initialSessionCheckDone.current && 
            !isLoadingSessions && 
            sessions.length === 0 && 
            !activeSessionId && 
            !sessionError && 
            !isProcessingSessionAction) {
            
            console.log("[ProjectQueryPage] useEffect (Default Create Check): Triggering default session creation.");
            // Prevent this effect from running again immediately
            initialSessionCheckDone.current = false; // Reset flag temporarily during creation
            handleCreateSession("Main Chat");
        }
    }, [isLoadingSessions, sessions, activeSessionId, sessionError, isProcessingSessionAction, handleCreateSession]);
    // --- END REVISED ---
    // --- END REVISED ---

    const handleRenameSession = useCallback(async () => {
        if (!activeSessionId) return;
        const currentSession = sessions.find(s => s.id === activeSessionId);
        const newName = window.prompt("Enter new name for this chat session:", currentSession?.name || "");
        if (!newName || !newName.trim() || newName.trim() === currentSession?.name) return;

        setIsProcessingSessionAction(true);
        setSessionError(null);
        try {
            await renameChatSession(projectId, activeSessionId, { name: newName.trim() });
            console.log(`[ProjectQueryPage] Renamed session ${activeSessionId}`);
            await fetchSessions(activeSessionId);
        } catch (err) {
            console.error("[ProjectQueryPage] Error renaming session:", err);
            setSessionError(`Failed to rename session: ${err.response?.data?.detail || err.message}`);
            setIsProcessingSessionAction(false); // Reset on error
        } finally {
             // setIsLoadingProcessing(false) handled by fetchSessions
        }
    }, [projectId, activeSessionId, sessions, fetchSessions]);

    const handleDeleteSession = useCallback(async () => {
        if (!activeSessionId || sessions.length <= 1) {
            return;
        }
        const currentSession = sessions.find(s => s.id === activeSessionId);
        if (!window.confirm(`Are you sure you want to delete chat session "${currentSession?.name || activeSessionId}"? This cannot be undone.`)) {
            return;
        }

        setIsProcessingSessionAction(true);
        setSessionError(null);
        const sessionToDeleteId = activeSessionId;
        
        try {
            // Find the session to switch to after deletion
            const remainingSessionId = sessions.find(s => s.id !== sessionToDeleteId)?.id;
            
            // Delete the current session
            await deleteChatSession(projectId, sessionToDeleteId);
            console.log(`[ProjectQueryPage] Deleted session ${sessionToDeleteId}, switching to ${remainingSessionId}`);
            
            // Set active session to another one before fetching
            if (remainingSessionId) {
                setActiveSessionId(remainingSessionId);
            } else {
                setActiveSessionId(null);
            }
            
            // Re-fetch sessions to update the list
            await fetchSessions(remainingSessionId);
        } catch (err) {
            console.error("[ProjectQueryPage] Error deleting session:", err);
            setSessionError(`Failed to delete session: ${err.response?.data?.detail || err.message}`);
            setActiveSessionId(sessionToDeleteId); // Restore active ID if delete failed
            setIsProcessingSessionAction(false); // Reset on error
        }
        // setIsLoadingProcessing(false) handled by fetchSessions
    }, [projectId, activeSessionId, sessions, fetchSessions]);

    const handleSessionChange = (event) => {
        const newSessionId = event.target.value;
        console.log(`[ProjectQueryPage] Session changed to: ${newSessionId}`);
        // Ensure we set a session ID only if it's valid
        if (newSessionId && sessions.some(s => s.id === newSessionId)) {
            setActiveSessionId(newSessionId);
        }
    };


    const disableSessionControls = isLoadingProject || isLoadingSessions || isProcessingSessionAction;

    return (
        <div>
            <nav style={{ marginBottom: '1rem' }}>
                <Link to={`/projects/${projectId}`}>&lt; Back to Project Overview</Link>
            </nav>

            {isLoadingProject ? (
                <h2>Loading Project Query Interface...</h2>
            ) : projectError ? (
                 <h2 style={{ color: 'red' }}>Error Loading Project Query</h2>
            ) : (
                <h2>Chat with AI about Project: {projectName}</h2>
            )}

            <p>Project ID: {projectId}</p>
            {projectError && <p style={{ color: 'red' }}>{projectError}</p>}

            <hr />

            {/* Session Management UI */}
            <h3>Chat Sessions</h3>
             {isLoadingSessions && !initialSessionCheckDone.current && <p style={sessionStyles.loading}>Loading sessions...</p>} {/* Show loading only initially */}
             {sessionError && <p style={sessionStyles.error}>{sessionError}</p>}
             {!isLoadingProject && ( // Render controls once project is loaded
                <div style={sessionStyles.container}>
                    <label htmlFor="session-select" style={{whiteSpace: 'nowrap'}}>Active Session:</label>
                    <select
                        id="session-select"
                        value={activeSessionId || ''}
                        onChange={handleSessionChange}
                        disabled={disableSessionControls}
                        style={sessionStyles.select}
                        aria-label="Select Chat Session"
                    >
                        {/* Render options only if not loading sessions */}
                        {!isLoadingSessions && sessions.map(session => (
                            <option key={session.id} value={session.id}>
                                {session.name} ({session.id.substring(0, 6)}...)
                            </option>
                        ))}
                        {/* Show placeholder if loading or if loading finished and no sessions */}
                        {(isLoadingSessions || (!isLoadingSessions && sessions.length === 0)) && (
                            <option value="" disabled>
                                {isLoadingSessions ? 'Loading...' : 'No sessions available'}
                            </option>
                        )}
                    </select>
                    <button onClick={() => handleCreateSession()} style={sessionStyles.button} disabled={disableSessionControls}>New Session</button>
                    <button onClick={handleRenameSession} style={sessionStyles.button} disabled={disableSessionControls || !activeSessionId}>Rename</button>
                    <button
                        onClick={handleDeleteSession}
                        style={{...sessionStyles.button, color: (disableSessionControls || sessions.length <= 1) ? undefined : 'red', ...((disableSessionControls || sessions.length <= 1) && sessionStyles.buttonDisabled)}}
                        disabled={disableSessionControls || sessions.length <= 1}
                        title={sessions.length <= 1 ? "Cannot delete the last session" : "Delete current session"}
                    >
                        Delete
                    </button>
                </div>
            )}

            {/* Query Interface */}
            {/* Render only when everything is loaded and an active session exists */}
            {projectId && !isLoadingProject && !projectError && !isLoadingSessions && !sessionError && activeSessionId && (
                <QueryInterface
                    key={activeSessionId} // Keep key to force remount on session change
                    projectId={projectId}
                    activeSessionId={activeSessionId}
                />
            )}

        </div>
    );
}

export default ProjectQueryPage;