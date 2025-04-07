
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
from app.services.scene_service import scene_service
# Import the service instance *used by the dependency* to mock it
from app.services.chapter_service import chapter_service as chapter_service_for_dependency
# Import models for type checking and response validation
from app.models.scene import SceneRead, SceneList, SceneCreate, SceneUpdate
from app.models.chapter import ChapterRead # Needed for mocking chapter dependency
from app.models.common import Message

# Create a TestClient instance
client = TestClient(app)

# --- Constants for Testing ---
PROJECT_ID = "test-project-scenes"
CHAPTER_ID = "test-chapter-scenes"
SCENE_ID_1 = "scene-id-1"
SCENE_ID_2 = "scene-id-2"
NON_EXISTENT_CHAPTER_ID = "chapter-404"
NON_EXISTENT_SCENE_ID = "scene-404"

# --- Mock Dependency Helper ---
# Mocks the chapter_service.get_by_id call used in the dependency
def mock_chapter_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id')
    chapter_id_arg = kwargs.get('chapter_id')
    # print(f"Mocking chapter_service.get_by_id called with project: {project_id_arg}, chapter: {chapter_id_arg}") # Debug
    if chapter_id_arg == NON_EXISTENT_CHAPTER_ID:
         raise HTTPException(status_code=404, detail=f"Chapter {chapter_id_arg} not found")
    # Simulate project check implicitly by not raising for project_id
    # print(f"Mock chapter_service: Returning mock chapter for ID {chapter_id_arg}") # Debug
    return ChapterRead(id=chapter_id_arg, project_id=project_id_arg, title=f"Mock Chapter {chapter_id_arg}", order=1)

# --- Test Scene API Endpoints ---

# Patch BOTH the scene_service (used by endpoint logic) AND
# the chapter_service (used by the dependency)
# Note: The target for chapter_service patch is where the dependency imports it from.
@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True) # Target dependency import
def test_create_scene_success(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test successful scene creation."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    scene_data_in = {"title": "Opening Scene", "order": 1, "content": "It begins..."}
    mock_created_scene = SceneRead(
        id=SCENE_ID_1,
        project_id=PROJECT_ID,
        chapter_id=CHAPTER_ID,
        title=scene_data_in["title"],
        order=scene_data_in["order"],
        content=scene_data_in["content"]
    )
    mock_scene_service.create.return_value = mock_created_scene

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/", json=scene_data_in)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == mock_created_scene.model_dump()
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.create.assert_called_once()
    call_args, call_kwargs = mock_scene_service.create.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert call_kwargs['chapter_id'] == CHAPTER_ID
    assert isinstance(call_kwargs['scene_in'], SceneCreate)
    assert call_kwargs['scene_in'].title == scene_data_in['title']
    assert call_kwargs['scene_in'].order == scene_data_in['order']
    assert call_kwargs['scene_in'].content == scene_data_in['content']

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_create_scene_order_conflict(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test scene creation with an order conflict (409)."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    scene_data_in = {"title": "Conflict Scene", "order": 1, "content": "..."}
    mock_scene_service.create.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Scene order 1 already exists"
    )

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/", json=scene_data_in)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "Scene order 1 already exists" in response.json()["detail"]
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.create.assert_called_once()

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_create_scene_chapter_not_found(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test scene creation when the chapter does not exist (404 from dependency)."""
    mock_chapter_service_dep.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Chapter {NON_EXISTENT_CHAPTER_ID} not found"
    )
    scene_data_in = {"title": "Lost Scene", "order": 1, "content": "..."}

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/{NON_EXISTENT_CHAPTER_ID}/scenes/", json=scene_data_in)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Chapter {NON_EXISTENT_CHAPTER_ID} not found" in response.json()["detail"]
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=NON_EXISTENT_CHAPTER_ID)
    mock_scene_service.create.assert_not_called()

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_create_scene_validation_error(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test scene creation with invalid data (e.g., negative order)."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    invalid_data = {"title": "Valid Title", "order": -1, "content": ""} # Invalid order

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/", json=invalid_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()['detail'][0]['type'] == 'greater_than_equal'
    assert response.json()['detail'][0]['loc'] == ['body', 'order']
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.create.assert_not_called()

# --- List Scenes ---

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_list_scenes_empty(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test listing scenes when none exist."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    mock_scene_service.get_all_for_chapter.return_value = SceneList(scenes=[])

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"scenes": []}
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.get_all_for_chapter.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_list_scenes_with_data(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test listing scenes when some exist."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    scene1 = SceneRead(id=SCENE_ID_1, project_id=PROJECT_ID, chapter_id=CHAPTER_ID, title="S1", order=1, content="C1")
    scene2 = SceneRead(id=SCENE_ID_2, project_id=PROJECT_ID, chapter_id=CHAPTER_ID, title="S2", order=2, content="C2")
    mock_scene_service.get_all_for_chapter.return_value = SceneList(scenes=[scene1, scene2])

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/")

    assert response.status_code == status.HTTP_200_OK
    expected_data = {
        "scenes": [
            scene1.model_dump(),
            scene2.model_dump()
        ]
    }
    assert response.json() == expected_data
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.get_all_for_chapter.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)

# --- Get Scene by ID ---

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_get_scene_success(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test successfully getting a scene by ID."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    mock_scene = SceneRead(id=SCENE_ID_1, project_id=PROJECT_ID, chapter_id=CHAPTER_ID, title="Found Scene", order=1, content="Found Content")
    mock_scene_service.get_by_id.return_value = mock_scene

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{SCENE_ID_1}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_scene.model_dump()
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID, scene_id=SCENE_ID_1)

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_get_scene_not_found(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test getting a scene that does not exist (404)."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    mock_scene_service.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Scene {NON_EXISTENT_SCENE_ID} not found"
    )

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{NON_EXISTENT_SCENE_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Scene {NON_EXISTENT_SCENE_ID} not found" in response.json()["detail"]
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID, scene_id=NON_EXISTENT_SCENE_ID)

# --- Update Scene ---

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_update_scene_success(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test successfully updating a scene."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    update_data = {"title": "Updated Scene Title", "content": "Updated content."}
    mock_updated_scene = SceneRead(
        id=SCENE_ID_1,
        project_id=PROJECT_ID,
        chapter_id=CHAPTER_ID,
        title=update_data["title"],
        order=1, # Assume order doesn't change
        content=update_data["content"]
    )
    mock_scene_service.update.return_value = mock_updated_scene

    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{SCENE_ID_1}", json=update_data)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_updated_scene.model_dump()
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.update.assert_called_once()
    call_args, call_kwargs = mock_scene_service.update.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert call_kwargs['chapter_id'] == CHAPTER_ID
    assert call_kwargs['scene_id'] == SCENE_ID_1
    assert isinstance(call_kwargs['scene_in'], SceneUpdate)
    assert call_kwargs['scene_in'].title == update_data['title']
    assert call_kwargs['scene_in'].content == update_data['content']

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_update_scene_not_found(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test updating a scene that does not exist (404)."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    update_data = {"title": "Doesn't Matter"}
    mock_scene_service.update.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Scene {NON_EXISTENT_SCENE_ID} not found"
    )

    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{NON_EXISTENT_SCENE_ID}", json=update_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Scene {NON_EXISTENT_SCENE_ID} not found" in response.json()["detail"]
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.update.assert_called_once()

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_update_scene_order_conflict(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test updating a scene causing an order conflict (409)."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    update_data = {"order": 2} # Assume order 2 already exists
    mock_scene_service.update.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail="Scene order 2 already exists"
    )

    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{SCENE_ID_1}", json=update_data)

    assert response.status_code == status.HTTP_409_CONFLICT
    assert "Scene order 2 already exists" in response.json()["detail"]
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.update.assert_called_once()

# --- Delete Scene ---

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_delete_scene_success(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test successfully deleting a scene."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    mock_scene_service.delete.return_value = None # Delete returns None

    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{SCENE_ID_1}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Scene {SCENE_ID_1} deleted successfully"}
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.delete.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID, scene_id=SCENE_ID_1)

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_delete_scene_not_found(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test deleting a scene that does not exist (404)."""
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    mock_scene_service.delete.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Scene {NON_EXISTENT_SCENE_ID} not found"
    )

    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{NON_EXISTENT_SCENE_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Scene {NON_EXISTENT_SCENE_ID} not found" in response.json()["detail"]
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.delete.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID, scene_id=NON_EXISTENT_SCENE_ID)