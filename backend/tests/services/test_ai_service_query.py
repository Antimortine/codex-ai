# Copyright 2025 Antimortine
# ... (imports remain the same) ...
import pytest
from unittest.mock import MagicMock, AsyncMock, call, patch
from fastapi import HTTPException, status
from pathlib import Path
import asyncio
from typing import Dict, Optional, List

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
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Source text 1", metadata={'file_path': 'plan.md'}), score=0.9)
    mock_node2 = NodeWithScore(node=TextNode(id_='n2', text="Source text 2", metadata={'file_path': 'scenes/s1.md'}), score=0.8)
    mock_source_nodes = [mock_node1, mock_node2]
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = None

    # Configure mocks (using the args from the patch decorators)
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": return mock_plan_content
            if block_name == "synopsis.md": return mock_synopsis_content
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_content_block_path.side_effect = lambda pid, fname: Path(f"user_projects/{pid}/{fname}")
    mock_file_service._get_project_path.return_value = Path(f"user_projects/{project_id}")
    mock_file_service.path_exists.return_value = False

    mock_rag_engine.query = AsyncMock(return_value=(mock_answer, mock_source_nodes, mock_direct_sources_info))

    # Instantiate AIService (it will use the patched instances)
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
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id,
        query_text=query_text,
        explicit_plan=mock_plan_content,
        explicit_synopsis=mock_synopsis_content,
        direct_sources_data=[],
        paths_to_filter={'user_projects\\test-proj-uuid\\plan.md', 'user_projects\\test-proj-uuid\\synopsis.md'} # Check filter paths
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
    mock_source_nodes = []
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = None

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
            elif block_name == "synopsis.md": return "Synopsis content exists."
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_content_block_path.side_effect = lambda pid, fname: Path(f"user_projects/{pid}/{fname}")
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
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id,
        query_text=query_text,
        explicit_plan="",
        explicit_synopsis="Synopsis content exists.",
        direct_sources_data=[],
        paths_to_filter={'user_projects\\test-proj-uuid-2\\synopsis.md'} # Only synopsis path added
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
    mock_source_nodes = []
    mock_direct_sources_info: Optional[List[Dict[str, str]]] = None

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
        if p_id == project_id:
            if block_name == "plan.md": raise ValueError("Unexpected file system issue")
            elif block_name == "synopsis.md": return "Synopsis is available."
        pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_content_block_path.side_effect = lambda pid, fname: Path(f"user_projects/{pid}/{fname}")
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
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id,
        query_text=query_text,
        explicit_plan="Error loading plan.",
        explicit_synopsis="Synopsis is available.",
        direct_sources_data=[],
        paths_to_filter={'user_projects\\test-proj-uuid-3\\synopsis.md'} # Only synopsis path added
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

    # Configure mocks
    def file_read_side_effect(p_id, block_name):
         if p_id == project_id:
             if block_name == "plan.md": return mock_plan_content
             if block_name == "synopsis.md": return mock_synopsis_content
         pytest.fail(f"Unexpected call to read_content_block_file: {p_id}, {block_name}")
    mock_file_service.read_content_block_file.side_effect = file_read_side_effect
    mock_file_service.read_project_metadata.return_value = {"chapters": {}, "characters": {}}
    mock_file_service._get_content_block_path.side_effect = lambda pid, fname: Path(f"user_projects/{pid}/{fname}")
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
    mock_rag_engine.query.assert_awaited_once_with(
        project_id=project_id,
        query_text=query_text,
        explicit_plan=mock_plan_content,
        explicit_synopsis=mock_synopsis_content,
        direct_sources_data=[],
        paths_to_filter={'user_projects\\test-proj-uuid-4\\plan.md', 'user_projects\\test-proj-uuid-4\\synopsis.md'} # Check filter paths
    )