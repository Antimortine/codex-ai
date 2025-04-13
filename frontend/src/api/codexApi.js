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

import axios from 'axios';

// Define the base URL of your FastAPI backend
const API_BASE_URL = 'http://localhost:8000/api/v1'; // Match your backend prefix

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// --- Project Endpoints ---
export const listProjects = () => apiClient.get('/projects/');
export const createProject = (data) => apiClient.post('/projects/', data); // data: { name: "..." }
export const getProject = (projectId) => apiClient.get(`/projects/${projectId}`);
export const updateProject = (projectId, data) => apiClient.patch(`/projects/${projectId}`, data);
export const deleteProject = (projectId) => apiClient.delete(`/projects/${projectId}`);

// --- Chapter Endpoints ---
export const listChapters = (projectId) => apiClient.get(`/projects/${projectId}/chapters/`);
export const createChapter = (projectId, data) => apiClient.post(`/projects/${projectId}/chapters/`, data); // data: { title: "...", order: ... }
export const getChapter = (projectId, chapterId) => apiClient.get(`/projects/${projectId}/chapters/${chapterId}`);
export const updateChapter = (projectId, chapterId, data) => apiClient.patch(`/projects/${projectId}/chapters/${chapterId}`, data);
export const deleteChapter = (projectId, chapterId) => apiClient.delete(`/projects/${projectId}/chapters/${chapterId}`);

// --- Scene Endpoints ---
export const listScenes = (projectId, chapterId) => apiClient.get(`/projects/${projectId}/chapters/${chapterId}/scenes/`);
export const createScene = (projectId, chapterId, data) => apiClient.post(`/projects/${projectId}/chapters/${chapterId}/scenes/`, data); // data: { title: "...", order: ..., content: "..." }
export const getScene = (projectId, chapterId, sceneId) => apiClient.get(`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`);
export const updateScene = (projectId, chapterId, sceneId, data) => apiClient.patch(`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`, data);
export const deleteScene = (projectId, chapterId, sceneId) => apiClient.delete(`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`);

// --- Character Endpoints ---
export const listCharacters = (projectId) => apiClient.get(`/projects/${projectId}/characters/`);
export const createCharacter = (projectId, data) => apiClient.post(`/projects/${projectId}/characters/`, data); // data: { name: "...", description: "..." }
export const getCharacter = (projectId, characterId) => apiClient.get(`/projects/${projectId}/characters/${characterId}`);
export const updateCharacter = (projectId, characterId, data) => apiClient.patch(`/projects/${projectId}/characters/${characterId}`, data);
export const deleteCharacter = (projectId, characterId) => apiClient.delete(`/projects/${projectId}/characters/${characterId}`);

// --- Content Block Endpoints (Project Level) ---
export const getPlan = (projectId) => apiClient.get(`/projects/${projectId}/plan`);
export const updatePlan = (projectId, data) => apiClient.put(`/projects/${projectId}/plan`, data); // data: { content: "..." }

export const getSynopsis = (projectId) => apiClient.get(`/projects/${projectId}/synopsis`);
export const updateSynopsis = (projectId, data) => apiClient.put(`/projects/${projectId}/synopsis`, data); // data: { content: "..." }

export const getWorldInfo = (projectId) => apiClient.get(`/projects/${projectId}/world`);
export const updateWorldInfo = (projectId, data) => apiClient.put(`/projects/${projectId}/world`, data); // data: { content: "..." }

// --- Content Block Endpoints (Chapter Level) ---
export const getChapterPlan = (projectId, chapterId) => apiClient.get(`/projects/${projectId}/chapters/${chapterId}/plan`);
export const updateChapterPlan = (projectId, chapterId, data) => apiClient.put(`/projects/${projectId}/chapters/${chapterId}/plan`, data); // data: { content: "..." }

export const getChapterSynopsis = (projectId, chapterId) => apiClient.get(`/projects/${projectId}/chapters/${chapterId}/synopsis`);
export const updateChapterSynopsis = (projectId, chapterId, data) => apiClient.put(`/projects/${projectId}/chapters/${chapterId}/synopsis`, data); // data: { content: "..." }

// --- Note Endpoints --- ADDED
/**
 * Lists all notes for a project, sorted by last modified descending.
 * @param {string} projectId - The ID of the project.
 * @returns {Promise<AxiosResponse<any>>} - Expected data: { notes: [{id, title, last_modified}, ...] }
 */
export const listNotes = (projectId) => apiClient.get(`/projects/${projectId}/notes/`);

/**
 * Creates a new note for a project.
 * @param {string} projectId - The ID of the project.
 * @param {object} data - The request body. e.g., { title: "New Note Title" }
 * @returns {Promise<AxiosResponse<any>>} - Returns the created note {id, title, last_modified}.
 */
export const createNote = (projectId, data) => apiClient.post(`/projects/${projectId}/notes/`, data);

/**
 * Gets a specific note by ID, including its content.
 * @param {string} projectId - The ID of the project.
 * @param {string} noteId - The ID of the note.
 * @returns {Promise<AxiosResponse<any>>} - Returns the full note {id, title, content, last_modified}.
 */
export const getNote = (projectId, noteId) => apiClient.get(`/projects/${projectId}/notes/${noteId}`);

/**
 * Updates a specific note (title and/or content).
 * @param {string} projectId - The ID of the project.
 * @param {string} noteId - The ID of the note.
 * @param {object} data - The request body. e.g., { title?: "Updated Title", content?: "Updated content." }
 * @returns {Promise<AxiosResponse<any>>} - Returns the updated note {id, title, content, last_modified}.
 */
export const updateNote = (projectId, noteId, data) => apiClient.patch(`/projects/${projectId}/notes/${noteId}`, data);

/**
 * Deletes a specific note.
 * @param {string} projectId - The ID of the project.
 * @param {string} noteId - The ID of the note to delete.
 * @returns {Promise<AxiosResponse<any>>} - Returns a success message {message: "..."}.
 */
export const deleteNote = (projectId, noteId) => apiClient.delete(`/projects/${projectId}/notes/${noteId}`);
// --- END ADDED ---

// --- Chapter Compilation Endpoint ---
/**
 * Compiles chapter content.
 * @param {string} projectId - Project ID.
 * @param {string} chapterId - Chapter ID.
 * @param {object} params - Optional query parameters { include_titles?: boolean, separator?: string }.
 * @returns {Promise<AxiosResponse<any>>} - Expected data: { filename: string, content: string }
 */
export const compileChapterContent = (projectId, chapterId, params = {}) => {
    return apiClient.get(`/projects/${projectId}/chapters/${chapterId}/compile`, { params });
};


// --- AI Endpoints ---
export const queryProjectContext = (projectId, data) => apiClient.post(`/ai/query/${projectId}`, data);
export const generateSceneDraft = (projectId, chapterId, requestData) => {
  return apiClient.post(`/ai/generate/scene/${projectId}/${chapterId}`, requestData);
};
export const rephraseText = (projectId, requestData) => {
    return apiClient.post(`/ai/edit/rephrase/${projectId}`, requestData);
};
export const splitChapterIntoScenes = (projectId, chapterId, requestData = {}) => {
    return apiClient.post(`/ai/split/chapter/${projectId}/${chapterId}`, requestData);
};
export const rebuildProjectIndex = (projectId) => apiClient.post(`/ai/rebuild_index/${projectId}`);

// --- Chat History & Session Endpoints ---

// --- Chat Session CRUD ---
/**
 * Lists all chat sessions for a project.
 * @param {string} projectId - The ID of the project.
 * @returns {Promise<AxiosResponse<any>>} - Expected data: { sessions: [{id, name, project_id}, ...] }
 */
export const listChatSessions = (projectId) => apiClient.get(`/projects/${projectId}/chat_sessions`);

/**
 * Creates a new chat session for a project.
 * @param {string} projectId - The ID of the project.
 * @param {object} data - The request body. e.g., { name: "New Session Name" }
 * @returns {Promise<AxiosResponse<any>>} - Returns the created session {id, name, project_id}.
 */
export const createChatSession = (projectId, data) => apiClient.post(`/projects/${projectId}/chat_sessions`, data);

/**
 * Renames a specific chat session.
 * @param {string} projectId - The ID of the project.
 * @param {string} sessionId - The ID of the session to rename.
 * @param {object} data - The request body. e.g., { name: "Updated Name" }
 * @returns {Promise<AxiosResponse<any>>} - Returns the updated session {id, name, project_id}.
 */
export const renameChatSession = (projectId, sessionId, data) => apiClient.patch(`/projects/${projectId}/chat_sessions/${sessionId}`, data);

/**
 * Deletes a specific chat session and its history.
 * @param {string} projectId - The ID of the project.
 * @param {string} sessionId - The ID of the session to delete.
 * @returns {Promise<AxiosResponse<any>>} - Returns a success message {message: "..."}.
 */
export const deleteChatSession = (projectId, sessionId) => apiClient.delete(`/projects/${projectId}/chat_sessions/${sessionId}`);

// --- Chat History (Per Session) ---
/**
 * Gets the chat history for a specific session within a project.
 * @param {string} projectId - The ID of the project.
 * @param {string} sessionId - The ID of the specific chat session.
 * @returns {Promise<AxiosResponse<any>>} - Expected data: { history: [{id, query, response?, error?}, ...] }
 */
export const getChatHistory = (projectId, sessionId) => apiClient.get(`/projects/${projectId}/chat_history/${sessionId}`);

/**
 * Updates (overwrites) the chat history for a specific session within a project.
 * @param {string} projectId - The ID of the project.
 * @param {string} sessionId - The ID of the specific chat session.
 * @param {object} data - The request body. e.g., { history: [{id, query, response?, error?}, ...] }
 * @returns {Promise<AxiosResponse<any>>} - Returns the saved history { history: [...] }.
 */
export const updateChatHistory = (projectId, sessionId, data) => apiClient.put(`/projects/${projectId}/chat_history/${sessionId}`, data);


// Optional: Add interceptors for error handling or adding auth tokens later
apiClient.interceptors.response.use(
  response => response,
  error => {
    // Log or handle errors globally
    console.error('API call error:', error.response || error.message || error);
    return Promise.reject(error);
  }
);

export default apiClient; // Can also export individual functions