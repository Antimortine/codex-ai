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
from pathlib import Path # Import Path
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM, CompletionResponse
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore, TextNode
from typing import Optional, Dict, Set # Import Optional, Dict, Set

from tenacity import RetryError, stop_after_attempt, wait_exponential, retry, retry_if_exception # Import tenacity decorators
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted # Import potential base/specific errors


# Import the class we are testing and the retry predicate
from app.rag.query_processor import QueryProcessor, _is_retryable_google_api_error
from app.core.config import settings

# --- Fixtures (Use shared fixtures from conftest.py) ---

# --- Helper to create mock ClientError ---
class MockGoogleAPIError(GoogleAPICallError):
     """Minimal mock error inheriting from a base Google error."""
     def __init__(self, message, status_code=None):
         super().__init__(message)
         self.status_code = status_code
         self.message = message

def create_mock_client_error(status_code: int, message: str = "API Error") -> MockGoogleAPIError:
    """Creates a mock Exception that mimics Google API errors for retry logic testing."""
    if status_code == 429:
        try:
            error = ResourceExhausted(message)
            setattr(error, 'status_code', status_code)
        except TypeError:
            error = MockGoogleAPIError(message=message, status_code=status_code)
    else:
        error = MockGoogleAPIError(message=message, status_code=status_code)

    if not hasattr(error, 'status_code'):
        setattr(error, 'status_code', status_code)
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
    plan_path = Path(f"user_projects/{project_id}/plan.md")
    scene_path = Path(f"user_projects/{project_id}/scenes/s1.md")
    # Mock retrieved nodes, including one that should be filtered
    mock_node_plan = NodeWithScore(node=TextNode(id_='n1', text="The hero wants to climb.", metadata={'file_path': str(plan_path), 'project_id': project_id, 'document_type': 'Plan', 'document_title': 'Project Plan'}), score=0.9)
    mock_node_scene = NodeWithScore(node=TextNode(id_='n2', text="Goal is the summit.", metadata={'file_path': str(scene_path), 'project_id': project_id, 'document_type': 'Scene', 'document_title': 'Opening Scene'}), score=0.8)
    retrieved_nodes = [mock_node_plan, mock_node_scene]
    # Define the expected *filtered* nodes
    expected_filtered_nodes = [mock_node_scene]
    # Define the paths that AIService would pass for filtering
    paths_to_filter_set = {str(plan_path)}

    expected_answer = "The main character's goal is to reach the mountain summit."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    # Pass the filter set to the query method
    answer, source_nodes, direct_info = await processor.query(
        project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set
    )

    assert answer == expected_answer
    # --- MODIFIED: Assert against filtered nodes ---
    assert source_nodes == expected_filtered_nodes
    # --- END MODIFIED ---
    assert direct_info is None
    mock_retriever_class.assert_called_once_with(index=mock_index, similarity_top_k=settings.RAG_QUERY_SIMILARITY_TOP_K, filters=ANY)
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert query_text in prompt_arg
    assert plan in prompt_arg
    assert synopsis in prompt_arg
    # Check prompt includes only the non-filtered node
    assert 'Source (Plan: "Project Plan")' not in prompt_arg # Should be filtered
    assert "The hero wants to climb." not in prompt_arg # Should be filtered
    assert 'Source (Scene: "Opening Scene")' in prompt_arg
    assert "Goal is the summit." in prompt_arg


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
    retrieved_nodes = [] # No nodes retrieved
    expected_filtered_nodes = [] # Still empty after filtering
    paths_to_filter_set = {str(Path(f"user_projects/{project_id}/plan.md"))} # Example filter

    expected_answer = "Based on the plan and synopsis, there is no mention of dragons."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    answer, source_nodes, direct_info = await processor.query(
        project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set
    )

    assert answer == expected_answer
    assert source_nodes == expected_filtered_nodes # Should be empty
    assert direct_info is None
    mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert "No additional relevant context snippets were retrieved via search." in prompt_arg

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
    assert source_nodes == [] # Expect empty list on error
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
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Some context", metadata={'file_path': 'scenes/s1.md'}), score=0.9)
    retrieved_nodes = [mock_node1] # Assume retrieval works
    expected_filtered_nodes = [mock_node1] # Assume it wouldn't be filtered
    paths_to_filter_set = {str(Path(f"user_projects/{project_id}/plan.md"))}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=ValueError("LLM prompt validation failed"))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    answer, source_nodes, direct_info = await processor.query(
        project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set
    )

    assert "Sorry, an internal error occurred processing the query." in answer
    # --- MODIFIED: Assert against expected filtered nodes even on error ---
    # The filtering happens before the LLM call fails
    assert source_nodes == [] # Error handler returns empty list now
    # --- END MODIFIED ---
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
    expected_filtered_nodes = []
    paths_to_filter_set = {str(Path(f"user_projects/{project_id}/plan.md"))}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=""))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)

    answer, source_nodes, direct_info = await processor.query(
        project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set
    )

    assert "(The AI did not provide an answer based on the context.)" in answer
    assert source_nodes == expected_filtered_nodes # Should be empty
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

    mock_llm.acomplete.side_effect = [
        create_mock_client_error(429, "Rate limit 1"),
        create_mock_client_error(429, "Rate limit 2"),
        expected_response
    ]

    response = await processor._execute_llm_complete(prompt)

    assert response == expected_response
    assert mock_llm.acomplete.await_count == 3
    mock_llm.acomplete.assert_has_awaits([call(prompt), call(prompt), call(prompt)])

@pytest.mark.asyncio
async def test_query_retry_failure(mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic fails after all attempts."""
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    prompt = "Test prompt"
    final_error = create_mock_client_error(429, "Rate limit final")

    mock_llm.acomplete.side_effect = [
        create_mock_client_error(429, "Rate limit 1"),
        create_mock_client_error(429, "Rate limit 2"),
        final_error
    ]

    with pytest.raises(GoogleAPICallError) as exc_info:
        await processor._execute_llm_complete(prompt)

    assert exc_info.value is final_error
    assert hasattr(exc_info.value, 'status_code') and exc_info.value.status_code == 429
    assert mock_llm.acomplete.await_count == 3

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
    project_id = "proj-qp-retry-fail"
    query_text = "Query that hits rate limit."
    plan = "Plan"
    synopsis = "Synopsis"
    mock_node_plan = NodeWithScore(node=TextNode(id_='n1', text="Plan context", metadata={'file_path': f'user_projects/{project_id}/plan.md'}), score=0.9)
    mock_node_scene = NodeWithScore(node=TextNode(id_='n2', text="Scene context", metadata={'file_path': f'user_projects/{project_id}/scenes/s1.md'}), score=0.8)
    retrieved_nodes = [mock_node_plan, mock_node_scene]
    # Define the expected *filtered* nodes (plan should be filtered)
    expected_filtered_nodes = [mock_node_scene]
    paths_to_filter_set = {str(Path(f"user_projects/{project_id}/plan.md"))}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)

    final_error = create_mock_client_error(429, "Rate limit")
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    # Patch the internal helper method that is decorated
    with patch.object(processor, '_execute_llm_complete', side_effect=final_error) as mock_decorated_method:

        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set
        )

        assert "Rate limit exceeded for query after multiple retries" in answer
        # --- MODIFIED: Assert against expected filtered nodes ---
        assert source_nodes == expected_filtered_nodes
        # --- END MODIFIED ---
        assert direct_info is None
        mock_decorated_method.assert_awaited_once() # The decorated method is called once by query()

# --- END TESTS ---