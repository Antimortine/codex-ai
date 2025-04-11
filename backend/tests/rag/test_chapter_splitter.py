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
from unittest.mock import MagicMock, AsyncMock, patch, ANY, call
import logging
from typing import Optional, List

from tenacity import RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted
from fastapi import HTTPException, status

# Import the class we are testing
from app.rag.chapter_splitter import ChapterSplitter, _is_retryable_google_api_error # Import predicate too

# Import necessary LlamaIndex types for mocking
from llama_index.core.llms import LLM, CompletionResponse
from llama_index.core.indices.vector_store import VectorStoreIndex
# --- ADDED: Imports for retrieval mocking ---
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore, TextNode
# --- END ADDED ---

# Import models used
from app.models.ai import ProposedScene


# --- Fixtures ---
@pytest.fixture
def mock_llm_for_splitter():
    llm = MagicMock(spec=LLM)
    llm.acomplete = AsyncMock() # Mock the completion endpoint
    return llm

@pytest.fixture
def mock_index_for_splitter(): # Keep fixture even if unused by constructor for now
    return MagicMock(spec=VectorStoreIndex)

@pytest.fixture
def chapter_splitter(mock_index_for_splitter: MagicMock, mock_llm_for_splitter: MagicMock) -> ChapterSplitter:
    # Pass index even if not used by current logic
    return ChapterSplitter(index=mock_index_for_splitter, llm=mock_llm_for_splitter)


# --- Helper to create mock ClientError ---
class MockGoogleAPIError(GoogleAPICallError):
     def __init__(self, message, status_code=None):
         super().__init__(message)
         self.status_code = status_code
         self.message = message

def create_mock_client_error(status_code: int, message: str = "API Error") -> MockGoogleAPIError:
    if status_code == 429:
        try:
            error = ResourceExhausted(message)
            setattr(error, 'status_code', status_code)
        except TypeError:
            error = MockGoogleAPIError(message=message, status_code=status_code)
    else:
        error = MockGoogleAPIError(message=message, status_code=status_code)
    if not hasattr(error, 'status_code'): setattr(error, 'status_code', status_code)
    if not hasattr(error, 'message'): setattr(error, 'message', message)
    return error

# --- Test Cases ---
# (Non-retry tests unchanged)
@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_success(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-1"; chapter_id = "ch-split-1"; chapter_content = "Scene 1 content. Some break. Scene 2 content."; plan = "Plan"; synopsis = "Synopsis"
    expected_scenes = [ ProposedScene(suggested_title="Scene 1 Title", content="Scene 1 content."), ProposedScene(suggested_title="Scene 2 Title", content="Some break. Scene 2 content.") ]
    mock_llm_response_text = ("<<<SCENE_START>>>\nTITLE: Scene 1 Title\nCONTENT:\nScene 1 content.\n<<<SCENE_END>>>\n<<<SCENE_START>>>\nTITLE: Scene 2 Title\nCONTENT:\nSome break. Scene 2 content.\n<<<SCENE_END>>>")
    # Mock retriever
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Return empty nodes for simplicity
    # Mock LLM
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert result == expected_scenes
    mock_retriever_instance.aretrieve.assert_awaited_once() # Check retrieval was called
    mock_llm_for_splitter.acomplete.assert_awaited_once(); prompt_arg = mock_llm_for_splitter.acomplete.call_args[0][0]; assert chapter_content in prompt_arg; assert "<<<SCENE_START>>>" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_empty_content(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-empty"; chapter_id = "ch-split-empty"; chapter_content = "   "; plan = "Plan"; synopsis = "Synopsis"
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert result == []
    mock_retriever_class.return_value.aretrieve.assert_not_awaited() # Retrieval shouldn't happen
    mock_llm_for_splitter.acomplete.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_llm_returns_malformed_response(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-malformed"; chapter_id = "ch-split-malformed"; chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    mock_llm_response_text = "Scene 1: Content 1\nScene 2: Content 2"
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert result == []
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm_for_splitter.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_llm_returns_partial_match(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-partial"; chapter_id = "ch-split-partial"; chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    expected_scenes = [ProposedScene(suggested_title="Valid Scene", content="Valid Content.")]
    mock_llm_response_text = ("<<<SCENE_START>>>\nTITLE: Valid Scene\nCONTENT:\nValid Content.\n<<<SCENE_END>>>\nINVALID BLOCK HERE\n<<<SCENE_START>>>\nJust some text\n<<<SCENE_END>>>")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert result == expected_scenes
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm_for_splitter.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_llm_error_non_retryable(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-llm-error"; chapter_id = "ch-split-llm-error"; chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_llm_for_splitter.acomplete = AsyncMock(side_effect=ValueError("LLM validation failed"))
    with pytest.raises(HTTPException) as exc_info: await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert exc_info.value.status_code == 500
    # --- MODIFIED: Assert correct error message ---
    assert "Error: An unexpected error occurred during chapter splitting. Please check logs." in exc_info.value.detail
    # --- END MODIFIED ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm_for_splitter.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_llm_empty_response(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-llm-empty"; chapter_id = "ch-split-llm-empty"; chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=""))
    with pytest.raises(HTTPException) as exc_info: await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert exc_info.value.status_code == 500; assert "Error: The AI failed to propose scene splits." in exc_info.value.detail
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm_for_splitter.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_content_validation_warning(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock, caplog):
    project_id = "proj-split-contentloss"; chapter_id = "ch-split-contentloss"; chapter_content = "This is the original long content that should be mostly preserved."; plan = "Plan"; synopsis = "Synopsis"
    short_scenes = [ProposedScene(suggested_title="Short Scene", content="Short.")]
    mock_llm_response_text = ("<<<SCENE_START>>>\nTITLE: Short Scene\nCONTENT:\nShort.\n<<<SCENE_END>>>")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    with caplog.at_level(logging.WARNING): result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert result == short_scenes; assert len(caplog.records) >= 1; assert any("Concatenated split content length" in rec.message and "significantly differs from original" in rec.message for rec in caplog.records)
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm_for_splitter.acomplete.assert_awaited_once()

# --- Tests for Retry Logic (REVISED) ---
@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_retry_success(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test retry logic succeeds on the third LLM attempt."""
    # Arrange
    project_id = "proj-split-retry-ok"; chapter_id = "ch-split-retry-ok"
    chapter_content = "Content"; plan, synopsis = "P", "S"
    expected_scenes = [ProposedScene(suggested_title="OK Scene", content="Content")]
    mock_llm_response_text = (
        "<<<SCENE_START>>>\n"
        "TITLE: OK Scene\n"
        "CONTENT:\n"
        "Content\n"
        "<<<SCENE_END>>>"
    )
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Mock retrieval call
    # Configure the underlying llm.acomplete mock
    call_count = 0
    async def mock_acomplete_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1: raise create_mock_client_error(429, "Rate limit 1")
        elif call_count == 2: raise create_mock_client_error(429, "Rate limit 2")
        else: return CompletionResponse(text=mock_llm_response_text)
    mock_llm_for_splitter.acomplete.side_effect = mock_acomplete_side_effect

    # Act - Call the main split method
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == expected_scenes
    mock_retriever_instance.aretrieve.assert_awaited_once() # Check retrieval
    assert mock_llm_for_splitter.acomplete.await_count == 3


@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
async def test_split_retry_failure(mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test retry logic fails after all LLM attempts."""
    # Arrange
    project_id = "proj-split-retry-fail"; chapter_id = "ch-split-retry-fail"
    chapter_content = "Content"; plan, synopsis = "P", "S"
    final_error = create_mock_client_error(429, "Rate limit final")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Mock retrieval call
    # Configure the underlying llm.acomplete mock
    mock_llm_for_splitter.acomplete.side_effect = final_error # Always raise

    # Act & Assert - Expect the main split method to raise HTTPException 429
    with pytest.raises(HTTPException) as exc_info:
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Error: Rate limit exceeded after multiple retries" in exc_info.value.detail
    mock_retriever_instance.aretrieve.assert_awaited_once() # Check retrieval
    # Assert the underlying llm method was called 3 times by tenacity
    assert mock_llm_for_splitter.acomplete.await_count == 3