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

from app.services.ai_service import AIService, LoadedContext # Import LoadedContext
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
    mock_chapter_plan = "Chapter plan content."; mock_chapter_synopsis = None # Simulate missing
    mock_prev_scene_id = "scene-id-2"; mock_prev_scene_content = "## Previous Scene\nContent of the scene before."
    mock_generated_title = "New Scene"; mock_generated_content = "The character walked into the dimly lit room."
    mock_generated_dict = {"title": mock_generated_title, "content": mock_generated_content}
    mock_chapter_metadata = { "scenes": { "scene-id-1": {"title": "Scene 1", "order": 1}, mock_prev_scene_id: {"title": "Scene 2", "order": 2}, "scene-id-3": {"title": "Scene 3", "order": 3} } }
    mock_scene_path_2 = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{mock_prev_scene_id}.md").resolve()
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()
    mock_chapter_plan_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/plan.md").resolve()

    # Mock _load_context return value
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': mock_synopsis,
        'chapter_plan': mock_chapter_plan,
        'chapter_synopsis': mock_chapter_synopsis, # None
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path), str(mock_chapter_plan_path)}
    }

    # Configure mocks for loading previous scenes
    def get_scene_path_side_effect(p_id, c_id, s_id):
        if p_id == project_id and c_id == chapter_id and s_id == mock_prev_scene_id: return mock_scene_path_2.parent / mock_scene_path_2.name # Return non-resolved for consistency
        pytest.fail(f"Unexpected call to _get_scene_path with scene_id: {s_id}")
    def read_text_file_side_effect(path):
        if path == (mock_scene_path_2.parent / mock_scene_path_2.name): return mock_prev_scene_content
        pytest.fail(f"Unexpected call to read_text_file with path: {path}")
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.side_effect = get_scene_path_side_effect
    mock_file_service.read_text_file.side_effect = read_text_file_side_effect
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    monkeypatch.setattr(settings, 'RAG_GENERATION_PREVIOUS_SCENE_COUNT', 1, raising=False)
    monkeypatch.setattr('app.services.ai_service.PREVIOUS_SCENE_COUNT', 1, raising=False)

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method
        result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

        # Assertions
        assert isinstance(result, dict); assert result["title"] == mock_generated_title; assert result["content"] == mock_generated_content
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
        mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
        mock_file_service._get_scene_path.assert_called_once_with(project_id, chapter_id, mock_prev_scene_id)
        mock_file_service.read_text_file.assert_called_once_with(mock_scene_path_2.parent / mock_scene_path_2.name)

        # Verify rag_engine call
        expected_filter_set = {
            str(mock_plan_path), str(mock_synopsis_path), str(mock_chapter_plan_path),
            str(mock_scene_path_2) # Include previous scene path
        }
        # --- FIXED: Added explicit_chapter_plan and explicit_chapter_synopsis ---
        mock_rag_engine.generate_scene.assert_awaited_once_with(
            project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
            previous_scene_order=request_data.previous_scene_order,
            explicit_plan=mock_plan,
            explicit_synopsis=mock_synopsis,
            explicit_chapter_plan=mock_chapter_plan,
            explicit_chapter_synopsis=None, # Was None in mock_loaded_context
            explicit_previous_scenes=[(2, mock_prev_scene_content)],
            paths_to_filter=expected_filter_set
        )
        # --- END FIXED ---


@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_generate_scene_draft_success_first_scene(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test successful scene generation for the first scene (no previous)."""
    project_id = "gen-proj-2"; chapter_id = "ch-1"
    request_data = AISceneGenerationRequest(prompt_summary="The story begins.", previous_scene_order=0)
    mock_plan = "Plan for first scene."; mock_synopsis = "Synopsis for first scene."
    mock_generated_title = "Chapter 1, Scene 1"; mock_generated_content = "It was a dark and stormy night."
    mock_generated_dict = {"title": mock_generated_title, "content": mock_generated_content}
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()

    # Mock _load_context return value
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': mock_synopsis,
        'chapter_plan': None, # Assume none for this chapter
        'chapter_synopsis': None,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path)}
    }

    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method
        result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

        # Assertions
        assert isinstance(result, dict); assert result["title"] == mock_generated_title; assert result["content"] == mock_generated_content
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
        mock_file_service.read_chapter_metadata.assert_not_called() # Not called if previous_scene_order is 0
        mock_file_service.read_text_file.assert_not_called()

        # Verify rag_engine call
        # --- FIXED: Added explicit_chapter_plan and explicit_chapter_synopsis ---
        mock_rag_engine.generate_scene.assert_awaited_once_with(
            project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
            previous_scene_order=request_data.previous_scene_order,
            explicit_plan=mock_plan,
            explicit_synopsis=mock_synopsis,
            explicit_chapter_plan=None, # Was None in mock_loaded_context
            explicit_chapter_synopsis=None, # Was None in mock_loaded_context
            explicit_previous_scenes=[],
            paths_to_filter=mock_loaded_context['filter_paths']
        )
        # --- END FIXED ---

@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_generate_scene_draft_context_not_found(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test scene generation when context files are missing (404)."""
    project_id = "gen-proj-3"; chapter_id = "ch-2"
    request_data = AISceneGenerationRequest(prompt_summary="Something happens.", previous_scene_order=1)
    mock_generated_title = "Scene 2"; mock_generated_content = "Despite missing context, something happened."
    mock_generated_dict = {"title": mock_generated_title, "content": mock_generated_content}

    # Mock _load_context return value (all None, empty filter set)
    mock_loaded_context: LoadedContext = {
        'project_plan': None,
        'project_synopsis': None,
        'chapter_plan': None,
        'chapter_synopsis': None,
        'filter_paths': set()
    }

    # Mock previous scene loading (also fails with 404)
    mock_file_service.read_chapter_metadata.side_effect = HTTPException(status_code=404, detail="Not Found")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method
        result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

        # Assertions
        assert isinstance(result, dict); assert result["title"] == mock_generated_title; assert result["content"] == mock_generated_content
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
        mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id) # Called for previous scene check
        mock_file_service.read_text_file.assert_not_called() # Not called as metadata failed

        # Verify rag_engine call
        # --- FIXED: Added explicit_chapter_plan and explicit_chapter_synopsis ---
        mock_rag_engine.generate_scene.assert_awaited_once_with(
            project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
            previous_scene_order=request_data.previous_scene_order,
            explicit_plan=None, # Was None in mock_loaded_context
            explicit_synopsis=None, # Was None in mock_loaded_context
            explicit_chapter_plan=None, # Was None in mock_loaded_context
            explicit_chapter_synopsis=None, # Was None in mock_loaded_context
            explicit_previous_scenes=[],
            paths_to_filter=set() # Empty set
        )
        # --- END FIXED ---

@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_generate_scene_draft_context_load_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test scene generation when context loading raises unexpected errors."""
    project_id = "gen-proj-4"; chapter_id = "ch-3"
    request_data = AISceneGenerationRequest(prompt_summary="Error handling test.", previous_scene_order=1)
    mock_generated_title = "Scene 2"; mock_generated_content = "Generated despite loading errors."
    mock_generated_dict = {"title": mock_generated_title, "content": mock_generated_content}
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()

    # Mock _load_context return value (project plan error, chapter context ok)
    mock_loaded_context: LoadedContext = {
        'project_plan': None, # Simulate error during load
        'project_synopsis': "Synopsis loaded okay.",
        'chapter_plan': "Chapter Plan OK.",
        'chapter_synopsis': None,
        'filter_paths': {str(mock_synopsis_path)} # Only synopsis path added
    }

    # Mock previous scene loading (also fails)
    mock_file_service.read_chapter_metadata.side_effect = OSError("Cannot read metadata")
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method
        result = await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

        # Assertions
        assert isinstance(result, dict); assert result["title"] == mock_generated_title; assert result["content"] == mock_generated_content
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
        mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
        mock_file_service.read_text_file.assert_not_called()

        # Verify rag_engine call
        # --- FIXED: Added explicit_chapter_plan and explicit_chapter_synopsis ---
        mock_rag_engine.generate_scene.assert_awaited_once_with(
            project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
            previous_scene_order=request_data.previous_scene_order,
            explicit_plan=None, # Was None in mock_loaded_context
            explicit_synopsis="Synopsis loaded okay.",
            explicit_chapter_plan="Chapter Plan OK.", # Was loaded in mock_loaded_context
            explicit_chapter_synopsis=None, # Was None in mock_loaded_context
            explicit_previous_scenes=[],
            paths_to_filter=mock_loaded_context['filter_paths']
        )
        # --- END FIXED ---

# --- Tests for RAG engine errors remain unchanged ---
@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_generate_scene_draft_rag_engine_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test scene generation when the rag_engine itself raises an error."""
    project_id = "gen-proj-5"; chapter_id = "ch-4"
    request_data = AISceneGenerationRequest(prompt_summary="Engine failure test.", previous_scene_order=1)
    mock_plan = "Plan."; mock_synopsis = "Synopsis."; mock_chapter_metadata = {"scenes": {}}
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()

    # Mock _load_context
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': mock_synopsis,
        'chapter_plan': None,
        'chapter_synopsis': None,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path)}
    }
    # Mock previous scene loading
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_rag_engine.generate_scene = AsyncMock(side_effect=HTTPException(status_code=503, detail="LLM Service Unavailable"))

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method and expect the exception
        with pytest.raises(HTTPException) as exc_info:
            await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

        assert exc_info.value.status_code == 503
        assert "LLM Service Unavailable" in exc_info.value.detail
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
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
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()

    # Mock _load_context
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': mock_synopsis,
        'chapter_plan': None,
        'chapter_synopsis': None,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path)}
    }
    mock_rag_engine.generate_scene = AsyncMock(return_value=mock_generated_dict)

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method and expect an HTTPException because the service should detect the error string
        with pytest.raises(HTTPException) as exc_info:
            await service_instance.generate_scene_draft(project_id, chapter_id, request_data)

        assert exc_info.value.status_code == 500
        assert error_string in exc_info.value.detail
        mock_load_ctx.assert_called_once_with(project_id, chapter_id)
        mock_rag_engine.generate_scene.assert_awaited_once() # Still called once