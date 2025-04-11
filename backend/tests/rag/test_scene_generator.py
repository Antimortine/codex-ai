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
from typing import Dict, List, Tuple, Optional, Any # Added List, Tuple, Optional, Any

from tenacity import RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted
from fastapi import HTTPException, status

# Import the class we are testing
from app.rag.scene_generator import SceneGenerator, _is_retryable_google_api_error # Import predicate too
from app.core.config import settings
# --- ADDED: Import file_service for mocking ---
from app.services.file_service import file_service
# --- END ADDED ---

# --- Fixtures are defined in tests/rag/conftest.py ---

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
# --- End Helper ---


# --- Test SceneGenerator (Single Call + Parsing) ---
# (Non-retry tests unchanged)
@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_success_with_context(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-1"; chapter_id = "ch-sg-1"; prompt_summary = "Character enters the tavern."; previous_scene_order = 1; plan = "Plan: Go to tavern."; synopsis = "Synopsis: Hero needs info."; prev_scene_content = "## Scene 1\nHero walks down the street."; explicit_previous_scenes = [(1, prev_scene_content)]; chapter_title = "The Journey Begins"
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Tavern description.", metadata={'file_path': 'world.md', 'project_id': project_id, 'document_type': 'World', 'document_title': 'World Info'}), score=0.85)
    retrieved_nodes = [mock_node1]; mock_llm_response_title = "The Tavern Door"; mock_llm_response_content = "He pushed open the heavy tavern door, revealing the smoky interior."; mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"; expected_result_dict = {"title": mock_llm_response_title, "content": mock_llm_response_content}
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_draft = await generator.generate_scene(project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes)
    assert generated_draft == expected_result_dict; mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once(); mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]; assert prompt_summary in prompt_arg; assert plan in prompt_arg; assert synopsis in prompt_arg; assert prev_scene_content in prompt_arg; assert f"Chapter '{chapter_title}'" in prompt_arg; assert 'Source (World: "World Info")' in prompt_arg; assert "Tavern description." in prompt_arg; assert 'file_path' not in prompt_arg; assert "Output Format Requirement:" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_success_first_scene(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-2"; chapter_id = "ch-sg-2"; prompt_summary = "The story begins."; previous_scene_order = 0; plan = "Plan: Introduction."; synopsis = "Synopsis: A new beginning."; explicit_previous_scenes = []; chapter_title = "First Chapter"; retrieved_nodes = []
    mock_llm_response_title = "Chapter Start"; mock_llm_response_content = "The sun rose over the quiet village."; mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"; expected_result_dict = {"title": mock_llm_response_title, "content": mock_llm_response_content}
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_draft = await generator.generate_scene(project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes)
    assert generated_draft == expected_result_dict; mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once(); mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]; assert f"Chapter '{chapter_title}'" in prompt_arg; assert "Previous Scene(s):** N/A" in prompt_arg; assert "No additional context retrieved" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_success_no_rag_nodes(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-3"; chapter_id = "ch-sg-3"; prompt_summary = None; previous_scene_order = 2; plan = "Plan"; synopsis = "Synopsis"; prev_scene_content = "## Scene 2\nSomething happened."; explicit_previous_scenes = [(2, prev_scene_content)]; retrieved_nodes = []; chapter_title = "Middle Chapter"
    mock_llm_response_title = "Aftermath"; mock_llm_response_content = "Following the previous events, the character reflected."; mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"; expected_result_dict = {"title": mock_llm_response_title, "content": mock_llm_response_content}
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_draft = await generator.generate_scene(project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes)
    assert generated_draft == expected_result_dict; mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once(); mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]; assert f"Chapter '{chapter_title}'" in prompt_arg; assert "No additional context retrieved" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_retriever_error(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-4"; chapter_id = "ch-sg-4"; prompt_summary = "Summary"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "Error Chapter"
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever failed")); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with pytest.raises(HTTPException) as exc_info: await generator.generate_scene(project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes)
    assert exc_info.value.status_code == 500; assert "Error: An unexpected error occurred during scene generation. Please check logs." in exc_info.value.detail
    mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once(); mock_llm.acomplete.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_llm_error(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-5"; chapter_id = "ch-sg-5"; prompt_summary = "Summary"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "LLM Error Chapter"; retrieved_nodes = []
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=ValueError("LLM failed validation")); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with pytest.raises(HTTPException) as exc_info: await generator.generate_scene(project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes)
    assert exc_info.value.status_code == 500; assert "Error: An unexpected error occurred during scene generation. Please check logs." in exc_info.value.detail
    mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once(); mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_llm_empty_response(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-6"; chapter_id = "ch-sg-6"; prompt_summary = "Summary"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "Empty Response Chapter"; retrieved_nodes = []
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text="")); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with pytest.raises(HTTPException) as exc_info: await generator.generate_scene(project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes)
    assert exc_info.value.status_code == 500; assert "Error: The AI failed to generate a scene draft." in exc_info.value.detail
    mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once(); mock_llm.acomplete.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_llm_bad_format_response(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-7"; chapter_id = "ch-sg-7"; prompt_summary = "Summary"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "Bad Format Chapter"; retrieved_nodes = []
    mock_llm_response_text = "Just the content, no title heading."; expected_result_dict = {"title": "Untitled Scene", "content": mock_llm_response_text}
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_draft = await generator.generate_scene(project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes)
    assert generated_draft == expected_result_dict; mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once(); mock_llm.acomplete.assert_awaited_once()

# --- MODIFIED: Retry Test ---
@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True) # Mock file_service used for chapter title
async def test_generate_scene_handles_retry_failure_gracefully(
    mock_file_svc: MagicMock, # Add mock file service
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test that generate_scene raises HTTPException 429 after rate limit retries fail."""
    project_id = "proj-sg-retry-fail"; chapter_id = "ch-sg-retry-fail"; prompt_summary = "Summary"; previous_scene_order = 1
    plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]
    chapter_title = "Retry Fail Chapter"
    retrieved_nodes = []

    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}} # Mock chapter title lookup
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)

    # Configure the mock LLM's acomplete method to always raise the retryable error
    final_error = create_mock_client_error(429, "Rate limit")
    mock_llm.acomplete.side_effect = final_error # This will be raised by _execute_llm_complete after retries

    generator = SceneGenerator(index=mock_index, llm=mock_llm)

    # Call the main method, which contains the try/except block
    with pytest.raises(HTTPException) as exc_info:
         await generator.generate_scene(
             project_id, chapter_id, prompt_summary, previous_scene_order, plan, synopsis, explicit_previous_scenes
         )

    # Assert the correct HTTPException is raised by the main method's error handling
    assert exc_info.value.status_code == 429
    assert "Error: Rate limit exceeded after multiple retries." in exc_info.value.detail
    # Assert the underlying llm method was called 3 times by tenacity
    assert mock_llm.acomplete.await_count == 3
# --- END MODIFIED ---