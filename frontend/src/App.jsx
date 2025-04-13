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
import { Routes, Route } from 'react-router-dom';
import MainLayout from './layouts/MainLayout';
import ProjectListPage from './pages/ProjectListPage';
import ProjectDetailPage from './pages/ProjectDetailPage';
import PlanEditPage from './pages/PlanEditPage';
import SynopsisEditPage from './pages/SynopsisEditPage';
import WorldEditPage from './pages/WorldEditPage';
import CharacterEditPage from './pages/CharacterEditPage';
import SceneEditPage from './pages/SceneEditPage';
import ProjectQueryPage from './pages/ProjectQueryPage';
// --- ADDED: Import new chapter edit pages ---
import ChapterPlanEditPage from './pages/ChapterPlanEditPage';
import ChapterSynopsisEditPage from './pages/ChapterSynopsisEditPage';
// --- END ADDED ---
// --- ADDED: Import new note pages (Placeholders for now) ---
import ProjectNotesPage from './pages/ProjectNotesPage'; // Assuming this file will be created
import NoteEditPage from './pages/NoteEditPage';       // Assuming this file will be created
// --- END ADDED ---

import './App.css';


function App() {
  return (
    <Routes>
      <Route path="/" element={<MainLayout />}>
        <Route index element={<ProjectListPage />} />
        <Route path="projects/:projectId" element={<ProjectDetailPage />} />
        <Route path="projects/:projectId/plan" element={<PlanEditPage />} />
        <Route path="projects/:projectId/synopsis" element={<SynopsisEditPage />} />
        <Route path="projects/:projectId/world" element={<WorldEditPage />} />
        <Route path="projects/:projectId/characters/:characterId" element={<CharacterEditPage />} />
        <Route path="projects/:projectId/chapters/:chapterId/scenes/:sceneId" element={<SceneEditPage />} />
        <Route path="projects/:projectId/query" element={<ProjectQueryPage />} />
        {/* --- ADDED: Routes for chapter plan/synopsis --- */}
        <Route path="projects/:projectId/chapters/:chapterId/plan" element={<ChapterPlanEditPage />} />
        <Route path="projects/:projectId/chapters/:chapterId/synopsis" element={<ChapterSynopsisEditPage />} />
        {/* --- END ADDED --- */}
        {/* --- ADDED: Routes for project notes --- */}
        <Route path="projects/:projectId/notes" element={<ProjectNotesPage />} />
        <Route path="projects/:projectId/notes/:noteId" element={<NoteEditPage />} />
        {/* --- END ADDED --- */}
        <Route path="*" element={<div><h2>404 Not Found</h2></div>} />
      </Route>
    </Routes>
  );
}
export default App;