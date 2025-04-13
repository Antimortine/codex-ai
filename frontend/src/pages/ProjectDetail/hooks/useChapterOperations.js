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
    deleteChapter, 
    updateChapter,
    splitChapterIntoScenes,
    compileChapterContent
} from '../../../api/codexApi';

/**
 * Custom hook to manage chapter-related operations
 * 
 * @param {string} projectId - The ID of the project
 * @returns {Object} Chapter data and operations
 */
export function useChapterOperations(projectId) {
    // Keep track of component mount status to prevent state updates after unmount
    const isMounted = useRef(true);
    // Chapter state
    const [chapters, setChapters] = useState([]);
    const [isLoadingChapters, setIsLoadingChapters] = useState(true);
    const [newChapterTitle, setNewChapterTitle] = useState('');
    
    // Chapter editing state
    const [editingChapterId, setEditingChapterId] = useState(null);
    const [editedChapterTitle, setEditedChapterTitle] = useState('');
    const [isSavingChapter, setIsSavingChapter] = useState(false);
    const [saveChapterError, setSaveChapterError] = useState(null);
    
    // Chapter splitting state
    const [splitInputContent, setSplitInputContent] = useState({});
    const [proposedSplits, setProposedSplits] = useState([]);
    const [chapterIdForSplits, setChapterIdForSplits] = useState(null);
    const [showSplitModal, setShowSplitModal] = useState(false);
    const [isCreatingScenesFromSplit, setIsCreatingScenesFromSplit] = useState(false);
    const [createFromSplitError, setCreateFromSplitError] = useState(null);
    const [isSplittingChapter, setIsSplittingChapter] = useState(false);
    const [splittingChapterId, setSplittingChapterId] = useState(null);
    const [splitError, setSplitError] = useState(null);
    
    // Chapter compilation state
    const [isCompilingChapter, setIsCompilingChapter] = useState(false);
    const [compilingChapterId, setCompilingChapterId] = useState(null);
    const [compiledContent, setCompiledContent] = useState('');
    const [showCompiledContentModal, setShowCompiledContentModal] = useState(false);
    const [compileError, setCompileError] = useState(null);

    // Reset state when project ID changes and set up cleanup
    useEffect(() => {
        // Set mounted flag and reset state
        isMounted.current = true;
        
        const resetState = () => {
            if (isMounted.current) {
                setIsLoadingChapters(true);
                setChapters([]);
                setEditingChapterId(null);
                setEditedChapterTitle('');
                setSaveChapterError('');
                setCompiledContent({});
                setNewChapterTitle('');
            }
        };
        
        resetState();
        
        // Only load chapters if component is still mounted
        if (isMounted.current) {
            loadChapters();
        }
        
        // Cleanup function to prevent state updates after unmount
        return () => {
            isMounted.current = false;
        };
    }, [projectId]);

    const loadChapters = useCallback(async () => {
        if (!projectId) return;
        
        setIsLoadingChapters(true);
        listChapters(projectId)
            .then(response => {
                // Sort chapters by order
                const sortedChapters = [...response.data.chapters].sort((a, b) => a.order - b.order);
                if (isMounted.current) {
                    setChapters(sortedChapters);
                }
            })
            .catch(err => {
                console.error('Error loading chapters:', err);
            })
            .finally(() => {
                if (isMounted.current) {
                    setIsLoadingChapters(false);
                }
            });
    }, [projectId]);

    // Handle creating a new chapter
    const handleCreateChapter = useCallback(async () => {
        if (!newChapterTitle.trim()) return;
        
        // Store isMounted in a local variable to avoid race conditions
        let isComponentMounted = isMounted.current;
        
        try {
            const response = await createChapter(projectId, { title: newChapterTitle });
            if (isComponentMounted && isMounted.current) {
                setChapters(prev => {
                    const updated = [...prev, response.data];
                    return updated.sort((a, b) => a.order - b.order);
                });
                setNewChapterTitle('');
            }
        } catch (err) {
            console.error('Error creating chapter:', err);
        }
    }, [projectId, newChapterTitle]);

    // Handle deleting a chapter
    const handleDeleteChapter = useCallback(async (chapterId) => {
        if (!window.confirm('Are you sure you want to delete this chapter? This action cannot be undone.')) {
            return;
        }
        
        try {
            await deleteChapter(projectId, chapterId);
            setChapters(prev => prev.filter(chapter => chapter.id !== chapterId));
        } catch (err) {
            console.error('Error deleting chapter:', err);
        }
    }, [projectId]);

    // Handle editing a chapter title
    const handleEditChapterClick = useCallback((chapter) => {
        setEditingChapterId(chapter.id);
        setEditedChapterTitle(chapter.title);
        setSaveChapterError(null);
    }, []);

    // Handle saving a chapter title
    const handleSaveChapterTitle = useCallback(async () => {
        if (!editedChapterTitle.trim() || !editingChapterId) return;
        
        setIsSavingChapter(true);
        setSaveChapterError(null);
        
        try {
            const response = await updateChapter(projectId, editingChapterId, { 
                title: editedChapterTitle 
            });
            
            setChapters(prev => 
                prev.map(ch => ch.id === editingChapterId 
                    ? { ...ch, title: response.data.title } 
                    : ch
                )
            );
            
            // Reset editing state
            setEditingChapterId(null);
            setEditedChapterTitle('');
        } catch (err) {
            console.error('Error updating chapter:', err);
            setSaveChapterError(err.message || 'Failed to update chapter');
        } finally {
            setIsSavingChapter(false);
        }
    }, [projectId, editingChapterId, editedChapterTitle]);

    // Handle canceling chapter edit
    const handleCancelChapterEdit = useCallback(() => {
        setEditingChapterId(null);
        setEditedChapterTitle('');
        setSaveChapterError(null);
    }, []);

    // Handle opening split chapter modal
    const handleOpenSplitModal = useCallback((chapterId, initialContent = '') => {
        setChapterIdForSplits(chapterId);
        setSplitInputContent(prev => ({ ...prev, [chapterId]: initialContent }));
        setProposedSplits([]);
        setSplitError(null);
        setShowSplitModal(true);
    }, []);

    // Handle splitting a chapter into scenes
    const handleSplitChapter = useCallback(async () => {
        if (!chapterIdForSplits || !splitInputContent[chapterIdForSplits]?.trim()) {
            setSplitError('Please enter content to split');
            return;
        }
        
        setIsSplittingChapter(true);
        setSplittingChapterId(chapterIdForSplits);
        setSplitError(null);
        
        try {
            const response = await splitChapterIntoScenes(
                projectId, 
                chapterIdForSplits, 
                splitInputContent[chapterIdForSplits]
            );
            
            setProposedSplits(response.data.scenes || []);
        } catch (err) {
            console.error('Error splitting chapter:', err);
            setSplitError(err.message || 'Failed to split chapter');
        } finally {
            setIsSplittingChapter(false);
            setSplittingChapterId(null);
        }
    }, [projectId, chapterIdForSplits, splitInputContent]);

    // Handle compiling chapter content
    const handleCompileChapter = useCallback(async (chapterId) => {
        setIsCompilingChapter(true);
        setCompilingChapterId(chapterId);
        setCompileError(null);
        
        try {
            const response = await compileChapterContent(projectId, chapterId);
            if (isMounted.current) {
                setCompiledContent(response.data.content || '');
                setShowCompiledContentModal(true);
            }
        } catch (err) {
            console.error('Error compiling chapter:', err);
            setCompileError(err.message || 'Failed to compile chapter');
        } finally {
            setIsCompilingChapter(false);
            setCompilingChapterId(null);
        }
    }, [projectId]);

    return {
        // State
        chapters,
        isLoadingChapters,
        newChapterTitle,
        editingChapterId,
        editedChapterTitle,
        isSavingChapter,
        saveChapterError,
        splitInputContent,
        proposedSplits,
        chapterIdForSplits,
        showSplitModal,
        isCreatingScenesFromSplit,
        createFromSplitError,
        isSplittingChapter,
        splittingChapterId,
        splitError,
        isCompilingChapter,
        compilingChapterId,
        compiledContent,
        showCompiledContentModal,
        compileError,
        
        // Actions
        setNewChapterTitle,
        setEditedChapterTitle,
        setSplitInputContent,
        setShowSplitModal,
        setShowCompiledContentModal,
        handleCreateChapter,
        handleDeleteChapter,
        handleEditChapterClick,
        handleSaveChapterTitle,
        handleCancelChapterEdit,
        handleOpenSplitModal,
        handleSplitChapter,
        handleCompileChapter
    };
}
