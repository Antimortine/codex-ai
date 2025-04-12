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
from unittest.mock import patch, MagicMock
from fastapi import HTTPException, status, Depends, Path # Import Path and Depends
from pathlib import Path as FilePath # Import Path from pathlib AS FilePath to avoid name clash

# Import the FastAPI app instance
from app.main import app
# Import the service instance *used by the endpoint module* to mock it
from app.services.chapter_service import chapter_service
from app.services.file_service import file_service
# Import the service instance *used by the dependency* to mock it
from app.services.project_service import project_service as project_service_for_dependency
# Import models for type checking and response validation
from app.models.chapter import ChapterRead, ChapterList, ChapterCreate, ChapterUpdate
from app.models.content_block import ContentBlockRead, ContentBlockUpdate
from app.models.project import ProjectRead # Needed for mocking project dependency
from app.models.common import Message
# --- ADDED: Import the actual dependency function to override ---
from app.api.v1.endpoints.scenes import get_chapter_dependency
# --- END ADDED ---

# Create a TestClient instance
client = TestClient(app)

# --- Constants for Testing ---
PROJECT_ID = "test-project-chapters"
CHAPTER_ID_1 = "chap-id-1"
CHAPTER_ID_2 = "chap-id-2"
NON_EXISTENT_PROJECT_ID = "project-404"
NON_EXISTENT_CHAPTER_ID = "chapter-404"
CHAPTER_PLAN_CONTENT = "# Chapter Plan\n\n- Outline point 1"
CHAPTER_SYNOPSIS_CONTENT = "This chapter is about..."
UPDATED_CONTENT = "Updated chapter block content."

# --- Mock Dependency Helper ---
def mock_project_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id', args[0] if args else PROJECT_ID)
    if project_id_arg == NON_EXISTENT_PROJECT_ID:
         raise HTTPException(status_code=404, detail=f"Project {project_id_arg} not found")
    # Return a simple object or dict mimicking ProjectRead enough for the check
    return {'id': project_id_arg, 'name': f"Mock Project {project_id_arg}"}

# --- Mock Chapter Dependency Implementation ---
# This function will replace the real dependency during tests
# It needs to be async because the real dependency is async
async def override_get_chapter_dependency(project_id: str = Path(...), chapter_id: str = Path(...)):
    # Simulate the dependency's logic using our constants
    # Check project existence (simulated)
    if project_id == NON_EXISTENT_PROJECT_ID:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    # Check chapter existence (simulated)
    if chapter_id == NON_EXISTENT_CHAPTER_ID:
        raise HTTPException(status_code=404, detail=f"Chapter {chapter_id} not found in project {project_id}")
    # If checks pass, return the IDs
    return project_id, chapter_id
# --- END Mock Chapter Dependency Implementation ---


# --- Test Chapter API Endpoints ---
# (Existing tests unchanged - Omitted for brevity)
@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_create_chapter_success(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test successful chapter creation."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    chapter_data_in = {"title": "The First Chapter", "order": 1}
    mock_created_chapter = ChapterRead(
        id=CHAPTER_ID_1,
        project_id=PROJECT_ID,
        title=chapter_data_in["title"],
        order=chapter_data_in["order"]
    )
    mock_chapter_service.create.return_value = mock_created_chapter

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/", json=chapter_data_in)

    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["id"] == CHAPTER_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["title"] == chapter_data_in["title"]
    assert response_data["order"] == chapter_data_in["order"]
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.create.assert_called_once()
    call_args, call_kwargs = mock_chapter_service.create.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert isinstance(call_kwargs['chapter_in'], ChapterCreate)
    assert call_kwargs['chapter_in'].title == chapter_data_in['title']
    assert call_kwargs['chapter_in'].order == chapter_data_in['order']

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_create_chapter_order_conflict(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test chapter creation with an order conflict (409)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    chapter_data_in = {"title": "Conflict Chapter", "order": 1}
    error_detail = "Chapter order 1 already exists"
    mock_chapter_service.create.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=error_detail
    )

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/", json=chapter_data_in)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": error_detail}
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.create.assert_called_once() # Service was called

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_create_chapter_validation_error(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test chapter creation with invalid data (e.g., empty title)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    invalid_data = {"title": "", "order": 1} # Empty title is invalid

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/", json=invalid_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert response_data['detail'][0]['type'] == 'string_too_short'
    assert response_data['detail'][0]['loc'] == ['body', 'title']
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID) # Dependency is still checked
    mock_chapter_service.create.assert_not_called()

# --- List Chapters ---

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_list_chapters_empty(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test listing chapters when none exist."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    mock_chapter_service.get_all_for_project.return_value = ChapterList(chapters=[])

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "chapters" in response_data
    assert isinstance(response_data["chapters"], list)
    assert len(response_data["chapters"]) == 0
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.get_all_for_project.assert_called_once_with(project_id=PROJECT_ID)

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_list_chapters_with_data(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test listing chapters when some exist."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    chap1 = ChapterRead(id=CHAPTER_ID_1, project_id=PROJECT_ID, title="Ch 1", order=1)
    chap2 = ChapterRead(id=CHAPTER_ID_2, project_id=PROJECT_ID, title="Ch 2", order=2)
    mock_chapter_service.get_all_for_project.return_value = ChapterList(chapters=[chap1, chap2])

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "chapters" in response_data
    assert isinstance(response_data["chapters"], list)
    assert len(response_data["chapters"]) == 2
    assert response_data["chapters"][0]["id"] == CHAPTER_ID_1
    assert response_data["chapters"][0]["project_id"] == PROJECT_ID
    assert response_data["chapters"][0]["title"] == "Ch 1"
    assert response_data["chapters"][0]["order"] == 1
    assert response_data["chapters"][1]["id"] == CHAPTER_ID_2
    assert response_data["chapters"][1]["project_id"] == PROJECT_ID
    assert response_data["chapters"][1]["title"] == "Ch 2"
    assert response_data["chapters"][1]["order"] == 2
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.get_all_for_project.assert_called_once_with(project_id=PROJECT_ID)

# --- Get Chapter by ID ---

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Mock for dependency
def test_get_chapter_success(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test successfully getting a chapter by ID."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists # Project exists
    mock_chapter = ChapterRead(id=CHAPTER_ID_1, project_id=PROJECT_ID, title="Found Chapter", order=1)
    mock_chapter_service.get_by_id.return_value = mock_chapter # Chapter exists

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == CHAPTER_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["title"] == "Found Chapter"
    assert response_data["order"] == 1
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID) # Dependency check
    mock_chapter_service.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID_1)

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Mock for dependency
def test_get_chapter_not_found(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test getting a chapter that does not exist (404)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists # Project exists
    error_detail = f"Chapter {NON_EXISTENT_CHAPTER_ID} not found in project {PROJECT_ID}"
    mock_chapter_service.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail
    )

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{NON_EXISTENT_CHAPTER_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=NON_EXISTENT_CHAPTER_ID)

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Mock for dependency
def test_get_chapter_project_not_found(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test getting a chapter when the project does not exist (404 from dependency)."""
    error_detail = f"Project {NON_EXISTENT_PROJECT_ID} not found"
    mock_project_service_dep.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail
    )

    response = client.get(f"/api/v1/projects/{NON_EXISTENT_PROJECT_ID}/chapters/{CHAPTER_ID_1}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=NON_EXISTENT_PROJECT_ID)
    mock_chapter_service.get_by_id.assert_not_called() # Chapter service not reached

# --- Update Chapter ---

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Mock for dependency
def test_update_chapter_success(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test successfully updating a chapter."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    update_data = {"title": "Updated Chapter Title", "order": 5}
    mock_updated_chapter = ChapterRead(
        id=CHAPTER_ID_1,
        project_id=PROJECT_ID,
        title=update_data["title"],
        order=update_data["order"]
    )
    mock_chapter_service.update.return_value = mock_updated_chapter

    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}", json=update_data)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == CHAPTER_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["title"] == update_data["title"]
    assert response_data["order"] == update_data["order"]
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.update.assert_called_once()
    call_args, call_kwargs = mock_chapter_service.update.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert call_kwargs['chapter_id'] == CHAPTER_ID_1
    assert isinstance(call_kwargs['chapter_in'], ChapterUpdate)
    assert call_kwargs['chapter_in'].title == update_data['title']
    assert call_kwargs['chapter_in'].order == update_data['order']

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Mock for dependency
def test_update_chapter_not_found(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test updating a chapter that does not exist (404)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    update_data = {"title": "Doesn't Matter"}
    error_detail = f"Chapter {NON_EXISTENT_CHAPTER_ID} not found"
    mock_chapter_service.update.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail
    )

    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{NON_EXISTENT_CHAPTER_ID}", json=update_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.update.assert_called_once() # Service method is still called

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Mock for dependency
def test_update_chapter_order_conflict(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test updating a chapter causing an order conflict (409)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    update_data = {"order": 2} # Assume order 2 already exists
    error_detail = "Chapter order 2 already exists"
    mock_chapter_service.update.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=error_detail
    )

    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}", json=update_data)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": error_detail}
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.update.assert_called_once()

# --- Delete Chapter ---

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Mock for dependency
def test_delete_chapter_success(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test successfully deleting a chapter."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    mock_chapter_service.delete.return_value = None # Delete returns None

    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "message" in response_data
    assert response_data["message"] == f"Chapter {CHAPTER_ID_1} deleted successfully"
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.delete.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID_1)

@patch('app.api.v1.endpoints.chapters.chapter_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Mock for dependency
def test_delete_chapter_not_found(mock_project_service_dep: MagicMock, mock_chapter_service: MagicMock):
    """Test deleting a chapter that does not exist (404)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    error_detail = f"Chapter {NON_EXISTENT_CHAPTER_ID} not found"
    mock_chapter_service.delete.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail
    )

    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/chapters/{NON_EXISTENT_CHAPTER_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_chapter_service.delete.assert_called_once_with(project_id=PROJECT_ID, chapter_id=NON_EXISTENT_CHAPTER_ID)


# --- ADDED: Tests for Chapter Plan/Synopsis Endpoints ---

# === GET Chapter Plan ===
@patch('app.api.v1.endpoints.chapters.file_service', autospec=True)
def test_get_chapter_plan_success(mock_file_svc: MagicMock):
    """Test successful GET for chapter plan."""
    # Override the dependency for this test
    app.dependency_overrides[get_chapter_dependency] = override_get_chapter_dependency
    mock_file_svc.read_chapter_plan_file.return_value = CHAPTER_PLAN_CONTENT

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}/plan")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == CHAPTER_PLAN_CONTENT
    mock_file_svc.read_chapter_plan_file.assert_called_once_with(PROJECT_ID, CHAPTER_ID_1)
    app.dependency_overrides = {} # Clear overrides after test

@patch('app.api.v1.endpoints.chapters.file_service', autospec=True)
def test_get_chapter_plan_not_found(mock_file_svc: MagicMock):
    """Test GET chapter plan when file doesn't exist (returns empty)."""
    app.dependency_overrides[get_chapter_dependency] = override_get_chapter_dependency
    mock_file_svc.read_chapter_plan_file.return_value = None # Service returns None

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}/plan")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == "" # Endpoint returns empty string
    mock_file_svc.read_chapter_plan_file.assert_called_once_with(PROJECT_ID, CHAPTER_ID_1)
    app.dependency_overrides = {}

# === PUT Chapter Plan ===
@patch('app.api.v1.endpoints.chapters.file_service', autospec=True)
def test_update_chapter_plan_success(mock_file_svc: MagicMock):
    """Test successful PUT update for chapter plan."""
    app.dependency_overrides[get_chapter_dependency] = override_get_chapter_dependency
    mock_file_svc.write_chapter_plan_file.return_value = None
    update_data = {"content": UPDATED_CONTENT}

    response = client.put(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}/plan", json=update_data)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == UPDATED_CONTENT
    mock_file_svc.write_chapter_plan_file.assert_called_once_with(PROJECT_ID, CHAPTER_ID_1, UPDATED_CONTENT)
    app.dependency_overrides = {}

# === GET Chapter Synopsis ===
@patch('app.api.v1.endpoints.chapters.file_service', autospec=True)
def test_get_chapter_synopsis_success(mock_file_svc: MagicMock):
    """Test successful GET for chapter synopsis."""
    app.dependency_overrides[get_chapter_dependency] = override_get_chapter_dependency
    mock_file_svc.read_chapter_synopsis_file.return_value = CHAPTER_SYNOPSIS_CONTENT

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}/synopsis")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == CHAPTER_SYNOPSIS_CONTENT
    mock_file_svc.read_chapter_synopsis_file.assert_called_once_with(PROJECT_ID, CHAPTER_ID_1)
    app.dependency_overrides = {}

@patch('app.api.v1.endpoints.chapters.file_service', autospec=True)
def test_get_chapter_synopsis_not_found(mock_file_svc: MagicMock):
    """Test GET chapter synopsis when file doesn't exist (returns empty)."""
    app.dependency_overrides[get_chapter_dependency] = override_get_chapter_dependency
    mock_file_svc.read_chapter_synopsis_file.return_value = None # Service returns None

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}/synopsis")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == "" # Endpoint returns empty string
    mock_file_svc.read_chapter_synopsis_file.assert_called_once_with(PROJECT_ID, CHAPTER_ID_1)
    app.dependency_overrides = {}

# === PUT Chapter Synopsis ===
@patch('app.api.v1.endpoints.chapters.file_service', autospec=True)
def test_update_chapter_synopsis_success(mock_file_svc: MagicMock):
    """Test successful PUT update for chapter synopsis."""
    app.dependency_overrides[get_chapter_dependency] = override_get_chapter_dependency
    mock_file_svc.write_chapter_synopsis_file.return_value = None
    update_data = {"content": UPDATED_CONTENT}

    response = client.put(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID_1}/synopsis", json=update_data)

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == UPDATED_CONTENT
    mock_file_svc.write_chapter_synopsis_file.assert_called_once_with(PROJECT_ID, CHAPTER_ID_1, UPDATED_CONTENT)
    app.dependency_overrides = {}

# === Test Dependency Failure for Chapter Plan/Synopsis ===
@patch('app.api.v1.endpoints.chapters.file_service', autospec=True)
def test_get_chapter_plan_chapter_not_found(mock_file_svc: MagicMock):
    """Test GET chapter plan when chapter dependency fails."""
    error_detail = f"Chapter {NON_EXISTENT_CHAPTER_ID} not found in project {PROJECT_ID}"
    # Override the dependency to raise 404
    app.dependency_overrides[get_chapter_dependency] = lambda: (_ for _ in ()).throw(HTTPException(status_code=404, detail=error_detail))

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{NON_EXISTENT_CHAPTER_ID}/plan")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail} # Should now match the chapter error
    mock_file_svc.read_chapter_plan_file.assert_not_called()
    app.dependency_overrides = {} # Clear override

@patch('app.api.v1.endpoints.chapters.file_service', autospec=True)
def test_update_chapter_plan_chapter_not_found(mock_file_svc: MagicMock):
    """Test PUT chapter plan when chapter dependency fails."""
    error_detail = f"Chapter {NON_EXISTENT_CHAPTER_ID} not found in project {PROJECT_ID}"
    app.dependency_overrides[get_chapter_dependency] = lambda: (_ for _ in ()).throw(HTTPException(status_code=404, detail=error_detail))
    update_data = {"content": UPDATED_CONTENT}

    response = client.put(f"/api/v1/projects/{PROJECT_ID}/chapters/{NON_EXISTENT_CHAPTER_ID}/plan", json=update_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail} # Should now match the chapter error
    mock_file_svc.write_chapter_plan_file.assert_not_called()
    app.dependency_overrides = {} # Clear override

# --- END ADDED ---