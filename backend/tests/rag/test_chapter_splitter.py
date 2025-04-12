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
import logging
from typing import Optional, List, Set # Import Set
from pathlib import Path # Import Path

from tenacity import RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted
from fastapi import HTTPException, status

# Import the class we are testing
from app.rag.chapter_splitter import ChapterSplitter, _is_retryable_google_api_error # Import predicate too
from app.services.file_service import file_service

# Import necessary LlamaIndex types for mocking
from llama_index.core.llms import LLM, CompletionResponse
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore, TextNode

# Import models used
from app.models.ai import ProposedScene
# Import settings
from app.core.config import settings # Import settings


# --- Fixtures ---
@pytest.fixture
def mock_llm_for_splitter():
    llm = MagicMock(spec=LLM)
    llm.acomplete = AsyncMock() # Mock the completion endpoint
    return llm

@pytest.fixture
def mock_index_for_splitter(): # Keep fixture even if unused by constructor for now
    return MagicMock(spec=VectorStoreIndex)

@pytest.fixture
def chapter_splitter(mock_index_for_splitter: MagicMock, mock_llm_for_splitter: MagicMock) -> ChapterSplitter:
    # Pass index even if not used by current logic
    return ChapterSplitter(index=mock_index_for_splitter, llm=mock_llm_for_splitter)


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

# --- Test Cases ---
@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True) # Mock retriever
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_success(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-1"; chapter_id = "ch-split-1"; chapter_content = "Scene 1 content. Some break. Scene 2 content.";
    # Make context long enough to guarantee truncation based on default MAX_CONTEXT_LENGTH
    long_string_multiplier = (settings.MAX_CONTEXT_LENGTH // 4) + 2 # Ensure it's longer
    plan = ("Plan" * long_string_multiplier)
    synopsis = ("Synopsis" * long_string_multiplier)
    chapter_plan = "Chapter Plan"; chapter_synopsis = "Chapter Synopsis" # Not truncated
    chapter_title = "The First Chapter"
    expected_scenes = [ ProposedScene(suggested_title="Scene 1 Title", content="Scene 1 content."), ProposedScene(suggested_title="Scene 2 Title", content="Some break. Scene 2 content.") ]
    mock_llm_response_text = ("<<<SCENE_START>>>\nTITLE: Scene 1 Title\nCONTENT:\nScene 1 content.\n<<<SCENE_END>>>\n<<<SCENE_START>>>\nTITLE: Scene 2 Title\nCONTENT:\nSome break. Scene 2 content.\n<<<SCENE_END>>>")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    with patch.object(chapter_splitter, '_execute_llm_complete', wraps=chapter_splitter._execute_llm_complete) as mock_execute_llm:
        result = await chapter_splitter.split(
            project_id, chapter_id, chapter_content,
            plan, synopsis,
            chapter_plan, chapter_synopsis
        )
        assert result == expected_scenes
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once(); prompt_arg = mock_execute_llm.call_args[0][0]; assert chapter_content in prompt_arg; assert "<<<SCENE_START>>>" in prompt_arg
        # Check truncated context
        truncated_plan = plan[:settings.MAX_CONTEXT_LENGTH] + ('...' if len(plan) > settings.MAX_CONTEXT_LENGTH else '')
        truncated_synopsis = synopsis[:settings.MAX_CONTEXT_LENGTH] + ('...' if len(synopsis) > settings.MAX_CONTEXT_LENGTH else '')
        assert "**Project Plan:**" in prompt_arg; assert truncated_plan in prompt_arg
        if len(plan) > settings.MAX_CONTEXT_LENGTH: assert plan not in prompt_arg
        assert "**Project Synopsis:**" in prompt_arg; assert truncated_synopsis in prompt_arg
        if len(synopsis) > settings.MAX_CONTEXT_LENGTH: assert synopsis not in prompt_arg
        assert f"**Chapter Plan (for Chapter '{chapter_title}'):**" in prompt_arg; assert chapter_plan in prompt_arg # Not truncated
        assert f"**Chapter Synopsis (for Chapter '{chapter_title}'):**" in prompt_arg; assert chapter_synopsis in prompt_arg # Not truncated

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_empty_content(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-empty"; chapter_id = "ch-split-empty"; chapter_content = "   "; plan = "Plan"; synopsis = "Synopsis"
    chapter_plan = None; chapter_synopsis = None
    result = await chapter_splitter.split(
        project_id, chapter_id, chapter_content,
        plan, synopsis,
        chapter_plan, chapter_synopsis
    )
    assert result == []
    mock_retriever_class.return_value.aretrieve.assert_not_awaited()
    mock_llm_for_splitter.acomplete.assert_not_awaited()
    mock_file_svc.read_project_metadata.assert_not_called()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_llm_returns_malformed_response(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-malformed"; chapter_id = "ch-split-malformed"; chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    chapter_plan = None; chapter_synopsis = None
    chapter_title = "Malformed Chapter"
    mock_llm_response_text = "Scene 1: Content 1\nScene 2: Content 2"
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    with patch.object(chapter_splitter, '_execute_llm_complete', wraps=chapter_splitter._execute_llm_complete) as mock_execute_llm:
        result = await chapter_splitter.split(
            project_id, chapter_id, chapter_content,
            plan, synopsis,
            chapter_plan, chapter_synopsis
        )
        assert result == []
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_llm_returns_partial_match(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-partial"; chapter_id = "ch-split-partial"; chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    chapter_plan = None; chapter_synopsis = None
    chapter_title = "Partial Chapter"
    expected_scenes = [ProposedScene(suggested_title="Valid Scene", content="Valid Content.")]
    mock_llm_response_text = ("<<<SCENE_START>>>\nTITLE: Valid Scene\nCONTENT:\nValid Content.\n<<<SCENE_END>>>\nINVALID BLOCK HERE\n<<<SCENE_START>>>\nJust some text\n<<<SCENE_END>>>")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    with patch.object(chapter_splitter, '_execute_llm_complete', wraps=chapter_splitter._execute_llm_complete) as mock_execute_llm:
        result = await chapter_splitter.split(
            project_id, chapter_id, chapter_content,
            plan, synopsis,
            chapter_plan, chapter_synopsis
        )
        assert result == expected_scenes
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_llm_error_non_retryable(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-llm-error"; chapter_id = "ch-split-llm-error"; chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    chapter_plan = None; chapter_synopsis = None
    chapter_title = "Error Chapter"
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    with patch.object(chapter_splitter, '_execute_llm_complete', side_effect=ValueError("LLM validation failed")) as mock_execute_llm:
        with pytest.raises(HTTPException) as exc_info:
            await chapter_splitter.split(
                project_id, chapter_id, chapter_content,
                plan, synopsis,
                chapter_plan, chapter_synopsis
            )
        assert exc_info.value.status_code == 500
        assert "Error: An unexpected error occurred during chapter splitting. Please check logs." in exc_info.value.detail
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_llm_empty_response(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    project_id = "proj-split-llm-empty"; chapter_id = "ch-split-llm-empty"; chapter_content = "Some content."; plan = "Plan"; synopsis = "Synopsis"
    chapter_plan = None; chapter_synopsis = None
    chapter_title = "Empty Chapter"
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    with patch.object(chapter_splitter, '_execute_llm_complete', return_value=CompletionResponse(text="")) as mock_execute_llm:
        with pytest.raises(HTTPException) as exc_info:
            await chapter_splitter.split(
                project_id, chapter_id, chapter_content,
                plan, synopsis,
                chapter_plan, chapter_synopsis
            )
        assert exc_info.value.status_code == 500; assert "Error: The AI failed to propose scene splits." in exc_info.value.detail
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()

@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_content_validation_warning(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock, caplog):
    project_id = "proj-split-contentloss"; chapter_id = "ch-split-contentloss"; chapter_content = "This is the original long content that should be mostly preserved."; plan = "Plan"; synopsis = "Synopsis"
    chapter_plan = None; chapter_synopsis = None
    chapter_title = "Content Loss Chapter"
    short_scenes = [ProposedScene(suggested_title="Short Scene", content="Short.")]
    mock_llm_response_text = ("<<<SCENE_START>>>\nTITLE: Short Scene\nCONTENT:\nShort.\n<<<SCENE_END>>>")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    with patch.object(chapter_splitter, '_execute_llm_complete', wraps=chapter_splitter._execute_llm_complete) as mock_execute_llm:
        with caplog.at_level(logging.WARNING):
            result = await chapter_splitter.split(
                project_id, chapter_id, chapter_content,
                plan, synopsis,
                chapter_plan, chapter_synopsis
            )
        assert result == short_scenes; assert len(caplog.records) >= 1; assert any("Concatenated split content length" in rec.message and "significantly differs from original" in rec.message for rec in caplog.records)
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()

# --- Tests for Retry Logic ---
@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_retry_success(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test retry logic succeeds on the third LLM attempt."""
    project_id = "proj-split-retry-ok"; chapter_id = "ch-split-retry-ok"
    chapter_content = "Content"; plan, synopsis = "P", "S"
    chapter_plan = None; chapter_synopsis = None
    chapter_title = "Retry Chapter"
    expected_scenes = [ProposedScene(suggested_title="OK Scene", content="Content")]
    mock_llm_response_text = (
        "<<<SCENE_START>>>\n"
        "TITLE: OK Scene\n"
        "CONTENT:\n"
        "Content\n"
        "<<<SCENE_END>>>"
    )
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    call_count = 0
    async def mock_acomplete_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1: raise create_mock_client_error(429, "Rate limit 1")
        elif call_count == 2: raise create_mock_client_error(429, "Rate limit 2")
        else: return CompletionResponse(text=mock_llm_response_text)
    mock_llm_for_splitter.acomplete.side_effect = mock_acomplete_side_effect

    result = await chapter_splitter.split(
        project_id, chapter_id, chapter_content,
        plan, synopsis,
        chapter_plan, chapter_synopsis
    )

    assert result == expected_scenes
    mock_retriever_instance.aretrieve.assert_awaited_once()
    assert mock_llm_for_splitter.acomplete.await_count == 3
    expected_calls = [
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE)
    ]
    mock_llm_for_splitter.acomplete.assert_has_awaits(expected_calls)


@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_retry_failure(mock_file_svc: MagicMock, mock_retriever_class: MagicMock, chapter_splitter: ChapterSplitter, mock_llm_for_splitter: MagicMock):
    """Test retry logic fails after all LLM attempts."""
    project_id = "proj-split-retry-fail"; chapter_id = "ch-split-retry-fail"
    chapter_content = "Content"; plan, synopsis = "P", "S"
    chapter_plan = None; chapter_synopsis = None
    chapter_title = "Retry Fail Chapter"
    final_error = create_mock_client_error(429, "Rate limit final")
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=[])
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_llm_for_splitter.acomplete.side_effect = final_error

    with pytest.raises(HTTPException) as exc_info:
        await chapter_splitter.split(
            project_id, chapter_id, chapter_content,
            plan, synopsis,
            chapter_plan, chapter_synopsis
        )

    assert exc_info.value.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert "Error: Rate limit exceeded after multiple retries" in exc_info.value.detail
    mock_retriever_instance.aretrieve.assert_awaited_once()
    assert mock_llm_for_splitter.acomplete.await_count == 3
    expected_calls = [
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE),
        call(ANY, temperature=settings.LLM_TEMPERATURE)
    ]
    mock_llm_for_splitter.acomplete.assert_has_awaits(expected_calls)

# --- Deduplication and Filtering Test ---
@pytest.mark.asyncio
@patch('app.rag.chapter_splitter.VectorIndexRetriever', autospec=True)
@patch('app.rag.chapter_splitter.file_service', autospec=True)
async def test_split_deduplicates_and_filters_nodes(
    mock_file_svc: MagicMock,
    mock_retriever_class: MagicMock,
    chapter_splitter: ChapterSplitter,
    mock_llm_for_splitter: MagicMock
):
    project_id = "proj-split-dedup-filter"; chapter_id = "ch-split-dedup-filter"
    chapter_content = "Chapter content to split."
    plan = "Plan"; synopsis = "Synopsis"
    chapter_plan = None; chapter_synopsis = None
    chapter_title = "Dedup Chapter"
    plan_path_str = f"user_projects/{project_id}/plan.md"
    scene1_path_str = f"user_projects/{project_id}/scenes/s1.md"
    scene2_path_str = f"user_projects/{project_id}/scenes/s2.md"
    char_path_str = f"user_projects/{project_id}/characters/c1.md"
    mock_node_plan = NodeWithScore(node=TextNode(id_='n_plan', text="Plan context.", metadata={'file_path': plan_path_str, 'document_type': 'Plan'}), score=0.9)
    mock_node_s1_low = NodeWithScore(node=TextNode(id_='n_s1_low', text="Scene 1 context.", metadata={'file_path': scene1_path_str, 'document_type': 'Scene'}), score=0.7)
    mock_node_s1_high = NodeWithScore(node=TextNode(id_='n_s1_high', text="Scene 1 context.", metadata={'file_path': scene1_path_str, 'document_type': 'Scene'}), score=0.8)
    mock_node_s2 = NodeWithScore(node=TextNode(id_='n_s2', text="Scene 2 context.", metadata={'file_path': scene2_path_str, 'document_type': 'Scene'}), score=0.75)
    mock_node_char = NodeWithScore(node=TextNode(id_='n_char', text="Character info.", metadata={'file_path': char_path_str, 'document_type': 'Character'}), score=0.85)
    retrieved_nodes: List[NodeWithScore] = [ mock_node_plan, mock_node_s1_low, mock_node_s1_high, mock_node_s2, mock_node_char, ]
    paths_to_filter_set = {str(Path(plan_path_str).resolve())}
    expected_final_nodes: List[NodeWithScore] = [ mock_node_s1_high, mock_node_s2, mock_node_char, ]
    mock_llm_response_text = ("<<<SCENE_START>>>\nTITLE: Split Scene 1\nCONTENT:\nPart 1.\n<<<SCENE_END>>>")
    expected_scenes = [ProposedScene(suggested_title="Split Scene 1", content="Part 1.")]
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_file_svc.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title}}}
    mock_llm_for_splitter.acomplete = AsyncMock(return_value=CompletionResponse(text=mock_llm_response_text))
    with patch.object(chapter_splitter, '_execute_llm_complete', wraps=chapter_splitter._execute_llm_complete) as mock_execute_llm:
        result = await chapter_splitter.split(
            project_id, chapter_id, chapter_content,
            plan, synopsis,
            chapter_plan, chapter_synopsis,
            paths_to_filter=paths_to_filter_set
        )
        assert result == expected_scenes
        mock_retriever_instance.aretrieve.assert_awaited_once()
        mock_execute_llm.assert_awaited_once()
        prompt_arg = mock_execute_llm.call_args[0][0]
        assert "Plan context." not in prompt_arg
        assert "Scene 1 context." in prompt_arg
        assert "Scene 2 context." in prompt_arg
        assert "Character info." in prompt_arg

# --- END TESTS ---