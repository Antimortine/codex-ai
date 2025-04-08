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
    # --- Ensure the instance attribute exists for patching/checking later if needed ---
    # Although it's set inside split, having it on the instance might simplify some mock setups
    # splitter = ChapterSplitter(index=mock_index_for_splitter, llm=mock_llm_for_splitter)
    # splitter._tool_result_storage = {"scenes": None} # Initialize attribute
    # return splitter
    # --- Let's stick to the current implementation where it's defined in split ---
    return ChapterSplitter(index=mock_index_for_splitter, llm=mock_llm_for_splitter)


# --- Helper to create mock Agent responses ---

def create_mock_agent_response(response_text: str) -> AgentChatResponse:
    return AgentChatResponse(response=response_text, source_nodes=[])

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

    # --- MODIFIED: agent_achat_side_effect to modify the *instance's* storage ---
    async def agent_achat_side_effect(agent_input_arg):
        # Simulate the tool function being called and modifying the instance's storage
        try:
            # Directly validate and assign to the instance attribute that the real function uses
            validated_data = ProposedSceneListAdapter.validate_python(raw_tool_args["proposed_scenes"])
            chapter_splitter._tool_result_storage["scenes"] = validated_data # Modify instance attr
        except ValidationError:
            pytest.fail("Simulated tool validation failed unexpectedly in test side effect")
        return create_mock_agent_response("Tool executed successfully.")
    # --- END MODIFIED ---

    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect)

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == expected_scenes # Check the final returned list
    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()
    agent_input_arg = mock_agent_instance.achat.call_args[0][0]
    assert chapter_content in agent_input_arg
    assert plan in agent_input_arg
    assert synopsis in agent_input_arg
    # --- REMOVED assertion on side_effect_storage ---
    # assert side_effect_storage["scenes"] == expected_scenes
    # --- The main assertion `assert result == expected_scenes` is sufficient ---


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
    # Simulate agent returning a text response *without* the side effect modifying storage
    mock_agent_instance.achat = AsyncMock(return_value=create_mock_agent_response("I couldn't figure out how to split this."))

    # Act & Assert
    expected_error_msg = "Agent failed to execute the tool correctly or store results."
    with pytest.raises(RuntimeError) as exc_info:
         await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)
    assert expected_error_msg in str(exc_info.value.__cause__)
    assert "Agent response: I couldn't figure out" in str(exc_info.value.__cause__)

    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()
    # We expect _tool_result_storage to be None inside the split method, leading to the error


@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.ReActAgent')
async def test_split_agent_chat_error(mock_agent_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test when the agent's achat method raises an exception."""
    # Arrange
    project_id = "proj-split-agent-error"
    chapter_id = "ch-split-agent-error"
    chapter_content = "Some content."
    plan = "Plan"
    synopsis = "Synopsis"

    mock_agent_instance = mock_agent_class.from_tools.return_value
    mock_agent_instance.achat = AsyncMock(side_effect=RuntimeError("Agent internal error"))

    # Act & Assert
    with pytest.raises(RuntimeError, match="Failed to split chapter due to Agent or LLM error: Agent internal error"):
        await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()

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
    raw_tool_args = {"proposed_scenes": []} # Agent provides empty list

    mock_agent_instance = mock_agent_class.from_tools.return_value

    # Simulate agent calling the tool with an empty list
    async def agent_achat_side_effect(agent_input_arg):
        try:
            validated_data = ProposedSceneListAdapter.validate_python(raw_tool_args["proposed_scenes"])
            chapter_splitter._tool_result_storage["scenes"] = validated_data # Store empty list
        except ValidationError:
            pytest.fail("Simulated tool validation failed unexpectedly in test side effect")
        return create_mock_agent_response("Tool executed, no scenes found.")
    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect)

    # Act
    result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == [] # Expect empty list back
    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()
    # --- REMOVED assertion on side_effect_storage ---
    # assert side_effect_storage["scenes"] == []
    # --- The main assertion `assert result == []` is sufficient ---


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
    # Invalid data structure
    invalid_raw_tool_args = {"proposed_scenes": [{"title_typo": "Invalid Scene"}]}

    mock_agent_instance = mock_agent_class.from_tools.return_value
    tool_error_message = "Validation Error Placeholder"

    # Simulate agent calling the tool with invalid data
    async def agent_achat_side_effect(agent_input_arg):
        nonlocal tool_error_message
        tools_list = mock_agent_class.from_tools.call_args.kwargs.get('tools', [])
        tool_fn = tools_list[0].fn if tools_list else None
        if tool_fn:
             # Call the tool function, which should raise ValidationError internally
             # and return an error string
             tool_response_str = tool_fn(**invalid_raw_tool_args)
             tool_error_message = tool_response_str # Capture the error message
        else:
             pytest.fail("Tool function not found in mocked agent creation")
        # Agent returns the error string from the tool
        return create_mock_agent_response(tool_error_message)

    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect)

    # Act & Assert
    expected_error_msg = "Agent failed to execute the tool correctly or store results."
    with pytest.raises(RuntimeError) as exc_info:
         await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    assert expected_error_msg in str(exc_info.value.__cause__)
    # Check that the agent's final response (containing the validation error string) is included
    assert "Error: Validation failed" in str(exc_info.value.__cause__)

    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()
    # We expect _tool_result_storage to be None inside the split method


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

    # Simulate agent calling the tool successfully with the short list
    async def agent_achat_side_effect(agent_input_arg):
        tools_list = mock_agent_class.from_tools.call_args.kwargs.get('tools', [])
        tool_fn = tools_list[0].fn if tools_list else None
        if tool_fn:
             try:
                 validated_data = ProposedSceneListAdapter.validate_python(raw_tool_args["proposed_scenes"])
                 chapter_splitter._tool_result_storage["scenes"] = validated_data # Store short list
             except ValidationError:
                 pytest.fail("Simulated tool validation failed unexpectedly in test side effect")
        else:
             pytest.fail("Tool function not found in mocked agent creation")
        return create_mock_agent_response("Tool executed.")
    mock_agent_instance.achat = AsyncMock(side_effect=agent_achat_side_effect)

    # Act
    with caplog.at_level(logging.WARNING):
        result = await chapter_splitter.split(project_id, chapter_id, chapter_content, plan, synopsis)

    # Assert
    assert result == short_scenes
    assert "Concatenated content length" in caplog.text
    assert "significantly differs from original" in caplog.text
    mock_agent_class.from_tools.assert_called_once()
    mock_agent_instance.achat.assert_awaited_once()
    # --- REMOVED assertion on side_effect_storage ---
    # assert side_effect_storage["scenes"] == short_scenes
    # --- The main assertion `assert result == short_scenes` is sufficient ---