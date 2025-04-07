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
from pathlib import Path
import asyncio

# Import the *class* we are testing, not the singleton instance
from app.services.ai_service import AIService
# Import classes for dependencies
from app.services.file_service import FileService
from app.rag.engine import RagEngine
# Import models used in responses/arguments
from app.models.ai import AISceneGenerationRequest
# Import settings for PREVIOUS_SCENE_COUNT
from app.core.config import settings

# --- Tests for AIService.generate_scene_draft ---

@pytest.mark.asyncio
async def test_generate_scene_draft_success_with_previous(monkeypatch): # Add monkeypatch
    """Test successful scene generation with plan, synopsis, and previous scene."""
    project_id = "gen-proj-1"
    chapter_id = "ch-1"
    request_data = AISceneGenerationRequest(prompt_summary="Character enters the room.", previous_scene_order=2)
    mock_plan = "Project plan content."
    mock_synopsis = "Project synopsis content."
    mock_prev_scene_id = "scene-id-2"
    mock_prev_scene_content = "## Previous Scene\nContent of the scene before."
    mock_generated_content = "## New Scene\nThe character walked into the dimly lit room."
    mock_chapter_metadata = {
        "scenes": {
            "scene-id-1": {"title": "Scene 1", "order": 1},
            mock_prev_scene_id: {"title": "Scene 2", "order": 2}, # The previous scene
            "scene-id-3": {"title": "Scene 3", "order": 3},
        }
    }
    # Define the path expected by the mock setup
    mock_scene_path_2 = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{mock_prev_scene_id}.md")

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure file service mocks using side_effect for more control
    def get_scene_path_side_effect(p_id, c_id, s_id):
        # Only return the path for the scene we expect to load (scene-id-2)
        if p_id == project_id and c_id == chapter_id and s_id == mock_prev_scene_id:
            return mock_scene_path_2
        # For any other scene ID requested in this test, fail explicitly
        pytest.fail(f"Unexpected call to _get_scene_path with scene_id: {s_id}")

    def read_text_file_side_effect(path):
        # Only return content for the path we expect to read
        if path == mock_scene_path_2:
            return mock_prev_scene_content
        pytest.fail(f"Unexpected call to read_text_file with path: {path}")

    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else pytest.fail("Unexpected block read")
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.side_effect = get_scene_path_side_effect
    mock_file_service.read_text_file.side_effect = read_text_file_side_effect

    # Configure rag engine mock
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_content)

    # --- Force PREVIOUS_SCENE_COUNT to 1 for this test ---
    # Patch the setting object directly
    monkeypatch.setattr(settings, 'RAG_GENERATION_PREVIOUS_SCENE_COUNT', 1, raising=False)
    # Patch the constant within the ai_service module where it's imported
    monkeypatch.setattr('app.services.ai_service.PREVIOUS_SCENE_COUNT', 1, raising=False)

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        # Instantiation happens after monkeypatching the module-level constant
        service_instance = AIService()

    # Call the method
    result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    # Assertions
    assert result == mock_generated_content
    mock_file_service.read_content_block_file.assert_has_calls([call(project_id, "plan.md"), call(project_id, "synopsis.md")], any_order=True)
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)

    # Verify _get_scene_path was called ONLY for the expected scene (scene-id-2)
    mock_file_service._get_scene_path.assert_called_once_with(project_id, chapter_id, mock_prev_scene_id)

    # Verify read_text_file was called ONLY for the expected scene path
    mock_file_service.read_text_file.assert_called_once_with(mock_scene_path_2)

    mock_rag_engine.generate_scene.assert_awaited_once_with(
        project_id=project_id,
        chapter_id=chapter_id,
        prompt_summary=request_data.prompt_summary,
        previous_scene_order=request_data.previous_scene_order,
        explicit_plan=mock_plan,
        explicit_synopsis=mock_synopsis,
        explicit_previous_scenes=[(2, mock_prev_scene_content)] # Expecting only scene 2
    )


@pytest.mark.asyncio
async def test_generate_scene_draft_success_first_scene():
    """Test successful scene generation for the first scene (no previous)."""
    project_id = "gen-proj-2"
    chapter_id = "ch-1"
    # previous_scene_order is 0 or None for the first scene
    request_data = AISceneGenerationRequest(prompt_summary="The story begins.", previous_scene_order=0)
    mock_plan = "Plan for first scene."
    mock_synopsis = "Synopsis for first scene."
    mock_generated_content = "## Chapter 1, Scene 1\nIt was a dark and stormy night."

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks (no chapter metadata or scene read needed)
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else pytest.fail("Unexpected block read")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_content)

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()

    # Call the method
    result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    # Assertions
    assert result == mock_generated_content
    mock_file_service.read_content_block_file.assert_has_calls([call(project_id, "plan.md"), call(project_id, "synopsis.md")], any_order=True)
    mock_file_service.read_chapter_metadata.assert_not_called() # Shouldn't be called if previous_scene_order is 0
    mock_file_service.read_text_file.assert_not_called() # Shouldn't read previous scenes
    mock_rag_engine.generate_scene.assert_awaited_once_with(
        project_id=project_id,
        chapter_id=chapter_id,
        prompt_summary=request_data.prompt_summary,
        previous_scene_order=request_data.previous_scene_order,
        explicit_plan=mock_plan,
        explicit_synopsis=mock_synopsis,
        explicit_previous_scenes=[] # No previous scenes expected
    )

@pytest.mark.asyncio
async def test_generate_scene_draft_context_not_found():
    """Test scene generation when plan/synopsis/metadata are missing (404)."""
    project_id = "gen-proj-3"
    chapter_id = "ch-2"
    request_data = AISceneGenerationRequest(prompt_summary="Something happens.", previous_scene_order=1)
    mock_generated_content = "## Scene 2\nDespite missing context, something happened."

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks
    mock_file_service.read_content_block_file.side_effect = HTTPException(status_code=404, detail="Not Found")
    mock_file_service.read_chapter_metadata.side_effect = HTTPException(status_code=404, detail="Not Found")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_content)

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()

    # Call the method
    result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    # Assertions
    assert result == mock_generated_content
    assert mock_file_service.read_content_block_file.call_count == 2 # Called for plan and synopsis
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id) # Called even if 404
    mock_file_service.read_text_file.assert_not_called() # No previous scenes loaded if metadata fails
    mock_rag_engine.generate_scene.assert_awaited_once_with(
        project_id=project_id,
        chapter_id=chapter_id,
        prompt_summary=request_data.prompt_summary,
        previous_scene_order=request_data.previous_scene_order,
        explicit_plan="", # Expect empty string on 404
        explicit_synopsis="", # Expect empty string on 404
        explicit_previous_scenes=[] # Expect empty list
    )

@pytest.mark.asyncio
async def test_generate_scene_draft_context_load_error():
    """Test scene generation when context loading raises unexpected errors."""
    project_id = "gen-proj-4"
    chapter_id = "ch-3"
    request_data = AISceneGenerationRequest(prompt_summary="Error handling test.", previous_scene_order=1)
    mock_generated_content = "## Scene 2\nGenerated despite loading errors."

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks
    def read_block_error(p_id, b_name):
        if b_name == "plan.md": raise ValueError("Plan load failed")
        if b_name == "synopsis.md": return "Synopsis loaded okay."
        pytest.fail("Unexpected block read")
    mock_file_service.read_content_block_file.side_effect = read_block_error
    mock_file_service.read_chapter_metadata.side_effect = OSError("Cannot read metadata")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_content)

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()

    # Call the method
    result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    # Assertions
    assert result == mock_generated_content
    assert mock_file_service.read_content_block_file.call_count == 2
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_file_service.read_text_file.assert_not_called()
    mock_rag_engine.generate_scene.assert_awaited_once_with(
        project_id=project_id,
        chapter_id=chapter_id,
        prompt_summary=request_data.prompt_summary,
        previous_scene_order=request_data.previous_scene_order,
        explicit_plan="Error loading plan.", # Expect error string
        explicit_synopsis="Synopsis loaded okay.",
        explicit_previous_scenes=[] # Expect empty list due to metadata error
    )

@pytest.mark.asyncio
async def test_generate_scene_draft_rag_engine_error():
    """Test scene generation when the rag_engine itself raises an error."""
    project_id = "gen-proj-5"
    chapter_id = "ch-4"
    request_data = AISceneGenerationRequest(prompt_summary="Engine failure test.", previous_scene_order=1)
    mock_plan = "Plan."
    mock_synopsis = "Synopsis."
    mock_chapter_metadata = {"scenes": {}} # No previous scenes needed for this test

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else pytest.fail("Unexpected block read")
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    # Simulate engine failure
    mock_rag_engine.generate_scene = AsyncMock(side_effect=HTTPException(status_code=503, detail="LLM Service Unavailable"))

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()

    # Call the method and expect the exception
    with pytest.raises(HTTPException) as exc_info:
        await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    assert exc_info.value.status_code == 503
    assert "LLM Service Unavailable" in exc_info.value.detail

    # Verify mocks up to the point of failure
    mock_file_service.read_content_block_file.assert_has_calls([call(project_id, "plan.md"), call(project_id, "synopsis.md")], any_order=True)
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_rag_engine.generate_scene.assert_awaited_once() # Should have been called

@pytest.mark.asyncio
async def test_generate_scene_draft_rag_engine_returns_error_string():
    """Test scene generation when rag_engine returns an error string."""
    project_id = "gen-proj-6"
    chapter_id = "ch-5"
    request_data = AISceneGenerationRequest(prompt_summary="Engine error string test.", previous_scene_order=0)
    mock_plan = "Plan."
    mock_synopsis = "Synopsis."
    error_string = "Error: Generation failed due to content policy."

    # Mocks
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else pytest.fail("Unexpected block read")
    mock_rag_engine.generate_scene = AsyncMock(return_value=error_string)

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()

    # Call the method and expect an HTTPException because the service should detect the error string
    with pytest.raises(HTTPException) as exc_info:
        await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    assert exc_info.value.status_code == 500
    assert error_string in exc_info.value.detail

    # Verify mocks
    mock_file_service.read_content_block_file.assert_has_calls([call(project_id, "plan.md"), call(project_id, "synopsis.md")], any_order=True)
    mock_rag_engine.generate_scene.assert_awaited_once()