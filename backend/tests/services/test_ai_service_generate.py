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
from pathlib import Path
import asyncio
from typing import Dict, List, Tuple, Optional, Set # Import Set

from app.services.ai_service import AIService
from app.services.file_service import FileService
from app.rag.engine import RagEngine
from app.models.ai import AISceneGenerationRequest
from app.core.config import settings
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store import VectorStoreIndex


# --- Test AIService.generate_scene_draft ---

@pytest.mark.asyncio
# --- MODIFIED: Patch imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_generate_scene_draft_success_with_previous(mock_file_service: MagicMock, mock_rag_engine: MagicMock, monkeypatch): # Args match patch order
    """Test successful scene generation with plan, synopsis, and previous scene."""
    project_id = "gen-proj-1"; chapter_id = "ch-1"
    request_data = AISceneGenerationRequest(prompt_summary="Character enters the room.", previous_scene_order=2)
    mock_plan = "Project plan content."; mock_synopsis = "Project synopsis content."
    mock_prev_scene_id = "scene-id-2"; mock_prev_scene_content = "## Previous Scene\nContent of the scene before."
    mock_generated_title = "New Scene"; mock_generated_content = "The character walked into the dimly lit room."
    mock_generated_dict = {"title": mock_generated_title, "content": mock_generated_content}
    mock_chapter_metadata = { "scenes": { "scene-id-1": {"title": "Scene 1", "order": 1}, mock_prev_scene_id: {"title": "Scene 2", "order": 2}, "scene-id-3": {"title": "Scene 3", "order": 3} } }
    mock_scene_path_2 = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{mock_prev_scene_id}.md")
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md")
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")

    # Configure mocks (using args from patch decorators)
    def get_scene_path_side_effect(p_id, c_id, s_id):
        if p_id == project_id and c_id == chapter_id and s_id == mock_prev_scene_id: return mock_scene_path_2
        pytest.fail(f"Unexpected call to _get_scene_path with scene_id: {s_id}")
    def read_text_file_side_effect(path):
        if path == mock_scene_path_2: return mock_prev_scene_content
        pytest.fail(f"Unexpected call to read_text_file with path: {path}")
    # --- MODIFIED: Mock _get_content_block_path ---
    def get_content_block_path_side_effect(p_id, b_name):
        if p_id == project_id:
            if b_name == "plan.md": return mock_plan_path
            if b_name == "synopsis.md": return mock_synopsis_path
        pytest.fail(f"Unexpected call to _get_content_block_path: {p_id}, {b_name}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    # --- END MODIFIED ---
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else pytest.fail("Unexpected block read")
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.side_effect = get_scene_path_side_effect
    mock_file_service.read_text_file.side_effect = read_text_file_side_effect
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    monkeypatch.setattr(settings, 'RAG_GENERATION_PREVIOUS_SCENE_COUNT', 1, raising=False)
    monkeypatch.setattr('app.services.ai_service.PREVIOUS_SCENE_COUNT', 1, raising=False)

    # Instantiate AIService
    service_instance = AIService()

    # Call the method
    result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    # Assertions
    assert isinstance(result, dict); assert result["title"] == mock_generated_title; assert result["content"] == mock_generated_content
    mock_file_service.read_content_block_file.assert_has_calls([call(project_id, "plan.md"), call(project_id, "synopsis.md")], any_order=True)
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_file_service._get_scene_path.assert_called_once_with(project_id, chapter_id, mock_prev_scene_id)
    mock_file_service.read_text_file.assert_called_once_with(mock_scene_path_2)
    # --- MODIFIED: Add paths_to_filter to assertion ---
    expected_filter_set = {str(mock_plan_path), str(mock_synopsis_path)}
    mock_rag_engine.generate_scene.assert_awaited_once_with(
        project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
        previous_scene_order=request_data.previous_scene_order, explicit_plan=mock_plan,
        explicit_synopsis=mock_synopsis, explicit_previous_scenes=[(2, mock_prev_scene_content)],
        paths_to_filter=expected_filter_set # Check the set
    )
    # --- END MODIFIED ---


@pytest.mark.asyncio
# --- MODIFIED: Patch the imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_generate_scene_draft_success_first_scene(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test successful scene generation for the first scene (no previous)."""
    project_id = "gen-proj-2"; chapter_id = "ch-1"
    request_data = AISceneGenerationRequest(prompt_summary="The story begins.", previous_scene_order=0)
    mock_plan = "Plan for first scene."; mock_synopsis = "Synopsis for first scene."
    mock_generated_title = "Chapter 1, Scene 1"; mock_generated_content = "It was a dark and stormy night."
    mock_generated_dict = {"title": mock_generated_title, "content": mock_generated_content}
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
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else pytest.fail("Unexpected block read")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    # Instantiate AIService
    service_instance = AIService()

    # Call the method
    result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    # Assertions
    assert isinstance(result, dict); assert result["title"] == mock_generated_title; assert result["content"] == mock_generated_content
    mock_file_service.read_content_block_file.assert_has_calls([call(project_id, "plan.md"), call(project_id, "synopsis.md")], any_order=True)
    mock_file_service.read_chapter_metadata.assert_not_called()
    mock_file_service.read_text_file.assert_not_called()
    # --- MODIFIED: Add paths_to_filter to assertion ---
    expected_filter_set = {str(mock_plan_path), str(mock_synopsis_path)}
    mock_rag_engine.generate_scene.assert_awaited_once_with(
        project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
        previous_scene_order=request_data.previous_scene_order, explicit_plan=mock_plan,
        explicit_synopsis=mock_synopsis, explicit_previous_scenes=[],
        paths_to_filter=expected_filter_set # Check the set
    )
    # --- END MODIFIED ---

@pytest.mark.asyncio
# --- MODIFIED: Patch the imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_generate_scene_draft_context_not_found(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test scene generation when plan/synopsis/metadata are missing (404)."""
    project_id = "gen-proj-3"; chapter_id = "ch-2"
    request_data = AISceneGenerationRequest(prompt_summary="Something happens.", previous_scene_order=1)
    mock_generated_title = "Scene 2"; mock_generated_content = "Despite missing context, something happened."
    mock_generated_dict = {"title": mock_generated_title, "content": mock_generated_content}
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md")
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")

    # Configure mocks
    # --- MODIFIED: Simulate 404 for read, but allow path retrieval ---
    mock_file_service.read_content_block_file.side_effect = HTTPException(status_code=404, detail="Not Found")
    mock_file_service._get_content_block_path.side_effect = lambda p, b: mock_plan_path if b == "plan.md" else mock_synopsis_path if b == "synopsis.md" else None
    # --- END MODIFIED ---
    mock_file_service.read_chapter_metadata.side_effect = HTTPException(status_code=404, detail="Not Found")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    # Instantiate AIService
    service_instance = AIService()

    # Call the method
    result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    # Assertions
    assert isinstance(result, dict); assert result["title"] == mock_generated_title; assert result["content"] == mock_generated_content
    # --- MODIFIED: Assert read_content_block_file was called ---
    assert mock_file_service.read_content_block_file.call_count == 2
    # --- END MODIFIED ---
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_file_service.read_text_file.assert_not_called()
    # --- MODIFIED: Add paths_to_filter (empty set) to assertion ---
    # Paths are added even if read fails with 404
    expected_filter_set = {str(mock_plan_path), str(mock_synopsis_path)}
    mock_rag_engine.generate_scene.assert_awaited_once_with(
        project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
        previous_scene_order=request_data.previous_scene_order, explicit_plan="", # Correctly expect "" due to 404
        explicit_synopsis="", # Correctly expect "" due to 404
        explicit_previous_scenes=[],
        paths_to_filter=expected_filter_set # Expect paths to be added
    )
    # --- END MODIFIED ---

@pytest.mark.asyncio
# --- MODIFIED: Patch the imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_generate_scene_draft_context_load_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test scene generation when context loading raises unexpected errors."""
    project_id = "gen-proj-4"; chapter_id = "ch-3"
    request_data = AISceneGenerationRequest(prompt_summary="Error handling test.", previous_scene_order=1)
    mock_generated_title = "Scene 2"; mock_generated_content = "Generated despite loading errors."
    mock_generated_dict = {"title": mock_generated_title, "content": mock_generated_content}
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md") # Define plan path even if read fails
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")

    # Configure mocks
    def read_block_error(p_id, b_name):
        if b_name == "plan.md": raise ValueError("Plan load failed") # Non-404 error
        if b_name == "synopsis.md": return "Synopsis loaded okay."
        pytest.fail("Unexpected block read")
    # --- MODIFIED: Mock _get_content_block_path ---
    def get_content_block_path_side_effect(p_id, b_name):
        if p_id == project_id:
            # Simulate path retrieval works for both, even if read fails for plan
            if b_name == "plan.md": return mock_plan_path
            if b_name == "synopsis.md": return mock_synopsis_path
        pytest.fail(f"Unexpected call to _get_content_block_path: {p_id}, {b_name}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    # --- END MODIFIED ---
    mock_file_service.read_content_block_file.side_effect = read_block_error
    mock_file_service.read_chapter_metadata.side_effect = OSError("Cannot read metadata")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    # Instantiate AIService
    service_instance = AIService()

    # Call the method
    result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    # Assertions
    assert isinstance(result, dict); assert result["title"] == mock_generated_title; assert result["content"] == mock_generated_content
    # --- MODIFIED: Assert read_content_block_file was called ---
    assert mock_file_service.read_content_block_file.call_count == 2
    # --- END MODIFIED ---
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_file_service.read_text_file.assert_not_called()
    # --- MODIFIED: Add paths_to_filter to assertion ---
    # Both paths should be added because path retrieval succeeded before read failed
    expected_filter_set = {str(mock_plan_path), str(mock_synopsis_path)}
    mock_rag_engine.generate_scene.assert_awaited_once_with(
        project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
        previous_scene_order=request_data.previous_scene_order, explicit_plan="Error loading plan.", # Correctly expect "Error..."
        explicit_synopsis="Synopsis loaded okay.", explicit_previous_scenes=[],
        paths_to_filter=expected_filter_set # Check the set
    )
    # --- END MODIFIED ---

# --- Tests for RAG engine errors remain unchanged ---
@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_generate_scene_draft_rag_engine_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test scene generation when the rag_engine itself raises an error."""
    project_id = "gen-proj-5"; chapter_id = "ch-4"
    request_data = AISceneGenerationRequest(prompt_summary="Engine failure test.", previous_scene_order=1)
    mock_plan = "Plan."; mock_synopsis = "Synopsis."; mock_chapter_metadata = {"scenes": {}}
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md")
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")

    # Configure mocks
    def get_content_block_path_side_effect(p_id, b_name):
        if p_id == project_id:
            if b_name == "plan.md": return mock_plan_path
            if b_name == "synopsis.md": return mock_synopsis_path
        pytest.fail(f"Unexpected call to _get_content_block_path: {p_id}, {b_name}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else pytest.fail("Unexpected block read")
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_rag_engine.generate_scene = AsyncMock(side_effect=HTTPException(status_code=503, detail="LLM Service Unavailable"))

    # Instantiate AIService
    service_instance = AIService()

    # Call the method and expect the exception
    with pytest.raises(HTTPException) as exc_info:
        await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    assert exc_info.value.status_code == 503
    assert "LLM Service Unavailable" in exc_info.value.detail
    mock_file_service.read_content_block_file.assert_has_calls([call(project_id, "plan.md"), call(project_id, "synopsis.md")], any_order=True)
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_rag_engine.generate_scene.assert_awaited_once() # Still called once

@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_generate_scene_draft_rag_engine_returns_error_string(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test scene generation when rag_engine returns an error string."""
    project_id = "gen-proj-6"; chapter_id = "ch-5"
    request_data = AISceneGenerationRequest(prompt_summary="Engine error string test.", previous_scene_order=0)
    mock_plan = "Plan."; mock_synopsis = "Synopsis."
    error_string = "Error: Generation failed due to content policy."
    mock_generated_dict = {"title": "Error Title", "content": error_string}
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md")
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")

    # Configure mocks
    def get_content_block_path_side_effect(p_id, b_name):
        if p_id == project_id:
            if b_name == "plan.md": return mock_plan_path
            if b_name == "synopsis.md": return mock_synopsis_path
        pytest.fail(f"Unexpected call to _get_content_block_path: {p_id}, {b_name}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    mock_file_service.read_content_block_file.side_effect = lambda p_id, b_name: mock_plan if b_name == "plan.md" else mock_synopsis if b_name == "synopsis.md" else pytest.fail("Unexpected block read")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    # Instantiate AIService
    service_instance = AIService()

    # Call the method and expect an HTTPException because the service should detect the error string
    with pytest.raises(HTTPException) as exc_info:
        await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

    assert exc_info.value.status_code == 500
    assert error_string in exc_info.value.detail
    mock_file_service.read_content_block_file.assert_has_calls([call(project_id, "plan.md"), call(project_id, "synopsis.md")], any_order=True)
    mock_rag_engine.generate_scene.assert_awaited_once() # Still called once