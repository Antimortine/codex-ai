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
import { useParams, Link } from 'react-router-dom';
import QueryInterface from '../components/QueryInterface'; // Import the component
import { getProject } from '../api/codexApi'; // To fetch project name

function ProjectQueryPage() {
    const { projectId } = useParams();
    const [projectName, setProjectName] = useState('...');
    const [isLoadingProject, setIsLoadingProject] = useState(true);
    const [projectError, setProjectError] = useState(null);

    // Fetch project name for context
    useEffect(() => {
        let isMounted = true;
        setIsLoadingProject(true);
        setProjectError(null);

        if (!projectId) {
            if (isMounted) {
                setProjectError("Project ID not found in URL.");
                setIsLoadingProject(false);
            }
            return;
        }

        getProject(projectId)
            .then(response => {
                if (isMounted) {
                    setProjectName(response.data.name || 'Unknown Project');
                }
            })
            .catch(err => {
                console.error("[ProjectQueryPage] getProject FAILED:", err);
                if (isMounted) {
                    setProjectError(`Failed to load project details: ${err.message}`);
                    setProjectName('Error Loading Project');
                }
            })
            .finally(() => {
                if (isMounted) {
                    setIsLoadingProject(false);
                }
            });

        return () => { isMounted = false; };
    }, [projectId]);

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

            {/* Render the QueryInterface component, passing the projectId */}
            {projectId && !isLoadingProject && !projectError && (
                <QueryInterface projectId={projectId} />
            )}

        </div>
    );
}

export default ProjectQueryPage;