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
// ... (listProjects, createProject, etc. - unchanged) ...
export const listProjects = () => apiClient.get('/projects/');
export const createProject = (data) => apiClient.post('/projects/', data); // data: { name: "..." }
export const getProject = (projectId) => apiClient.get(`/projects/${projectId}`);
export const updateProject = (projectId, data) => apiClient.patch(`/projects/${projectId}`, data);
export const deleteProject = (projectId) => apiClient.delete(`/projects/${projectId}`);

// --- Chapter Endpoints ---
// ... (listChapters, createChapter, etc. - unchanged) ...
export const listChapters = (projectId) => apiClient.get(`/projects/${projectId}/chapters/`);
export const createChapter = (projectId, data) => apiClient.post(`/projects/${projectId}/chapters/`, data); // data: { title: "...", order: ... }
export const getChapter = (projectId, chapterId) => apiClient.get(`/projects/${projectId}/chapters/${chapterId}`);
export const updateChapter = (projectId, chapterId, data) => apiClient.patch(`/projects/${projectId}/chapters/${chapterId}`, data);
export const deleteChapter = (projectId, chapterId) => apiClient.delete(`/projects/${projectId}/chapters/${chapterId}`);

// --- Scene Endpoints ---
// ... (listScenes, createScene, etc. - unchanged) ...
export const listScenes = (projectId, chapterId) => apiClient.get(`/projects/${projectId}/chapters/${chapterId}/scenes/`);
export const createScene = (projectId, chapterId, data) => apiClient.post(`/projects/${projectId}/chapters/${chapterId}/scenes/`, data); // data: { title: "...", order: ..., content: "..." }
export const getScene = (projectId, chapterId, sceneId) => apiClient.get(`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`);
export const updateScene = (projectId, chapterId, sceneId, data) => apiClient.patch(`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`, data);
export const deleteScene = (projectId, chapterId, sceneId) => apiClient.delete(`/projects/${projectId}/chapters/${chapterId}/scenes/${sceneId}`);

// --- Character Endpoints ---
// ... (listCharacters, createCharacter, etc. - unchanged) ...
export const listCharacters = (projectId) => apiClient.get(`/projects/${projectId}/characters/`);
export const createCharacter = (projectId, data) => apiClient.post(`/projects/${projectId}/characters/`, data); // data: { name: "...", description: "..." }
export const getCharacter = (projectId, characterId) => apiClient.get(`/projects/${projectId}/characters/${characterId}`);
export const updateCharacter = (projectId, characterId, data) => apiClient.patch(`/projects/${projectId}/characters/${characterId}`, data);
export const deleteCharacter = (projectId, characterId) => apiClient.delete(`/projects/${projectId}/characters/${characterId}`);

// --- Content Block Endpoints (Plan, Synopsis, World) ---
// ... (getPlan, updatePlan, etc. - unchanged) ...
export const getPlan = (projectId) => apiClient.get(`/projects/${projectId}/plan`);
export const updatePlan = (projectId, data) => apiClient.put(`/projects/${projectId}/plan`, data); // data: { content: "..." }

export const getSynopsis = (projectId) => apiClient.get(`/projects/${projectId}/synopsis`);
export const updateSynopsis = (projectId, data) => apiClient.put(`/projects/${projectId}/synopsis`, data); // data: { content: "..." }

export const getWorldInfo = (projectId) => apiClient.get(`/projects/${projectId}/world`);
export const updateWorldInfo = (projectId, data) => apiClient.put(`/projects/${projectId}/world`, data); // data: { content: "..." }


// --- AI Endpoints ---

/**
 * Sends a query to the AI for a specific project context.
 */
export const queryProjectContext = (projectId, data) => apiClient.post(`/ai/query/${projectId}`, data);

/**
 * Requests the AI to generate a scene draft for a specific chapter.
 */
export const generateSceneDraft = (projectId, chapterId, requestData) => {
  return apiClient.post(`/ai/generate/scene/${projectId}/${chapterId}`, requestData);
};

/**
 * Requests AI suggestions for rephrasing selected text.
 * @param {string} projectId - The ID of the project context.
 * @param {object} requestData - The request body. e.g., { selected_text: "...", context_before: "...", context_after: "..." }
 * @returns {Promise<AxiosResponse<any>>} - The Axios response promise. Expected data format: { suggestions: ["...", "..."] }
 */
export const rephraseText = (projectId, requestData) => {
    return apiClient.post(`/ai/edit/rephrase/${projectId}`, requestData);
};

/**
 * Requests the AI to split a chapter's content into proposed scenes.
 * @param {string} projectId - The ID of the project.
 * @param {string} chapterId - The ID of the chapter to split.
 * @param {object} requestData - Optional request body (currently empty).
 * @returns {Promise<AxiosResponse<any>>} - The Axios response promise. Expected data format: { proposed_scenes: [{ suggested_title: "...", content: "..." }, ...] }
 */
export const splitChapterIntoScenes = (projectId, chapterId, requestData = {}) => {
    return apiClient.post(`/ai/split/chapter/${projectId}/${chapterId}`, requestData);
};


// Optional: Add interceptors for error handling or adding auth tokens later
// ... (interceptor unchanged) ...

export default apiClient; // Can also export individual functions