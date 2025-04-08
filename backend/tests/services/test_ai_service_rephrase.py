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
from app.models.ai import AIRephraseRequest
# --- ADDED: Import LLM and VectorStoreIndex for mocking ---
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store import VectorStoreIndex
# --- END ADDED ---

# --- Tests for AIService.rephrase_text ---

@pytest.mark.asyncio
async def test_rephrase_text_success():
    """Test successful rephrase call."""
    project_id = "rephrase-proj-1"
    request_data = AIRephraseRequest(
        selected_text="The quick brown fox",
        context_before="Before text.",
        context_after="After text."
    )
    mock_suggestions = ["The speedy brown fox", "The fast brown fox", "A quick fox of brown color"]

    # Mocks
    mock_rag_engine = MagicMock(spec=RagEngine)
    mock_file_service = MagicMock(spec=FileService) # Needed for instantiation patch
    # --- ADDED: Define llm and index attributes on mock_rag_engine ---
    mock_rag_engine.llm = MagicMock(spec=LLM)
    mock_rag_engine.index = MagicMock(spec=VectorStoreIndex)
    # --- END ADDED ---

    # Configure mock
    mock_rag_engine.rephrase = AsyncMock(return_value=mock_suggestions)

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service): # Patch file_service even if not directly used by rephrase
        service_instance = AIService()

    # Call the method
    result = await service_instance.rephrase_text(project_id, request_data)

    # Assertions
    assert result == mock_suggestions
    mock_rag_engine.rephrase.assert_awaited_once_with(
        project_id=project_id,
        selected_text=request_data.selected_text,
        context_before=request_data.context_before,
        context_after=request_data.context_after
    )

@pytest.mark.asyncio
async def test_rephrase_text_engine_error():
    """Test rephrase when the rag_engine raises an error."""
    project_id = "rephrase-proj-2"
    request_data = AIRephraseRequest(selected_text="Text to fail on")

    # Mocks
    mock_rag_engine = MagicMock(spec=RagEngine)
    mock_file_service = MagicMock(spec=FileService)
    # --- ADDED: Define llm and index attributes on mock_rag_engine ---
    mock_rag_engine.llm = MagicMock(spec=LLM)
    mock_rag_engine.index = MagicMock(spec=VectorStoreIndex)
    # --- END ADDED ---

    # Configure mock
    mock_rag_engine.rephrase = AsyncMock(side_effect=HTTPException(status_code=500, detail="Rephrase LLM failed"))

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()

    # Call the method and expect exception
    with pytest.raises(HTTPException) as exc_info:
        await service_instance.rephrase_text(project_id, request_data)

    assert exc_info.value.status_code == 500
    assert "Rephrase LLM failed" in exc_info.value.detail
    mock_rag_engine.rephrase.assert_awaited_once_with(
        project_id=project_id,
        selected_text=request_data.selected_text,
        context_before=request_data.context_before,
        context_after=request_data.context_after
    )

@pytest.mark.asyncio
async def test_rephrase_text_engine_returns_error_string():
    """Test rephrase when the rag_engine returns an error string."""
    project_id = "rephrase-proj-3"
    request_data = AIRephraseRequest(selected_text="Another text")
    error_string = "Error: Rephrasing blocked by safety filter."

    # Mocks
    mock_rag_engine = MagicMock(spec=RagEngine)
    mock_file_service = MagicMock(spec=FileService)
    # --- ADDED: Define llm and index attributes on mock_rag_engine ---
    mock_rag_engine.llm = MagicMock(spec=LLM)
    mock_rag_engine.index = MagicMock(spec=VectorStoreIndex)
    # --- END ADDED ---

    # Configure mock
    mock_rag_engine.rephrase = AsyncMock(return_value=[error_string]) # Engine returns list with error

    # Instantiate AIService with mocks
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
        service_instance = AIService()

    # Call the method and expect exception
    with pytest.raises(HTTPException) as exc_info:
        await service_instance.rephrase_text(project_id, request_data)

    assert exc_info.value.status_code == 500
    assert error_string in exc_info.value.detail
    mock_rag_engine.rephrase.assert_awaited_once_with(
        project_id=project_id,
        selected_text=request_data.selected_text,
        context_before=request_data.context_before,
        context_after=request_data.context_after
    )