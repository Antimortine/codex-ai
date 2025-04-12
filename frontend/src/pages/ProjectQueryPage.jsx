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

import React, { useState, useEffect, useCallback, useRef } from 'react';
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
    const initialSessionCheckDone = useRef(false);
    const defaultSessionCreationAttempted = useRef(false);

    // Fetch project name
    useEffect(() => {
        let isMounted = true;
        setIsLoadingProject(true);
        setProjectError(null);
        initialSessionCheckDone.current = false;
        defaultSessionCreationAttempted.current = false;
        if (!projectId) { if (isMounted) { setProjectError("Project ID not found in URL."); setIsLoadingProject(false); } return; }
        getProject(projectId)
            .then(response => { if (isMounted) { setProjectName(response.data.name || 'Unknown Project'); } })
            .catch(err => { console.error("[ProjectQueryPage] getProject FAILED:", err); if (isMounted) { setProjectError(`Failed to load project details: ${err.message}`); setProjectName('Error Loading Project'); } })
            .finally(() => { if (isMounted) { setIsLoadingProject(false); } });
        return () => { isMounted = false; };
    }, [projectId]);

    // Fetch Sessions - Simplified dependencies
    const fetchSessions = useCallback(async (selectSessionId = null) => {
        if (!projectId) return Promise.resolve([]);
        // Set loading true only if not already processing another session action
        if (!isProcessingSessionAction) {
             setIsLoadingSessions(true);
        }
        setSessionError(null);
        let fetchedSessions = [];
        try {
            const response = await listChatSessions(projectId);
            fetchedSessions = response.data?.sessions || [];
            setSessions(fetchedSessions);
            console.log("[ProjectQueryPage] Fetched sessions:", fetchedSessions);

            let sessionToActivate = null;
            const currentActiveId = activeSessionId; // Read current value from state closure
            if (selectSessionId && fetchedSessions.some(s => s.id === selectSessionId)) {
                sessionToActivate = selectSessionId;
            } else if (fetchedSessions.length > 0) {
                const currentActiveStillExists = currentActiveId && fetchedSessions.some(s => s.id === currentActiveId);
                sessionToActivate = currentActiveStillExists ? currentActiveId : fetchedSessions[0].id;
            }

            // Only update activeSessionId if it's different or null initially
            if (sessionToActivate !== currentActiveId) {
                 setActiveSessionId(sessionToActivate);
                 console.log(`[ProjectQueryPage] Set active session to: ${sessionToActivate}`);
            } else {
                 console.log(`[ProjectQueryPage] Active session remains: ${currentActiveId}`);
            }
            return fetchedSessions;

        } catch (err) {
            console.error("[ProjectQueryPage] Error fetching sessions:", err);
            setSessionError(`Failed to load chat sessions: ${err.response?.data?.detail || err.message}`);
            setActiveSessionId(null);
            setSessions([]);
            return [];
        } finally {
            setIsLoadingSessions(false); // Always set loading false here
            if (!initialSessionCheckDone.current) {
                initialSessionCheckDone.current = true;
            }
        }
    }, [projectId]); // Removed activeSessionId and isProcessingSessionAction

    // --- Session Action Handlers ---
    // handleCreateSession now manages its own processing state fully
    const handleCreateSession = useCallback(async (defaultName = null) => {
        const newSessionName = defaultName || window.prompt("Enter name for the new chat session:");
        if (!newSessionName || !newSessionName.trim()) return null;

        setIsProcessingSessionAction(true); // Set processing TRUE
        setSessionError(null);
        let newSessionId = null;
        try {
            const response = await createChatSession(projectId, { name: newSessionName.trim() });
            newSessionId = response.data.id;
            console.log("[ProjectQueryPage] Created new session:", response.data);
            await fetchSessions(newSessionId); // Fetch sessions again, activating the new one
            return newSessionId;
        } catch (err) {
            console.error("[ProjectQueryPage] Error creating session:", err);
            setSessionError(`Failed to create session: ${err.response?.data?.detail || err.message}`);
            return null;
        } finally {
            setIsProcessingSessionAction(false); // Reset processing FALSE in finally
        }
    }, [projectId, fetchSessions]); // Depends on fetchSessions

    // Rename Handler - manages its own processing state
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
        } finally {
            setIsProcessingSessionAction(false); // Reset processing FALSE in finally
        }
    }, [projectId, activeSessionId, sessions, fetchSessions]);

    // Delete Handler - manages its own processing state
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
            await deleteChatSession(projectId, sessionToDeleteId);
            console.log(`[ProjectQueryPage] Deleted session ${sessionToDeleteId}`);
            setActiveSessionId(null); // Reset active session ID temporarily
            await fetchSessions(); // Re-fetch sessions, which will select the new first one
        } catch (err) {
            console.error("[ProjectQueryPage] Error deleting session:", err);
            setSessionError(`Failed to delete session: ${err.response?.data?.detail || err.message}`);
            setActiveSessionId(sessionToDeleteId); // Restore active ID if delete failed
        } finally {
             setIsProcessingSessionAction(false); // Reset processing FALSE in finally
        }
    }, [projectId, activeSessionId, sessions, fetchSessions]);


    // Initial fetch useEffect
    useEffect(() => {
        if (projectId && !isLoadingProject && !projectError) {
            console.log("[ProjectQueryPage] Initial fetch effect triggered.");
            fetchSessions();
        }
    }, [projectId, isLoadingProject, projectError, fetchSessions]);

    // Default creation useEffect
    useEffect(() => {
        // Check conditions *after* initial load is complete
        // Use the ref to ensure it only runs once per project load.
        if (initialSessionCheckDone.current && !isLoadingSessions && sessions.length === 0 && !activeSessionId && !sessionError && !isProcessingSessionAction && !defaultSessionCreationAttempted.current) {
            console.log("[ProjectQueryPage] useEffect (Default Create Check): Triggering default session creation.");
            defaultSessionCreationAttempted.current = true; // Mark as attempted
            // Call handleCreateSession - it manages its own processing state now
            handleCreateSession("Main Chat");
        }
    // Removed handleCreateSession from deps, use ref instead
    }, [initialSessionCheckDone.current, isLoadingSessions, sessions, activeSessionId, sessionError, isProcessingSessionAction]);


    // handleSessionChange (no changes)
    const handleSessionChange = (event) => {
        const newSessionId = event.target.value;
        console.log(`[ProjectQueryPage] Session changed to: ${newSessionId}`);
        setActiveSessionId(newSessionId);
    };


    // Combined disable flag remains the same
    const disableSessionControls = isLoadingProject || isLoadingSessions || isProcessingSessionAction;

    // --- Rendering logic remains the same ---
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
             {isLoadingSessions && !initialSessionCheckDone.current && <p style={sessionStyles.loading}>Loading sessions...</p>}
             {sessionError && <p style={sessionStyles.error}>{sessionError}</p>}
             {!isLoadingProject && (
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
                        {!isLoadingSessions && sessions.map(session => (
                            <option key={session.id} value={session.id}>
                                {session.name} ({session.id.substring(0, 6)}...)
                            </option>
                        ))}
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
            {projectId && !isLoadingProject && !projectError && !isLoadingSessions && !sessionError && activeSessionId && (
                <QueryInterface
                    key={activeSessionId}
                    projectId={projectId}
                    activeSessionId={activeSessionId}
                />
            )}

        </div>
    );
}

export default ProjectQueryPage;