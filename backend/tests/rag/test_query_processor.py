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
from typing import Optional, Dict, Set, List # Import Optional, Dict, Set, List

from tenacity import RetryError, stop_after_attempt, wait_exponential, retry, retry_if_exception # Import tenacity decorators
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted # Import potential base/specific errors


# Import the class we are testing and the retry predicate
from app.rag.query_processor import QueryProcessor, _is_retryable_google_api_error
from app.core.config import settings # Import settings to get default temperature

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
    mock_node_plan = NodeWithScore(node=TextNode(id_='n1', text="The hero wants to climb.", metadata={'file_path': str(plan_path), 'project_id': project_id, 'document_type': 'Plan', 'document_title': 'Project Plan'}), score=0.9)
    mock_node_scene = NodeWithScore(node=TextNode(id_='n2', text="Goal is the summit.", metadata={'file_path': str(scene_path), 'project_id': project_id, 'document_type': 'Scene', 'document_title': 'Opening Scene'}), score=0.8)
    retrieved_nodes = [mock_node_plan, mock_node_scene]
    expected_filtered_nodes = [mock_node_scene]
    paths_to_filter_set = {str(plan_path.resolve())}

    expected_answer = "The main character's goal is to reach the mountain summit."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    with patch.object(processor, '_execute_llm_complete', wraps=processor._execute_llm_complete) as mock_execute_llm:
        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set, direct_chapter_context=None
        )

        assert answer == expected_answer
        assert source_nodes == expected_filtered_nodes
        assert direct_info is None
        mock_retriever_class.assert_called_once_with(index=mock_index, similarity_top_k=settings.RAG_QUERY_SIMILARITY_TOP_K, filters=ANY)
        mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
        mock_execute_llm.assert_awaited_once()
        internal_call_args, internal_call_kwargs = mock_execute_llm.call_args
        prompt_arg = internal_call_args[0]
        assert query_text in prompt_arg
        assert "**Project Plan:**" in prompt_arg
        assert plan in prompt_arg
        assert "**Project Synopsis:**" in prompt_arg
        assert synopsis in prompt_arg
        assert 'Source (Scene: "Opening Scene")' in prompt_arg
        assert "Goal is the summit." in prompt_arg
        assert 'Source (Plan: "Project Plan")' not in prompt_arg
        assert "The hero wants to climb." not in prompt_arg
        assert "**Directly Requested Chapter Context" not in prompt_arg


@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_success_no_nodes(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-qp-2"
    query_text = "Any mention of dragons?"
    plan = "No dragons here." * 10000 # Make plan long enough to be truncated
    synopsis = None # Simulate synopsis missing
    retrieved_nodes = []
    expected_filtered_nodes = []
    paths_to_filter_set = {str(Path(f"user_projects/{project_id}/plan.md").resolve())}

    expected_answer = "Based on the plan, there is no mention of dragons."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    with patch.object(processor, '_execute_llm_complete', wraps=processor._execute_llm_complete) as mock_execute_llm:
        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set, direct_chapter_context=None
        )

        assert answer == expected_answer
        assert source_nodes == expected_filtered_nodes
        assert direct_info is None
        mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
        mock_execute_llm.assert_awaited_once()
        internal_call_args, internal_call_kwargs = mock_execute_llm.call_args
        prompt_arg = internal_call_args[0]
        assert "**Project Plan:**" in prompt_arg
        assert plan in prompt_arg # Not truncated in QueryProcessor
        assert "**Project Synopsis:**" not in prompt_arg
        assert "No additional relevant context snippets were retrieved via search." in prompt_arg
        assert "**Directly Requested Chapter Context" not in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_success_with_direct_chapter_context(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-qp-chap-ctx"
    query_text = "What happens in Chapter Alpha?" # Query mentions chapter
    plan = "Overall plan."
    synopsis = "Overall synopsis."
    chapter_title = "Chapter Alpha"
    chapter_plan = "Plan for Alpha."
    chapter_synopsis = "Synopsis for Alpha."
    direct_chapter_context = {
        'chapter_plan': chapter_plan,
        'chapter_synopsis': chapter_synopsis,
        'chapter_title': chapter_title
    }
    retrieved_nodes = [] # No RAG nodes for simplicity
    expected_filtered_nodes = []
    paths_to_filter_set = { # Paths passed from AIService
        str(Path(f"user_projects/{project_id}/plan.md").resolve()),
        str(Path(f"user_projects/{project_id}/synopsis.md").resolve()),
        str(Path(f"user_projects/{project_id}/chapters/ch-alpha/plan.md").resolve()),
        str(Path(f"user_projects/{project_id}/chapters/ch-alpha/synopsis.md").resolve())
    }

    expected_answer = "In Chapter Alpha, the plan is Plan for Alpha and the synopsis is Synopsis for Alpha."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    with patch.object(processor, '_execute_llm_complete', wraps=processor._execute_llm_complete) as mock_execute_llm:
        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis,
            paths_to_filter=paths_to_filter_set,
            direct_chapter_context=direct_chapter_context
        )

        assert answer == expected_answer
        assert source_nodes == expected_filtered_nodes
        assert direct_info is not None
        assert len(direct_info) == 2
        assert {'type': 'ChapterPlan', 'name': f"Plan for Chapter '{chapter_title}'"} in direct_info
        assert {'type': 'ChapterSynopsis', 'name': f"Synopsis for Chapter '{chapter_title}'"} in direct_info

        mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
        mock_execute_llm.assert_awaited_once()
        internal_call_args, internal_call_kwargs = mock_execute_llm.call_args
        prompt_arg = internal_call_args[0]
        assert "**Project Plan:**" in prompt_arg
        assert plan in prompt_arg
        assert "**Project Synopsis:**" in prompt_arg
        assert synopsis in prompt_arg
        assert f"**Directly Requested Chapter Context (for Chapter '{chapter_title}'):**" in prompt_arg
        assert "--- Start Chapter Plan ---" in prompt_arg
        assert chapter_plan in prompt_arg
        assert "--- Start Chapter Synopsis ---" in prompt_arg
        assert chapter_synopsis in prompt_arg
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
    answer, source_nodes, direct_info = await processor.query(project_id, query_text, plan, synopsis, direct_chapter_context=None)
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
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Some context", metadata={'file_path': 'scenes/s1.md'}), score=0.9)
    retrieved_nodes = [mock_node1]
    expected_filtered_nodes = [mock_node1]
    paths_to_filter_set = {str(Path(f"user_projects/{project_id}/plan.md").resolve())}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    with patch.object(processor, '_execute_llm_complete', side_effect=ValueError("LLM prompt validation failed")) as mock_decorated_method:
        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set, direct_chapter_context=None
        )

        assert "Sorry, an internal error occurred processing the query." in answer
        assert source_nodes == []
        assert direct_info is None
        mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
        mock_decorated_method.assert_awaited_once()

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
    paths_to_filter_set = {str(Path(f"user_projects/{project_id}/plan.md").resolve())}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    with patch.object(processor, '_execute_llm_complete', return_value=CompletionResponse(text="")) as mock_decorated_method:
        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set, direct_chapter_context=None
        )

        assert "(The AI did not provide an answer based on the context.)" in answer
        assert source_nodes == expected_filtered_nodes
        assert direct_info is None
        mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
        mock_decorated_method.assert_awaited_once()


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
    expected_calls = [
        call(prompt, temperature=settings.LLM_TEMPERATURE),
        call(prompt, temperature=settings.LLM_TEMPERATURE),
        call(prompt, temperature=settings.LLM_TEMPERATURE)
    ]
    mock_llm.acomplete.assert_has_awaits(expected_calls)

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
    expected_calls = [
        call(prompt, temperature=settings.LLM_TEMPERATURE),
        call(prompt, temperature=settings.LLM_TEMPERATURE),
        call(prompt, temperature=settings.LLM_TEMPERATURE)
    ]
    mock_llm.acomplete.assert_has_awaits(expected_calls)

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
    mock_llm.acomplete.assert_awaited_once_with(prompt, temperature=settings.LLM_TEMPERATURE)

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
    plan_path_str = f'user_projects/{project_id}/plan.md'
    scene_path_str = f'user_projects/{project_id}/scenes/s1.md'
    mock_node_plan = NodeWithScore(node=TextNode(id_='n1', text="Plan context", metadata={'file_path': plan_path_str}), score=0.9)
    mock_node_scene = NodeWithScore(node=TextNode(id_='n2', text="Scene context", metadata={'file_path': scene_path_str}), score=0.8)
    retrieved_nodes = [mock_node_plan, mock_node_scene]
    expected_filtered_nodes = [mock_node_scene]
    paths_to_filter_set = {str(Path(plan_path_str).resolve())}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)

    final_error = create_mock_client_error(429, "Rate limit")
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    # Patch the internal helper method that is decorated
    with patch.object(processor, '_execute_llm_complete', side_effect=final_error) as mock_decorated_method:
        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set, direct_chapter_context=None
        )

        assert "Rate limit exceeded for query after multiple retries" in answer
        assert source_nodes == expected_filtered_nodes
        assert direct_info is None
        mock_decorated_method.assert_awaited_once()


# --- Tests for Node Deduplication and Filtering ---
@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_deduplicates_and_filters_nodes(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-qp-dedup-filter"
    query_text = "Deduplicate and filter test"
    plan = "Plan"
    synopsis = "Synopsis"
    plan_path_str = f"user_projects/{project_id}/plan.md"
    scene1_path_str = f"user_projects/{project_id}/scenes/s1.md"
    scene2_path_str = f"user_projects/{project_id}/scenes/s2.md"
    char_path_str = f"user_projects/{project_id}/characters/c1.md"

    mock_node_plan = NodeWithScore(node=TextNode(id_='n_plan', text="Plan context.", metadata={'file_path': plan_path_str, 'document_type': 'Plan'}), score=0.9)
    mock_node_s1_low = NodeWithScore(node=TextNode(id_='n_s1_low', text="Scene 1 content.", metadata={'file_path': scene1_path_str, 'document_type': 'Scene'}), score=0.7)
    mock_node_s1_high = NodeWithScore(node=TextNode(id_='n_s1_high', text="Scene 1 content.", metadata={'file_path': scene1_path_str, 'document_type': 'Scene'}), score=0.8)
    mock_node_s2 = NodeWithScore(node=TextNode(id_='n_s2', text="Scene 2 content.", metadata={'file_path': scene2_path_str, 'document_type': 'Scene'}), score=0.75)
    mock_node_char = NodeWithScore(node=TextNode(id_='n_char', text="Character info.", metadata={'file_path': char_path_str, 'document_type': 'Character'}), score=0.85)

    retrieved_nodes: List[NodeWithScore] = [ mock_node_plan, mock_node_s1_low, mock_node_s1_high, mock_node_s2, mock_node_char, ]
    paths_to_filter_set = {str(Path(plan_path_str).resolve())}
    expected_final_nodes: List[NodeWithScore] = [ mock_node_s1_high, mock_node_s2, mock_node_char, ]

    expected_answer = "Answer based on filtered and deduplicated context."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    with patch.object(processor, '_execute_llm_complete', wraps=processor._execute_llm_complete) as mock_execute_llm:
        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set, direct_chapter_context=None
        )

        assert answer == expected_answer
        assert sorted([n.node.node_id for n in source_nodes]) == sorted([n.node.node_id for n in expected_final_nodes])
        assert len(source_nodes) == len(expected_final_nodes)
        assert direct_info is None
        mock_retriever_instance.aretrieve.assert_awaited_once_with(query_text)
        mock_execute_llm.assert_awaited_once()
        internal_call_args, internal_call_kwargs = mock_execute_llm.call_args
        prompt_arg = internal_call_args[0]
        assert "Plan context." not in prompt_arg
        assert "Scene 1 content." in prompt_arg
        assert "Scene 2 content." in prompt_arg
        assert "Character info." in prompt_arg


@pytest.mark.asyncio
@patch('app.rag.query_processor.VectorIndexRetriever', autospec=True)
async def test_query_node_without_filepath_is_not_filtered(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test that nodes without a file_path are never filtered out."""
    project_id = "proj-qp-no-path-filter"
    query_text = "Test no path filtering"
    plan = "Plan"
    synopsis = "Synopsis"
    plan_path_str = f"user_projects/{project_id}/plan.md"

    mock_node_plan = NodeWithScore(node=TextNode(id_='n_plan', text="Plan context.", metadata={'file_path': plan_path_str, 'document_type': 'Plan'}), score=0.9)
    mock_node_no_path = NodeWithScore(node=TextNode(id_='n_no_path', text="Context without file path.", metadata={'document_type': 'Unknown'}), score=0.8)

    retrieved_nodes: List[NodeWithScore] = [mock_node_plan, mock_node_no_path]
    paths_to_filter_set = {str(Path(plan_path_str).resolve())}
    expected_final_nodes: List[NodeWithScore] = [mock_node_no_path]

    expected_answer = "Answer based on non-filtered node."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=expected_answer))
    processor = QueryProcessor(index=mock_index, llm=mock_llm)
    with patch.object(processor, '_execute_llm_complete', wraps=processor._execute_llm_complete) as mock_execute_llm:
        answer, source_nodes, direct_info = await processor.query(
            project_id, query_text, plan, synopsis, paths_to_filter=paths_to_filter_set, direct_chapter_context=None
        )

        assert source_nodes == expected_final_nodes
        internal_call_args, internal_call_kwargs = mock_execute_llm.call_args
        prompt_arg = internal_call_args[0]
        assert "Plan context." not in prompt_arg
        assert "Context without file path." in prompt_arg

# --- END TESTS ---