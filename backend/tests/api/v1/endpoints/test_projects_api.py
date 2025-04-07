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
from unittest.mock import patch, MagicMock # For mocking service layer
from fastapi import HTTPException, status # Import for mocking exceptions

# Import the FastAPI app instance
# Ensure conftest.py added the project root to sys.path
from app.main import app
from app.services.project_service import project_service # To mock its methods
from app.models.project import ProjectRead, ProjectList, ProjectCreate, ProjectUpdate # Import models for type checking
from app.models.common import Message # Import for delete response

# Create a TestClient instance
client = TestClient(app)

# --- Test Project API Endpoints ---

@patch('app.api.v1.endpoints.projects.project_service', autospec=True) # Mock the service instance used by the endpoint
def test_list_projects_empty(mock_project_service: MagicMock):
    """Test listing projects when none exist."""
    # Configure the mock to return an empty list
    mock_project_service.get_all.return_value = ProjectList(projects=[])

    response = client.get("/api/v1/projects/")

    assert response.status_code == 200
    assert response.json() == {"projects": []}
    mock_project_service.get_all.assert_called_once() # Verify the service method was called

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_list_projects_with_data(mock_project_service: MagicMock):
    """Test listing projects when some exist."""
    # Configure the mock to return sample data
    project1 = ProjectRead(id="uuid-1", name="Project Alpha")
    project2 = ProjectRead(id="uuid-2", name="Project Beta")
    mock_project_service.get_all.return_value = ProjectList(projects=[project1, project2])

    response = client.get("/api/v1/projects/")

    assert response.status_code == 200
    # Pydantic models in response are dicts, compare dicts
    expected_data = {
        "projects": [
            {"id": "uuid-1", "name": "Project Alpha"},
            {"id": "uuid-2", "name": "Project Beta"}
        ]
    }
    assert response.json() == expected_data
    mock_project_service.get_all.assert_called_once()

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_create_project_success(mock_project_service: MagicMock):
    """Test successful project creation."""
    project_name = "My New Test Project"
    new_project_data = {"name": project_name}
    # Configure the mock service's create method
    created_project = ProjectRead(id="new-uuid", name=project_name)
    mock_project_service.create.return_value = created_project

    response = client.post("/api/v1/projects/", json=new_project_data)

    assert response.status_code == 201 # Check for Created status
    # Compare dicts
    assert response.json() == {"id": "new-uuid", "name": project_name}
    # Verify the service method was called correctly
    mock_project_service.create.assert_called_once()
    # Check the argument passed to the mock (it's a Pydantic model instance passed as kwarg)
    _, call_kwargs = mock_project_service.create.call_args
    assert isinstance(call_kwargs['project_in'], ProjectCreate)
    assert call_kwargs['project_in'].name == project_name


@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_create_project_missing_name(mock_project_service: MagicMock):
    """Test project creation with missing name (should fail validation)."""
    response = client.post("/api/v1/projects/", json={}) # Empty JSON body

    assert response.status_code == 422 # Unprocessable Entity
    response_data = response.json()
    assert "detail" in response_data
    assert isinstance(response_data["detail"], list)
    assert len(response_data["detail"]) > 0
    # Check specific Pydantic v2 error structure/message
    assert response_data["detail"][0]["type"] == "missing"
    assert response_data["detail"][0]["loc"] == ["body", "name"]
    assert "Field required" in response_data["detail"][0]["msg"]
    mock_project_service.create.assert_not_called() # Service should not be called

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_create_project_empty_name(mock_project_service: MagicMock):
    """Test project creation with empty name string (should fail validation)."""
    response = client.post("/api/v1/projects/", json={"name": ""}) # Empty name

    assert response.status_code == 422 # Unprocessable Entity
    response_data = response.json()
    assert "detail" in response_data
    assert isinstance(response_data["detail"], list)
    assert len(response_data["detail"]) > 0
    # Check specific Pydantic v2 error structure/message
    assert response_data["detail"][0]["type"] == "string_too_short"
    assert response_data["detail"][0]["loc"] == ["body", "name"]
    assert "String should have at least 1 character" in response_data["detail"][0]["msg"]
    mock_project_service.create.assert_not_called()

# --- Tests for GET /projects/{project_id} ---

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_get_project_success(mock_project_service: MagicMock):
    """Test successfully getting a project by ID."""
    project_id = "existing-uuid"
    project_data = ProjectRead(id=project_id, name="Found Project")
    mock_project_service.get_by_id.return_value = project_data

    response = client.get(f"/api/v1/projects/{project_id}")

    assert response.status_code == 200
    assert response.json() == {"id": project_id, "name": "Found Project"}
    mock_project_service.get_by_id.assert_called_once_with(project_id=project_id)

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_get_project_not_found(mock_project_service: MagicMock):
    """Test getting a project that does not exist (404)."""
    project_id = "non-existent-uuid"
    # Configure the mock to raise the expected HTTPException
    mock_project_service.get_by_id.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Project {project_id} not found"
    )

    response = client.get(f"/api/v1/projects/{project_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Project {project_id} not found"}
    mock_project_service.get_by_id.assert_called_once_with(project_id=project_id)

# --- Tests for PATCH /projects/{project_id} ---

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_update_project_success(mock_project_service: MagicMock):
    """Test successfully updating a project's name."""
    project_id = "update-uuid"
    update_data = {"name": "Updated Project Name"}
    updated_project = ProjectRead(id=project_id, name="Updated Project Name")
    mock_project_service.update.return_value = updated_project

    response = client.patch(f"/api/v1/projects/{project_id}", json=update_data)

    assert response.status_code == 200
    assert response.json() == {"id": project_id, "name": "Updated Project Name"}
    # Verify the service method was called correctly
    mock_project_service.update.assert_called_once()
    call_args, call_kwargs = mock_project_service.update.call_args
    assert call_kwargs['project_id'] == project_id
    assert isinstance(call_kwargs['project_in'], ProjectUpdate)
    assert call_kwargs['project_in'].name == update_data['name']

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_update_project_not_found(mock_project_service: MagicMock):
    """Test updating a project that does not exist (404)."""
    project_id = "non-existent-uuid"
    update_data = {"name": "Doesn't Matter"}
    # Configure the mock to raise 404
    mock_project_service.update.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Project {project_id} not found"
    )

    response = client.patch(f"/api/v1/projects/{project_id}", json=update_data)

    assert response.status_code == 404
    assert response.json() == {"detail": f"Project {project_id} not found"}
    mock_project_service.update.assert_called_once() # Service method is still called

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_update_project_empty_name(mock_project_service: MagicMock):
    """Test updating a project with an empty name (422 validation error)."""
    project_id = "validation-uuid"
    update_data = {"name": ""} # Invalid empty name

    response = client.patch(f"/api/v1/projects/{project_id}", json=update_data)

    assert response.status_code == 422
    response_data = response.json()
    assert "detail" in response_data
    assert isinstance(response_data["detail"], list)
    assert len(response_data["detail"]) > 0
    # Check specific Pydantic v2 error structure/message
    assert response_data["detail"][0]["type"] == "string_too_short"
    assert response_data["detail"][0]["loc"] == ["body", "name"]
    assert "String should have at least 1 character" in response_data["detail"][0]["msg"]
    mock_project_service.update.assert_not_called() # Service should not be called

# --- Tests for DELETE /projects/{project_id} ---

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_delete_project_success(mock_project_service: MagicMock):
    """Test successfully deleting a project."""
    project_id = "delete-uuid"
    # Configure the mock delete method to return None (or just not raise an exception)
    mock_project_service.delete.return_value = None

    response = client.delete(f"/api/v1/projects/{project_id}")

    assert response.status_code == 200 # Status OK
    assert response.json() == {"message": f"Project {project_id} deleted successfully"}
    mock_project_service.delete.assert_called_once_with(project_id=project_id)

@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_delete_project_not_found(mock_project_service: MagicMock):
    """Test deleting a project that does not exist (404)."""
    project_id = "non-existent-uuid"
    # Configure the mock to raise 404
    mock_project_service.delete.side_effect = HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Project {project_id} not found"
    )

    response = client.delete(f"/api/v1/projects/{project_id}")

    assert response.status_code == 404
    assert response.json() == {"detail": f"Project {project_id} not found"}
    mock_project_service.delete.assert_called_once_with(project_id=project_id)