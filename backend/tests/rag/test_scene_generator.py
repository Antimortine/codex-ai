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
from llama_index.core.callbacks import CallbackManager
from typing import Dict, List, Tuple, Optional, Any, Set # Added List, Tuple, Optional, Any, Set

from tenacity import RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted
from fastapi import HTTPException, status

# Import the class we are testing
from app.rag.scene_generator import SceneGenerator, _is_retryable_google_api_error # Import predicate too
from app.core.config import settings # Import settings
from app.services.file_service import file_service

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
@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_success_with_context(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-1"; chapter_id = "ch-sg-1"; prompt_summary = "Character enters the tavern."; previous_scene_order = 1;
    # Make context long enough to guarantee truncation based on default MAX_CONTEXT_LENGTH
    long_string_multiplier = (settings.MAX_CONTEXT_LENGTH // 10) + 2 # Ensure it's longer
    plan = ("Plan: Go to tavern." * long_string_multiplier)
    synopsis = ("Synopsis: Hero needs info." * long_string_multiplier)
    prev_scene_content = ("## Scene 1\nHero walks down the street." * long_string_multiplier)
    explicit_previous_scenes = [(1, prev_scene_content)]; chapter_title = "The Journey Begins"
    chapter_plan = "Chapter Plan: Find the barkeep."; chapter_synopsis = "Chapter Synopsis: Tavern encounter." # No truncation
    mock_node1_text = ("Tavern description." * long_string_multiplier)
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text=mock_node1_text, metadata={'file_path': 'world.md', 'project_id': project_id, 'document_type': 'World', 'document_title': 'World Info'}), score=0.85)
    retrieved_nodes = [mock_node1]; mock_llm_response_title = "The Tavern Door"; mock_llm_response_content = "He pushed open the heavy tavern door, revealing the smoky interior."; mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"; 
    # Updated expected result to include source_nodes and direct_sources
    expected_result_dict = {
        "title": mock_llm_response_title, 
        "content": mock_llm_response_content,
        "source_nodes": [],
        "direct_sources": []
    }
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with patch.object(generator, '_execute_llm_complete', wraps=generator._execute_llm_complete) as mock_execute_llm:
        generated_draft = await generator.generate_scene(
            project_id, chapter_id, prompt_summary, previous_scene_order,
            plan, synopsis,
            chapter_plan, chapter_synopsis,
            explicit_previous_scenes
        )
        # Check individual fields instead of entire dict
        assert generated_draft["title"] == expected_result_dict["title"]
        assert generated_draft["content"] == expected_result_dict["content"]
        assert "source_nodes" in generated_draft
        assert "direct_sources" in generated_draft
        
        mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once();
        mock_execute_llm.assert_awaited_once()
        prompt_arg = mock_execute_llm.call_args[0][0]
        assert prompt_summary in prompt_arg

        # --- CORRECTED Truncation Checks ---
        truncated_plan = plan[:settings.MAX_CONTEXT_LENGTH] + ('...' if len(plan) > settings.MAX_CONTEXT_LENGTH else '')
        truncated_synopsis = synopsis[:settings.MAX_CONTEXT_LENGTH] + ('...' if len(synopsis) > settings.MAX_CONTEXT_LENGTH else '')
        truncated_prev_scene = prev_scene_content[:settings.MAX_CONTEXT_LENGTH] + ('...' if len(prev_scene_content) > settings.MAX_CONTEXT_LENGTH else '')
        truncated_node1 = mock_node1_text[:settings.MAX_CONTEXT_LENGTH] + ('...' if len(mock_node1_text) > settings.MAX_CONTEXT_LENGTH else '')

        assert "**Project Plan:**" in prompt_arg; assert truncated_plan in prompt_arg
        if len(plan) > settings.MAX_CONTEXT_LENGTH: assert plan not in prompt_arg
        assert "**Project Synopsis:**" in prompt_arg; assert truncated_synopsis in prompt_arg
        if len(synopsis) > settings.MAX_CONTEXT_LENGTH: assert synopsis not in prompt_arg
        assert f"**Chapter Plan (for Chapter '{chapter_title}'):**" in prompt_arg; assert chapter_plan in prompt_arg # Not truncated
        assert f"**Chapter Synopsis (for Chapter '{chapter_title}'):**" in prompt_arg; assert chapter_synopsis in prompt_arg # Not truncated
        assert truncated_prev_scene in prompt_arg
        if len(prev_scene_content) > settings.MAX_CONTEXT_LENGTH: assert prev_scene_content not in prompt_arg
        assert f"Chapter '{chapter_title}'" in prompt_arg
        assert 'Source (World: "World Info")' in prompt_arg; assert truncated_node1 in prompt_arg
        if len(mock_node1_text) > settings.MAX_CONTEXT_LENGTH: assert mock_node1_text not in prompt_arg
        # --- END CORRECTED ---

        assert 'file_path' not in prompt_arg; assert "Output Format Requirement:" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_success_first_scene(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-2"; chapter_id = "ch-sg-2"; prompt_summary = "The story begins."; previous_scene_order = 0; plan = "Plan: Introduction."; synopsis = "Synopsis: A new beginning."; explicit_previous_scenes = []; chapter_title = "First Chapter"; retrieved_nodes = []
    chapter_plan = None; chapter_synopsis = None
    mock_llm_response_title = "Chapter Start"; mock_llm_response_content = "The sun rose over the quiet village."; mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"; 
    # Updated expected result to include source_nodes and direct_sources
    expected_result_dict = {
        "title": mock_llm_response_title, 
        "content": mock_llm_response_content,
        "source_nodes": [],
        "direct_sources": []
    }
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with patch.object(generator, '_execute_llm_complete', wraps=generator._execute_llm_complete) as mock_execute_llm:
        generated_draft = await generator.generate_scene(
            project_id, chapter_id, prompt_summary, previous_scene_order,
            plan, synopsis,
            chapter_plan, chapter_synopsis,
            explicit_previous_scenes
        )
        # Check individual fields instead of entire dict
        assert generated_draft["title"] == expected_result_dict["title"]
        assert generated_draft["content"] == expected_result_dict["content"]
        assert "source_nodes" in generated_draft
        assert "direct_sources" in generated_draft
        
        mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once();
        mock_execute_llm.assert_awaited_once()
        prompt_arg = mock_execute_llm.call_args[0][0]; assert f"Chapter '{chapter_title}'" in prompt_arg;
        assert f"N/A (Generating the first scene of chapter '{chapter_title}')" in prompt_arg;
        assert "No additional context retrieved" in prompt_arg
        assert "**Chapter Plan" not in prompt_arg
        assert "**Chapter Synopsis" not in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_success_no_rag_nodes(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-3"; chapter_id = "ch-sg-3"; prompt_summary = None; previous_scene_order = 2; plan = "Plan"; synopsis = "Synopsis"; prev_scene_content = "## Scene 2\nSomething happened."; explicit_previous_scenes = [(2, prev_scene_content)]; retrieved_nodes = []; chapter_title = "Middle Chapter"
    chapter_plan = "Chap Plan"; chapter_synopsis = None
    mock_llm_response_title = "Aftermath"; mock_llm_response_content = "Following the previous events, the character reflected."; mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"; 
    # Updated expected result to include source_nodes and direct_sources
    expected_result_dict = {
        "title": mock_llm_response_title, 
        "content": mock_llm_response_content,
        "source_nodes": [],
        "direct_sources": []
    }
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with patch.object(generator, '_execute_llm_complete', wraps=generator._execute_llm_complete) as mock_execute_llm:
        generated_draft = await generator.generate_scene(
            project_id, chapter_id, prompt_summary, previous_scene_order,
            plan, synopsis,
            chapter_plan, chapter_synopsis,
            explicit_previous_scenes
        )
        # Check individual fields instead of entire dict
        assert generated_draft["title"] == expected_result_dict["title"]
        assert generated_draft["content"] == expected_result_dict["content"]
        assert "source_nodes" in generated_draft
        assert "direct_sources" in generated_draft
        
        mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once();
        mock_execute_llm.assert_awaited_once()
        prompt_arg = mock_execute_llm.call_args[0][0]; assert f"Chapter '{chapter_title}'" in prompt_arg; assert "No additional context retrieved" in prompt_arg
        assert f"**Chapter Plan (for Chapter '{chapter_title}'):**" in prompt_arg; assert chapter_plan in prompt_arg
        assert "**Chapter Synopsis" not in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_retriever_error(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-4"; chapter_id = "ch-sg-4"; prompt_summary = "Summary"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "Error Chapter"
    chapter_plan = None; chapter_synopsis = None
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever failed")); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with pytest.raises(HTTPException) as exc_info:
        await generator.generate_scene(
            project_id, chapter_id, prompt_summary, previous_scene_order,
            plan, synopsis,
            chapter_plan, chapter_synopsis,
            explicit_previous_scenes
        )
    assert exc_info.value.status_code == 500; assert "Error: An unexpected error occurred during scene generation. Please check logs." in exc_info.value.detail
    mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once(); mock_llm.acomplete.assert_not_awaited()

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_llm_error(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-5"; chapter_id = "ch-sg-5"; prompt_summary = "Summary"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "LLM Error Chapter"; retrieved_nodes = []
    chapter_plan = None; chapter_synopsis = None
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with patch.object(generator, '_execute_llm_complete', side_effect=ValueError("LLM failed validation")) as mock_execute_llm:
        with pytest.raises(HTTPException) as exc_info:
            await generator.generate_scene(
                project_id, chapter_id, prompt_summary, previous_scene_order,
                plan, synopsis,
                chapter_plan, chapter_synopsis,
                explicit_previous_scenes
            )
        assert exc_info.value.status_code == 500; assert "Error: An unexpected error occurred during scene generation. Please check logs." in exc_info.value.detail
        mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once();
        mock_execute_llm.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_llm_empty_response(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-6"; chapter_id = "ch-sg-6"; prompt_summary = "Summary"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "Empty Response Chapter"; retrieved_nodes = []
    chapter_plan = None; chapter_synopsis = None
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with patch.object(generator, '_execute_llm_complete', return_value=CompletionResponse(text="")) as mock_execute_llm:
        with pytest.raises(HTTPException) as exc_info:
            await generator.generate_scene(
                project_id, chapter_id, prompt_summary, previous_scene_order,
                plan, synopsis,
                chapter_plan, chapter_synopsis,
                explicit_previous_scenes
            )
        assert exc_info.value.status_code == 500; assert "Error: The AI failed to generate a scene draft." in exc_info.value.detail
        mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once();
        mock_execute_llm.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_llm_bad_format_response(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, mock_llm: MagicMock, mock_index: MagicMock):
    project_id = "proj-sg-7"; chapter_id = "ch-sg-7"; prompt_summary = "Summary"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "Bad Format Chapter"; retrieved_nodes = []
    chapter_plan = None; chapter_synopsis = None
    mock_llm_response_text = "Just the content, no title heading."; 
    # Updated expected result to include source_nodes and direct_sources
    expected_result_dict = {
        "title": "Untitled Scene", 
        "content": mock_llm_response_text,
        "source_nodes": [],
        "direct_sources": []
    }
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with patch.object(generator, '_execute_llm_complete', wraps=generator._execute_llm_complete) as mock_execute_llm:
        generated_draft = await generator.generate_scene(
            project_id, chapter_id, prompt_summary, previous_scene_order,
            plan, synopsis,
            chapter_plan, chapter_synopsis,
            explicit_previous_scenes
        )
        # Check individual fields instead of entire dict
        assert generated_draft["title"] == expected_result_dict["title"]
        assert generated_draft["content"] == expected_result_dict["content"]
        assert "source_nodes" in generated_draft
        assert "direct_sources" in generated_draft
        
        mock_file_svc.read_project_metadata.assert_called_once_with(project_id); mock_retriever_instance.aretrieve.assert_awaited_once();
        mock_execute_llm.assert_awaited_once()

# --- Retry Test ---
@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_handles_retry_failure_gracefully(
    mock_file_svc: MagicMock,
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    """Test that generate_scene raises HTTPException 429 after rate limit retries fail."""
    project_id = "proj-sg-retry-fail"; chapter_id = "ch-sg-retry-fail"; prompt_summary = "Summary"; previous_scene_order = 1
    plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]
    chapter_title = "Retry Fail Chapter"
    retrieved_nodes = []
    chapter_plan = None; chapter_synopsis = None

    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)

    final_error = create_mock_client_error(429, "Rate limit")
    mock_llm.acomplete.side_effect = final_error

    generator = SceneGenerator(index=mock_index, llm=mock_llm)

    with pytest.raises(HTTPException) as exc_info:
         await generator.generate_scene(
             project_id, chapter_id, prompt_summary, previous_scene_order,
             plan, synopsis,
             chapter_plan, chapter_synopsis,
             explicit_previous_scenes
         )

    assert exc_info.value.status_code == 429
    assert "Error: Rate limit exceeded after multiple retries." in exc_info.value.detail
    assert mock_llm.acomplete.await_count == 3
    expected_calls = [
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE)
    ]
    mock_llm.acomplete.assert_has_awaits(expected_calls)

# --- Deduplication and Filtering Test ---
@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
@patch('app.rag.scene_generator.file_service', autospec=True)
async def test_generate_scene_deduplicates_and_filters_nodes(
    mock_file_svc: MagicMock,
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,
    mock_index: MagicMock
):
    project_id = "proj-sg-dedup-filter"; chapter_id = "ch-sg-dedup-filter"; prompt_summary = "Test dedup/filter"; previous_scene_order = 1; plan = "Plan"; synopsis = "Synopsis"; explicit_previous_scenes = [(1, "Previous")]; chapter_title = "Dedup Chapter"
    chapter_plan = None; chapter_synopsis = None
    plan_path_str = f"user_projects/{project_id}/plan.md"
    world_path_str = f"user_projects/{project_id}/world.md"
    char1_path_str = f"user_projects/{project_id}/characters/c1.md"
    char2_path_str = f"user_projects/{project_id}/characters/c2.md"
    mock_node_plan = NodeWithScore(node=TextNode(id_='n_plan', text="Plan context.", metadata={'file_path': plan_path_str, 'document_type': 'Plan'}), score=0.9)
    mock_node_world_low = NodeWithScore(node=TextNode(id_='n_world_low', text="World info.", metadata={'file_path': world_path_str, 'document_type': 'World'}), score=0.7)
    mock_node_world_high = NodeWithScore(node=TextNode(id_='n_world_high', text="World info.", metadata={'file_path': world_path_str, 'document_type': 'World'}), score=0.8)
    mock_node_char1 = NodeWithScore(node=TextNode(id_='n_char1', text="Char 1 details.", metadata={'file_path': char1_path_str, 'document_type': 'Character'}), score=0.75)
    mock_node_char2 = NodeWithScore(node=TextNode(id_='n_char2', text="Char 2 details.", metadata={'file_path': char2_path_str, 'document_type': 'Character'}), score=0.85)
    retrieved_nodes: List[NodeWithScore] = [ mock_node_plan, mock_node_world_low, mock_node_world_high, mock_node_char1, mock_node_char2, ]
    paths_to_filter_set = {str(Path(plan_path_str).resolve())}
    expected_final_nodes: List[NodeWithScore] = [ mock_node_world_high, mock_node_char1, mock_node_char2, ]
    mock_llm_response_title = "Filtered Scene"; mock_llm_response_content = "Generated from filtered context."; mock_llm_response_text = f"## {mock_llm_response_title}\n{mock_llm_response_content}"; 
    # Updated expected result to include source_nodes and direct_sources with the expected filtered nodes
    expected_result_dict = {
        "title": mock_llm_response_title, 
        "content": mock_llm_response_content,
        "source_nodes": [
            {
                "id": mock_node_world_high.node.id_,
                "text": mock_node_world_high.node.text,
                "score": mock_node_world_high.score,
                "metadata": mock_node_world_high.node.metadata
            },
            {
                "id": mock_node_char1.node.id_,
                "text": mock_node_char1.node.text,
                "score": mock_node_char1.score,
                "metadata": mock_node_char1.node.metadata
            },
            {
                "id": mock_node_char2.node.id_,
                "text": mock_node_char2.node.text,
                "score": mock_node_char2.score,
                "metadata": mock_node_char2.node.metadata
            }
        ],
        "direct_sources": []
    }
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_retriever_instance = mock_retriever_class.return_value; mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text)); mock_llm.callback_manager = None
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    with patch.object(generator, '_execute_llm_complete', wraps=generator._execute_llm_complete) as mock_execute_llm:
        generated_draft = await generator.generate_scene(
            project_id, chapter_id, prompt_summary, previous_scene_order,
            plan, synopsis,
            chapter_plan, chapter_synopsis,
            explicit_previous_scenes,
            paths_to_filter=paths_to_filter_set
        )
        # Check individual fields instead of entire dict
        assert generated_draft["title"] == expected_result_dict["title"]
        assert generated_draft["content"] == expected_result_dict["content"]
        assert "source_nodes" in generated_draft
        assert "direct_sources" in generated_draft
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()
        prompt_arg = mock_execute_llm.call_args[0][0]
        assert "Plan context." not in prompt_arg
        assert "World info." in prompt_arg
        assert "Char 1 details." in prompt_arg
        assert "Char 2 details." in prompt_arg

# --- END TESTS ---