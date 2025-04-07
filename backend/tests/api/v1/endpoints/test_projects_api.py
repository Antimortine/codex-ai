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

# Import the FastAPI app instance
# Ensure conftest.py added the project root to sys.path
from app.main import app
from app.services.project_service import project_service # To mock its methods
from app.models.project import ProjectRead, ProjectList, ProjectCreate # Import models for type checking

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
    # --- MODIFIED: Check keyword arguments ---
    # Check the argument passed to the mock (it's a Pydantic model instance passed as kwarg)
    _, call_kwargs = mock_project_service.create.call_args
    assert isinstance(call_kwargs['project_in'], ProjectCreate)
    assert call_kwargs['project_in'].name == project_name
    # --- END MODIFIED ---


@patch('app.api.v1.endpoints.projects.project_service', autospec=True)
def test_create_project_missing_name(mock_project_service: MagicMock):
    """Test project creation with missing name (should fail validation)."""
    response = client.post("/api/v1/projects/", json={}) # Empty JSON body

    assert response.status_code == 422 # Unprocessable Entity
    response_data = response.json()
    assert "detail" in response_data
    assert isinstance(response_data["detail"], list)
    assert len(response_data["detail"]) > 0
    # --- MODIFIED: Check specific Pydantic v2 error structure/message ---
    assert response_data["detail"][0]["type"] == "missing"
    assert response_data["detail"][0]["loc"] == ["body", "name"]
    assert "Field required" in response_data["detail"][0]["msg"]
    # --- END MODIFIED ---
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
    # --- MODIFIED: Check specific Pydantic v2 error structure/message ---
    assert response_data["detail"][0]["type"] == "string_too_short"
    assert response_data["detail"][0]["loc"] == ["body", "name"]
    assert "String should have at least 1 character" in response_data["detail"][0]["msg"]
    # --- END MODIFIED ---
    mock_project_service.create.assert_not_called()

# TODO: Add tests for GET /projects/{project_id} (success and 404)
# TODO: Add tests for PATCH /projects/{project_id} (success, 404, validation errors)
# TODO: Add tests for DELETE /projects/{project_id} (success and 404)