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

import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { listProjects, createProject, deleteProject } from '../api/codexApi'; // Import API functions

function ProjectListPage() {
  const [projects, setProjects] = useState([]);
  const [newProjectName, setNewProjectName] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetchProjects = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const response = await listProjects();
      setProjects(response.data.projects || []);
    } catch (err) {
      console.error("Error fetching projects:", err);
      setError('Failed to load projects.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects(); // Fetch projects when component mounts
  }, []);

  const handleCreateProject = async (e) => {
    e.preventDefault(); // Prevent default form submission
    if (!newProjectName.trim()) {
      setError("Project name cannot be empty.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      await createProject({ name: newProjectName });
      setNewProjectName(''); // Clear input field
      fetchProjects(); // Refresh the list
    } catch (err) {
      console.error("Error creating project:", err);
      setError('Failed to create project.');
      setIsLoading(false); // Keep loading false on error
    }
    // setIsLoading(false) will be called by fetchProjects() on success
  };

  const handleDeleteProject = async (projectId, projectName) => {
    // Simple confirmation dialog
    if (!window.confirm(`Are you sure you want to delete project "${projectName}"? This cannot be undone.`)) {
      return;
    }
    setIsLoading(true); // Indicate loading during delete
    setError(null);
    try {
      await deleteProject(projectId);
      fetchProjects(); // Refresh the list
    } catch (err) {
      console.error(`Error deleting project ${projectId}:`, err);
      setError('Failed to delete project.');
      setIsLoading(false); // Keep loading false on error
    }
     // setIsLoading(false) will be called by fetchProjects() on success
  };


  return (
    <div>
      <h2>Your Projects</h2>

      {/* Form to Create New Project */}
      <form onSubmit={handleCreateProject} style={{ marginBottom: '1rem' }}>
        <input
          type="text"
          value={newProjectName}
          onChange={(e) => setNewProjectName(e.target.value)}
          placeholder="New project name"
          disabled={isLoading}
        />
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'Creating...' : 'Create Project'}
        </button>
      </form>

      {/* Display Loading/Error/Project List */}
      {isLoading && <p>Loading projects...</p>}
      {error && <p style={{ color: 'red' }}>Error: {error}</p>}

      {!isLoading && !error && (
        <ul>
          {projects.length === 0 ? (
            <p>No projects found. Create one above!</p>
          ) : (
            projects.map(project => (
              <li key={project.id} style={{ marginBottom: '0.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {/* Link to the project detail page */}
                <Link to={`/projects/${project.id}`}>{project.name}</Link>
                <button
                  onClick={() => handleDeleteProject(project.id, project.name)}
                  disabled={isLoading}
                  style={{ marginLeft: '1rem', color: 'red', cursor: 'pointer' }}
                >
                  Delete
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
}

export default ProjectListPage;