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
import {
    listChapters,
    createChapter,
    updateChapter,
    deleteChapter,
    splitChapterIntoScenes, // Import split API
    compileChapterContent, // Import compile API
} from '../../../api/codexApi';
import { saveAs } from 'file-saver'; // For downloading compiled content

// Helper to extract error messages (can be shared or kept local)
const getApiErrorMessage = (error, defaultMessage = 'An unknown error occurred') => {
    if (error?.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
            try {
                const firstError = error.response.data.detail[0];
                const field = (Array.isArray(firstError?.loc) && firstError.loc.length > 1) ? firstError.loc.slice(1).join('.') : (Array.isArray(firstError?.loc) && firstError.loc.length === 1 ? firstError.loc[0] : 'input');
                const msg = firstError?.msg || 'Invalid input';
                return `${msg} (field: ${field})`;
            } catch (e) { return JSON.stringify(error.response.data.detail); }
        }
        if (typeof detail === 'string') { return detail; }
        if (typeof detail === 'object' && detail !== null) { return JSON.stringify(detail); }
    }
    if (error?.message) { return error.message; }
    return defaultMessage;
};


/**
 * Custom hook to manage chapter-related operations
 *
 * @param {string} projectId - The ID of the project
 * @returns {Object} Chapter data and operations
 */
export function useChapterOperations(projectId) {
    const isMounted = useRef(true);
    const [chapters, setChapters] = useState([]);
    const [isLoadingChapters, setIsLoadingChapters] = useState(true);
    const [error, setError] = useState(null); // General error for loading/creation
    const [chapterErrors, setChapterErrors] = useState({}); // Specific errors { [chapterId]: msg, [`split_${id}`]: msg, etc. }

    // Chapter Creation
    const [newChapterTitle, setNewChapterTitle] = useState('');
    const [isCreatingChapter, setIsCreatingChapter] = useState(false);

    // Chapter Editing
    const [editingChapterId, setEditingChapterId] = useState(null);
    const [editedChapterTitle, setEditedChapterTitle] = useState('');
    const [isSavingChapter, setIsSavingChapter] = useState(false);
    // Removed saveChapterError, using chapterErrors[chapterId]

    // Chapter Splitting
    const [showSplitModal, setShowSplitModal] = useState(false);
    const [chapterIdForSplits, setChapterIdForSplits] = useState(null);
    const [splitInputContent, setSplitInputContent] = useState({}); // { [chapterId]: content }
    const [proposedSplits, setProposedSplits] = useState([]);
    const [isSplittingChapter, setIsSplittingChapter] = useState(false);
    const [splittingChapterId, setSplittingChapterId] = useState(null); // Track which chapter is splitting
    // Removed splitError, using chapterErrors[`split_${chapterId}`]
    // Removed createFromSplitError, handled by sceneOps.sceneErrors[`split_create_${chapterId}`]

    // Chapter Compilation
    const [showCompiledContentModal, setShowCompiledContentModal] = useState(false);
    const [compiledContent, setCompiledContent] = useState('');
    const [compiledFileName, setCompiledFileName] = useState('');
    const [isCompilingChapter, setIsCompilingChapter] = useState(false);
    const [compilingChapterId, setCompilingChapterId] = useState(null);
    // Removed compileError, using chapterErrors[`compile_${chapterId}`]


    // Effect for component mount tracking
    useEffect(() => {
        isMounted.current = true;
        return () => { isMounted.current = false; };
    }, []);

    // Fetch chapters when project ID changes
    useEffect(() => {
        const abortController = new AbortController();
        const signal = abortController.signal;

        const fetchChapters = async () => {
            if (!projectId) {
                setChapters([]); setIsLoadingChapters(false); return;
            }
            let isComponentMounted = isMounted.current;
            if (isComponentMounted) { setIsLoadingChapters(true); setError(null); setChapterErrors({}); }

            try {
                if (signal.aborted) return;
                const response = await listChapters(projectId);
                if (isComponentMounted && isMounted.current && !signal.aborted) {
                    // Ensure order is numeric and sort
                    const sortedChapters = (response.data.chapters || [])
                        .map(ch => ({ ...ch, order: Number(ch.order) || 0 }))
                        .sort((a, b) => a.order - b.order);
                    setChapters(sortedChapters);
                }
            } catch (err) {
                if (signal.aborted) return;
                console.error('Error loading chapters:', err);
                if (isComponentMounted && isMounted.current) {
                    setError(getApiErrorMessage(err, 'Failed to load chapters'));
                }
            } finally {
                if (isComponentMounted && isMounted.current) { setIsLoadingChapters(false); }
            }
        };

        fetchChapters();
        return () => { abortController.abort(); };
    }, [projectId]);

    // --- Chapter CRUD ---

    const handleCreateChapter = useCallback(async () => {
        if (!newChapterTitle.trim() || !projectId) return;
        let isComponentMounted = isMounted.current;
        if (isComponentMounted) { setIsCreatingChapter(true); setError(null); } // Clear general error

        try {
            const nextOrder = chapters.length > 0 ? Math.max(0, ...chapters.map(c => Number(c.order) || 0)) + 1 : 1;
            const response = await createChapter(projectId, { title: newChapterTitle, order: nextOrder });
            if (isComponentMounted && isMounted.current) {
                setChapters(prev => [...prev, { ...response.data, order: Number(response.data.order) || 0 }].sort((a, b) => a.order - b.order));
                setNewChapterTitle('');
            }
        } catch (err) {
            console.error('Error creating chapter:', err);
            if (isComponentMounted && isMounted.current) {
                setError(getApiErrorMessage(err, 'Failed to create chapter')); // Set general error
            }
        } finally {
            if (isComponentMounted && isMounted.current) { setIsCreatingChapter(false); }
        }
    }, [projectId, newChapterTitle, chapters]); // Added chapters dependency

    const handleDeleteChapter = useCallback(async (chapterId, chapterTitle) => {
        const confirmMessage = `Are you sure you want to delete the chapter "${chapterTitle || 'this chapter'}" and all its scenes? This action cannot be undone.`;
        if (!window.confirm(confirmMessage)) return;

        let isComponentMounted = isMounted.current;
        const errorKey = chapterId; // Use chapterId as the key for delete errors
        if (isComponentMounted) {
            // Consider adding a specific deleting state if needed: setDeletingChapterId(chapterId);
            setChapterErrors(prev => { const n = { ...prev }; delete n[errorKey]; return n; }); // Clear previous error
        }

        try {
            // *** API call uses projectId and chapterId ***
            await deleteChapter(projectId, chapterId);
            if (isComponentMounted && isMounted.current) {
                setChapters(prev => prev
                    .filter(c => c.id !== chapterId)
                    // Re-order remaining chapters
                    .map((chapter, index) => ({ ...chapter, order: index + 1 }))
                    .sort((a, b) => a.order - b.order) // Ensure sorted
                );
            }
        } catch (err) {
            console.error('Error deleting chapter:', err);
            if (isComponentMounted && isMounted.current) {
                setChapterErrors(prev => ({ ...prev, [errorKey]: getApiErrorMessage(err, 'Failed to delete chapter') }));
            }
        } finally {
             if (isComponentMounted && isMounted.current) {
                 // Clear specific deleting state if added: setDeletingChapterId(null);
             }
        }
    }, [projectId]); // Recreate if projectId changes

    // --- Chapter Editing ---

    const handleEditChapterClick = useCallback((chapter) => {
        setEditingChapterId(chapter.id);
        setEditedChapterTitle(chapter.title);
        setChapterErrors(prev => { const n = { ...prev }; delete n[chapter.id]; return n; }); // Clear previous edit error
    }, []);

    const handleCancelChapterEdit = useCallback(() => {
        setEditingChapterId(null);
        setEditedChapterTitle('');
    }, []);

    const handleSaveChapterTitle = useCallback(async () => {
        if (!editingChapterId || !editedChapterTitle.trim()) return;
        let isComponentMounted = isMounted.current;
        const errorKey = editingChapterId;
        if (isComponentMounted) { setIsSavingChapter(true); setChapterErrors(prev => { const n = { ...prev }; delete n[errorKey]; return n; }); }

        try {
            // Find original chapter to get order
            const originalChapter = chapters.find(c => c.id === editingChapterId);
            if (!originalChapter) throw new Error("Original chapter not found for saving.");

            const response = await updateChapter(projectId, editingChapterId, { title: editedChapterTitle, order: originalChapter.order }); // Keep original order
            if (isComponentMounted && isMounted.current) {
                setChapters(prev => prev
                    .map(c => c.id === editingChapterId ? { ...response.data, order: Number(response.data.order) || 0 } : c)
                    .sort((a, b) => a.order - b.order) // Ensure sorted
                );
                setEditingChapterId(null);
                setEditedChapterTitle('');
            }
        } catch (err) {
            console.error('Error saving chapter title:', err);
            if (isComponentMounted && isMounted.current) {
                setChapterErrors(prev => ({ ...prev, [errorKey]: getApiErrorMessage(err, 'Failed to save chapter title') }));
            }
        } finally {
            if (isComponentMounted && isMounted.current) { setIsSavingChapter(false); }
        }
    }, [projectId, editingChapterId, editedChapterTitle, chapters]); // Added chapters dependency

    // --- Chapter Splitting ---

    const handleSplitInputChange = useCallback((chapterId, value) => {
        setSplitInputContent(prev => ({ ...prev, [chapterId]: value }));
    }, []);

    const handleOpenSplitModal = useCallback((chapterId) => {
        setChapterIdForSplits(chapterId);
        setProposedSplits([]); // Clear previous proposals
        const errorKey = `split_${chapterId}`;
        setChapterErrors(prev => { const n = { ...prev }; delete n[errorKey]; return n; }); // Clear previous error
        setShowSplitModal(true);
    }, []);

    const handleCloseSplitModal = useCallback(() => {
        setShowSplitModal(false);
        setChapterIdForSplits(null);
        setProposedSplits([]);
        setSplittingChapterId(null); // Clear splitting marker
    }, []);

    const handleSplitChapter = useCallback(async () => { // Renamed from handleSplitChapterApiCall for clarity
        if (!chapterIdForSplits || !splitInputContent[chapterIdForSplits]?.trim()) return;

        let isComponentMounted = isMounted.current;
        const errorKey = `split_${chapterIdForSplits}`;
        if (isComponentMounted) {
            setIsSplittingChapter(true);
            setSplittingChapterId(chapterIdForSplits); // Set marker
            setProposedSplits([]); // Clear old splits
            setChapterErrors(prev => { const n = { ...prev }; delete n[errorKey]; return n; }); // Clear previous error
        }

        try {
            // Use chapter_content to match the backend model field name
            const requestData = { chapter_content: splitInputContent[chapterIdForSplits] };
            const response = await splitChapterIntoScenes(projectId, chapterIdForSplits, requestData);
            if (isComponentMounted && isMounted.current) {
                setProposedSplits(response.data.proposed_scenes || []);
            }
        } catch (err) {
            console.error('Error splitting chapter:', err);
            if (isComponentMounted && isMounted.current) {
                setChapterErrors(prev => ({ ...prev, [errorKey]: getApiErrorMessage(err, 'Failed to split chapter') }));
            }
        } finally {
            if (isComponentMounted && isMounted.current) {
                setIsSplittingChapter(false);
                // Keep splittingChapterId set while modal is open? Clear on close.
            }
        }
    }, [projectId, chapterIdForSplits, splitInputContent]);

    // --- Chapter Compilation ---

    const handleCompileChapter = useCallback(async (chapterId) => {
        let isComponentMounted = isMounted.current;
        const errorKey = `compile_${chapterId}`;
        if (isComponentMounted) {
            setIsCompilingChapter(true);
            setCompilingChapterId(chapterId);
            setCompiledContent(''); // Clear previous
            setCompiledFileName(''); // Clear previous
            setChapterErrors(prev => { const n = { ...prev }; delete n[errorKey]; return n; }); // Clear previous error
        }

        try {
            // Example: Include titles, use double newline separator
            const params = { include_titles: true, separator: '\n\n' };
            const response = await compileChapterContent(projectId, chapterId, params);
            if (isComponentMounted && isMounted.current) {
                setCompiledContent(response.data.content);
                setCompiledFileName(response.data.filename);
                // Option 1: Show modal
                // setShowCompiledContentModal(true);
                // Option 2: Trigger download directly
                const blob = new Blob([response.data.content], { type: 'text/markdown;charset=utf-8' });
                saveAs(blob, response.data.filename); // Use file-saver
            }
        } catch (err) {
            console.error('Error compiling chapter:', err);
            if (isComponentMounted && isMounted.current) {
                setChapterErrors(prev => ({ ...prev, [errorKey]: getApiErrorMessage(err, 'Failed to compile chapter') }));
                // Optionally show modal even on error to display the message
                // setCompiledContent(''); // Ensure no stale content shown
                // setCompiledFileName('');
                // setShowCompiledContentModal(true);
            }
        } finally {
            if (isComponentMounted && isMounted.current) {
                setIsCompilingChapter(false);
                setCompilingChapterId(null); // Clear marker
            }
        }
    }, [projectId]);

     const handleCloseCompileModal = useCallback(() => {
         setShowCompiledContentModal(false);
         setCompiledContent('');
         setCompiledFileName('');
         setCompilingChapterId(null); // Clear marker if modal is closed
     }, []);


    return {
        // State
        chapters,
        isLoadingChapters,
        error, // General loading/creation error
        chapterErrors, // Specific errors
        newChapterTitle,
        isCreatingChapter,
        editingChapterId,
        editedChapterTitle,
        isSavingChapter,
        showSplitModal,
        chapterIdForSplits,
        splitInputContent,
        proposedSplits,
        isSplittingChapter,
        splittingChapterId,
        showCompiledContentModal,
        compiledContent,
        compiledFileName,
        isCompilingChapter,
        compilingChapterId,

        // Actions
        setNewChapterTitle,
        handleCreateChapter,
        handleDeleteChapter,
        handleEditChapterClick,
        setEditedChapterTitle, // Allow direct setting for input binding
        handleSaveChapterTitle,
        handleCancelChapterEdit,
        handleSplitInputChange,
        handleOpenSplitModal,
        handleCloseSplitModal,
        handleSplitChapter, // Renamed API call trigger
        handleCompileChapter,
        handleCloseCompileModal,
    };
}