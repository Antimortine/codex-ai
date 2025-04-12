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
from typing import List, Optional, Set # Import Set

from tenacity import RetryError, stop_after_attempt, wait_exponential, retry, retry_if_exception
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted

# Import the class we are testing
from app.rag.rephraser import Rephraser, _is_retryable_google_api_error
from app.core.config import settings # Import settings

# --- Fixtures (Use shared fixtures from conftest.py) ---

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

# --- Test Rephraser ---
# (Unchanged tests omitted for brevity)
@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_success_with_context(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-1"; selected_text = "walked quickly"; context_before = "The hero"; context_after = "to the door."; plan = "Plan"; synopsis = "Synopsis"
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Heroes often hurry.", metadata={'file_path': 'char/hero.md', 'project_id': project_id, 'character_name': 'Hero', 'document_type': 'Character', 'document_title': 'Hero'}), score=0.8)
    retrieved_nodes = [mock_node1]; llm_response_text = "1. hurried\n2. strode rapidly\n3. moved swiftly"; expected_suggestions = ["hurried", "strode rapidly", "moved swiftly"]
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    with patch.object(rephraser, '_execute_llm_complete', wraps=rephraser._execute_llm_complete) as mock_execute_llm:
        # --- MODIFIED: Pass plan/synopsis ---
        suggestions = await rephraser.rephrase(
            project_id, selected_text, context_before, context_after,
            plan, synopsis # Pass context
        )
        # --- END MODIFIED ---
        assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT]
        mock_retriever_class.assert_called_once_with(index=mock_index, similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K, filters=ANY)
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()
        prompt_arg = mock_execute_llm.call_args[0][0]
        assert selected_text in prompt_arg
        assert 'Source (Character: "Hero")' in prompt_arg
        assert "Heroes often hurry." in prompt_arg
        assert 'file_path' not in prompt_arg
        # --- ADDED: Assert context in prompt ---
        assert "**Project Plan:**" in prompt_arg; assert plan in prompt_arg
        assert "**Project Synopsis:**" in prompt_arg; assert synopsis in prompt_arg
        # --- END ADDED ---

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_success_no_context(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-2"; selected_text = "very big"; retrieved_nodes = []; plan = None; synopsis = None # Simulate missing context
    llm_response_text = "1. huge\n2. enormous\n3. gigantic"; expected_suggestions = ["huge", "enormous", "gigantic"]
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    with patch.object(rephraser, '_execute_llm_complete', wraps=rephraser._execute_llm_complete) as mock_execute_llm:
        # --- MODIFIED: Pass None for plan/synopsis ---
        suggestions = await rephraser.rephrase(
            project_id, selected_text, None, None,
            plan, synopsis # Pass None
        )
        # --- END MODIFIED ---
        assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT]
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()
        prompt_arg = mock_execute_llm.call_args[0][0]; assert "No specific context was retrieved via search." in prompt_arg;
        # --- ADDED: Assert context NOT in prompt ---
        assert "**Project Plan:**" not in prompt_arg
        assert "**Project Synopsis:**" not in prompt_arg
        # --- END ADDED ---

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_retriever_error(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-3"; selected_text = "text"; plan = "Plan"; synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever failed"))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    # --- MODIFIED: Pass plan/synopsis ---
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    # --- END MODIFIED ---
    assert len(suggestions) == 1; assert "Error: An unexpected internal error occurred while rephrasing." in suggestions[0]
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_error_non_retryable(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-4"; selected_text = "text"; retrieved_nodes = []; plan = "Plan"; synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    # Patch the internal helper to raise the error
    with patch.object(rephraser, '_execute_llm_complete', side_effect=ValueError("LLM failed")) as mock_execute_llm:
        # --- MODIFIED: Pass plan/synopsis ---
        suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
        # --- END MODIFIED ---
        assert len(suggestions) == 1
        assert "Error: An unexpected internal error occurred while rephrasing." in suggestions[0]
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once() # Called once

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_empty_response(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-5"; selected_text = "text"; retrieved_nodes = []; plan = "Plan"; synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    # Patch the internal helper to return empty text
    with patch.object(rephraser, '_execute_llm_complete', return_value=CompletionResponse(text="")) as mock_execute_llm:
        # --- MODIFIED: Pass plan/synopsis ---
        suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
        # --- END MODIFIED ---
        assert len(suggestions) == 1; assert "Error: The AI failed to generate suggestions." in suggestions[0]
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_unparseable_response(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-6"; selected_text = "text"; retrieved_nodes = []; plan = "Plan"; synopsis = "Synopsis"
    llm_response_text = "Here are some ideas: idea one, idea two, idea three."
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    with patch.object(rephraser, '_execute_llm_complete', wraps=rephraser._execute_llm_complete) as mock_execute_llm:
        # --- MODIFIED: Pass plan/synopsis ---
        suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
        # --- END MODIFIED ---
        # Fallback parsing now splits by line
        expected_suggestions = ["Here are some ideas: idea one, idea two, idea three."]
        assert suggestions == expected_suggestions
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()

@pytest.mark.asyncio
async def test_rephrase_empty_input(mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-7"; selected_text = "  "; plan = "Plan"; synopsis = "Synopsis"
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    # --- MODIFIED: Pass plan/synopsis ---
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    # --- END MODIFIED ---
    assert suggestions == []; mock_llm.acomplete.assert_not_awaited()


# --- Tests for Retry Logic ---

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True) # Need retriever mock for main call
async def test_rephrase_retry_success(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic succeeds on the third attempt."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    project_id = "proj-retry"; selected_text = "text"; plan = "Plan"; synopsis = "Synopsis"
    expected_response = CompletionResponse(text="1. Success")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Mock retriever call

    call_count = 0
    async def mock_acomplete_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise create_mock_client_error(429, "Rate limit 1")
        elif call_count == 2:
            raise create_mock_client_error(429, "Rate limit 2")
        else:
            return expected_response

    mock_llm.acomplete.side_effect = mock_acomplete_side_effect

    # --- MODIFIED: Pass plan/synopsis ---
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    # --- END MODIFIED ---

    assert suggestions == ["Success"]
    assert mock_llm.acomplete.await_count == 3
    # --- ADDED: Assert with temperature ---
    expected_calls = [
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE)
    ]
    mock_llm.acomplete.assert_has_awaits(expected_calls)
    # --- END ADDED ---

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True) # Need retriever mock for main call
async def test_rephrase_retry_failure(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic fails after all attempts."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    project_id = "proj-retry-fail"; selected_text = "text"; plan = "Plan"; synopsis = "Synopsis"
    final_error = create_mock_client_error(429, "Rate limit final")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Mock retriever call

    mock_llm.acomplete.side_effect = final_error # Always raise the final error

    # --- MODIFIED: Pass plan/synopsis ---
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    # --- END MODIFIED ---

    assert len(suggestions) == 1
    assert "Error: Rate limit exceeded after multiple retries." in suggestions[0]
    assert mock_llm.acomplete.await_count == 3
    # --- ADDED: Assert with temperature ---
    expected_calls = [
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE)
    ]
    mock_llm.acomplete.assert_has_awaits(expected_calls)
    # --- END ADDED ---

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True) # Need retriever mock for main call
async def test_rephrase_retry_non_retryable_error(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic stops immediately for non-retryable errors."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    project_id = "proj-retry-non"; selected_text = "text"; plan = "Plan"; synopsis = "Synopsis"
    non_retryable_error = ValueError("Invalid prompt format")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Mock retriever call

    mock_llm.acomplete.side_effect = non_retryable_error

    # --- MODIFIED: Pass plan/synopsis ---
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    # --- END MODIFIED ---

    assert len(suggestions) == 1
    assert "Error: An unexpected internal error occurred while rephrasing." in suggestions[0]
    assert mock_llm.acomplete.await_count == 1
    # --- ADDED: Assert with temperature ---
    mock_llm.acomplete.assert_awaited_once_with(ANY, temperature=settings.LLM_TEMPERATURE)
    # --- END ADDED ---

# --- ADDED: Tests for Node Deduplication and Filtering ---
# (Unchanged tests omitted for brevity)
@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_deduplicates_and_filters_nodes(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-rp-dedup-filter"
    selected_text = "filter me"
    plan = "Plan"
    synopsis = "Synopsis"
    plan_path_str = f"user_projects/{project_id}/plan.md"
    scene1_path_str = f"user_projects/{project_id}/scenes/s1.md"
    scene2_path_str = f"user_projects/{project_id}/scenes/s2.md"
    char_path_str = f"user_projects/{project_id}/characters/c1.md"

    # Mock retrieved nodes:
    # - plan node (should be filtered)
    # - scene1 node (duplicate 1, lower score)
    # - scene1 node (duplicate 2, higher score, keep this one)
    # - scene2 node (unique, keep)
    # - character node (unique, keep)
    mock_node_plan = NodeWithScore(node=TextNode(id_='n_plan', text="Plan context.", metadata={'file_path': plan_path_str, 'document_type': 'Plan'}), score=0.9)
    mock_node_s1_low = NodeWithScore(node=TextNode(id_='n_s1_low', text="Scene 1 context.", metadata={'file_path': scene1_path_str, 'document_type': 'Scene'}), score=0.7)
    mock_node_s1_high = NodeWithScore(node=TextNode(id_='n_s1_high', text="Scene 1 context.", metadata={'file_path': scene1_path_str, 'document_type': 'Scene'}), score=0.8) # Same content/path, higher score
    mock_node_s2 = NodeWithScore(node=TextNode(id_='n_s2', text="Scene 2 content.", metadata={'file_path': scene2_path_str, 'document_type': 'Scene'}), score=0.75)
    mock_node_char = NodeWithScore(node=TextNode(id_='n_char', text="Character info.", metadata={'file_path': char_path_str, 'document_type': 'Character'}), score=0.85)

    retrieved_nodes: List[NodeWithScore] = [
        mock_node_plan,
        mock_node_s1_low,
        mock_node_s1_high, # Duplicate content/path
        mock_node_s2,
        mock_node_char,
    ]

    # Define the paths that AIService would pass for filtering
    paths_to_filter_set = {str(Path(plan_path_str).resolve())} # Filter out the plan node

    # Expected nodes *after* filtering and deduplication:
    expected_final_nodes: List[NodeWithScore] = [
        mock_node_s1_high,
        mock_node_s2,
        mock_node_char,
    ]

    llm_response_text = "1. filtered suggestion"; expected_suggestions = ["filtered suggestion"]
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    with patch.object(rephraser, '_execute_llm_complete', wraps=rephraser._execute_llm_complete) as mock_execute_llm:

        # Pass the filter set to the rephrase method
        # --- MODIFIED: Pass plan/synopsis and filter set ---
        suggestions = await rephraser.rephrase(
            project_id, selected_text, None, None,
            plan, synopsis, # Pass context
            paths_to_filter=paths_to_filter_set
        )
        # --- END MODIFIED ---

        # Assertions
        assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT]
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()
        prompt_arg = mock_execute_llm.call_args[0][0]

        # Check prompt includes only the non-filtered, non-duplicated nodes
        assert "Plan context." not in prompt_arg        # Filtered
        assert "Scene 1 context." in prompt_arg         # Kept (from high score node)
        assert "Scene 2 content." in prompt_arg         # Kept
        assert "Character info." in prompt_arg         # Kept

# --- END ADDED ---

# --- END TESTS ---