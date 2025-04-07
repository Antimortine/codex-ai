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
from app.services.file_service import file_service
# Import the service instance *used by the dependency* to mock it
from app.services.project_service import project_service as project_service_for_dependency
# Import models for type checking and response validation
from app.models.content_block import ContentBlockRead, ContentBlockUpdate
from app.models.project import ProjectRead # Needed for mocking project dependency

# Create a TestClient instance
client = TestClient(app)

# --- Constants for Testing ---
PROJECT_ID = "test-project-blocks"
NON_EXISTENT_PROJECT_ID = "project-404"
PLAN_CONTENT = "# Project Plan\n\n- Step 1\n- Step 2"
SYNOPSIS_CONTENT = "This is the synopsis."
WORLD_CONTENT = "## World Info\n\nDetails about the world."
UPDATED_CONTENT = "This is the updated content."

# --- Mock Dependency Helper ---
def mock_project_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id', args[0] if args else PROJECT_ID)
    if project_id_arg == NON_EXISTENT_PROJECT_ID:
         raise HTTPException(status_code=404, detail=f"Project {project_id_arg} not found")
    return ProjectRead(id=project_id_arg, name=f"Mock Project {project_id_arg}")

# --- Parameterization Data ---
BLOCK_TYPES = [
    ("plan", PLAN_CONTENT),
    ("synopsis", SYNOPSIS_CONTENT),
    ("world", WORLD_CONTENT),
]

# --- Test Content Block API Endpoints ---

# === GET Tests ===
@pytest.mark.parametrize("block_name, initial_content", BLOCK_TYPES)
@patch('app.api.v1.endpoints.content_blocks.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_get_block_success(mock_project_dep: MagicMock, mock_file_svc: MagicMock, block_name: str, initial_content: str):
    """Test successful GET for a content block."""
    endpoint_path = f"/api/v1/projects/{PROJECT_ID}/{block_name}"
    file_name = f"{block_name}.md"

    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_file_svc.read_content_block_file.return_value = initial_content

    response = client.get(endpoint_path)

    assert response.status_code == status.HTTP_200_OK
    # Assert specific fields
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == initial_content
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_file_svc.read_content_block_file.assert_called_once_with(PROJECT_ID, file_name)

@pytest.mark.parametrize("block_name, initial_content", BLOCK_TYPES)
@patch('app.api.v1.endpoints.content_blocks.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_get_block_file_not_found(mock_project_dep: MagicMock, mock_file_svc: MagicMock, block_name: str, initial_content: str):
    """Test GET when the specific block file doesn't exist (returns empty)."""
    endpoint_path = f"/api/v1/projects/{PROJECT_ID}/{block_name}"
    file_name = f"{block_name}.md"

    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_file_svc.read_content_block_file.side_effect = HTTPException(status_code=404)

    response = client.get(endpoint_path)

    assert response.status_code == status.HTTP_200_OK
    # Assert specific fields for the handled 404 case
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == "" # Endpoint handles 404 by returning empty
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_file_svc.read_content_block_file.assert_called_once_with(PROJECT_ID, file_name)

@pytest.mark.parametrize("block_name, initial_content", BLOCK_TYPES)
@patch('app.api.v1.endpoints.content_blocks.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_get_block_project_not_found(mock_project_dep: MagicMock, mock_file_svc: MagicMock, block_name: str, initial_content: str):
    """Test GET when the project itself doesn't exist (404 from dependency)."""
    endpoint_path_404 = f"/api/v1/projects/{NON_EXISTENT_PROJECT_ID}/{block_name}"
    error_detail = f"Project {NON_EXISTENT_PROJECT_ID} not found"
    mock_project_dep.get_by_id.side_effect = HTTPException(status_code=404, detail=error_detail)

    response = client.get(endpoint_path_404)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_project_dep.get_by_id.assert_called_once_with(project_id=NON_EXISTENT_PROJECT_ID)
    mock_file_svc.read_content_block_file.assert_not_called()

# === PUT Tests ===
@pytest.mark.parametrize("block_name, initial_content", BLOCK_TYPES)
@patch('app.api.v1.endpoints.content_blocks.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_block_success(mock_project_dep: MagicMock, mock_file_svc: MagicMock, block_name: str, initial_content: str):
    """Test successful PUT update for a content block."""
    endpoint_path = f"/api/v1/projects/{PROJECT_ID}/{block_name}"
    file_name = f"{block_name}.md"

    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_file_svc.write_content_block_file.return_value = None # Write returns None
    update_data = {"content": UPDATED_CONTENT}

    response = client.put(endpoint_path, json=update_data)

    assert response.status_code == status.HTTP_200_OK
    # Assert specific fields
    response_data = response.json()
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["content"] == UPDATED_CONTENT
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    # Verify service call arguments
    mock_file_svc.write_content_block_file.assert_called_once_with(PROJECT_ID, file_name, UPDATED_CONTENT)

@pytest.mark.parametrize("block_name, initial_content", BLOCK_TYPES)
@patch('app.api.v1.endpoints.content_blocks.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_block_project_not_found(mock_project_dep: MagicMock, mock_file_svc: MagicMock, block_name: str, initial_content: str):
    """Test PUT when the project doesn't exist (404 from dependency)."""
    endpoint_path_404 = f"/api/v1/projects/{NON_EXISTENT_PROJECT_ID}/{block_name}"
    error_detail = f"Project {NON_EXISTENT_PROJECT_ID} not found"
    mock_project_dep.get_by_id.side_effect = HTTPException(status_code=404, detail=error_detail)
    update_data = {"content": UPDATED_CONTENT}

    response = client.put(endpoint_path_404, json=update_data)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}
    mock_project_dep.get_by_id.assert_called_once_with(project_id=NON_EXISTENT_PROJECT_ID)
    mock_file_svc.write_content_block_file.assert_not_called()

@pytest.mark.parametrize("block_name, initial_content", BLOCK_TYPES)
@patch('app.api.v1.endpoints.content_blocks.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_block_validation_error(mock_project_dep: MagicMock, mock_file_svc: MagicMock, block_name: str, initial_content: str):
    """Test PUT with invalid data (missing content field)."""
    endpoint_path = f"/api/v1/projects/{PROJECT_ID}/{block_name}"

    mock_project_dep.get_by_id.side_effect = mock_project_exists
    invalid_data = {} # Missing 'content'

    response = client.put(endpoint_path, json=invalid_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    response_data = response.json()
    assert response_data['detail'][0]['type'] == 'missing'
    assert response_data['detail'][0]['loc'] == ['body', 'content']
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_file_svc.write_content_block_file.assert_not_called()

@pytest.mark.parametrize("block_name, initial_content", BLOCK_TYPES)
@patch('app.api.v1.endpoints.content_blocks.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_block_write_error(mock_project_dep: MagicMock, mock_file_svc: MagicMock, block_name: str, initial_content: str):
    """Test PUT when file writing fails."""
    endpoint_path = f"/api/v1/projects/{PROJECT_ID}/{block_name}"
    file_name = f"{block_name}.md"
    error_detail = f"Could not write to {file_name}"

    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_file_svc.write_content_block_file.side_effect = HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=error_detail
    )
    update_data = {"content": UPDATED_CONTENT}

    response = client.put(endpoint_path, json=update_data)

    assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert response.json() == {"detail": error_detail}
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_file_svc.write_content_block_file.assert_called_once_with(PROJECT_ID, file_name, UPDATED_CONTENT)