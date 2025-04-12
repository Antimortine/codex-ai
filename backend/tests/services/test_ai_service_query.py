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
from unittest.mock import MagicMock, AsyncMock, call, patch, ANY # Import ANY
from fastapi import HTTPException, status
from pathlib import Path
import asyncio
from typing import Dict, Optional, List, Set # Import Set

from app.services.ai_service import AIService, LoadedContext # Import LoadedContext
from app.services.file_service import FileService # Keep for spec
from app.rag.engine import RagEngine # Keep for spec
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store import VectorStoreIndex


# --- Test AIService.query_project Methods ---

@pytest.mark.asyncio
# --- MODIFIED: Patch rag_engine and file_service (for entity list compilation) ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_query_project_success_no_direct_match(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test successful query_project call with no direct entity matches."""
    project_id = "test-proj-uuid"
    query_text = "What is the main theme?"
    mock_plan_content = "This is the project plan."
    mock_synopsis_content = "This is the project synopsis."
    mock_answer = "The main theme is adventure."
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()
    mock_scene_path = Path(f"user_projects/{project_id}/scenes/s1.md").resolve()
    mock_node_scene = NodeWithScore(node=TextNode(id_='n2', text="Source text 2", metadata={'file_path': str(mock_scene_path)}), score=0.8)
    mock_filtered_source_nodes = [mock_node_scene]
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = None

    # Mock the _load_context helper return value
    mock_loaded_project_context: LoadedContext = {
        'project_plan': mock_plan_content,
        'project_synopsis': mock_synopsis_content,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path)}
    }

    # Mock entity list compilation parts (still needed before _load_context)
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_content_block_path.side_effect = lambda pid, fname: {
        "plan.md": mock_plan_path.parent / "plan.md",
        "synopsis.md": mock_synopsis_path.parent / "synopsis.md",
        "world.md": mock_plan_path.parent / "world.md"
    }.get(fname)
    mock_file_service._get_project_path.return_value = mock_plan_path.parent
    mock_file_service.path_exists.return_value = False # For notes dir check

    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_filtered_source_nodes, mock_direct_sources_info))

    # Instantiate AIService and patch its internal helper
    service_instance_under_test = AIService()
    with patch.object(service_instance_under_test, '_load_context', return_value=mock_loaded_project_context) as mock_load_ctx:

        # Call the method
        answer, source_nodes, direct_info = await service_instance_under_test.query_project(project_id, query_text)

        # Assertions
        assert answer == mock_answer
        assert source_nodes == mock_filtered_source_nodes
        assert direct_info == mock_direct_sources_info

        # Verify mocks
        mock_load_ctx.assert_called_once_with(project_id) # Called once for project context
        # Verify rag_engine call
        mock_rag_engine.query.assert_awaited_once_with(
            project_id=project_id,
            query_text=query_text,
            explicit_plan=mock_plan_content,
            explicit_synopsis=mock_synopsis_content,
            direct_sources_data=[], # No direct matches
            direct_chapter_context=None, # No chapter match
            paths_to_filter=mock_loaded_project_context['filter_paths'] # Paths from project context
        )

@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_query_project_success_with_direct_chapter_match(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test query_project call with a direct chapter title match."""
    project_id = "test-proj-direct-chap"
    chapter_id = "ch1-abc"
    chapter_title = "The First Chapter"
    query_text = f"What is the plan for {chapter_title}?"
    mock_plan_content = "Overall project plan."
    mock_synopsis_content = "Overall project synopsis."
    mock_chapter_plan_content = "Plan specific to chapter 1."
    mock_chapter_synopsis_content = None # Simulate chapter synopsis missing
    mock_answer = "Chapter 1 plan is..."
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md").resolve()
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md").resolve()
    mock_chapter_plan_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/plan.md").resolve()
    mock_chapter_synopsis_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/synopsis.md").resolve() # Path exists even if file doesn't
    mock_filtered_source_nodes = []
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = [ # Expected direct info
         {'type': 'ChapterPlan', 'name': f"Plan for Chapter '{chapter_title}'"}
    ]

    # Mock _load_context return values
    mock_loaded_project_context: LoadedContext = {
        'project_plan': mock_plan_content,
        'project_synopsis': mock_synopsis_content,
        'filter_paths': {str(mock_plan_path), str(mock_synopsis_path)}
    }
    mock_loaded_chapter_context: LoadedContext = {
        'chapter_plan': mock_chapter_plan_content,
        'chapter_synopsis': None, # FileService returns None if not found
        'filter_paths': {str(mock_chapter_plan_path)}, # Only plan path added
        'chapter_title': chapter_title
    }

    # Mock entity list compilation to include the chapter
    mock_file_service.read_project_metadata.return_value = {
        "chapters": {chapter_id: {"title": chapter_title}},
        "characters": {}
    }
    # Mock path helpers used during entity list compilation
    mock_file_service._get_content_block_path.side_effect = lambda pid, fname: {
        "plan.md": mock_plan_path.parent / "plan.md",
        "synopsis.md": mock_synopsis_path.parent / "synopsis.md",
        "world.md": mock_plan_path.parent / "world.md"
    }.get(fname)
    mock_file_service._get_chapter_plan_path.return_value = mock_chapter_plan_path
    mock_file_service._get_chapter_synopsis_path.return_value = mock_chapter_synopsis_path
    mock_file_service._get_project_path.return_value = mock_plan_path.parent
    mock_file_service.path_exists.return_value = False # For notes dir check

    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_filtered_source_nodes, mock_direct_sources_info))

    # Instantiate AIService and patch its internal helper
    service_instance_under_test = AIService()
    # Patch _load_context to return different values based on args
    def load_context_side_effect(p_id, c_id=None):
        if c_id == chapter_id:
            return mock_loaded_chapter_context
        elif c_id is None:
            return mock_loaded_project_context
        else:
            pytest.fail(f"Unexpected chapter_id in _load_context: {c_id}")
    with patch.object(service_instance_under_test, '_load_context', side_effect=load_context_side_effect) as mock_load_ctx:

        # Call the method
        answer, source_nodes, direct_info = await service_instance_under_test.query_project(project_id, query_text)

        # Assertions
        assert answer == mock_answer
        assert source_nodes == mock_filtered_source_nodes
        assert direct_info == mock_direct_sources_info # Check direct info list

        # Verify mocks
        assert mock_load_ctx.call_count == 2
        mock_load_ctx.assert_has_calls([
            call(project_id), # First call for project context
            call(project_id, chapter_id) # Second call for matched chapter context
        ])

        # Verify rag_engine call
        expected_final_filter_paths = {
            str(mock_plan_path),
            str(mock_synopsis_path),
            str(mock_chapter_plan_path) # Only chapter plan was loaded
        }
        expected_direct_chapter_context = {
            'chapter_plan': mock_chapter_plan_content,
            'chapter_synopsis': None,
            'chapter_title': chapter_title
        }
        mock_rag_engine.query.assert_awaited_once_with(
            project_id=project_id,
            query_text=query_text,
            explicit_plan=mock_plan_content,
            explicit_synopsis=mock_synopsis_content,
            direct_sources_data=[], # No other direct matches
            direct_chapter_context=expected_direct_chapter_context, # Pass chapter context
            paths_to_filter=expected_final_filter_paths # Combined filter paths
        )

@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_query_project_context_load_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test query_project when _load_context returns None for some fields."""
    project_id = "test-proj-uuid-3"
    query_text = "Any details on characters?"
    mock_answer = "Character details are sparse."
    mock_source_nodes = []
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = None

    # Mock _load_context returning partial context
    mock_loaded_project_context: LoadedContext = {
        'project_plan': None, # Simulate plan load error/missing
        'project_synopsis': "Synopsis is available.",
        'filter_paths': {str(Path(f"user_projects/{project_id}/synopsis.md").resolve())} # Only synopsis path
    }

    # Mock entity list compilation (return empty for simplicity)
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_content_block_path.side_effect = lambda pid, fname: Path(f"user_projects/{pid}/{fname}")
    mock_file_service._get_project_path.return_value = Path(f"user_projects/{project_id}")
    mock_file_service.path_exists.return_value = False

    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_source_nodes, mock_direct_sources_info))

    # Instantiate AIService and patch helper
    service_instance_under_test = AIService()
    with patch.object(service_instance_under_test, '_load_context', return_value=mock_loaded_project_context) as mock_load_ctx:

        # Call the method
        answer, source_nodes, direct_info = await service_instance_under_test.query_project(project_id, query_text)

        # Assertions
        assert answer == mock_answer
        assert source_nodes == mock_source_nodes
        assert direct_info == mock_direct_sources_info

        # Verify mocks
        mock_load_ctx.assert_called_once_with(project_id)
        mock_rag_engine.query.assert_awaited_once_with(
            project_id=project_id,
            query_text=query_text,
            explicit_plan=None, # Correctly expect None
            explicit_synopsis="Synopsis is available.",
            direct_sources_data=[],
            direct_chapter_context=None,
            paths_to_filter=mock_loaded_project_context['filter_paths']
        )


@pytest.mark.asyncio
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
async def test_query_project_rag_engine_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test query_project when the rag_engine itself raises an error."""
    project_id = "test-proj-uuid-4"
    query_text = "This query will fail."
    mock_plan_content = "Plan exists."
    mock_synopsis_content = "Synopsis exists."

    # Mock _load_context
    mock_loaded_project_context: LoadedContext = {
        'project_plan': mock_plan_content,
        'project_synopsis': mock_synopsis_content,
        'filter_paths': {
            str(Path(f"user_projects/{project_id}/plan.md").resolve()),
            str(Path(f"user_projects/{project_id}/synopsis.md").resolve())
        }
    }

    # Mock entity list compilation (return empty for simplicity)
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_content_block_path.side_effect = lambda pid, fname: Path(f"user_projects/{pid}/{fname}")
    mock_file_service._get_project_path.return_value = Path(f"user_projects/{project_id}")
    mock_file_service.path_exists.return_value = False

    mock_rag_engine.query = AsyncMock(side_effect=RuntimeError("LLM API failed"))

    # Instantiate AIService and patch helper
    service_instance_under_test = AIService()
    with patch.object(service_instance_under_test, '_load_context', return_value=mock_loaded_project_context) as mock_load_ctx:

        # Call the method and expect the error
        with pytest.raises(RuntimeError, match="LLM API failed"):
            await service_instance_under_test.query_project(project_id, query_text)

        # Verify mocks
        mock_load_ctx.assert_called_once_with(project_id)
        mock_rag_engine.query.assert_awaited_once_with(
            project_id=project_id,
            query_text=query_text,
            explicit_plan=mock_plan_content,
            explicit_synopsis=mock_synopsis_content,
            direct_sources_data=[],
            direct_chapter_context=None,
            paths_to_filter=mock_loaded_project_context['filter_paths']
        )