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
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from pydantic import ValidationError
import logging # Import logging for caplog test

# Import the class we are testing
from app.rag.chapter_splitter import ChapterSplitter
# Import necessary LlamaIndex types for mocking
from llama_index.core.llms import LLM, ChatResponse, ChatMessage, MessageRole
from llama_index.core.base.llms.types import CompletionResponse # For older mock style if needed
# Import ToolCall instead of ToolOutput
from llama_index.core.indices.vector_store import VectorStoreIndex # For init
# Import models used
from app.models.ai import ProposedScene, ProposedSceneList

# --- Fixtures ---

# Use the shared mock_llm fixture from tests/rag/conftest.py
# Use the shared mock_index fixture from tests/rag/conftest.py

@pytest.fixture
def chapter_splitter(mock_index: MagicMock, mock_llm: MagicMock) -> ChapterSplitter:
    """Fixture to create a ChapterSplitter instance with mocked dependencies."""
    # --- Ensure chat is an AsyncMock within the fixture ---
    if not isinstance(mock_llm.chat, AsyncMock):
         mock_llm.chat = AsyncMock()
    # --- Reset mock before use in test ---
    mock_llm.chat.reset_mock() # Explicitly reset before test runs
    return ChapterSplitter(index=mock_index, llm=mock_llm)

# --- Helper to create mock LLM responses ---

def create_mock_chat_response(tool_calls: list = None, content: str = None) -> ChatResponse:
    """Creates a mock ChatResponse object."""
    mock_message = ChatMessage(role=MessageRole.ASSISTANT, content=content)
    if tool_calls:
        # Store tool calls in additional_kwargs, which is the standard place
        mock_message.additional_kwargs = {"tool_calls": tool_calls}
    return ChatResponse(message=mock_message)

def create_mock_tool_call(tool_name: str, arguments: dict) -> MagicMock:
     """Creates a mock object representing a tool call structure."""
     mock_call = MagicMock()
     mock_call.tool_name = tool_name
     mock_call.tool_arguments = arguments # Store the raw arguments dict
     mock_call.id = "mock_tool_call_id_" + tool_name
     return mock_call

# --- Test Cases ---

@pytest.mark.asyncio
async def test_split_success(chapter_splitter: ChapterSplitter, mock_llm: MagicMock):
    """Test successful chapter splitting with valid tool call."""
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
    tool_arguments_dict = {"proposed_scenes": [s.model_dump() for s in expected_scenes]}
    mock_tool_call = create_mock_tool_call("save_proposed_scenes", tool_arguments_dict)
    mock_response = create_mock_chat_response(tool_calls=[mock_tool_call])
    mock_llm.chat = AsyncMock(return_value=mock_response) # Re-assign mock specific to this test

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == expected_scenes
    mock_llm.chat.assert_awaited_once()
    call_args, call_kwargs = mock_llm.chat.call_args
    messages = call_kwargs.get('messages', [])
    assert any(chapter_content in msg.content for msg in messages if msg.role == MessageRole.USER)
    assert any(plan in msg.content for msg in messages if msg.role == MessageRole.USER)
    assert any(synopsis in msg.content for msg in messages if msg.role == MessageRole.USER)
    assert call_kwargs.get('tool_choice') is not None

@pytest.mark.asyncio
async def test_split_empty_content(chapter_splitter: ChapterSplitter, mock_llm: MagicMock):
    """Test splitting with empty chapter content."""
    # Arrange
    project_id = "proj-split-empty"
    chapter_id = "ch-split-empty"
    chapter_content = "   " # Whitespace only
    plan = "Plan"
    synopsis = "Synopsis"

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == []
    # --- MODIFIED Assertion ---
    # Use assert_not_awaited() which is the canonical way for AsyncMock
    mock_llm.chat.assert_not_awaited()
    # --- END MODIFIED ---

@pytest.mark.asyncio
async def test_split_no_tool_call(chapter_splitter: ChapterSplitter, mock_llm: MagicMock):
    """Test when the LLM responds but doesn't make the expected tool call."""
    # Arrange
    project_id = "proj-split-notool"
    chapter_id = "ch-split-notool"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"
    mock_response = create_mock_chat_response(content="I analyzed the text but couldn't split it.")
    mock_llm.chat = AsyncMock(return_value=mock_response) # Re-assign mock specific to this test

    # Act & Assert
    expected_error_msg = "Failed to split chapter due to LLM or processing error: LLM failed to call the required tool to save proposed scenes."
    with pytest.raises(RuntimeError, match=expected_error_msg):
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    mock_llm.chat.assert_awaited_once()

@pytest.mark.asyncio
async def test_split_wrong_tool_call(chapter_splitter: ChapterSplitter, mock_llm: MagicMock):
    """Test when the LLM calls an unexpected tool."""
    # Arrange
    project_id = "proj-split-wrongtool"
    chapter_id = "ch-split-wrongtool"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"
    mock_tool_call = create_mock_tool_call("some_other_tool", {"arg": "value"})
    mock_response = create_mock_chat_response(tool_calls=[mock_tool_call])
    mock_llm.chat = AsyncMock(return_value=mock_response) # Re-assign mock specific to this test

    # Act & Assert
    expected_error_msg = "Failed to split chapter due to LLM or processing error: LLM called unexpected tool: some_other_tool"
    with pytest.raises(RuntimeError, match=expected_error_msg):
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    mock_llm.chat.assert_awaited_once()

@pytest.mark.asyncio
async def test_split_invalid_tool_arguments(chapter_splitter: ChapterSplitter, mock_llm: MagicMock):
    """Test when tool arguments fail Pydantic validation."""
    # Arrange
    project_id = "proj-split-invalidargs"
    chapter_id = "ch-split-invalidargs"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"
    invalid_tool_arguments = {"proposed_scenes": [{"title_typo": "Scene 1", "content": "..."}]}
    mock_tool_call = create_mock_tool_call("save_proposed_scenes", invalid_tool_arguments)
    mock_response = create_mock_chat_response(tool_calls=[mock_tool_call])
    mock_llm.chat = AsyncMock(return_value=mock_response) # Re-assign mock specific to this test

    # Act & Assert
    with pytest.raises(RuntimeError) as exc_info:
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert "Failed to split chapter due to LLM or processing error" in str(exc_info.value)
    assert "LLM returned data in an unexpected format" in str(exc_info.value)
    mock_llm.chat.assert_awaited_once()

@pytest.mark.asyncio
async def test_split_empty_scene_list_in_args(chapter_splitter: ChapterSplitter, mock_llm: MagicMock):
    """Test when tool arguments are valid but the proposed_scenes list is empty."""
    # Arrange
    project_id = "proj-split-emptyargs"
    chapter_id = "ch-split-emptyargs"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"
    empty_tool_arguments = {"proposed_scenes": []}
    mock_tool_call = create_mock_tool_call("save_proposed_scenes", empty_tool_arguments)
    mock_response = create_mock_chat_response(tool_calls=[mock_tool_call])
    mock_llm.chat = AsyncMock(return_value=mock_response) # Re-assign mock specific to this test

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == []
    mock_llm.chat.assert_awaited_once()

@pytest.mark.asyncio
async def test_split_llm_chat_error(chapter_splitter: ChapterSplitter, mock_llm: MagicMock):
    """Test when the llm.chat call itself raises an exception."""
    # Arrange
    project_id = "proj-split-llmerror"
    chapter_id = "ch-split-llmerror"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"
    mock_llm.chat = AsyncMock(side_effect=RuntimeError("LLM API connection failed")) # Re-assign mock specific to this test

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to split chapter due to LLM or processing error: LLM API connection failed"):
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    mock_llm.chat.assert_awaited_once()

@pytest.mark.asyncio
async def test_split_content_validation_warning(chapter_splitter: ChapterSplitter, mock_llm: MagicMock, caplog):
    """Test the optional content length validation warning."""
    # Arrange
    project_id = "proj-split-contentloss"
    chapter_id = "ch-split-contentloss"
    chapter_content = "This is the original long content that should be mostly preserved."
    plan = "Plan"
    synopsis = "Synopsis"
    short_scenes = [
        ProposedScene(suggested_title="Short Scene", content="Short.")
    ]
    tool_arguments_dict = {"proposed_scenes": [s.model_dump() for s in short_scenes]}
    mock_tool_call = create_mock_tool_call("save_proposed_scenes", tool_arguments_dict)
    mock_response = create_mock_chat_response(tool_calls=[mock_tool_call])
    mock_llm.chat = AsyncMock(return_value=mock_response) # Re-assign mock specific to this test

    # Act
    with caplog.at_level(logging.WARNING):
        result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == short_scenes
    assert "Concatenated content length" in caplog.text
    assert "significantly differs from original" in caplog.text
    mock_llm.chat.assert_awaited_once()