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
from typing import Set # Import Set

from app.services.ai_service import AIService
from app.services.file_service import FileService
from app.rag.engine import RagEngine
from app.models.ai import AIChapterSplitRequest, ProposedScene
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store import VectorStoreIndex


# --- Test AIService.split_chapter_into_scenes ---

@pytest.mark.asyncio
# --- MODIFIED: Patch imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_split_chapter_success(mock_file_service: MagicMock, mock_rag_engine: MagicMock): # Args match patch order
    """Test successful chapter splitting."""
    project_id = "split-proj-1"; chapter_id = "split-ch-1"
    chapter_content = "This is the full chapter content.\nIt has multiple potential scenes."
    request_data = AIChapterSplitRequest(chapter_content=chapter_content)
    mock_plan = "Plan context."; mock_synopsis = "Synopsis context."
    mock_proposed_scenes = [ ProposedScene(suggested_title="Scene A", content="This is the full chapter content."), ProposedScene(suggested_title="Scene B", content="It has multiple potential scenes.") ]
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md")
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")

    # Configure mocks
    # --- MODIFIED: Mock _get_content_block_path ---
    def get_content_block_path_side_effect(p_id, b_name):
        if p_id == project_id:
            if b_name == "plan.md": return mock_plan_path
            if b_name == "synopsis.md": return mock_synopsis_path
        pytest.fail(f"Unexpected call to _get_content_block_path: {p_id}, {b_name}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    # --- END MODIFIED ---
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else ""
    # Configure the rag_engine's split_chapter method
    mock_rag_engine.split_chapter = AsyncMock(return_value=mock_proposed_scenes)

    # Instantiate AIService
    service_instance = AIService()

    # Act
    result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

    # Assert
    assert result == mock_proposed_scenes
    mock_file_service.read_content_block_file.assert_has_calls([ call(project_id, "plan.md"), call(project_id, "synopsis.md") ], any_order=True)
    # --- MODIFIED: Add paths_to_filter to assertion ---
    expected_filter_set = {str(mock_plan_path), str(mock_synopsis_path)}
    mock_rag_engine.split_chapter.assert_awaited_once_with(
        project_id=project_id, chapter_id=chapter_id, chapter_content=chapter_content,
        explicit_plan=mock_plan, explicit_synopsis=mock_synopsis,
        paths_to_filter=expected_filter_set # Check filter
    )
    # --- END MODIFIED ---

@pytest.mark.asyncio
# --- MODIFIED: Patch imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_split_chapter_empty_content_in_request(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test splitting when the request body contains empty content."""
    project_id = "split-proj-empty"; chapter_id = "split-ch-empty"
    request_data = AIChapterSplitRequest(chapter_content="  ") # Whitespace only

    # Instantiate AIService
    service_instance = AIService()

    # Act
    result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

    # Assert
    assert result == [] # Expect empty list back
    mock_file_service.read_content_block_file.assert_not_called()
    mock_rag_engine.split_chapter.assert_not_awaited()


@pytest.mark.asyncio
# --- MODIFIED: Patch imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_split_chapter_context_load_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test splitting when loading plan/synopsis fails."""
    project_id = "split-proj-ctx-err"; chapter_id = "split-ch-ctx-err"
    chapter_content = "Valid chapter content."
    request_data = AIChapterSplitRequest(chapter_content=chapter_content)
    mock_proposed_scenes = [ProposedScene(suggested_title="Scene", content="Valid chapter content.")]
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md") # Define plan path even if read fails
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")

    # Configure mocks - Plan fails, Synopsis succeeds
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": raise ValueError("Disk read error") # Non-404 error
            if block_name == "synopsis.md": return "Synopsis OK."
        return ""
    # --- MODIFIED: Mock _get_content_block_path ---
    def get_content_block_path_side_effect(p_id, b_name):
        if p_id == project_id:
            # Simulate path retrieval works for both, even if read fails for plan
            if b_name == "plan.md": return mock_plan_path
            if b_name == "synopsis.md": return mock_synopsis_path
        pytest.fail(f"Unexpected call to _get_content_block_path: {p_id}, {b_name}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    # --- END MODIFIED ---
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_rag_engine.split_chapter = AsyncMock(return_value=mock_proposed_scenes)

    # Instantiate AIService
    service_instance = AIService()

    # Act
    result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

    # Assert
    assert result == mock_proposed_scenes # Should still succeed
    # --- MODIFIED: Assert read_content_block_file calls ---
    # It will be called for plan (and fail), then called for synopsis (and succeed)
    mock_file_service.read_content_block_file.assert_has_calls([
        call(project_id, "plan.md"),
        call(project_id, "synopsis.md")
    ], any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    # --- END MODIFIED ---
    # --- MODIFIED: Add paths_to_filter to assertion ---
    # Both paths should be added because path retrieval succeeded before read failed
    expected_filter_set = {str(mock_plan_path), str(mock_synopsis_path)}
    mock_rag_engine.split_chapter.assert_awaited_once_with(
        project_id=project_id, chapter_id=chapter_id, chapter_content=chapter_content,
        explicit_plan="Error loading plan.", # Correctly expect "Error..."
        explicit_synopsis="Synopsis OK.",
        paths_to_filter=expected_filter_set # Check filter
    )
    # --- END MODIFIED ---

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
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md")
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")

    # Configure mocks
    def get_content_block_path_side_effect(p_id, b_name):
        if p_id == project_id:
            if b_name == "plan.md": return mock_plan_path
            if b_name == "synopsis.md": return mock_synopsis_path
        pytest.fail(f"Unexpected call to _get_content_block_path: {p_id}, {b_name}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else ""
    # Simulate splitter raising an HTTPException
    mock_rag_engine.split_chapter = AsyncMock(side_effect=HTTPException(status_code=500, detail="LLM failed during split"))

    # Instantiate AIService
    service_instance = AIService()

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

    assert exc_info.value.status_code == 500
    assert "LLM failed during split" in exc_info.value.detail
    mock_file_service.read_content_block_file.assert_has_calls([ call(project_id, "plan.md"), call(project_id, "synopsis.md") ], any_order=True)
    mock_rag_engine.split_chapter.assert_awaited_once() # Still called once