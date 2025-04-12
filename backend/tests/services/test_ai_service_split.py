# Copyright 2025 Antimortine
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from unittest.mock import MagicMock, AsyncMock, call, patch, ANY # Import ANY
from fastapi import HTTPException, status
from pathlib import Path # Import Path
from typing import Set, List, Optional, Dict # Added List, Optional, Dict

from app.services.ai_service import AIService, LoadedContext # Import LoadedContext
from app.services.file_service import FileService
from app.rag.engine import RagEngine
from app.models.ai import AIChapterSplitRequest, ProposedScene
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store import VectorStoreIndex


# --- Test AIService.split_chapter_into_scenes ---

@pytest.mark.asyncio
# --- MODIFIED: Patch rag_engine and file_service (no longer needed for context) ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True) # Keep for consistency
# --- END MODIFIED ---
async def test_split_chapter_success(mock_file_service: MagicMock, mock_rag_engine: MagicMock): # Args match patch order
    """Test successful chapter splitting."""
    project_id = "split-proj-1"; chapter_id = "split-ch-1"
    chapter_content = "This is the full chapter content.\nIt has multiple potential scenes."
    request_data = AIChapterSplitRequest(chapter_content=chapter_content)
    mock_plan = "Plan context."; mock_synopsis = "Synopsis context."
    mock_chapter_plan = "Chapter plan."; mock_chapter_synopsis = "Chapter synopsis."
    mock_proposed_scenes = [ ProposedScene(suggested_title="Scene A", content="This is the full chapter content."), ProposedScene(suggested_title="Scene B", content="It has multiple potential scenes.") ]
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()
    mock_chapter_plan_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/plan.md").resolve()
    mock_chapter_synopsis_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/synopsis.md").resolve()

    # Mock _load_context return value
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': mock_synopsis,
        'chapter_plan': mock_chapter_plan,
        'chapter_synopsis': mock_chapter_synopsis,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path), str(mock_chapter_plan_path), str(mock_chapter_synopsis_path)}
    }

    # Configure the rag_engine's split_chapter method
    mock_rag_engine.split_chapter = AsyncMock(return_value=mock_proposed_scenes)

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Act
        result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

        # Assert
        assert result == mock_proposed_scenes
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
        mock_rag_engine.split_chapter.assert_awaited_once_with(
            project_id=project_id, chapter_id=chapter_id, chapter_content=chapter_content,
            explicit_plan=mock_plan,
            explicit_synopsis=mock_synopsis,
            explicit_chapter_plan=mock_chapter_plan,
            explicit_chapter_synopsis=mock_chapter_synopsis,
            paths_to_filter=mock_loaded_context['filter_paths']
        )

@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_split_chapter_empty_content_in_request(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test splitting when the request body contains empty content."""
    project_id = "split-proj-empty"; chapter_id = "split-ch-empty"
    request_data = AIChapterSplitRequest(chapter_content="  ") # Whitespace only

    # Instantiate AIService
    service_instance = AIService()
    # No need to patch _load_context as it won't be called

    # Act
    result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

    # Assert
    assert result == [] # Expect empty list back
    mock_rag_engine.split_chapter.assert_not_awaited()


@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_split_chapter_context_load_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test splitting when loading context returns None for some fields."""
    project_id = "split-proj-ctx-err"; chapter_id = "split-ch-ctx-err"
    chapter_content = "Valid chapter content."
    request_data = AIChapterSplitRequest(chapter_content=chapter_content)
    mock_proposed_scenes = [ProposedScene(suggested_title="Scene", content="Valid chapter content.")]
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()
    mock_chapter_plan_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/plan.md").resolve()

    # Mock _load_context return value (missing project plan and chapter synopsis)
    mock_loaded_context: LoadedContext = {
        'project_plan': None,
        'project_synopsis': "Synopsis OK.",
        'chapter_plan': "Chapter Plan OK.",
        'chapter_synopsis': None,
        'filter_paths': {str(mock_synopsis_path), str(mock_chapter_plan_path)}
    }

    mock_rag_engine.split_chapter = AsyncMock(return_value=mock_proposed_scenes)

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Act
        result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

        # Assert
        assert result == mock_proposed_scenes # Should still succeed
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
        mock_rag_engine.split_chapter.assert_awaited_once_with(
            project_id=project_id, chapter_id=chapter_id, chapter_content=chapter_content,
            explicit_plan=None, # Correctly expect None
            explicit_synopsis="Synopsis OK.",
            explicit_chapter_plan="Chapter Plan OK.",
            explicit_chapter_synopsis=None, # Correctly expect None
            paths_to_filter=mock_loaded_context['filter_paths']
        )

# --- Test for splitter error remains unchanged ---
@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_split_chapter_splitter_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test splitting when the ChapterSplitter itself raises an error."""
    project_id = "split-proj-split-err"; chapter_id = "split-ch-split-err"
    chapter_content = "Content that causes splitter error."
    request_data = AIChapterSplitRequest(chapter_content=chapter_content)
    mock_plan = "Plan."; mock_synopsis = "Synopsis."
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()

    # Mock _load_context return value
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': mock_synopsis,
        'chapter_plan': None,
        'chapter_synopsis': None,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path)}
    }

    # Simulate splitter raising an HTTPException
    mock_rag_engine.split_chapter = AsyncMock(side_effect=HTTPException(status_code=500, detail="LLM failed during split"))

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

        assert exc_info.value.status_code == 500
        assert "LLM failed during split" in exc_info.value.detail
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
        mock_rag_engine.split_chapter.assert_awaited_once() # Still called once