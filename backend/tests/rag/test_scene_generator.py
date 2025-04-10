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
from llama_index.core.callbacks import CallbackManager

from tenacity import RetryError
from google.genai.errors import ClientError, APIError
from fastapi import HTTPException, status

# Import the class we are testing
from app.rag.scene_generator import SceneGenerator
from app.core.config import settings

# --- Fixtures are defined in tests/rag/conftest.py ---

# --- Helper to create mock ClientError (remains the same) ---
def create_mock_client_error(status_code: int, message: str = "API Error") -> ClientError:
    """Creates a mock ClientError, attempting different initializations."""
    error_dict = {"error": {"message": message, "code": status_code}}
    response_json = error_dict
    try:
        mock_response = MagicMock()
        mock_response.status_code = status_code
        mock_response.json.return_value = response_json
        error = ClientError(message, response=mock_response, response_json=response_json)
    except TypeError:
        try:
            error = ClientError(message, response_json=response_json)
        except TypeError:
            try:
                error = ClientError(f"{status_code} {message}", response_json=response_json)
            except Exception as final_fallback_error:
                 pytest.fail(f"Could not initialize ClientError mock. Last error: {final_fallback_error}")
    if not hasattr(error, 'status_code') or error.status_code != status_code:
         setattr(error, 'status_code', status_code)
    return error
# --- End Helper ---


# --- Test SceneGenerator (Single Call + Parsing) ---

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_success_with_context(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test successful scene generation with context and correct parsing."""
    # Arrange
    project_id = "proj-sg-1"; chapter_id = "ch-sg-1"; prompt_summary = "Character enters the tavern."
    previous_scene_order = 1; plan = "Plan: Go to tavern."; synopsis = "Synopsis: Hero needs info."
    prev_scene_content = "## Scene 1\nHero walks down the street."; explicit_previous_scenes = [(1, prev_scene_content)]
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Tavern description.", metadata={'file_path': 'world.md', 'project_id': project_id}), score=0.85)
    retrieved_nodes = [mock_node1]
    mock_llm_response_title = "The Tavern Door"
    mock_llm_response_content = "He pushed open the heavy tavern door, revealing the smoky interior."
    mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"
    expected_result_dict = {"title": mock_llm_response_title, "content": mock_llm_response_content}

    # Configure mocks
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    mock_llm.callback_manager = None

    # Instantiate and Act
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_draft = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order,
        plan, synopsis, explicit_previous_scenes
    )

    # --- CORRECTED ASSERTION ---
    assert generated_draft == expected_result_dict
    # --- END CORRECTION ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert prompt_summary in prompt_arg
    assert plan in prompt_arg
    assert synopsis in prompt_arg
    assert prev_scene_content in prompt_arg
    assert "Tavern description." in prompt_arg
    assert "Output Format Requirement:" in prompt_arg


@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_success_first_scene(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test successful generation for the first scene (no previous scenes)."""
    project_id = "proj-sg-2"; chapter_id = "ch-sg-2"; prompt_summary = "The story begins."; previous_scene_order = 0
    plan = "Plan: Introduction."; synopsis = "Synopsis: A new beginning."; explicit_previous_scenes = []
    retrieved_nodes = []
    mock_llm_response_title = "Chapter Start"
    mock_llm_response_content = "The sun rose over the quiet village."
    mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"
    expected_result_dict = {"title": mock_llm_response_title, "content": mock_llm_response_content}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    mock_llm.callback_manager = None

    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_draft = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes
    )

    # --- CORRECTED ASSERTION ---
    assert generated_draft == expected_result_dict
    # --- END CORRECTION ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert "Previous Scene(s):** N/A" in prompt_arg
    assert "No additional context retrieved" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_success_no_rag_nodes(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test successful generation when retriever finds no relevant nodes."""
    project_id = "proj-sg-3"; chapter_id = "ch-sg-3"; prompt_summary = None; previous_scene_order = 2
    plan = "Plan"; synopsis = "Synopsis"; prev_scene_content = "## Scene 2\nSomething happened."
    explicit_previous_scenes = [(2, prev_scene_content)]; retrieved_nodes = []
    mock_llm_response_title = "Aftermath"
    mock_llm_response_content = "Following the previous events, the character reflected."
    mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"
    expected_result_dict = {"title": mock_llm_response_title, "content": mock_llm_response_content}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    mock_llm.callback_manager = None

    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_draft = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes
    )

    # --- CORRECTED ASSERTION ---
    assert generated_draft == expected_result_dict
    # --- END CORRECTION ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert "No additional context retrieved" in prompt_arg


@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_retriever_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test generation when the retriever fails."""
    project_id = "proj-sg-4"; chapter_id = "ch-sg-4"; prompt_summary = "Summary"; previous_scene_order = 1
    plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever failed"))
    mock_llm.callback_manager = None

    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    # --- CORRECTED ASSERTION: Expect HTTPException ---
    with pytest.raises(HTTPException) as exc_info:
         await generator.generate_scene(
             project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes
         )
    assert exc_info.value.status_code == 500
    assert "Error: An unexpected error occurred during scene generation. Please check logs." in exc_info.value.detail
    # --- END CORRECTION ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_not_awaited()


@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_llm_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test generation when the LLM call fails with a non-retryable error."""
    project_id = "proj-sg-5"; chapter_id = "ch-sg-5"; prompt_summary = "Summary"; previous_scene_order = 1
    plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=ValueError("LLM failed validation"))
    mock_llm.callback_manager = None

    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    # --- CORRECTED ASSERTION: Expect HTTPException ---
    with pytest.raises(HTTPException) as exc_info:
         await generator.generate_scene(
             project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes
         )
    assert exc_info.value.status_code == 500
    assert "Error: An unexpected error occurred during scene generation. Please check logs." in exc_info.value.detail
    # --- END CORRECTION ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_llm_empty_response(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test generation when the LLM returns an empty response."""
    project_id = "proj-sg-6"; chapter_id = "ch-sg-6"; prompt_summary = "Summary"; previous_scene_order = 1
    plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=""))
    mock_llm.callback_manager = None

    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    # --- CORRECTED ASSERTION: Expect HTTPException ---
    with pytest.raises(HTTPException) as exc_info:
         await generator.generate_scene(
             project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes
         )
    assert exc_info.value.status_code == 500
    assert "Error: The AI failed to generate a scene draft." in exc_info.value.detail
    # --- END CORRECTION ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_llm_bad_format_response(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test generation when the LLM returns text without the required H2 heading."""
    project_id = "proj-sg-7"; chapter_id = "ch-sg-7"; prompt_summary = "Summary"; previous_scene_order = 1
    plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]
    retrieved_nodes = []
    mock_llm_response_text = "Just the content, no title heading."
    expected_result_dict = {"title": "Untitled Scene", "content": mock_llm_response_text}

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    mock_llm.callback_manager = None

    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_draft = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes
    )

    assert generated_draft == expected_result_dict # Check default title is used
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()


@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_handles_retry_failure_gracefully(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test that generate_scene raises HTTPException 429 after rate limit retries fail."""
    project_id = "proj-sg-retry-fail"; chapter_id = "ch-sg-retry-fail"; prompt_summary = "Summary"; previous_scene_order = 1
    plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=create_mock_client_error(429, "Rate limit"))
    mock_llm.callback_manager = None

    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    # --- CORRECTED ASSERTION: Expect HTTPException ---
    with pytest.raises(HTTPException) as exc_info:
         await generator.generate_scene(
             project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes
         )
    assert exc_info.value.status_code == 429
    assert "Error: Rate limit exceeded after multiple retries." in exc_info.value.detail
    # --- END CORRECTION ---
    mock_retriever_instance.aretrieve.assert_awaited_once()
    assert mock_llm.acomplete.await_count == 3