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
from typing import List, Optional

from tenacity import RetryError, stop_after_attempt, wait_exponential, retry, retry_if_exception
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted

# Import the class we are testing
from app.rag.rephraser import Rephraser, _is_retryable_google_api_error
from app.core.config import settings

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
# (Non-retry tests unchanged)
@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_success_with_context(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-1"; selected_text = "walked quickly"; context_before = "The hero"; context_after = "to the door."; plan = "Plan"; synopsis = "Synopsis"
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Heroes often hurry.", metadata={'file_path': 'char/hero.md', 'project_id': project_id, 'character_name': 'Hero', 'document_type': 'Character', 'document_title': 'Hero'}), score=0.8)
    retrieved_nodes = [mock_node1]; llm_response_text = "1. hurried\n2. strode rapidly\n3. moved swiftly"; expected_suggestions = ["hurried", "strode rapidly", "moved swiftly"]
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after, plan, synopsis)
    assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT]
    mock_retriever_class.assert_called_once_with(index=mock_index, similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K, filters=ANY)
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert selected_text in prompt_arg
    # --- MODIFIED: Assert corrected character formatting ---
    assert 'Source (Character: "Hero")' in prompt_arg
    # --- END MODIFIED ---
    assert "Heroes often hurry." in prompt_arg
    assert 'file_path' not in prompt_arg
    assert plan in prompt_arg
    assert synopsis in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_success_no_context(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-2"; selected_text = "very big"; retrieved_nodes = []; plan = "Plan"; synopsis = "Synopsis"
    llm_response_text = "1. huge\n2. enormous\n3. gigantic"; expected_suggestions = ["huge", "enormous", "gigantic"]
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT]
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]; assert "No specific context was retrieved via search." in prompt_arg; assert plan in prompt_arg; assert synopsis in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_retriever_error(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-3"; selected_text = "text"; plan = "Plan"; synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever failed"))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    assert len(suggestions) == 1; assert "Error: An unexpected internal error occurred while rephrasing." in suggestions[0]
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_error_non_retryable(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-4"; selected_text = "text"; retrieved_nodes = []; plan = "Plan"; synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=ValueError("LLM failed")) # Non-retryable error
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    assert len(suggestions) == 1
    # --- MODIFIED: Assert correct error message ---
    assert "Error: An unexpected internal error occurred while rephrasing." in suggestions[0]
    # --- END MODIFIED ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once() # Called once

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_empty_response(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-5"; selected_text = "text"; retrieved_nodes = []; plan = "Plan"; synopsis = "Synopsis"
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=""))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    assert len(suggestions) == 1; assert "Error: The AI failed to generate suggestions." in suggestions[0]
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_unparseable_response(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-6"; selected_text = "text"; retrieved_nodes = []; plan = "Plan"; synopsis = "Synopsis"
    llm_response_text = "Here are some ideas: idea one, idea two, idea three."
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    # Fallback parsing now splits by line
    expected_suggestions = ["Here are some ideas: idea one, idea two, idea three."]
    assert suggestions == expected_suggestions
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
async def test_rephrase_empty_input(mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-rp-7"; selected_text = "  "; plan = "Plan"; synopsis = "Synopsis"
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)
    assert suggestions == []; mock_llm.acomplete.assert_not_awaited()


# --- Tests for Retry Logic (REVISED) ---

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True) # Need retriever mock for main call
async def test_rephrase_retry_success(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic succeeds on the third attempt."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    project_id = "proj-retry"; selected_text = "text"; plan = "Plan"; synopsis = "Synopsis"
    expected_response = CompletionResponse(text="1. Success")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Mock retriever call

    # --- MODIFIED: Use callable side_effect ---
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
    # --- END MODIFIED ---

    # Call the main method, which uses the decorated _execute_llm_complete
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)

    # Assert the final result
    assert suggestions == ["Success"]
    # Assert the underlying llm method was called 3 times by tenacity
    assert mock_llm.acomplete.await_count == 3

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True) # Need retriever mock for main call
async def test_rephrase_retry_failure(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic fails after all attempts."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    project_id = "proj-retry-fail"; selected_text = "text"; plan = "Plan"; synopsis = "Synopsis"
    final_error = create_mock_client_error(429, "Rate limit final")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Mock retriever call

    # --- MODIFIED: Use callable side_effect ---
    mock_llm.acomplete.side_effect = final_error # Always raise the final error
    # --- END MODIFIED ---

    # Call the main method, which should catch the error after retries
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)

    # Assert the final result from the error handler
    assert len(suggestions) == 1
    assert "Error: Rate limit exceeded after multiple retries." in suggestions[0]
    # Assert the underlying llm method was called 3 times by tenacity
    assert mock_llm.acomplete.await_count == 3

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True) # Need retriever mock for main call
async def test_rephrase_retry_non_retryable_error(mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic stops immediately for non-retryable errors."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    project_id = "proj-retry-non"; selected_text = "text"; plan = "Plan"; synopsis = "Synopsis"
    non_retryable_error = ValueError("Invalid prompt format")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[]) # Mock retriever call

    # --- MODIFIED: Use callable side_effect ---
    mock_llm.acomplete.side_effect = non_retryable_error
    # --- END MODIFIED ---

    # Call the main method, which should catch the error
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None, plan, synopsis)

    # Assert the final result from the error handler
    assert len(suggestions) == 1
    # --- MODIFIED: Assert correct error message ---
    assert "Error: An unexpected internal error occurred while rephrasing." in suggestions[0]
    # --- END MODIFIED ---
    # Assert the underlying llm method was called only once
    assert mock_llm.acomplete.await_count == 1

# --- END REVISED TESTS ---