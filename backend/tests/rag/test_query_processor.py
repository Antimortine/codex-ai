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
from app.rag.query_processor import QueryProcessor
from app.core.config import settings # For RAG_QUERY_SIMILARITY_TOP_K

# --- Fixtures ---

@pytest.fixture
def mock_llm():
    """Fixture for a mock LLM."""
    llm = MagicMock(spec=LLM)
    # Configure the async completion method
    llm.acomplete = AsyncMock()
    return llm

@pytest.fixture
def mock_retriever():
    """Fixture for a mock VectorIndexRetriever."""
    retriever = MagicMock(spec=VectorIndexRetriever)
    # Configure the async retrieval method
    retriever.aretrieve = AsyncMock()
    return retriever

@pytest.fixture
def mock_index(mock_retriever):
    """Fixture for a mock VectorStoreIndex that returns our mock retriever."""
    index = MagicMock(spec=VectorStoreIndex)
    # Mock the behavior of creating a retriever from the index
    # We need to handle the __call__ or a specific method if LlamaIndex uses one
    # For simplicity, let's assume VectorIndexRetriever is instantiated directly
    # in the test setup or we patch its instantiation.
    # A simpler approach for testing QueryProcessor: pass the mock retriever directly if possible,
    # or mock the specific call that creates the retriever.
    # Let's patch the VectorIndexRetriever class itself.
    return index # The index itself might not need much mocking if we patch the retriever creation

# --- Test QueryProcessor ---

@pytest.mark.asyncio
# Patch the VectorIndexRetriever where it's used inside QueryProcessor.query
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_success_with_nodes(
    mock_retriever_class: MagicMock, # The patched class
    mock_llm: MagicMock,
    mock_index: MagicMock # Mock index is passed but might not be strictly needed if retriever is patched
):
    """Test successful query with retrieved nodes."""
    # Arrange
    project_id = "proj-qp-1"
    query_text = "What is the main character's goal?"
    plan = "Plan: Reach the mountain."
    synopsis = "Synopsis: A hero journeys."
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="The hero wants to climb.", metadata={'file_path': 'plan.md', 'project_id': project_id}), score=0.9)
    mock_node2 = NodeWithScore(node=TextNode(id_='n2', text="Goal is the summit.", metadata={'file_path': 'scenes/s1.md', 'project_id': project_id}), score=0.8)
    retrieved_nodes = [mock_node1, mock_node2]
    expected_answer = "The main character's goal is to reach the mountain summit."

    # Configure the mock retriever instance returned by the patched class
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)

    # Configure the mock LLM response
    mock_llm.acomplete.return_value = CompletionResponse(text=expected_answer)

    # Instantiate the class under test
    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    # Act
    answer, source_nodes = await processor.query(project_id, query_text, plan, synopsis)

    # Assert
    assert answer == expected_answer
    assert source_nodes == retrieved_nodes

    # Verify retriever instantiation and call
    mock_retriever_class.assert_called_once_with(
        index=mock_index,
        similarity_top_k=settings.RAG_QUERY_SIMILARITY_TOP_K,
        filters=ANY # Check filters more specifically if needed
    )
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)

    # Verify LLM call (check that the prompt contains key elements)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0] # Get the prompt string
    assert query_text in prompt_arg
    assert plan in prompt_arg
    assert synopsis in prompt_arg
    assert "The hero wants to climb." in prompt_arg # Check retrieved node content
    assert "Goal is the summit." in prompt_arg
    assert "Source: plan.md" in prompt_arg
    assert "Source: scenes/s1.md" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_success_no_nodes(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test successful query when no nodes are retrieved."""
    # Arrange
    project_id = "proj-qp-2"
    query_text = "Any mention of dragons?"
    plan = "No dragons here."
    synopsis = "A dragon-free story."
    retrieved_nodes = [] # No nodes retrieved
    expected_answer = "Based on the plan and synopsis, there is no mention of dragons."

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text=expected_answer)

    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    # Act
    answer, source_nodes = await processor.query(project_id, query_text, plan, synopsis)

    # Assert
    assert answer == expected_answer
    assert source_nodes == retrieved_nodes # Should be empty list

    # Verify retriever call
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)

    # Verify LLM call (check prompt includes explicit context and indication of no retrieved nodes)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert query_text in prompt_arg
    assert plan in prompt_arg
    assert synopsis in prompt_arg
    assert "No specific context snippets were retrieved via search." in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_retriever_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test query when the retriever fails."""
    # Arrange
    project_id = "proj-qp-3"
    query_text = "This query causes retriever error."
    plan = "Plan"
    synopsis = "Synopsis"

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever connection failed"))

    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    # Act
    answer, source_nodes = await processor.query(project_id, query_text, plan, synopsis)

    # Assert
    assert "Sorry, an error occurred" in answer
    assert source_nodes == [] # Expect empty list on error
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_not_awaited() # LLM should not be called

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_llm_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test query when the LLM call fails."""
    # Arrange
    project_id = "proj-qp-4"
    query_text = "This query causes LLM error."
    plan = "Plan"
    synopsis = "Synopsis"
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Some context", metadata={'file_path': 'plan.md', 'project_id': project_id}), score=0.9)
    retrieved_nodes = [mock_node1]

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=RuntimeError("LLM API timeout"))

    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    # Act
    answer, source_nodes = await processor.query(project_id, query_text, plan, synopsis)

    # Assert
    assert "Sorry, an error occurred" in answer
    assert source_nodes == [] # Expect empty list on error
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_awaited_once() # LLM was called

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_llm_empty_response(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test query when the LLM returns an empty response."""
    # Arrange
    project_id = "proj-qp-5"
    query_text = "Query leading to empty LLM response"
    plan = "Plan"
    synopsis = "Synopsis"
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    # Simulate LLM returning None or an empty text response
    mock_llm.acomplete.return_value = CompletionResponse(text="")

    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    # Act
    answer, source_nodes = await processor.query(project_id, query_text, plan, synopsis)

    # Assert
    # Check for the specific message the processor returns in this case
    assert "(The AI did not provide an answer based on the context.)" in answer
    assert source_nodes == retrieved_nodes # Should be empty list
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_awaited_once()