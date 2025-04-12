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
from typing import List, Optional # Added List, Optional

from app.services.ai_service import AIService, LoadedContext # Import LoadedContext
from app.services.file_service import FileService
from app.rag.engine import RagEngine
from app.models.ai import AIRephraseRequest
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store import VectorStoreIndex


# --- Test AIService.rephrase_text ---

@pytest.mark.asyncio
# --- MODIFIED: Patch the imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True) # Keep file_service patch for consistency
# --- END MODIFIED ---
async def test_rephrase_text_success(mock_file_service: MagicMock, mock_rag_engine: MagicMock): # Args match patch order
    """Test successful rephrase call."""
    project_id = "rephrase-proj-1"
    request_data = AIRephraseRequest(selected_text="The quick brown fox", context_before="Before text.", context_after="After text.")
    mock_suggestions = ["The speedy brown fox", "The fast brown fox", "A quick fox of brown color"]
    mock_plan = "Plan context."; mock_synopsis = "Synopsis context."
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()

    # Mock _load_context return value
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': mock_synopsis,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path)}
    }

    mock_rag_engine.rephrase = AsyncMock(return_value=mock_suggestions)

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method
        result = await service_instance.rephrase_text(project_id, request_data)

        # Assertions
        assert result == mock_suggestions
        mock_load_ctx.assert_called_once_with(project_id) # No chapter_id for rephrase
        mock_rag_engine.rephrase.assert_awaited_once_with(
            project_id=project_id, selected_text=request_data.selected_text,
            context_before=request_data.context_before, context_after=request_data.context_after,
            explicit_plan=mock_plan,
            explicit_synopsis=mock_synopsis,
            paths_to_filter=mock_loaded_context['filter_paths']
        )

@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_rephrase_text_engine_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test rephrase when the rag_engine raises an error."""
    project_id = "rephrase-proj-2"
    request_data = AIRephraseRequest(selected_text="Text to fail on")
    mock_plan = "Plan context."; mock_synopsis = None # Simulate synopsis missing
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()

    # Mock _load_context return value
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': None,
        'filter_paths': {str(mock_plan_path)}
    }

    mock_rag_engine.rephrase = AsyncMock(side_effect=HTTPException(status_code=500, detail="Rephrase LLM failed"))

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await service_instance.rephrase_text(project_id, request_data)

        assert exc_info.value.status_code == 500
        assert "Rephrase LLM failed" in exc_info.value.detail
        mock_load_ctx.assert_called_once_with(project_id)
        mock_rag_engine.rephrase.assert_awaited_once_with(
            project_id=project_id, selected_text=request_data.selected_text,
            context_before=request_data.context_before, context_after=request_data.context_after,
            explicit_plan=mock_plan,
            explicit_synopsis=None,
            paths_to_filter=mock_loaded_context['filter_paths']
        )

@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_rephrase_text_engine_returns_error_string(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test rephrase when the rag_engine returns an error string."""
    project_id = "rephrase-proj-3"
    request_data = AIRephraseRequest(selected_text="Another text")
    error_string = "Error: Rephrasing blocked by safety filter."
    mock_plan = "Plan context."; mock_synopsis = "Synopsis context."
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()

    # Mock _load_context return value
    mock_loaded_context: LoadedContext = {
        'project_plan': mock_plan,
        'project_synopsis': mock_synopsis,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path)}
    }

    mock_rag_engine.rephrase = AsyncMock(return_value=[error_string]) # Engine returns list with error

    # Instantiate AIService and patch helper
    service_instance = AIService()
    with patch.object(service_instance, '_load_context', return_value=mock_loaded_context) as mock_load_ctx:

        # Call the method and expect exception
        with pytest.raises(HTTPException) as exc_info:
            await service_instance.rephrase_text(project_id, request_data)

        assert exc_info.value.status_code == 500
        assert error_string in exc_info.value.detail
        mock_load_ctx.assert_called_once_with(project_id)
        mock_rag_engine.rephrase.assert_awaited_once_with(
            project_id=project_id, selected_text=request_data.selected_text,
            context_before=request_data.context_before, context_after=request_data.context_after,
            explicit_plan=mock_plan,
            explicit_synopsis=mock_synopsis,
            paths_to_filter=mock_loaded_context['filter_paths']
        )