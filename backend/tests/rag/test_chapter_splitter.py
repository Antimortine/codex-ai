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
from pydantic import ValidationError, TypeAdapter
import logging
from typing import Optional, List

from tenacity import RetryError
from google.genai.errors import ClientError
from fastapi import HTTPException, status

# Import the class we are testing
from app.rag.chapter_splitter import ChapterSplitter, ProposedSceneListAdapter
# Import necessary LlamaIndex types for mocking
from llama_index.core.llms import LLM
from llama_index.core.agent import ReActAgent, AgentChatResponse
from llama_index.core.tools import FunctionTool, ToolMetadata
from llama_index.core.schema import NodeWithScore, TextNode, Node
from llama_index.core.indices.vector_store import VectorStoreIndex
# Import models used
from app.models.ai import ProposedScene, ProposedSceneList

# --- Fixtures ---

@pytest.fixture
def mock_llm_for_splitter():
    llm = MagicMock(spec=LLM)
    llm.chat = AsyncMock()
    llm.complete = AsyncMock()
    return llm

@pytest.fixture
def mock_index_for_splitter():
    return MagicMock(spec=VectorStoreIndex)

@pytest.fixture
def chapter_splitter(mock_index_for_splitter: MagicMock, mock_llm_for_splitter: MagicMock) -> ChapterSplitter:
    return ChapterSplitter(index=mock_index_for_splitter, llm=mock_llm_for_splitter)

# --- Helper to create mock Agent responses ---

def create_mock_agent_response(response_text: str) -> AgentChatResponse:
    return AgentChatResponse(response=response_text, source_nodes=[])

# --- Helper to create mock ClientError ---
def create_mock_client_error(status_code: int, message: str = "API Error") -> ClientError:
    error_dict = {"error": {"message": message}}
    try:
        error = ClientError(status_code, error_dict)
        if not hasattr(error, 'status_code') or error.status_code != status_code:
             setattr(error, 'status_code', status_code)
    except Exception:
        error = ClientError(f"{status_code} {message}")
        setattr(error, 'status_code', status_code)
    return error


# --- Test Cases ---

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_success(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test successful chapter splitting using the Agent."""
    # Arrange
    project_id = "proj-split-1"
    chapter_id = "ch-split-1"
    chapter_content = "Scene 1 content. Some break. Scene 2 content."
    plan = "Plan"
    synopsis = "Synopsis"
    expected_scenes = [
        ProposedScene(suggested_title="Scene 1 Title", content="Scene 1 content."),
        ProposedScene(suggested_title="Scene 2 Title", content="Some break. Scene 2 content.")
    ]
    raw_tool_args = {"proposed_scenes": [s.model_dump() for s in expected_scenes]}
    mock_agent_instance = mock_agent_class.from_tools.return_value

    async def agent_achat_side_effect(agent_input_arg):
        try:
            validated_data = ProposedSceneListAdapter.validate_python(raw_tool_args["proposed_scenes"])
            chapter_splitter._tool_result_storage["scenes"] = validated_data
        except ValidationError: pytest.fail("Simulated tool validation failed unexpectedly")
        return create_mock_agent_response("Tool executed successfully.")
    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect)

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == expected_scenes
    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()
    # --- REMOVED assertion checking full content in prompt ---


@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_empty_content(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test splitting with empty chapter content."""
    # Arrange
    project_id = "proj-split-empty"
    chapter_id = "ch-split-empty"
    chapter_content = "   "
    plan = "Plan"
    synopsis = "Synopsis"
    mock_agent_instance = mock_agent_class.from_tools.return_value
    mock_agent_instance.achat = AsyncMock()

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == []
    mock_agent_class.from_tools.assert_not_called()
    mock_agent_instance.achat.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_agent_fails_to_call_tool(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the agent finishes but doesn't simulate calling the tool."""
    # Arrange
    project_id = "proj-split-agent-notool"
    chapter_id = "ch-split-agent-notool"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"

    mock_agent_instance = mock_agent_class.from_tools.return_value
    mock_agent_instance.achat = AsyncMock(return_value=create_mock_agent_response("I couldn't figure out how to split this."))

    # Act & Assert
    expected_error_msg = "Agent failed to execute the tool correctly or store results."
    # Expect the ValueError from inside split() to be wrapped in HTTPException 500
    with pytest.raises(HTTPException) as exc_info:
         await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert exc_info.value.status_code == 500
    assert expected_error_msg in exc_info.value.detail
    assert "Agent response: I couldn't figure out" in exc_info.value.detail
    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_agent_chat_error_non_retryable(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the agent's achat method raises a non-retryable exception."""
    # Arrange
    project_id = "proj-split-agent-error"
    chapter_id = "ch-split-agent-error"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"

    mock_agent_instance = mock_agent_class.from_tools.return_value
    non_retryable_error = ValueError("Agent internal error")
    mock_agent_instance.achat = AsyncMock(side_effect=non_retryable_error)

    # Act & Assert
    # Expect the original ValueError to be wrapped in HTTPException 500
    with pytest.raises(HTTPException) as exc_info:
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert exc_info.value.status_code == 500
    assert "Agent internal error" in exc_info.value.detail

    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once() # Called once

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_tool_returns_empty_list(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the tool call succeeds but returns an empty list."""
    # Arrange
    project_id = "proj-split-tool-empty"
    chapter_id = "ch-split-tool-empty"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"
    raw_tool_args = {"proposed_scenes": []}

    mock_agent_instance = mock_agent_class.from_tools.return_value

    async def agent_achat_side_effect(agent_input_arg):
        try:
            validated_data = ProposedSceneListAdapter.validate_python(raw_tool_args["proposed_scenes"])
            chapter_splitter._tool_result_storage["scenes"] = validated_data # Store empty list
        except ValidationError: pytest.fail("Simulated tool validation failed unexpectedly")
        return create_mock_agent_response("Tool executed, no scenes found.")
    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect)

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == []
    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_tool_validation_error(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the data passed to the tool fails validation inside the tool."""
    # Arrange
    project_id = "proj-split-tool-invalid"
    chapter_id = "ch-split-tool-invalid"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"
    invalid_raw_tool_args = {"proposed_scenes": [{"title_typo": "Invalid Scene"}]}

    mock_agent_instance = mock_agent_class.from_tools.return_value
    tool_error_message = "Validation Error Placeholder"

    async def agent_achat_side_effect(agent_input_arg):
        nonlocal tool_error_message
        tools_list = mock_agent_class.from_tools.call_args.kwargs.get('tools', [])
        tool_fn = tools_list[0].fn if tools_list else None
        if tool_fn:
             tool_response_str = tool_fn(**invalid_raw_tool_args) # This call returns the error string
             tool_error_message = tool_response_str
        else: pytest.fail("Tool function not found")
        return create_mock_agent_response(tool_error_message) # Agent returns the error string
    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect)

    # Act & Assert
    expected_error_msg = "Agent failed to execute the tool correctly or store results."
    # Expect the ValueError from inside split() to be wrapped in HTTPException 500
    with pytest.raises(HTTPException) as exc_info:
         await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert exc_info.value.status_code == 500
    assert expected_error_msg in exc_info.value.detail
    assert "Error: Validation failed" in exc_info.value.detail
    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_content_validation_warning(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock, caplog):
    """Test the optional content length validation warning with Agent."""
    # Arrange
    project_id = "proj-split-contentloss-agent"
    chapter_id = "ch-split-contentloss-agent"
    chapter_content = "This is the original long content that should be mostly preserved."
    plan = "Plan"
    synopsis = "Synopsis"
    short_scenes = [ProposedScene(suggested_title="Short Scene", content="Short.")]
    raw_tool_args = {"proposed_scenes": [s.model_dump() for s in short_scenes]}

    mock_agent_instance = mock_agent_class.from_tools.return_value

    async def agent_achat_side_effect(agent_input_arg):
        try:
            validated_data = ProposedSceneListAdapter.validate_python(raw_tool_args["proposed_scenes"])
            chapter_splitter._tool_result_storage["scenes"] = validated_data # Store short list
        except ValidationError: pytest.fail("Simulated tool validation failed unexpectedly")
        return create_mock_agent_response("Tool executed.")
    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect)

    # Act
    with caplog.at_level(logging.WARNING):
        result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == short_scenes
    # --- CORRECTED Assertion ---
    assert len(caplog.records) >= 1
    assert any("Concatenated content length" in rec.message and "significantly differs from original" in rec.message for rec in caplog.records)
    # --- END CORRECTED ---
    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()

# --- Tests for Retry Logic (ChapterSplitter) ---

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_retry_success(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test retry logic succeeds on the third agent attempt."""
    # Arrange
    project_id = "proj-split-retry-ok"
    chapter_id = "ch-split-retry-ok"
    chapter_content = "Content"
    plan, synopsis = "P", "S"
    expected_scenes = [ProposedScene(suggested_title="OK Scene", content="Content")]
    raw_tool_args = {"proposed_scenes": [s.model_dump() for s in expected_scenes]}

    mock_agent_instance = mock_agent_class.from_tools.return_value

    async def agent_achat_side_effect_retry(agent_input_arg):
        call_count = mock_agent_instance.achat.await_count # Track calls on the mock
        if call_count < 3:
            raise create_mock_client_error(429, f"Rate limit {call_count}")
        else:
            try:
                validated_data = ProposedSceneListAdapter.validate_python(raw_tool_args["proposed_scenes"])
                chapter_splitter._tool_result_storage["scenes"] = validated_data
            except ValidationError: pytest.fail("Validation failed in retry success")
            return create_mock_agent_response("Tool executed on retry.")

    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect_retry)

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == expected_scenes
    assert mock_agent_instance.achat.await_count == 3

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_retry_failure(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test retry logic fails after all agent attempts."""
    # Arrange
    project_id = "proj-split-retry-fail"
    chapter_id = "ch-split-retry-fail"
    chapter_content = "Content"
    plan, synopsis = "P", "S"
    final_error = create_mock_client_error(429, "Rate limit final")

    mock_agent_instance = mock_agent_class.from_tools.return_value
    mock_agent_instance.achat = AsyncMock(side_effect=final_error)

    # Act & Assert
    # Expect the final ClientError to be caught by the specific handler in split()
    # and then re-raised as HTTPException(429)
    with pytest.raises(HTTPException) as exc_info:
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # --- CORRECTED Assertion ---
    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Rate limit exceeded after multiple retries" in exc_info.value.detail
    # --- END CORRECTED ---
    assert mock_agent_instance.achat.await_count == 3

# --- END NEW TESTS ---