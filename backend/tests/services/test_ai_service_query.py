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

from app.services.ai_service import AIService
from app.services.file_service import FileService # Keep for spec
from app.rag.engine import RagEngine # Keep for spec
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store import VectorStoreIndex


# --- Test AIService.query_project Methods ---

@pytest.mark.asyncio
# --- MODIFIED: Patch the imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_query_project_success(mock_file_service: MagicMock, mock_rag_engine: MagicMock): # Args match patch order
    """Test successful query_project call with all context found."""
    project_id = "test-proj-uuid"
    query_text = "What is the main theme?"
    mock_plan_content = "This is the project plan."
    mock_synopsis_content = "This is the project synopsis."
    mock_answer = "The main theme is adventure."
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md")
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")
    mock_world_path = Path(f"user_projects/{project_id}/world.md") # Added world path
    mock_scene_path = Path(f"user_projects/{project_id}/scenes/s1.md")
    mock_node_scene = NodeWithScore(node=TextNode(id_='n2', text="Source text 2", metadata={'file_path': str(mock_scene_path)}), score=0.8)
    mock_filtered_source_nodes = [mock_node_scene]
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = None

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": return mock_plan_content
            if block_name == "synopsis.md": return mock_synopsis_content
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    def get_content_block_path_side_effect(pid, fname):
        if pid == project_id:
            if fname == "plan.md": return mock_plan_path
            if fname == "synopsis.md": return mock_synopsis_path
            if fname == "world.md": return mock_world_path # Handle world.md
        pytest.fail(f"Unexpected call to _get_content_block_path: {pid}, {fname}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    mock_file_service._get_project_path.return_value = Path(f"user_projects/{project_id}")
    mock_file_service.path_exists.return_value = False # For notes dir check

    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_filtered_source_nodes, mock_direct_sources_info))

    # Instantiate AIService
    service_instance_under_test = AIService()

    # Call the method
    answer, source_nodes, direct_info = await service_instance_under_test.query_project(project_id, query_text)

    # Assertions
    assert answer == mock_answer
    assert source_nodes == mock_filtered_source_nodes
    assert direct_info == mock_direct_sources_info

    # Verify mocks
    expected_file_calls = [call(project_id, "plan.md"), call(project_id, "synopsis.md")]
    mock_file_service.read_content_block_file.assert_has_calls(expected_file_calls, any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    expected_path_calls = [
        call(project_id, "plan.md"),
        call(project_id, "synopsis.md"),
        call(project_id, "world.md")
    ]
    mock_file_service._get_content_block_path.assert_has_calls(expected_path_calls, any_order=True)
    # Check filter paths in assert_awaited_once_with
    expected_filter_set = {str(mock_plan_path), str(mock_synopsis_path)} # Both reads succeeded
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id,
        query_text=query_text,
        explicit_plan=mock_plan_content,
        explicit_synopsis=mock_synopsis_content,
        direct_sources_data=[],
        paths_to_filter=expected_filter_set
    )


@pytest.mark.asyncio
# --- MODIFIED: Patch the imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_query_project_context_not_found(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test query_project when plan or synopsis files are not found (404)."""
    project_id = "test-proj-uuid-2"
    query_text = "Where is the setting?"
    mock_answer = "The setting is not clearly defined."
    mock_source_nodes = [] # Expect empty list
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = None
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md") # Define plan path even if read fails
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")
    mock_world_path = Path(f"user_projects/{project_id}/world.md") # Added world path

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
            elif block_name == "synopsis.md": return "Synopsis content exists."
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    def get_content_block_path_side_effect(pid, fname):
        if pid == project_id:
            # Simulate path retrieval works for plan even if read fails
            if fname == "plan.md": return mock_plan_path
            if fname == "synopsis.md": return mock_synopsis_path
            if fname == "world.md": return mock_world_path # Handle world.md
        pytest.fail(f"Unexpected call to _get_content_block_path: {pid}, {fname}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_project_path.return_value = Path(f"user_projects/{project_id}")
    mock_file_service.path_exists.return_value = False

    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_source_nodes, mock_direct_sources_info))

    # Instantiate AIService
    service_instance_under_test = AIService()

    # Call the method
    answer, source_nodes, direct_info = await service_instance_under_test.query_project(project_id, query_text)

    # Assertions
    assert answer == mock_answer
    assert source_nodes == mock_source_nodes
    assert direct_info == mock_direct_sources_info

    # Verify mocks
    # --- CORRECTED: Assert read_content_block_file was called twice ---
    expected_file_calls = [call(project_id, "plan.md"), call(project_id, "synopsis.md")]
    mock_file_service.read_content_block_file.assert_has_calls(expected_file_calls, any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    # --- END CORRECTED ---
    # Check filter paths in assert_awaited_once_with
    # --- CORRECTED: Expect ONLY synopsis path in filter set ---
    expected_filter_set = {str(mock_synopsis_path)} # Plan read failed, so its path wasn't added
    # --- END CORRECTED ---
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id,
        query_text=query_text,
        explicit_plan="", # Correctly expect ""
        explicit_synopsis="Synopsis content exists.",
        direct_sources_data=[],
        paths_to_filter=expected_filter_set
    )


@pytest.mark.asyncio
# --- MODIFIED: Patch the imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_query_project_context_load_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test query_project when loading context raises an unexpected error."""
    project_id = "test-proj-uuid-3"
    query_text = "Any details on characters?"
    mock_answer = "Character details are sparse."
    mock_source_nodes = [] # Expect empty list
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = None
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md") # Define plan path even if read fails
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")
    mock_world_path = Path(f"user_projects/{project_id}/world.md") # Added world path

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": raise ValueError("Unexpected file system issue") # Non-404 error
            elif block_name == "synopsis.md": return "Synopsis is available."
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    def get_content_block_path_side_effect(pid, fname):
        if pid == project_id:
            if fname == "plan.md": return mock_plan_path
            if fname == "synopsis.md": return mock_synopsis_path
            if fname == "world.md": return mock_world_path # Handle world.md
        pytest.fail(f"Unexpected call to _get_content_block_path: {pid}, {fname}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_project_path.return_value = Path(f"user_projects/{project_id}")
    mock_file_service.path_exists.return_value = False

    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_source_nodes, mock_direct_sources_info))

    # Instantiate AIService
    service_instance_under_test = AIService()

    # Call the method
    answer, source_nodes, direct_info = await service_instance_under_test.query_project(project_id, query_text)

    # Assertions
    assert answer == mock_answer
    assert source_nodes == mock_source_nodes
    assert direct_info == mock_direct_sources_info

    # Verify mocks
    expected_file_calls = [call(project_id, "plan.md"), call(project_id, "synopsis.md")]
    mock_file_service.read_content_block_file.assert_has_calls(expected_file_calls, any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    # Check filter paths in assert_awaited_once_with
    # --- CORRECTED: Expect ONLY synopsis path in filter set ---
    expected_filter_set = {str(mock_synopsis_path)} # Plan read failed, so its path wasn't added
    # --- END CORRECTED ---
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id,
        query_text=query_text,
        explicit_plan="Error loading plan.", # Correctly expect "Error..."
        explicit_synopsis="Synopsis is available.",
        direct_sources_data=[],
        paths_to_filter=expected_filter_set
    )


@pytest.mark.asyncio
# --- MODIFIED: Patch the imported instances ---
@patch('app.services.ai_service.rag_engine', autospec=True)
@patch('app.services.ai_service.file_service', autospec=True)
# --- END MODIFIED ---
async def test_query_project_rag_engine_error(mock_file_service: MagicMock, mock_rag_engine: MagicMock):
    """Test query_project when the rag_engine itself raises an error."""
    project_id = "test-proj-uuid-4"
    query_text = "This query will fail."
    mock_plan_content = "Plan exists."
    mock_synopsis_content = "Synopsis exists."
    mock_plan_path = Path(f"user_projects/{project_id}/plan.md")
    mock_synopsis_path = Path(f"user_projects/{project_id}/synopsis.md")
    mock_world_path = Path(f"user_projects/{project_id}/world.md") # Added world path

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
         if p_id == project_id:
             if block_name == "plan.md": return mock_plan_content
             if block_name == "synopsis.md": return mock_synopsis_content
         pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    def get_content_block_path_side_effect(pid, fname):
        if pid == project_id:
            if fname == "plan.md": return mock_plan_path
            if fname == "synopsis.md": return mock_synopsis_path
            if fname == "world.md": return mock_world_path # Handle world.md
        pytest.fail(f"Unexpected call to _get_content_block_path: {pid}, {fname}")
    mock_file_service._get_content_block_path.side_effect = get_content_block_path_side_effect
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_project_path.return_value = Path(f"user_projects/{project_id}")
    mock_file_service.path_exists.return_value = False

    mock_rag_engine.query = AsyncMock(side_effect=RuntimeError("LLM API failed"))

    # Instantiate AIService
    service_instance_under_test = AIService()

    # Call the method and expect the error
    with pytest.raises(RuntimeError, match="LLM API failed"):
        await service_instance_under_test.query_project(project_id, query_text)

    # Verify mocks
    expected_file_calls = [call(project_id, "plan.md"), call(project_id, "synopsis.md")]
    mock_file_service.read_content_block_file.assert_has_calls(expected_file_calls, any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    # Check filter paths in assert_awaited_once_with
    expected_filter_set = {str(mock_plan_path), str(mock_synopsis_path)}
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id,
        query_text=query_text,
        explicit_plan=mock_plan_content,
        explicit_synopsis=mock_synopsis_content,
        direct_sources_data=[],
        paths_to_filter=expected_filter_set # Check filter paths
    )