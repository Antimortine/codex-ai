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
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM, CompletionResponse
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore, TextNode
from typing import Optional, Dict # Import Optional, Dict

from tenacity import RetryError, stop_after_attempt, wait_exponential, retry, retry_if_exception # Import tenacity decorators
# --- MODIFIED: Import base error and specific error ---
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted # Import potential base/specific errors
# --- END MODIFIED ---


# Import the class we are testing and the retry predicate
from app.rag.query_processor import QueryProcessor, _is_retryable_google_api_error
from app.core.config import settings

# --- Fixtures (Use shared fixtures from conftest.py) ---

# --- Helper to create mock ClientError ---
# --- MODIFIED: Create a minimal class inheriting from GoogleAPICallError ---
class MockGoogleAPIError(GoogleAPICallError):
     """Minimal mock error inheriting from a base Google error."""
     def __init__(self, message, status_code=None):
         # Find a base class constructor that works, GoogleAPICallError might be abstract
         # Let's try Exception as the most basic
         super().__init__(message)
         self.status_code = status_code
         # Add other attributes if needed by the predicate or error handling
         self.message = message

def create_mock_client_error(status_code: int, message: str = "API Error") -> MockGoogleAPIError:
    """Creates a mock Exception that mimics Google API errors for retry logic testing."""
    # Use ResourceExhausted specifically for 429 if its constructor is simple enough
    if status_code == 429:
        try:
            # ResourceExhausted constructor usually takes just a message
            error = ResourceExhausted(message)
            # Manually set status_code if the class doesn't do it automatically
            setattr(error, 'status_code', status_code)
        except TypeError:
            # Fallback if ResourceExhausted constructor changed
            error = MockGoogleAPIError(message=message, status_code=status_code)
    else:
        # For other codes, use the generic mock base class
        error = MockGoogleAPIError(message=message, status_code=status_code)

    # Ensure status_code attribute exists
    if not hasattr(error, 'status_code'):
        setattr(error, 'status_code', status_code)
    # Add a basic 'message' attribute if it doesn't exist
    if not hasattr(error, 'message'):
         setattr(error, 'message', message)
    return error
# --- END MODIFIED ---


# --- Test QueryProcessor ---
@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_success_with_nodes(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-qp-1"
    query_text = "What is the main character's goal?"
    plan = "Plan: Reach the mountain."
    synopsis = "Synopsis: A hero journeys."
    # --- ADDED: Mock metadata including type/title ---
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="The hero wants to climb.", metadata={'file_path': 'plan.md', 'project_id': project_id, 'document_type': 'Plan', 'document_title': 'Project Plan'}), score=0.9)
    mock_node2 = NodeWithScore(node=TextNode(id_='n2', text="Goal is the summit.", metadata={'file_path': 'scenes/s1.md', 'project_id': project_id, 'document_type': 'Scene', 'document_title': 'Opening Scene'}), score=0.8)
    # --- END ADDED ---
    retrieved_nodes = [mock_node1, mock_node2]
    expected_answer = "The main character's goal is to reach the mountain summit."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    answer, source_nodes, direct_info = await processor.query(project_id, query_text, plan, synopsis)
    assert answer == expected_answer
    assert source_nodes == retrieved_nodes
    assert direct_info is None
    mock_retriever_class.assert_called_once_with(index=mock_index, similarity_top_k=settings.RAG_QUERY_SIMILARITY_TOP_K, filters=ANY)
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert query_text in prompt_arg
    assert plan in prompt_arg
    assert synopsis in prompt_arg
    # --- ADDED: Check for new source format in prompt ---
    assert 'Source (Plan: "Project Plan")' in prompt_arg
    assert "The hero wants to climb." in prompt_arg
    assert 'Source (Scene: "Opening Scene")' in prompt_arg
    assert "Goal is the summit." in prompt_arg
    # --- END ADDED ---


@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_success_no_nodes(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-qp-2"
    query_text = "Any mention of dragons?"
    plan = "No dragons here."
    synopsis = "A dragon-free story."
    retrieved_nodes = []
    expected_answer = "Based on the plan and synopsis, there is no mention of dragons."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    answer, source_nodes, direct_info = await processor.query(project_id, query_text, plan, synopsis)
    assert answer == expected_answer
    assert source_nodes == retrieved_nodes
    assert direct_info is None
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    # --- MODIFIED Assertion ---
    assert "No additional relevant context snippets were retrieved via search." in prompt_arg
    # --- END MODIFIED ---

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_retriever_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-qp-3"
    query_text = "This query causes retriever error."
    plan = "Plan"
    synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever connection failed"))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    answer, source_nodes, direct_info = await processor.query(project_id, query_text, plan, synopsis)
    assert "Sorry, an internal error occurred processing the query." in answer
    assert source_nodes == []
    assert direct_info is None
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_llm_error_non_retryable(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-qp-4"
    query_text = "This query causes LLM error."
    plan = "Plan"
    synopsis = "Synopsis"
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Some context", metadata={'file_path': 'plan.md', 'project_id': project_id}), score=0.9)
    retrieved_nodes = [mock_node1]
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=ValueError("LLM prompt validation failed"))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    answer, source_nodes, direct_info = await processor.query(project_id, query_text, plan, synopsis)
    assert "Sorry, an internal error occurred processing the query." in answer
    assert source_nodes == []
    assert direct_info is None
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_llm_empty_response(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-qp-5"
    query_text = "Query leading to empty LLM response"
    plan = "Plan"
    synopsis = "Synopsis"
    retrieved_nodes = []
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=""))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    answer, source_nodes, direct_info = await processor.query(project_id, query_text, plan, synopsis)
    assert "(The AI did not provide an answer based on the context.)" in answer
    assert source_nodes == retrieved_nodes
    assert direct_info is None
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_awaited_once()


# --- Tests for Retry Logic ---
@pytest.mark.asyncio
async def test_query_retry_success(mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic succeeds on the third attempt."""
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    prompt = "Test prompt"
    expected_response = CompletionResponse(text="Success")

    # Configure the mock LLM's acomplete method directly
    mock_llm.acomplete.side_effect = [
        create_mock_client_error(429, "Rate limit 1"),
        create_mock_client_error(429, "Rate limit 2"),
        expected_response # Success on the third call
    ]

    # Call the decorated method
    response = await processor._execute_llm_complete(prompt)

    # Assertions remain the same
    assert response == expected_response
    assert mock_llm.acomplete.await_count == 3
    mock_llm.acomplete.assert_has_awaits([call(prompt), call(prompt), call(prompt)])

@pytest.mark.asyncio
async def test_query_retry_failure(mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic fails after all attempts."""
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    prompt = "Test prompt"
    final_error = create_mock_client_error(429, "Rate limit final")

    # Configure the mock LLM's acomplete method directly
    mock_llm.acomplete.side_effect = [
        create_mock_client_error(429, "Rate limit 1"),
        create_mock_client_error(429, "Rate limit 2"),
        final_error # Final error raised by the mock on the 3rd call
    ]

    # Expect tenacity to re-raise the last error
    with pytest.raises(GoogleAPICallError) as exc_info:
        await processor._execute_llm_complete(prompt)

    # Check the raised exception
    assert exc_info.value is final_error # Should be the exact error instance
    assert hasattr(exc_info.value, 'status_code') and exc_info.value.status_code == 429
    assert mock_llm.acomplete.await_count == 3 # Tenacity made 3 calls

@pytest.mark.asyncio
async def test_query_retry_non_retryable_error(mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic stops immediately for non-429 errors."""
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    prompt = "Test prompt"
    non_retryable_error = ValueError("Invalid prompt format")

    mock_llm.acomplete.side_effect = non_retryable_error

    with pytest.raises(ValueError) as exc_info:
        await processor._execute_llm_complete(prompt)

    assert exc_info.value == non_retryable_error
    assert mock_llm.acomplete.await_count == 1

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_handles_retry_failure_gracefully(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test that the main query method handles the re-raised 429 error after retries."""
    # Arrange
    project_id = "proj-qp-retry-fail"
    query_text = "Query that hits rate limit."
    plan = "Plan"
    synopsis = "Synopsis"
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Some context", metadata={'file_path': 'plan.md', 'project_id': project_id}), score=0.9)
    retrieved_nodes = [mock_node1]

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)

    # Configure the mock LLM's acomplete method to always raise the retryable error
    final_error = create_mock_client_error(429, "Rate limit")
    # Patch the decorated method directly
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    with patch.object(processor, '_execute_llm_complete', side_effect=final_error) as mock_decorated_method:

        # Act - Call the main query method, which contains the try/except ClientError block
        answer, source_nodes, direct_info = await processor.query(project_id, query_text, plan, synopsis)

        # Assert
        # Check the correct error message from the GoogleAPICallError handler in processor.query
        assert "Rate limit exceeded for query after multiple retries" in answer
        assert source_nodes == retrieved_nodes # Nodes were retrieved before LLM call failed
        assert direct_info is None
        # Assert that the decorated method was called (tenacity handles the retries internally)
        mock_decorated_method.assert_awaited_once()

# --- END TESTS ---