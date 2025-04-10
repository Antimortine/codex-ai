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
# --- REMOVED Pydantic Imports (not needed for parsing tests) ---
# from pydantic import ValidationError, TypeAdapter
# --- END REMOVED ---
import logging
from typing import Optional, List

from tenacity import RetryError
from google.genai.errors import ClientError
from fastapi import HTTPException, status

# Import the class we are testing
from app.rag.chapter_splitter import ChapterSplitter
# --- REMOVED ProposedSceneListAdapter ---
# from app.rag.chapter_splitter import ProposedSceneListAdapter
# --- END REMOVED ---

# Import necessary LlamaIndex types for mocking
from llama_index.core.llms import LLM, CompletionResponse # Added CompletionResponse
# --- REMOVED Agent/Tool Imports ---
# from llama_index.core.agent import ReActAgent, AgentChatResponse
# from llama_index.core.tools import FunctionTool, ToolMetadata
# from llama_index.core.schema import NodeWithScore, TextNode, Node
# --- END REMOVED ---
from llama_index.core.indices.vector_store import VectorStoreIndex # Keep for constructor mock if needed

# Import models used
from app.models.ai import ProposedScene
# --- REMOVED ProposedSceneList ---
# from app.models.ai import ProposedSceneList
# --- END REMOVED ---


# --- Fixtures ---

@pytest.fixture
def mock_llm_for_splitter():
    llm = MagicMock(spec=LLM)
    llm.acomplete = AsyncMock() # Mock the completion endpoint
    return llm

# --- REMOVED mock_index_for_splitter (no longer needed) ---
# @pytest.fixture
# def mock_index_for_splitter():
#     return MagicMock(spec=VectorStoreIndex)
# --- END REMOVED ---

@pytest.fixture
# --- REMOVED mock_index_for_splitter dependency ---
def chapter_splitter(mock_llm_for_splitter: MagicMock) -> ChapterSplitter:
    # Pass None for index as it's not used anymore
    return ChapterSplitter(index=None, llm=mock_llm_for_splitter)
# --- END REMOVED ---


# --- REMOVED Agent Response Helper ---
# def create_mock_agent_response(response_text: str) -> AgentChatResponse:
#     return AgentChatResponse(response=response_text, source_nodes=[])
# --- END REMOVED ---

# --- Helper to create mock ClientError (remains the same) ---
def create_mock_client_error(status_code: int, message: str = "API Error") -> ClientError:
    error_dict = {"error": {"message": message, "code": status_code}}
    response_json = error_dict
    try:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = response_json
        error = ClientError(message, response=mock_response, response_json=response_json)
    except TypeError:
        try: error = ClientError(message, response_json=response_json)
        except TypeError:
            try: error = ClientError(f"{status_code} {message}", response_json=response_json)
            except Exception as final_fallback_error: pytest.fail(f"Could not initialize ClientError mock. Last error: {final_fallback_error}")
    if not hasattr(error, 'status_code') or error.status_code != status_code: setattr(error, 'status_code', status_code)
    return error


# --- Test Cases ---

@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
# @patch('app.rag.chapter_splitter.ReActAgent')
# --- END REMOVED ---
async def test_split_success(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test successful chapter splitting using single call + parsing."""
    # Arrange
    project_id = "proj-split-1"; chapter_id = "ch-split-1"
    chapter_content = "Scene 1 content. Some break. Scene 2 content."
    plan = "Plan"; synopsis = "Synopsis"
    expected_scenes = [
        ProposedScene(suggested_title="Scene 1 Title", content="Scene 1 content."),
        ProposedScene(suggested_title="Scene 2 Title", content="Some break. Scene 2 content.")
    ]
    # --- Mock LLM response text with delimiters ---
    mock_llm_response_text = (
        "<<<SCENE_START>>>\n"
        "TITLE: Scene 1 Title\n"
        "CONTENT:\n"
        "Scene 1 content.\n"
        "<<<SCENE_END>>>\n"
        "<<<SCENE_START>>>\n"
        "TITLE: Scene 2 Title\n"
        "CONTENT:\n"
        "Some break. Scene 2 content.\n"
        "<<<SCENE_END>>>"
    )
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    # --- END Mock LLM ---

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == expected_scenes
    mock_llm_for_splitter.acomplete.assert_awaited_once() # Check the correct method was called
    prompt_arg = mock_llm_for_splitter.acomplete.call_args[0][0]
    assert chapter_content in prompt_arg
    assert "<<<SCENE_START>>>" in prompt_arg # Check format instruction


@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
async def test_split_empty_content(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test splitting with empty chapter content."""
    # Arrange
    project_id = "proj-split-empty"; chapter_id = "ch-split-empty"
    chapter_content = "   "; plan = "Plan"; synopsis = "Synopsis"

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == []
    mock_llm_for_splitter.acomplete.assert_not_awaited() # LLM not called for empty input


@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
async def test_split_llm_returns_malformed_response(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the LLM returns text that doesn't match the expected delimiter format."""
    # Arrange
    project_id = "proj-split-malformed"; chapter_id = "ch-split-malformed"
    chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    # --- Mock LLM response text WITHOUT delimiters ---
    mock_llm_response_text = "Scene 1: Content 1\nScene 2: Content 2"
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    # --- END Mock LLM ---

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert: Expect empty list because parsing failed
    assert result == []
    mock_llm_for_splitter.acomplete.assert_awaited_once()


@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
async def test_split_llm_returns_partial_match(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the LLM returns one valid block and one invalid."""
    # Arrange
    project_id = "proj-split-partial"; chapter_id = "ch-split-partial"
    chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    expected_scenes = [ProposedScene(suggested_title="Valid Scene", content="Valid Content.")]
    # --- Mock LLM response text with one valid, one invalid block ---
    mock_llm_response_text = (
        "<<<SCENE_START>>>\n"
        "TITLE: Valid Scene\n"
        "CONTENT:\n"
        "Valid Content.\n"
        "<<<SCENE_END>>>\n"
        "INVALID BLOCK HERE\n"
        "<<<SCENE_START>>>\n" # Missing TITLE/CONTENT prefixes
        "Just some text\n"
        "<<<SCENE_END>>>"
    )
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    # --- END Mock LLM ---

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert: Only the valid scene should be parsed
    assert result == expected_scenes
    mock_llm_for_splitter.acomplete.assert_awaited_once()


@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
async def test_split_llm_error_non_retryable(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the LLM call fails with a non-retryable exception."""
    # Arrange
    project_id = "proj-split-llm-error"; chapter_id = "ch-split-llm-error"
    chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    # --- Mock LLM acomple to raise error ---
    mock_llm_for_splitter.acomplete = AsyncMock(side_effect=ValueError("LLM validation failed"))
    # --- END Mock LLM ---

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    assert exc_info.value.status_code == 500
    assert "Error: An unexpected error occurred during chapter splitting." in exc_info.value.detail
    mock_llm_for_splitter.acomplete.assert_awaited_once() # Called once


@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
async def test_split_llm_empty_response(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the LLM returns an empty response string."""
    # Arrange
    project_id = "proj-split-llm-empty"; chapter_id = "ch-split-llm-empty"
    chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    # --- Mock LLM acomple to return empty ---
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=""))
    # --- END Mock LLM ---

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    assert exc_info.value.status_code == 500
    assert "Error: The AI failed to propose scene splits." in exc_info.value.detail
    mock_llm_for_splitter.acomplete.assert_awaited_once()


@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
async def test_split_content_validation_warning(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock, caplog):
    """Test the optional content length validation warning."""
    # Arrange
    project_id = "proj-split-contentloss"; chapter_id = "ch-split-contentloss"
    chapter_content = "This is the original long content that should be mostly preserved."
    plan = "Plan"; synopsis = "Synopsis"
    # --- Mock LLM response with short content ---
    short_scenes = [ProposedScene(suggested_title="Short Scene", content="Short.")]
    mock_llm_response_text = (
        "<<<SCENE_START>>>\n"
        "TITLE: Short Scene\n"
        "CONTENT:\n"
        "Short.\n"
        "<<<SCENE_END>>>"
    )
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    # --- END Mock LLM ---

    # Act
    with caplog.at_level(logging.WARNING):
        result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == short_scenes
    assert len(caplog.records) >= 1
    assert any("Concatenated split content length" in rec.message and "significantly differs from original" in rec.message for rec in caplog.records)
    mock_llm_for_splitter.acomplete.assert_awaited_once()


# --- Tests for Retry Logic (ChapterSplitter - Single Call) ---

@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
async def test_split_retry_success(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
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
    # --- Mock LLM acomple with side effect for retry ---
    mock_llm_for_splitter.acomplete.side_effect = [
        create_mock_client_error(429, "Rate limit 1"),
        create_mock_client_error(429, "Rate limit 2"),
        CompletionResponse(text=mock_llm_response_text) # Success on 3rd try
    ]
    # --- END Mock LLM ---

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == expected_scenes
    assert mock_llm_for_splitter.acomplete.await_count == 3 # Verify retry


@pytest.mark.asyncio
# --- REMOVED Agent Patch ---
async def test_split_retry_failure(chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test retry logic fails after all LLM attempts."""
    # Arrange
    project_id = "proj-split-retry-fail"; chapter_id = "ch-split-retry-fail"
    chapter_content = "Content"; plan, synopsis = "P", "S"
    final_error = create_mock_client_error(429, "Rate limit final")
    # --- Mock LLM acomple to always fail ---
    mock_llm_for_splitter.acomplete.side_effect = final_error
    # --- END Mock LLM ---

    # Act & Assert
    with pytest.raises(HTTPException) as exc_info:
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Error: Rate limit exceeded after multiple retries" in exc_info.value.detail
    assert mock_llm_for_splitter.acomplete.await_count == 3 # Verify retry happened

# --- REMOVED Agent-specific tests ---
# test_split_agent_fails_to_call_tool
# test_split_tool_returns_empty_list
# test_split_tool_validation_error
# --- END REMOVED ---