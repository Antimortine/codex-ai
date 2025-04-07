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
# --- MODIFIED: Added patch back to the import ---
from unittest.mock import MagicMock, AsyncMock, call, patch
# --- END MODIFIED ---
from fastapi import HTTPException, status
from pathlib import Path
import asyncio

# Import the *class* we are testing, not the singleton instance
from app.services.ai_service import AIService
# Import classes for dependencies
from app.services.file_service import FileService
from app.rag.engine import RagEngine
# Import models used in responses/arguments
from llama_index.core.schema import NodeWithScore, TextNode

# --- Test AIService Methods ---

@pytest.mark.asyncio
async def test_query_project_success():
    """Test successful query_project call with all context found."""
    project_id = "test-proj-uuid"
    query_text = "What is the main theme?"
    mock_plan_content = "This is the project plan."
    mock_synopsis_content = "This is the project synopsis."
    mock_answer = "The main theme is adventure."
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Source text 1", metadata={'file_path': 'plan.md'}), score=0.9)
    mock_node2 = NodeWithScore(node=TextNode(id_='n2', text="Source text 2", metadata={'file_path': 'scenes/s1.md'}), score=0.8)
    mock_source_nodes = [mock_node1, mock_node2]

    # --- Create mock instances manually ---
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": return mock_plan_content
            if block_name == "synopsis.md": return mock_synopsis_content
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_source_nodes))

    # --- Instantiate AIService with mocks ---
    # Use patch context manager *only* during instantiation if __init__ uses singletons
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
         service_instance_under_test = AIService()
         # Ensure the instance uses our mocks if __init__ assigned them,
         # or assign them manually if __init__ doesn't.
         # Assuming __init__ assigns them based on the patched singletons:
         assert service_instance_under_test.rag_engine is mock_rag_engine
         assert service_instance_under_test.file_service is mock_file_service
         # If __init__ doesn't assign, uncomment these:
         # service_instance_under_test.rag_engine = mock_rag_engine
         # service_instance_under_test.file_service = mock_file_service


    # --- Call the method on the test instance ---
    answer, source_nodes = await service_instance_under_test.query_project(project_id, query_text)

    # Assertions
    assert answer == mock_answer
    assert source_nodes == mock_source_nodes

    # Verify mocks
    expected_file_calls = [call(project_id, "plan.md"), call(project_id, "synopsis.md")]
    mock_file_service.read_content_block_file.assert_has_calls(expected_file_calls, any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id, query_text=query_text, explicit_plan=mock_plan_content, explicit_synopsis=mock_synopsis_content
    )


@pytest.mark.asyncio
async def test_query_project_context_not_found():
    """Test query_project when plan or synopsis files are not found (404)."""
    project_id = "test-proj-uuid-2"
    query_text = "Where is the setting?"
    mock_answer = "The setting is not clearly defined."
    mock_source_nodes = []

    # Create mock instances
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md":
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
            elif block_name == "synopsis.md":
                return "Synopsis content exists."
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_source_nodes))

    # Instantiate AIService with mocks (using patch context for __init__)
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
         service_instance_under_test = AIService()
         assert service_instance_under_test.rag_engine is mock_rag_engine
         assert service_instance_under_test.file_service is mock_file_service
         # If __init__ doesn't assign, uncomment these:
         # service_instance_under_test.rag_engine = mock_rag_engine
         # service_instance_under_test.file_service = mock_file_service

    # Call the method
    answer, source_nodes = await service_instance_under_test.query_project(project_id, query_text)

    # Assertions
    assert answer == mock_answer
    assert source_nodes == mock_source_nodes

    # Verify mocks
    expected_file_calls = [call(project_id, "plan.md"), call(project_id, "synopsis.md")]
    mock_file_service.read_content_block_file.assert_has_calls(expected_file_calls, any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id, query_text=query_text, explicit_plan="", explicit_synopsis="Synopsis content exists."
    )


@pytest.mark.asyncio
async def test_query_project_context_load_error():
    """Test query_project when loading context raises an unexpected error."""
    project_id = "test-proj-uuid-3"
    query_text = "Any details on characters?"
    mock_answer = "Character details are sparse."
    mock_source_nodes = []

    # Create mock instances
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md":
                 raise ValueError("Unexpected file system issue")
            elif block_name == "synopsis.md":
                 return "Synopsis is available."
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_source_nodes))

    # Instantiate AIService with mocks (using patch context for __init__)
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
         service_instance_under_test = AIService()
         assert service_instance_under_test.rag_engine is mock_rag_engine
         assert service_instance_under_test.file_service is mock_file_service
         # If __init__ doesn't assign, uncomment these:
         # service_instance_under_test.rag_engine = mock_rag_engine
         # service_instance_under_test.file_service = mock_file_service

    # Call the method
    answer, source_nodes = await service_instance_under_test.query_project(project_id, query_text)

    # Assertions
    assert answer == mock_answer
    assert source_nodes == mock_source_nodes

    # Verify mocks
    expected_file_calls = [call(project_id, "plan.md"), call(project_id, "synopsis.md")]
    mock_file_service.read_content_block_file.assert_has_calls(expected_file_calls, any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id, query_text=query_text, explicit_plan="Error loading plan.", explicit_synopsis="Synopsis is available."
    )


@pytest.mark.asyncio
async def test_query_project_rag_engine_error():
    """Test query_project when the rag_engine itself raises an error."""
    project_id = "test-proj-uuid-4"
    query_text = "This query will fail."
    mock_plan_content = "Plan exists."
    mock_synopsis_content = "Synopsis exists."

    # Create mock instances
    mock_file_service = MagicMock(spec=FileService)
    mock_rag_engine = MagicMock(spec=RagEngine)

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
         if p_id == project_id:
             if block_name == "plan.md": return mock_plan_content
             if block_name == "synopsis.md": return mock_synopsis_content
         pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_rag_engine.query = AsyncMock(side_effect=RuntimeError("LLM API failed"))

    # Instantiate AIService with mocks (using patch context for __init__)
    with patch('app.services.ai_service.rag_engine', mock_rag_engine), \
         patch('app.services.ai_service.file_service', mock_file_service):
         service_instance_under_test = AIService()
         assert service_instance_under_test.rag_engine is mock_rag_engine
         assert service_instance_under_test.file_service is mock_file_service
         # If __init__ doesn't assign, uncomment these:
         # service_instance_under_test.rag_engine = mock_rag_engine
         # service_instance_under_test.file_service = mock_file_service

    # Call the method and expect the error
    with pytest.raises(RuntimeError, match="LLM API failed"):
        await service_instance_under_test.query_project(project_id, query_text)

    # Verify mocks
    expected_file_calls = [call(project_id, "plan.md"), call(project_id, "synopsis.md")]
    mock_file_service.read_content_block_file.assert_has_calls(expected_file_calls, any_order=True)
    assert mock_file_service.read_content_block_file.call_count == 2
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id, query_text=query_text, explicit_plan=mock_plan_content, explicit_synopsis=mock_synopsis_content
    )

# TODO: Add tests for generate_scene_draft
# TODO: Add tests for rephrase_text