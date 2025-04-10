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
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi import HTTPException, status
from pathlib import Path # Import Path
from typing import List, Optional, Dict # Import List, Optional, Dict

# Import the FastAPI app instance
from app.main import app
# Import the service instance *used by the endpoint module* to mock it
from app.services.ai_service import ai_service
# Import services *used by dependencies* to mock them
from app.services.project_service import project_service as project_service_for_dependency
from app.services.chapter_service import chapter_service as chapter_service_for_dependency
# Import models for type checking and response validation
from app.models.ai import (
    AIQueryRequest, AIQueryResponse, SourceNodeModel,
    AISceneGenerationRequest, AISceneGenerationResponse,
    AIRephraseRequest, AIRephraseResponse,
    AIChapterSplitRequest, AIChapterSplitResponse, ProposedScene
)
from app.models.common import Message
from app.models.project import ProjectRead
from app.models.chapter import ChapterRead
# Import LlamaIndex types for mocking service return values
from llama_index.core.schema import NodeWithScore, TextNode

# Create a TestClient instance
client = TestClient(app)

# --- Constants for Testing ---
PROJECT_ID = "test-project-ai"
CHAPTER_ID = "test-chapter-ai"
NON_EXISTENT_PROJECT_ID = "project-404"
NON_EXISTENT_CHAPTER_ID = "chapter-404"

# --- Mock Dependency Helpers ---
def mock_project_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id', args[0] if args else PROJECT_ID)
    if project_id_arg == NON_EXISTENT_PROJECT_ID:
         raise HTTPException(status_code=404, detail=f"Project {project_id_arg} not found")
    return ProjectRead(id=project_id_arg, name=f"Mock Project {project_id_arg}")

def mock_chapter_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id')
    chapter_id_arg = kwargs.get('chapter_id')
    if chapter_id_arg == NON_EXISTENT_CHAPTER_ID:
         raise HTTPException(status_code=404, detail=f"Chapter {chapter_id_arg} not found in project {project_id_arg}")
    # Assume project exists if chapter check is reached
    return ChapterRead(id=chapter_id_arg, project_id=project_id_arg, title=f"Mock Chapter {chapter_id_arg}", order=1)

# --- Test AI Query Endpoint ---
@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_query_project_success(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    query_data = {"query": "What is the plan?"}
    mock_answer = "The plan is to succeed."
    # --- MODIFIED: Expect filtered nodes ---
    # Example: Assume node1 (plan.md) is filtered out by the service
    mock_node_scene = NodeWithScore(node=TextNode(id_='n2', text="Source 2", metadata={'file_path': 'scenes/s1.md'}), score=0.8)
    mock_filtered_nodes = [mock_node_scene]
    # --- END MODIFIED ---
    mock_direct_sources_info = [{"type": "Plan", "name": "Project Plan"}] # Now a list
    # --- MODIFIED: Mock service returns filtered nodes ---
    mock_ai_svc.query_project = AsyncMock(return_value=(mock_answer, mock_filtered_nodes, mock_direct_sources_info))
    # --- END MODIFIED ---
    response = client.post(f"/api/v1/ai/query/{PROJECT_ID}", json=query_data)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["answer"] == mock_answer
    # --- MODIFIED: Assert based on filtered nodes ---
    assert len(response_data["source_nodes"]) == 1
    assert response_data["source_nodes"][0]["id"] == "n2"
    assert response_data["source_nodes"][0]["text"] == "Source 2"
    assert response_data["source_nodes"][0]["metadata"]["file_path"] == 'scenes/s1.md'
    # --- END MODIFIED ---
    assert response_data["direct_sources"] == mock_direct_sources_info

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_query_project_no_sources(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    query_data = {"query": "Anything about dragons?"}
    mock_answer = "No mention of dragons found."
    # Mock service returns 3-tuple (with empty list for nodes and None for direct sources)
    mock_ai_svc.query_project = AsyncMock(return_value=(mock_answer, [], None))
    response = client.post(f"/api/v1/ai/query/{PROJECT_ID}", json=query_data)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["answer"] == mock_answer
    assert response_data["source_nodes"] == [] # Expect empty list
    assert response_data["direct_sources"] is None

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_query_project_service_error(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    # (Unchanged)
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    query_data = {"query": "This will fail"}
    error_detail = "AI service failed"
    mock_ai_svc.query_project = AsyncMock(side_effect=HTTPException(status_code=500, detail=error_detail))
    response = client.post(f"/api/v1/ai/query/{PROJECT_ID}", json=query_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_detail}

# --- Test AI Scene Generation Endpoint ---
# (Unchanged)
@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_generate_scene_success(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    gen_data = {"prompt_summary": "A tense meeting", "previous_scene_order": 1}
    mock_generated_title = "The Meeting"
    mock_generated_content = "## The Meeting\nThe characters met under the pale moonlight."
    mock_service_return = {"title": mock_generated_title, "content": mock_generated_content}
    mock_ai_svc.generate_scene_draft = AsyncMock(return_value=mock_service_return)
    response = client.post(f"/api/v1/ai/generate/scene/{PROJECT_ID}/{CHAPTER_ID}", json=gen_data)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["title"] == mock_generated_title
    assert response_data["content"] == mock_generated_content

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_generate_scene_service_error(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    gen_data = {"prompt_summary": "This generation fails"}
    error_detail = "Failed to generate scene draft: Generation failed due to policy."
    mock_ai_svc.generate_scene_draft = AsyncMock(side_effect=HTTPException(status_code=500, detail=error_detail))
    response = client.post(f"/api/v1/ai/generate/scene/{PROJECT_ID}/{CHAPTER_ID}", json=gen_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_detail}

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_generate_scene_service_exception(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    gen_data = {"prompt_summary": "This generation fails"}
    mock_ai_svc.generate_scene_draft = AsyncMock(side_effect=ValueError("Unexpected service error"))
    response = client.post(f"/api/v1/ai/generate/scene/{PROJECT_ID}/{CHAPTER_ID}", json=gen_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert f"Failed to process AI scene generation for project {PROJECT_ID}, chapter {CHAPTER_ID}" in response.json()["detail"]

# --- Test AI Rephrase Endpoint ---
# (Unchanged)
@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rephrase_text_success(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    rephrase_data = {"selected_text": "The old house stood."}
    mock_suggestions = ["The ancient house remained."]
    mock_ai_svc.rephrase_text = AsyncMock(return_value=mock_suggestions)
    response = client.post(f"/api/v1/ai/edit/rephrase/{PROJECT_ID}", json=rephrase_data)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["suggestions"] == mock_suggestions

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rephrase_text_service_error(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    rephrase_data = {"selected_text": "This rephrase fails"}
    error_detail = "Failed to rephrase text: Rephrasing blocked by filter."
    mock_ai_svc.rephrase_text = AsyncMock(side_effect=HTTPException(status_code=500, detail=error_detail))
    response = client.post(f"/api/v1/ai/edit/rephrase/{PROJECT_ID}", json=rephrase_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_detail}

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rephrase_text_service_exception(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    rephrase_data = {"selected_text": "This rephrase fails"}
    mock_ai_svc.rephrase_text = AsyncMock(side_effect=TypeError("Unexpected argument"))
    response = client.post(f"/api/v1/ai/edit/rephrase/{PROJECT_ID}", json=rephrase_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert f"Failed to process AI rephrase request for project {PROJECT_ID}" in response.json()["detail"]


# --- Test AI Chapter Split Endpoint ---
# (Unchanged)
@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_split_chapter_success(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    split_request_data = {"chapter_content": "First part. Second part."}
    mock_proposed = [ProposedScene(suggested_title="Part 1", content="First part.")]
    mock_ai_svc.split_chapter_into_scenes = AsyncMock(return_value=mock_proposed)
    response = client.post(f"/api/v1/ai/split/chapter/{PROJECT_ID}/{CHAPTER_ID}", json=split_request_data)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert len(response_data["proposed_scenes"]) == 1

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_split_chapter_validation_error(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    invalid_split_request_data = {}
    response = client.post(f"/api/v1/ai/split/chapter/{PROJECT_ID}/{CHAPTER_ID}", json=invalid_split_request_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_split_chapter_service_error(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    split_request_data = {"chapter_content": "Content"}
    error_detail = "AI splitting failed due to internal error."
    mock_ai_svc.split_chapter_into_scenes = AsyncMock(side_effect=HTTPException(status_code=500, detail=error_detail))
    response = client.post(f"/api/v1/ai/split/chapter/{PROJECT_ID}/{CHAPTER_ID}", json=split_request_data)
    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_detail}

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_split_chapter_dependency_error(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    error_detail = f"Chapter {NON_EXISTENT_CHAPTER_ID} not found in project {PROJECT_ID}"
    mock_chapter_dep.get_by_id.side_effect = HTTPException(status_code=404, detail=error_detail)
    split_request_data = {"chapter_content": "Content"}
    response = client.post(f"/api/v1/ai/split/chapter/{PROJECT_ID}/{NON_EXISTENT_CHAPTER_ID}", json=split_request_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}


# --- Tests for Rebuild Index Endpoint ---
@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rebuild_index_success(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test successful index rebuild initiation."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_ai_svc.rebuild_project_index = AsyncMock(return_value=None) # AsyncMock for async endpoint

    response = client.post(f"/api/v1/ai/rebuild_index/{PROJECT_ID}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Index rebuild initiated for project {PROJECT_ID}."}
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_ai_svc.rebuild_project_index.assert_awaited_once_with(project_id=PROJECT_ID)

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rebuild_index_project_not_found(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test index rebuild when project is not found (404 from dependency)."""
    error_detail = f"Project {NON_EXISTENT_PROJECT_ID} not found"
    mock_project_dep.get_by_id.side_effect = HTTPException(status_code=404, detail=error_detail)

    response = client.post(f"/api/v1/ai/rebuild_index/{NON_EXISTENT_PROJECT_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_project_dep.get_by_id.assert_called_once_with(project_id=NON_EXISTENT_PROJECT_ID)
    mock_ai_svc.rebuild_project_index.assert_not_awaited()

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rebuild_index_service_error(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test index rebuild when the service raises an error."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    error_detail = "Failed to process index rebuild due to an internal error."
    mock_ai_svc.rebuild_project_index = AsyncMock(side_effect=HTTPException(status_code=500, detail=error_detail))

    response = client.post(f"/api/v1/ai/rebuild_index/{PROJECT_ID}")

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_detail}
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_ai_svc.rebuild_project_index.assert_awaited_once_with(project_id=PROJECT_ID)
# --- END ADDED ---