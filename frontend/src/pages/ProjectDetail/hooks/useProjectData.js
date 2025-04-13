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

import { useState, useEffect, useCallback, useRef } from 'react';
import { getProject, updateProject, rebuildProjectIndex } from '../../../api/codexApi';

/**
 * Custom hook to manage project data fetching, updating, and related operations.
 * 
 * @param {string} projectId - The ID of the project to fetch and manage
 * @returns {Object} Project data and related operations
 */
export function useProjectData(projectId) {
    // Keep track of component mount status to prevent state updates after unmount
    const isMounted = useRef(true);
    // Project state
    const [project, setProject] = useState(null);
    const [isLoadingProject, setIsLoadingProject] = useState(true);
    const [error, setError] = useState(null);
    
    // Project name editing state
    const [isEditingName, setIsEditingName] = useState(false);
    const [editedProjectName, setEditedProjectName] = useState('');
    const [isSavingName, setIsSavingName] = useState(false);
    const [saveNameError, setSaveNameError] = useState(null);
    const [saveNameSuccess, setSaveNameSuccess] = useState('');
    
    // Index rebuilding state
    const [isRebuildingIndex, setIsRebuildingIndex] = useState(false);
    const [rebuildError, setRebuildError] = useState(null);
    const [rebuildSuccessMessage, setRebuildSuccessMessage] = useState('');

    // Fetch project data when projectId changes
    useEffect(() => {
        // Set mounted flag
        isMounted.current = true;
        
        // Create an abort controller for managing cleanup
        const abortController = new AbortController();
        
        const fetchProject = async () => {
            if (!projectId) return;
            
            // Store mounted state in local variable to avoid race conditions
            let isComponentMounted = isMounted.current;
            
            if (isComponentMounted) {
                setIsLoadingProject(true);
                setProject(null);
                setError('');
            }
            
            try {
                if (!isComponentMounted) return;
                
                const response = await getProject(projectId);
                
                if (isComponentMounted && isMounted.current) {
                    setProject(response.data);
                    setIsLoadingProject(false);
                }
            } catch (err) {
                if (abortController.signal.aborted) return;
                
                console.error('Error fetching project:', err);
                
                if (isComponentMounted && isMounted.current) {
                    setError(err.message || 'Failed to load project');
                    setIsLoadingProject(false);
                }
            }
        };
        
        fetchProject();
        
        // Cleanup function
        return () => {
            abortController.abort();
            isMounted.current = false;
        };
    }, [projectId]);

    // Handle project name edit start
    const handleEditNameClick = useCallback(() => {
        setIsEditingName(true);
        setEditedProjectName(project?.name || '');
        // Reset status messages
        setSaveNameSuccess('');
        setSaveNameError(null);
    }, [project]);

    // Handle project name edit cancel
    const handleCancelNameEdit = useCallback(() => {
        setIsEditingName(false);
        setEditedProjectName(project?.name || '');
        // Reset status messages
        setSaveNameSuccess('');
        setSaveNameError(null);
    }, [project]);

    // Handle project name save
    const handleSaveProjectName = useCallback(async () => {
        if (!editedProjectName.trim()) {
            setSaveNameError('Project name cannot be empty');
            return;
        }
        
        setIsSavingName(true);
        setSaveNameSuccess('');
        setSaveNameError(null);
        
        try {
            const response = await updateProject(projectId, { name: editedProjectName });
            setProject(response.data);
            setIsEditingName(false);
            setSaveNameSuccess('Project name updated successfully!');
            // Auto-hide success message after 3 seconds
            setTimeout(() => setSaveNameSuccess(''), 3000);
        } catch (err) {
            console.error('Error updating project name:', err);
            setSaveNameError(err.message || 'Failed to update project name');
        } finally {
            setIsSavingName(false);
        }
    }, [projectId, editedProjectName]);

    // Handle project index rebuild
    const handleRebuildIndex = useCallback(async () => {
        setIsRebuildingIndex(true);
        setRebuildError(null);
        setRebuildSuccessMessage('');
        
        try {
            await rebuildProjectIndex(projectId);
            setRebuildSuccessMessage('Project index rebuilt successfully!');
            // Auto-hide success message after 5 seconds
            setTimeout(() => setRebuildSuccessMessage(''), 5000);
        } catch (err) {
            console.error('Error rebuilding project index:', err);
            setRebuildError(err.message || 'Failed to rebuild project index');
        } finally {
            setIsRebuildingIndex(false);
        }
    }, [projectId]);

    return {
        // State
        project,
        isLoadingProject,
        error,
        isEditingName,
        editedProjectName,
        isSavingName,
        saveNameError,
        saveNameSuccess,
        isRebuildingIndex,
        rebuildError,
        rebuildSuccessMessage,
        
        // Actions
        setEditedProjectName,
        handleEditNameClick,
        handleCancelNameEdit,
        handleSaveProjectName,
        handleRebuildIndex
    };
}
