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
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM, CompletionResponse
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore, TextNode

# Import the class we are testing
from app.rag.rephraser import Rephraser
from app.core.config import settings # For RAG settings

# --- Fixtures ---

@pytest.fixture
def mock_llm():
    """Fixture for a mock LLM."""
    llm = MagicMock(spec=LLM)
    llm.acomplete = AsyncMock()
    return llm

@pytest.fixture
def mock_retriever():
    """Fixture for a mock VectorIndexRetriever."""
    retriever = MagicMock(spec=VectorIndexRetriever)
    retriever.aretrieve = AsyncMock()
    return retriever

@pytest.fixture
def mock_index(mock_retriever):
    """Fixture for a mock VectorStoreIndex."""
    index = MagicMock(spec=VectorStoreIndex)
    return index

# --- Test Rephraser ---

@pytest.mark.asyncio
# Patch the VectorIndexRetriever where it's used inside Rephraser.rephrase
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_success_with_context(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test successful rephrasing with surrounding context and RAG nodes."""
    # Arrange
    project_id = "proj-rp-1"
    selected_text = "walked quickly"
    context_before = "The hero"
    context_after = "to the door."
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Heroes often hurry.", metadata={'file_path': 'char/hero.md', 'project_id': project_id, 'character_name': 'Hero'}), score=0.8)
    retrieved_nodes = [mock_node1]
    llm_response_text = """
1. hurried
2. strode rapidly
3. moved swiftly
    """
    expected_suggestions = ["hurried", "strode rapidly", "moved swiftly"]

    # Configure mocks
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text=llm_response_text)

    # Instantiate and Act
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after)

    # Assert
    assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT] # Ensure count limit is respected

    # Verify retriever instantiation and call
    mock_retriever_class.assert_called_once_with(
        index=mock_index,
        similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K, # Uses generation setting for now
        filters=ANY
    )
    expected_retrieval_query = f"Context relevant to the following passage: {context_before} {selected_text} {context_after}"
    mock_retriever_instance.aretrieve.assert_awaited_once_with(expected_retrieval_query)

    # Verify LLM call (check prompt contains key elements)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert selected_text in prompt_arg
    assert context_before in prompt_arg
    assert context_after in prompt_arg
    assert "Heroes often hurry." in prompt_arg # RAG context
    assert "Source: char/hero.md [Character: Hero]" in prompt_arg # Check RAG context formatting
    assert f"Provide exactly {settings.RAG_REPHRASE_SUGGESTION_COUNT} distinct suggestions" in prompt_arg
    assert "Present the suggestions as a numbered list" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_success_no_context(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test successful rephrasing with only selected text (no surrounding/RAG)."""
    # Arrange
    project_id = "proj-rp-2"
    selected_text = "very big"
    context_before = None
    context_after = None
    retrieved_nodes = [] # No RAG nodes
    llm_response_text = "1. huge\n2. enormous\n3. gigantic"
    expected_suggestions = ["huge", "enormous", "gigantic"]

    # Configure mocks
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text=llm_response_text)

    # Instantiate and Act
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after)

    # Assert
    assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT]

    # Verify retriever call
    expected_retrieval_query = f"Context relevant to the following passage: {selected_text}"
    mock_retriever_instance.aretrieve.assert_awaited_once_with(expected_retrieval_query)

    # Verify LLM call (check prompt structure)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert selected_text in prompt_arg
    assert "**Surrounding Text:**" not in prompt_arg # Should not be present
    assert f"**Text to Rephrase:**\n```\n{selected_text}\n```" in prompt_arg
    assert "No specific context was retrieved via search." in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_retriever_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test rephrasing when the retriever fails."""
    # Arrange
    project_id = "proj-rp-3"
    selected_text = "text"
    context_before = None
    context_after = None

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever failed"))

    # Instantiate and Act
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after)

    # Assert
    assert len(suggestions) == 1
    assert "Error: An unexpected error occurred while rephrasing." in suggestions[0]
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test rephrasing when the LLM call fails."""
    # Arrange
    project_id = "proj-rp-4"
    selected_text = "text"
    context_before = None
    context_after = None
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=RuntimeError("LLM failed"))

    # Instantiate and Act
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after)

    # Assert
    assert len(suggestions) == 1
    assert "Error: An unexpected error occurred while rephrasing." in suggestions[0]
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_empty_response(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test rephrasing when the LLM returns an empty response."""
    # Arrange
    project_id = "proj-rp-5"
    selected_text = "text"
    context_before = None
    context_after = None
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text="") # Empty response

    # Instantiate and Act
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after)

    # Assert
    assert len(suggestions) == 1
    assert "Error: The AI failed to generate suggestions." in suggestions[0]
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_unparseable_response(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test rephrasing when the LLM response cannot be parsed as a numbered list."""
    # Arrange
    project_id = "proj-rp-6"
    selected_text = "text"
    context_before = None
    context_after = None
    retrieved_nodes = []
    llm_response_text = "Here are some ideas: idea one, idea two, idea three." # Not numbered

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text=llm_response_text)

    # Instantiate and Act
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after)

    # Assert
    # Check if fallback parsing (split by newline) worked, or if it returned an error
    # In this case, the fallback should produce one line
    assert len(suggestions) == 1
    assert suggestions[0] == llm_response_text # Fallback returns the whole line
    # OR, if you expect an error:
    # assert "Error: Could not parse suggestions." in suggestions[0]

    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
async def test_rephrase_empty_input(mock_llm: MagicMock, mock_index: MagicMock):
    """Test rephrasing with empty selected text."""
    # Arrange
    project_id = "proj-rp-7"
    selected_text = "  " # Whitespace only
    context_before = None
    context_after = None

    # Instantiate and Act
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after)

    # Assert
    assert suggestions == [] # Expect empty list for empty input
    # Ensure retriever and LLM were not called
    # (Need to access the patched retriever if we were patching it)
    # For this test, we can assume they aren't called if input is empty.
    mock_llm.acomplete.assert_not_awaited()