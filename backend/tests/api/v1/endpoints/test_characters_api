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
from app.services.character_service import character_service
# Import the service instance *used by the dependency* to mock it
from app.services.project_service import project_service as project_service_for_dependency
# Import models for type checking and response validation
from app.models.character import CharacterRead, CharacterList, CharacterCreate, CharacterUpdate
from app.models.project import ProjectRead # Needed for mocking project dependency
from app.models.common import Message

# Create a TestClient instance
client = TestClient(app)

# --- Constants for Testing ---
PROJECT_ID = "test-project-chars"
CHARACTER_ID_1 = "char-id-1"
CHARACTER_ID_2 = "char-id-2"
NON_EXISTENT_PROJECT_ID = "project-404"
NON_EXISTENT_CHARACTER_ID = "character-404"

# --- Mock Dependency Helper ---
# Mocks the project_service.get_by_id call used in the dependency
def mock_project_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id', args[0] if args else PROJECT_ID)
    if project_id_arg == NON_EXISTENT_PROJECT_ID:
         raise HTTPException(status_code=404, detail=f"Project {project_id_arg} not found")
    return ProjectRead(id=project_id_arg, name=f"Mock Project {project_id_arg}")

# --- Test Character API Endpoints ---

# Patch BOTH the character_service (used by endpoint logic) AND
# the project_service (used by the dependency)
@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Target dependency import
def test_create_character_success(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test successful character creation."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    char_data_in = {"name": "Gandalf", "description": "A wizard"}
    mock_created_char = CharacterRead(
        id=CHARACTER_ID_1,
        project_id=PROJECT_ID,
        name=char_data_in["name"],
        description=char_data_in["description"]
    )
    mock_character_service.create.return_value = mock_created_char

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/characters/", json=char_data_in)

    assert response.status_code == status.HTTP_201_CREATED
    assert response.json() == mock_created_char.model_dump()
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.create.assert_called_once()
    call_args, call_kwargs = mock_character_service.create.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert isinstance(call_kwargs['character_in'], CharacterCreate)
    assert call_kwargs['character_in'].name == char_data_in['name']
    assert call_kwargs['character_in'].description == char_data_in['description']

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_create_character_project_not_found(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test character creation when the project does not exist (404 from dependency)."""
    mock_project_service_dep.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Project {NON_EXISTENT_PROJECT_ID} not found"
    )
    char_data_in = {"name": "Lost Character", "description": ""}

    response = client.post(f"/api/v1/projects/{NON_EXISTENT_PROJECT_ID}/characters/", json=char_data_in)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Project {NON_EXISTENT_PROJECT_ID} not found" in response.json()["detail"]
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=NON_EXISTENT_PROJECT_ID)
    mock_character_service.create.assert_not_called()

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_create_character_validation_error(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test character creation with invalid data (e.g., empty name)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    invalid_data = {"name": "", "description": "Valid description"} # Empty name

    response = client.post(f"/api/v1/projects/{PROJECT_ID}/characters/", json=invalid_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()['detail'][0]['type'] == 'string_too_short'
    assert response.json()['detail'][0]['loc'] == ['body', 'name']
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.create.assert_not_called()

# --- List Characters ---

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_list_characters_empty(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test listing characters when none exist."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    mock_character_service.get_all_for_project.return_value = CharacterList(characters=[])

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/characters/")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"characters": []}
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.get_all_for_project.assert_called_once_with(project_id=PROJECT_ID)

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_list_characters_with_data(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test listing characters when some exist."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    char1 = CharacterRead(id=CHARACTER_ID_1, project_id=PROJECT_ID, name="Char 1", description="Desc 1")
    char2 = CharacterRead(id=CHARACTER_ID_2, project_id=PROJECT_ID, name="Char 2", description="Desc 2")
    # Note: List endpoint might not return description, adjust mock if needed
    mock_character_service.get_all_for_project.return_value = CharacterList(characters=[char1, char2])

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/characters/")

    assert response.status_code == status.HTTP_200_OK
    expected_data = {
        "characters": [
            char1.model_dump(),
            char2.model_dump()
        ]
    }
    assert response.json() == expected_data
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.get_all_for_project.assert_called_once_with(project_id=PROJECT_ID)

# --- Get Character by ID ---

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_get_character_success(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test successfully getting a character by ID."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    mock_char = CharacterRead(id=CHARACTER_ID_1, project_id=PROJECT_ID, name="Found Character", description="Found Desc")
    mock_character_service.get_by_id.return_value = mock_char

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/characters/{CHARACTER_ID_1}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_char.model_dump()
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.get_by_id.assert_called_once_with(project_id=PROJECT_ID, character_id=CHARACTER_ID_1)

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_get_character_not_found(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test getting a character that does not exist (404)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    mock_character_service.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Character {NON_EXISTENT_CHARACTER_ID} not found"
    )

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/characters/{NON_EXISTENT_CHARACTER_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Character {NON_EXISTENT_CHARACTER_ID} not found" in response.json()["detail"]
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.get_by_id.assert_called_once_with(project_id=PROJECT_ID, character_id=NON_EXISTENT_CHARACTER_ID)

# --- Update Character ---

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_character_success(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test successfully updating a character."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    update_data = {"name": "Updated Name", "description": "Updated description."}
    mock_updated_char = CharacterRead(
        id=CHARACTER_ID_1,
        project_id=PROJECT_ID,
        name=update_data["name"],
        description=update_data["description"]
    )
    mock_character_service.update.return_value = mock_updated_char

    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/characters/{CHARACTER_ID_1}", json=update_data)

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == mock_updated_char.model_dump()
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.update.assert_called_once()
    call_args, call_kwargs = mock_character_service.update.call_args
    assert call_kwargs['project_id'] == PROJECT_ID
    assert call_kwargs['character_id'] == CHARACTER_ID_1
    assert isinstance(call_kwargs['character_in'], CharacterUpdate)
    assert call_kwargs['character_in'].name == update_data['name']
    assert call_kwargs['character_in'].description == update_data['description']

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_character_not_found(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test updating a character that does not exist (404)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    update_data = {"name": "Doesn't Matter"}
    mock_character_service.update.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Character {NON_EXISTENT_CHARACTER_ID} not found"
    )

    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/characters/{NON_EXISTENT_CHARACTER_ID}", json=update_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Character {NON_EXISTENT_CHARACTER_ID} not found" in response.json()["detail"]
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.update.assert_called_once()

# --- Delete Character ---

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_delete_character_success(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test successfully deleting a character."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    mock_character_service.delete.return_value = None # Delete returns None

    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/characters/{CHARACTER_ID_1}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json() == {"message": f"Character {CHARACTER_ID_1} deleted successfully"}
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.delete.assert_called_once_with(project_id=PROJECT_ID, character_id=CHARACTER_ID_1)

@patch('app.api.v1.endpoints.characters.character_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_delete_character_not_found(mock_project_service_dep: MagicMock, mock_character_service: MagicMock):
    """Test deleting a character that does not exist (404)."""
    mock_project_service_dep.get_by_id.side_effect = mock_project_exists
    mock_character_service.delete.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Character {NON_EXISTENT_CHARACTER_ID} not found"
    )

    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/characters/{NON_EXISTENT_CHARACTER_ID}")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Character {NON_EXISTENT_CHARACTER_ID} not found" in response.json()["detail"]
    mock_project_service_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_character_service.delete.assert_called_once_with(project_id=PROJECT_ID, character_id=NON_EXISTENT_CHARACTER_ID)