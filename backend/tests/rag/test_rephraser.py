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

from tenacity import RetryError
from google.genai.errors import ClientError

# Import the class we are testing
from app.rag.rephraser import Rephraser
from app.core.config import settings

# --- Fixtures (Use shared fixtures from conftest.py) ---

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

# --- Test Rephraser ---

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_success_with_context(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    # ... (test unchanged) ...
    project_id = "proj-rp-1"
    selected_text = "walked quickly"
    context_before = "The hero"
    context_after = "to the door."
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Heroes often hurry.", metadata={'file_path': 'char/hero.md', 'project_id': project_id, 'character_name': 'Hero'}), score=0.8)
    retrieved_nodes = [mock_node1]
    llm_response_text = "1. hurried\n2. strode rapidly\n3. moved swiftly"
    expected_suggestions = ["hurried", "strode rapidly", "moved swiftly"]
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, context_before, context_after)
    assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT]
    mock_retriever_class.assert_called_once_with(index=mock_index, similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K, filters=ANY)
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert selected_text in prompt_arg
    assert "Heroes often hurry." in prompt_arg


# ... (other non-retry tests remain the same) ...
@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_success_no_context(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    # ... (test unchanged) ...
    project_id = "proj-rp-2"
    selected_text = "very big"
    retrieved_nodes = []
    llm_response_text = "1. huge\n2. enormous\n3. gigantic"
    expected_suggestions = ["huge", "enormous", "gigantic"]
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None)
    assert suggestions == expected_suggestions[:settings.RAG_REPHRASE_SUGGESTION_COUNT]
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert "No specific context was retrieved via search." in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_retriever_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    # ... (test unchanged) ...
    project_id = "proj-rp-3"
    selected_text = "text"
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever failed"))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None)
    assert len(suggestions) == 1
    # --- CORRECTED Assertion ---
    assert "Error: An unexpected internal error occurred while rephrasing." in suggestions[0]
    # --- END CORRECTED ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_error_non_retryable(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    # ... (test unchanged) ...
    project_id = "proj-rp-4"
    selected_text = "text"
    retrieved_nodes = []
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=ValueError("LLM failed"))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None)
    assert len(suggestions) == 1
    # --- CORRECTED Assertion ---
    assert "Error: An unexpected internal error occurred while rephrasing." in suggestions[0]
    # --- END CORRECTED ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_llm_empty_response(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    # ... (test unchanged) ...
    project_id = "proj-rp-5"
    selected_text = "text"
    retrieved_nodes = []
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=""))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None)
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
    # ... (test unchanged) ...
    project_id = "proj-rp-6"
    selected_text = "text"
    retrieved_nodes = []
    llm_response_text = "Here are some ideas: idea one, idea two, idea three."
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=llm_response_text))
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None)
    assert len(suggestions) == 1
    assert suggestions[0] == llm_response_text
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
async def test_rephrase_empty_input(
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    # ... (test unchanged) ...
    project_id = "proj-rp-7"
    selected_text = "  "
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None)
    assert suggestions == []
    mock_llm.acomplete.assert_not_awaited()


# --- Tests for Retry Logic ---

@pytest.mark.asyncio
async def test_rephrase_retry_success(mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic succeeds on the third attempt."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    prompt = "Test rephrase prompt"
    expected_response = CompletionResponse(text="1. Success")

    mock_llm.acomplete.side_effect = [
        create_mock_client_error(429, "Rate limit 1"),
        create_mock_client_error(429, "Rate limit 2"),
        expected_response
    ]

    response = await rephraser._execute_llm_complete(prompt)

    assert response == expected_response
    assert mock_llm.acomplete.await_count == 3
    mock_llm.acomplete.assert_has_awaits([call(prompt), call(prompt), call(prompt)])

@pytest.mark.asyncio
async def test_rephrase_retry_failure(mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic fails after all attempts."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    prompt = "Test rephrase prompt"
    final_error = create_mock_client_error(429, "Rate limit final")

    mock_llm.acomplete.side_effect = [
        create_mock_client_error(429, "Rate limit 1"),
        create_mock_client_error(429, "Rate limit 2"),
        final_error
    ]

    with pytest.raises(ClientError) as exc_info:
        await rephraser._execute_llm_complete(prompt)

    assert exc_info.value is final_error
    assert mock_llm.acomplete.await_count == 3

@pytest.mark.asyncio
async def test_rephrase_retry_non_retryable_error(mock_llm: MagicMock, mock_index: MagicMock):
    """Test retry logic stops immediately for non-429 errors."""
    rephraser = Rephraser(index=mock_index, llm=mock_llm)
    prompt = "Test rephrase prompt"
    non_retryable_error = ValueError("Invalid prompt format")

    mock_llm.acomplete.side_effect = non_retryable_error

    with pytest.raises(ValueError) as exc_info:
        await rephraser._execute_llm_complete(prompt)

    assert exc_info.value == non_retryable_error
    assert mock_llm.acomplete.await_count == 1

@pytest.mark.asyncio
@patch('app.rag.rephraser.VectorIndexRetriever', autospec=True)
async def test_rephrase_handles_retry_failure_gracefully(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test that the main rephrase method handles the re-raised 429 error."""
    # Arrange
    project_id = "proj-rp-retry-fail"
    selected_text = "text"
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)

    # Simulate LLM always raising 429 via the helper method
    mock_llm.acomplete.side_effect = create_mock_client_error(429, "Rate limit")

    rephraser = Rephraser(index=mock_index, llm=mock_llm)

    # Act
    suggestions = await rephraser.rephrase(project_id, selected_text, None, None)

    # Assert
    assert len(suggestions) == 1
    # --- CORRECTED Assertion ---
    assert "Error: Rate limit exceeded after multiple retries." in suggestions[0]
    # --- END CORRECTED ---
    assert mock_llm.acomplete.await_count == 3 # Verify retry happened

# --- END NEW TESTS ---