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
import ProjectQueryPage from './pages/ProjectQueryPage'; // Import the new page

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
        {/* --- ADDED: Route for the new query page --- */}
        <Route path="projects/:projectId/query" element={<ProjectQueryPage />} />
        {/* --- END ADDED --- */}
        {/* TODO: Add maybe a chapter detail page later? */}
        <Route path="*" element={<div><h2>404 Not Found</h2></div>} />
      </Route>
    </Routes>
  );
}
export default App;