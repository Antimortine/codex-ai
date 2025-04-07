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
def mock_chapter_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id')
    chapter_id_arg = kwargs.get('chapter_id')
    if chapter_id_arg == NON_EXISTENT_CHAPTER_ID:
         # Raise the specific error message from the dependency
         raise HTTPException(status_code=404, detail=f"Chapter {chapter_id_arg} not found in project {project_id_arg}")
    # Assume project exists if chapter check is reached
    return ChapterRead(id=chapter_id_arg, project_id=project_id_arg, title=f"Mock Chapter {chapter_id_arg}", order=1)

# --- Test Scene API Endpoints ---
# (test_create_scene_success unchanged - omitted)
@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True) # Target dependency import
def test_create_scene_success(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
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
    response_data = response.json()
    assert response_data["id"] == SCENE_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["chapter_id"] == CHAPTER_ID
    assert response_data["title"] == scene_data_in["title"]
    assert response_data["order"] == scene_data_in["order"]
    assert response_data["content"] == scene_data_in["content"]
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.create.assert_called_once()
    call_args, call_kwargs = mock_scene_service.create.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert call_kwargs['chapter_id'] == CHAPTER_ID
    assert isinstance(call_kwargs['scene_in'], SceneCreate)
    assert call_kwargs['scene_in'].title == scene_data_in['title']
    assert call_kwargs['scene_in'].order == scene_data_in['order']
    assert call_kwargs['scene_in'].content == scene_data_in['content']

# (test_create_scene_order_conflict unchanged - omitted)
@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_create_scene_order_conflict(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    scene_data_in = {"title": "Conflict Scene", "order": 1, "content": "..."}
    error_detail = "Scene order 1 already exists"
    mock_scene_service.create.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=error_detail
    )
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/", json=scene_data_in)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": error_detail}
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.create.assert_called_once()


@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_create_scene_chapter_not_found(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    """Test scene creation when the chapter does not exist (404 from dependency)."""
    # *** THIS IS THE CORRECTED LINE ***
    error_detail = f"Chapter {NON_EXISTENT_CHAPTER_ID} not found in project {PROJECT_ID}"
    # *** END CORRECTION ***
    mock_chapter_service_dep.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail
    )
    scene_data_in = {"title": "Lost Scene", "order": 1, "content": "..."}

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/{NON_EXISTENT_CHAPTER_ID}/scenes/", json=scene_data_in)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    # Assert against the corrected detail
    assert response.json() == {"detail": error_detail}
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=NON_EXISTENT_CHAPTER_ID)
    mock_scene_service.create.assert_not_called()

# (Rest of the file remains unchanged - Omitted for brevity)
@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_create_scene_validation_error(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    invalid_data = {"title": "Valid Title", "order": -1, "content": ""} # Invalid order
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/", json=invalid_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert response_data['detail'][0]['type'] == 'greater_than_equal'
    assert response_data['detail'][0]['loc'] == ['body', 'order']
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.create.assert_not_called()

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_list_scenes_empty(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    mock_scene_service.get_all_for_chapter.return_value = SceneList(scenes=[])
    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "scenes" in response_data
    assert isinstance(response_data["scenes"], list)
    assert len(response_data["scenes"]) == 0
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.get_all_for_chapter.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_list_scenes_with_data(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    scene1 = SceneRead(id=SCENE_ID_1, project_id=PROJECT_ID, chapter_id=CHAPTER_ID, title="S1", order=1, content="C1")
    scene2 = SceneRead(id=SCENE_ID_2, project_id=PROJECT_ID, chapter_id=CHAPTER_ID, title="S2", order=2, content="C2")
    mock_scene_service.get_all_for_chapter.return_value = SceneList(scenes=[scene1, scene2])
    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "scenes" in response_data
    assert isinstance(response_data["scenes"], list)
    assert len(response_data["scenes"]) == 2
    assert response_data["scenes"][0]["id"] == SCENE_ID_1
    assert response_data["scenes"][0]["project_id"] == PROJECT_ID
    assert response_data["scenes"][0]["chapter_id"] == CHAPTER_ID
    assert response_data["scenes"][0]["title"] == "S1"
    assert response_data["scenes"][0]["order"] == 1
    assert response_data["scenes"][0]["content"] == "C1"
    assert response_data["scenes"][1]["id"] == SCENE_ID_2
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.get_all_for_chapter.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_get_scene_success(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    mock_scene = SceneRead(id=SCENE_ID_1, project_id=PROJECT_ID, chapter_id=CHAPTER_ID, title="Found Scene", order=1, content="Found Content")
    mock_scene_service.get_by_id.return_value = mock_scene
    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{SCENE_ID_1}")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == SCENE_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["chapter_id"] == CHAPTER_ID
    assert response_data["title"] == "Found Scene"
    assert response_data["order"] == 1
    assert response_data["content"] == "Found Content"
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID, scene_id=SCENE_ID_1)

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_get_scene_not_found(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    error_detail = f"Scene {NON_EXISTENT_SCENE_ID} not found"
    mock_scene_service.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail
    )
    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{NON_EXISTENT_SCENE_ID}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID, scene_id=NON_EXISTENT_SCENE_ID)

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_update_scene_success(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    update_data = {"title": "Updated Scene Title", "content": "Updated content."}
    mock_updated_scene = SceneRead(
        id=SCENE_ID_1,
        project_id=PROJECT_ID,
        chapter_id=CHAPTER_ID,
        title=update_data["title"],
        order=1,
        content=update_data["content"]
    )
    mock_scene_service.update.return_value = mock_updated_scene
    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{SCENE_ID_1}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == SCENE_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["chapter_id"] == CHAPTER_ID
    assert response_data["title"] == update_data["title"]
    assert response_data["order"] == 1
    assert response_data["content"] == update_data["content"]
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.update.assert_called_once()
    call_args, call_kwargs = mock_scene_service.update.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert call_kwargs['chapter_id'] == CHAPTER_ID
    assert call_kwargs['scene_id'] == SCENE_ID_1
    assert isinstance(call_kwargs['scene_in'], SceneUpdate)
    assert call_kwargs['scene_in'].title == update_data['title']
    assert call_kwargs['scene_in'].content == update_data['content']
    assert call_kwargs['scene_in'].order is None

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_update_scene_not_found(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    update_data = {"title": "Doesn't Matter"}
    error_detail = f"Scene {NON_EXISTENT_SCENE_ID} not found"
    mock_scene_service.update.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail
    )
    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{NON_EXISTENT_SCENE_ID}", json=update_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.update.assert_called_once()

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_update_scene_order_conflict(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    update_data = {"order": 2}
    error_detail = "Scene order 2 already exists"
    mock_scene_service.update.side_effect = HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=error_detail
    )
    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{SCENE_ID_1}", json=update_data)
    assert response.status_code == status.HTTP_409_CONFLICT
    assert response.json() == {"detail": error_detail}
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.update.assert_called_once()

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_delete_scene_success(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    mock_scene_service.delete.return_value = None
    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{SCENE_ID_1}")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "message" in response_data
    assert response_data["message"] == f"Scene {SCENE_ID_1} deleted successfully"
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.delete.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID, scene_id=SCENE_ID_1)

@patch('app.api.v1.endpoints.scenes.scene_service', autospec=True)
@patch('app.api.v1.endpoints.scenes.chapter_service', autospec=True)
def test_delete_scene_not_found(mock_chapter_service_dep: MagicMock, mock_scene_service: MagicMock):
    mock_chapter_service_dep.get_by_id.side_effect = mock_chapter_exists
    error_detail = f"Scene {NON_EXISTENT_SCENE_ID} not found"
    mock_scene_service.delete.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=error_detail
    )
    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/chapters/{CHAPTER_ID}/scenes/{NON_EXISTENT_SCENE_ID}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_chapter_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID)
    mock_scene_service.delete.assert_called_once_with(project_id=PROJECT_ID, chapter_id=CHAPTER_ID, scene_id=NON_EXISTENT_SCENE_ID)