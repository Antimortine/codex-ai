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
from fastapi import HTTPException, status

# Import the FastAPI app instance
from app.main import app
# Import the service instance *used by the endpoint module* to mock it
from app.services.chapter_service import chapter_service
# Import the service instance *used by the dependency* to mock it
from app.services.project_service import project_service as project_service_for_dependency
# Import models for type checking and response validation
from app.models.chapter import ChapterRead, ChapterList, ChapterCreate, ChapterUpdate
from app.models.project import ProjectRead # Needed for mocking project dependency
from app.models.common import Message

# Create a TestClient instance
client = TestClient(app)

# --- Constants for Testing ---
PROJECT_ID = "test-project-chapters"
CHAPTER_ID_1 = "chap-id-1"
CHAPTER_ID_2 = "chap-id-2"
NON_EXISTENT_PROJECT_ID = "project-404"
NON_EXISTENT_CHAPTER_ID = "chapter-404"

# --- Mock Dependency Helper ---
def mock_project_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id', args[0] if args else PROJECT_ID)
    if project_id_arg == NON_EXISTENT_PROJECT_ID:
         raise HTTPException(status_code=404, detail=f"Project {project_id_arg} not found")
    return ProjectRead(id=project_id_arg, name=f"Mock Project {project_id_arg}")

# --- Test Chapter API Endpoints ---

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
    # Assert specific fields
    response_data = response.json()
    assert response_data["id"] == CHAPTER_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["title"] == chapter_data_in["title"]
    assert response_data["order"] == chapter_data_in["order"]
    # Verify dependency check
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    # Verify service call arguments
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
    # Check specific Pydantic v2 error structure
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
    # Assert structure
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
    # Assert specific fields for each chapter
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
    # Assert specific fields
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
    # Make the *chapter* service raise the 404
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
    # Make the *project* service raise the 404 within the dependency check
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
    # Assert specific fields
    response_data = response.json()
    assert response_data["id"] == CHAPTER_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["title"] == update_data["title"]
    assert response_data["order"] == update_data["order"]
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    # Verify service call arguments
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
    # Assert specific message field
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