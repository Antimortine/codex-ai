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
from unittest.mock import MagicMock, AsyncMock, call, patch
from fastapi import HTTPException, status

# Import the class we are testing
from app.services.ai_service import AIService
# Import classes for dependencies
from app.services.file_service import FileService
from app.rag.engine import RagEngine
# Import models used
from app.models.ai import AIChapterSplitRequest, ProposedScene
# Import LLM and Index types for mocking engine attributes
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store import VectorStoreIndex

# --- Tests for AIService.split_chapter_into_scenes ---

@pytest.mark.asyncio
@patch('app.services.ai_service.ChapterSplitter')
async def test_split_chapter_success(mock_chapter_splitter_class: MagicMock):
    """Test successful chapter splitting."""
    project_id = "split-proj-1"
    chapter_id = "split-ch-1"
    chapter_content = "This is the full chapter content.\nIt has multiple potential scenes."
    request_data = AIChapterSplitRequest(chapter_content=chapter_content)
    mock_plan = "Plan context."
    mock_synopsis = "Synopsis context."
    mock_proposed_scenes = [
        ProposedScene(suggested_title="Scene A", content="This is the full chapter content."),
        ProposedScene(suggested_title="Scene B", content="It has multiple potential scenes.")
    ]

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)
    mock_splitter_instance = mock_chapter_splitter_class.return_value

    # Setup mocks for AIService __init__
    mock_rag_engine.llm = MagicMock(spec=LLM)
    mock_rag_engine.index = MagicMock(spec=VectorStoreIndex)

    # Configure mocks
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else ""
    # Configure the *instance*'s split method
    mock_splitter_instance.split = AsyncMock(return_value=mock_proposed_scenes)

    # Instantiate AIService, patching its dependencies
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()
        mock_chapter_splitter_class.assert_called_once_with(index=mock_rag_engine.index, llm=mock_rag_engine.llm)
        assert service_instance.chapter_splitter is mock_splitter_instance

        # Act
        result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

    # Assert
    assert result == mock_proposed_scenes
    mock_file_service.read_content_block_file.assert_has_calls([
        call(project_id, "plan.md"), call(project_id, "synopsis.md")
    ], any_order=True)
    mock_splitter_instance.split.assert_awaited_once_with(
        project_id=project_id,
        chapter_id=chapter_id,
        chapter_content=chapter_content,
        explicit_plan=mock_plan,
        explicit_synopsis=mock_synopsis
    )

@pytest.mark.asyncio
@patch('app.services.ai_service.ChapterSplitter')
async def test_split_chapter_empty_content_in_request(mock_chapter_splitter_class: MagicMock):
    """Test splitting when the request body contains empty content."""
    project_id = "split-proj-empty"
    chapter_id = "split-ch-empty"
    request_data = AIChapterSplitRequest(chapter_content="  ") # Whitespace only

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)
    mock_splitter_instance = mock_chapter_splitter_class.return_value
    # --- MODIFIED: Ensure the split method is an AsyncMock even if not called ---
    mock_splitter_instance.split = AsyncMock()
    # --- END MODIFIED ---

    # Setup mocks for AIService __init__
    mock_rag_engine.llm = MagicMock(spec=LLM)
    mock_rag_engine.index = MagicMock(spec=VectorStoreIndex)

    # Instantiate AIService
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()
        mock_chapter_splitter_class.assert_called_once()

        # Act
        result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

    # Assert
    assert result == [] # Expect empty list back
    mock_file_service.read_content_block_file.assert_not_called()
    # --- Use assert_not_awaited on the AsyncMock ---
    mock_splitter_instance.split.assert_not_awaited()
    # --- END Use assert_not_awaited ---


@pytest.mark.asyncio
@patch('app.services.ai_service.ChapterSplitter')
async def test_split_chapter_context_load_error(mock_chapter_splitter_class: MagicMock):
    """Test splitting when loading plan/synopsis fails."""
    project_id = "split-proj-ctx-err"
    chapter_id = "split-ch-ctx-err"
    chapter_content = "Valid chapter content."
    request_data = AIChapterSplitRequest(chapter_content=chapter_content)
    mock_proposed_scenes = [ProposedScene(suggested_title="Scene", content="Valid chapter content.")]

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)
    mock_splitter_instance = mock_chapter_splitter_class.return_value

    # Setup mocks for AIService __init__
    mock_rag_engine.llm = MagicMock(spec=LLM)
    mock_rag_engine.index = MagicMock(spec=VectorStoreIndex)

    # Configure mocks - Plan fails, Synopsis succeeds
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": raise ValueError("Disk read error")
            if block_name == "synopsis.md": return "Synopsis OK."
        return ""
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_splitter_instance.split = AsyncMock(return_value=mock_proposed_scenes)

    # Instantiate AIService
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()
        mock_chapter_splitter_class.assert_called_once()

        # Act
        result = await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

    # Assert
    assert result == mock_proposed_scenes # Should still succeed
    mock_file_service.read_content_block_file.assert_has_calls([
        call(project_id, "plan.md"), call(project_id, "synopsis.md")
    ], any_order=True)
    mock_splitter_instance.split.assert_awaited_once_with(
        project_id=project_id,
        chapter_id=chapter_id,
        chapter_content=chapter_content,
        explicit_plan="Error loading plan.",
        explicit_synopsis="Synopsis OK."
    )

@pytest.mark.asyncio
@patch('app.services.ai_service.ChapterSplitter')
async def test_split_chapter_splitter_error(mock_chapter_splitter_class: MagicMock):
    """Test splitting when the ChapterSplitter itself raises an error."""
    project_id = "split-proj-split-err"
    chapter_id = "split-ch-split-err"
    chapter_content = "Content that causes splitter error."
    request_data = AIChapterSplitRequest(chapter_content=chapter_content)
    mock_plan = "Plan."
    mock_synopsis = "Synopsis."

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)
    mock_splitter_instance = mock_chapter_splitter_class.return_value

    # Setup mocks for AIService __init__
    mock_rag_engine.llm = MagicMock(spec=LLM)
    mock_rag_engine.index = MagicMock(spec=VectorStoreIndex)

    # Configure mocks
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else ""
    # Simulate splitter raising an HTTPException
    mock_splitter_instance.split = AsyncMock(side_effect=HTTPException(status_code=500, detail="LLM failed during split"))

    # Instantiate AIService
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()
        mock_chapter_splitter_class.assert_called_once()

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            await service_instance.split_chapter_into_scenes(project_id, chapter_id, request_data)

        assert exc_info.value.status_code == 500
        assert "LLM failed during split" in exc_info.value.detail

    mock_file_service.read_content_block_file.assert_has_calls([
        call(project_id, "plan.md"), call(project_id, "synopsis.md")
    ], any_order=True)
    mock_splitter_instance.split.assert_awaited_once()