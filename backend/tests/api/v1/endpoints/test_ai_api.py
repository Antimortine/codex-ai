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
from unittest.mock import patch, MagicMock, AsyncMock # Use AsyncMock for async service methods
from fastapi import HTTPException, status

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
    AIRephraseRequest, AIRephraseResponse
)
from app.models.project import ProjectRead # Needed for mocking project dependency
from app.models.chapter import ChapterRead # Needed for mocking chapter dependency
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
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Dependency for query/rephrase
def test_query_project_success(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test successful AI query."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    query_data = {"query": "What is the plan?"}
    mock_answer = "The plan is to succeed."
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Source 1", metadata={'file_path': 'plan.md'}), score=0.9)
    mock_node2 = NodeWithScore(node=TextNode(id_='n2', text="Source 2", metadata={'file_path': 'scenes/s1.md'}), score=0.8)
    mock_ai_svc.query_project = AsyncMock(return_value=(mock_answer, [mock_node1, mock_node2]))

    response = client.post(f"/api/v1/ai/query/{PROJECT_ID}", json=query_data)

    assert response.status_code == status.HTTP_200_OK
    # Assert specific response structure and fields
    response_data = response.json()
    assert "answer" in response_data
    assert response_data["answer"] == mock_answer
    assert "source_nodes" in response_data
    assert isinstance(response_data["source_nodes"], list)
    assert len(response_data["source_nodes"]) == 2
    # Assert specific fields within source nodes
    assert response_data["source_nodes"][0]["id"] == "n1"
    assert response_data["source_nodes"][0]["text"] == "Source 1"
    assert response_data["source_nodes"][0]["score"] == 0.9
    assert response_data["source_nodes"][0]["metadata"]["file_path"] == "plan.md"
    assert response_data["source_nodes"][1]["id"] == "n2"
    assert response_data["source_nodes"][1]["text"] == "Source 2"
    assert response_data["source_nodes"][1]["score"] == 0.8
    assert response_data["source_nodes"][1]["metadata"]["file_path"] == "scenes/s1.md"
    # Verify dependency and service calls
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_ai_svc.query_project.assert_awaited_once_with(PROJECT_ID, query_data["query"])

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_query_project_no_sources(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test AI query returning no source nodes."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    query_data = {"query": "Anything about dragons?"}
    mock_answer = "No mention of dragons found."
    mock_ai_svc.query_project = AsyncMock(return_value=(mock_answer, [])) # Empty list of nodes

    response = client.post(f"/api/v1/ai/query/{PROJECT_ID}", json=query_data)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "answer" in response_data
    assert response_data["answer"] == mock_answer
    assert "source_nodes" in response_data
    assert response_data["source_nodes"] == [] # Expect empty list
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_ai_svc.query_project.assert_awaited_once_with(PROJECT_ID, query_data["query"])

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_query_project_service_error(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test AI query when the AI service raises an error."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    query_data = {"query": "This will fail"}
    error_detail = "AI service failed"
    mock_ai_svc.query_project = AsyncMock(side_effect=HTTPException(status_code=500, detail=error_detail))

    response = client.post(f"/api/v1/ai/query/{PROJECT_ID}", json=query_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # Assert exact error detail passed through from service
    assert response.json() == {"detail": error_detail}
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_ai_svc.query_project.assert_awaited_once_with(PROJECT_ID, query_data["query"])

# --- Test AI Scene Generation Endpoint ---

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True) # Dependency for generate
def test_generate_scene_success(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test successful AI scene generation."""
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    gen_data = {"prompt_summary": "A tense meeting", "previous_scene_order": 1}
    mock_generated_content = "## Scene 2\nThe characters met under the pale moonlight."
    mock_ai_svc.generate_scene_draft = AsyncMock(return_value=mock_generated_content)

    response = client.post(f"/api/v1/ai/generate/scene/{PROJECT_ID}/{CHAPTER_ID}", json=gen_data)

    assert response.status_code == status.HTTP_200_OK
    # Assert specific response field
    response_data = response.json()
    assert "generated_content" in response_data
    assert response_data["generated_content"] == mock_generated_content
    # Verify dependency check
    mock_chapter_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    # Verify service call arguments
    mock_ai_svc.generate_scene_draft.assert_awaited_once()
    call_args, call_kwargs = mock_ai_svc.generate_scene_draft.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert call_kwargs['chapter_id'] == CHAPTER_ID
    assert isinstance(call_kwargs['request_data'], AISceneGenerationRequest)
    assert call_kwargs['request_data'].prompt_summary == gen_data['prompt_summary']
    assert call_kwargs['request_data'].previous_scene_order == gen_data['previous_scene_order']


@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_generate_scene_service_error(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test AI scene generation when the AI service raises an HTTPException."""
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    gen_data = {"prompt_summary": "This generation fails"}
    error_detail = "Failed to generate scene draft: Generation failed due to policy."
    # Simulate service raising the HTTPException directly
    mock_ai_svc.generate_scene_draft = AsyncMock(side_effect=HTTPException(status_code=500, detail=error_detail))

    response = client.post(f"/api/v1/ai/generate/scene/{PROJECT_ID}/{CHAPTER_ID}", json=gen_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_detail} # Endpoint should pass the exception through
    mock_chapter_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_ai_svc.generate_scene_draft.assert_awaited_once()

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_generate_scene_service_exception(mock_chapter_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test AI scene generation when the AI service raises an unexpected exception."""
    mock_chapter_dep.get_by_id.side_effect = mock_chapter_exists
    gen_data = {"prompt_summary": "This generation fails"}
    mock_ai_svc.generate_scene_draft = AsyncMock(side_effect=ValueError("Unexpected service error")) # Non-HTTP error

    response = client.post(f"/api/v1/ai/generate/scene/{PROJECT_ID}/{CHAPTER_ID}", json=gen_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # Check the generic error message from the endpoint's exception handler
    assert f"Failed to process AI scene generation for project {PROJECT_ID}, chapter {CHAPTER_ID}" in response.json()["detail"]
    mock_chapter_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_ai_svc.generate_scene_draft.assert_awaited_once()

# --- Test AI Rephrase Endpoint ---

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Dependency for rephrase
def test_rephrase_text_success(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test successful AI text rephrasing."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    rephrase_data = {
        "selected_text": "The old house stood.",
        "context_before": "On the hill,",
        "context_after": "Silent and watchful."
    }
    mock_suggestions = [
        "The ancient house remained.",
        "The aged dwelling stood there.",
        "There stood the old house."
    ]
    mock_ai_svc.rephrase_text = AsyncMock(return_value=mock_suggestions)

    response = client.post(f"/api/v1/ai/edit/rephrase/{PROJECT_ID}", json=rephrase_data)

    assert response.status_code == status.HTTP_200_OK
    # Assert specific response field
    response_data = response.json()
    assert "suggestions" in response_data
    assert response_data["suggestions"] == mock_suggestions
    # Verify dependency check
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    # Verify service call arguments
    mock_ai_svc.rephrase_text.assert_awaited_once()
    call_args, call_kwargs = mock_ai_svc.rephrase_text.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert isinstance(call_kwargs['request_data'], AIRephraseRequest)
    assert call_kwargs['request_data'].selected_text == rephrase_data['selected_text']
    assert call_kwargs['request_data'].context_before == rephrase_data['context_before']
    assert call_kwargs['request_data'].context_after == rephrase_data['context_after']

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rephrase_text_service_error(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test AI rephrase when the AI service raises an HTTPException."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    rephrase_data = {"selected_text": "This rephrase fails"}
    error_detail = "Failed to rephrase text: Rephrasing blocked by filter."
    # Simulate service raising the HTTPException directly
    mock_ai_svc.rephrase_text = AsyncMock(side_effect=HTTPException(status_code=500, detail=error_detail))

    response = client.post(f"/api/v1/ai/edit/rephrase/{PROJECT_ID}", json=rephrase_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_detail} # Endpoint should pass the exception through
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_ai_svc.rephrase_text.assert_awaited_once()

@patch('app.api.v1.endpoints.ai.ai_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rephrase_text_service_exception(mock_project_dep: MagicMock, mock_ai_svc: MagicMock):
    """Test AI rephrase when the AI service raises an unexpected exception."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    rephrase_data = {"selected_text": "This rephrase fails"}
    mock_ai_svc.rephrase_text = AsyncMock(side_effect=TypeError("Unexpected argument")) # Non-HTTP error

    response = client.post(f"/api/v1/ai/edit/rephrase/{PROJECT_ID}", json=rephrase_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    # Check the generic error message from the endpoint's exception handler
    assert f"Failed to process AI rephrase request for project {PROJECT_ID}" in response.json()["detail"]
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_ai_svc.rephrase_text.assert_awaited_once()