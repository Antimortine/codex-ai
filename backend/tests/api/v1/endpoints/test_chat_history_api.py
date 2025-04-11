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
import uuid

# Import the FastAPI app instance
from app.main import app
# Import the service instance *used by the endpoint module* to mock it
from app.services.file_service import file_service
# Import the service instance *used by the dependency* to mock it
from app.services.project_service import project_service as project_service_for_dependency
# Import models for type checking and response validation
from app.models.ai import (
    ChatHistoryRead, ChatHistoryWrite, ChatHistoryEntry,
    ChatSessionCreate, ChatSessionRead, ChatSessionList, ChatSessionUpdate,
    AIQueryResponse # Import AIQueryResponse for constructing expected data
)
from app.models.project import ProjectRead # Needed for mocking project dependency
from app.models.common import Message

# Create a TestClient instance
client = TestClient(app)

# --- Constants for Testing ---
PROJECT_ID = "test-project-chat"
SESSION_ID_1 = str(uuid.uuid4())
SESSION_ID_2 = str(uuid.uuid4())
NON_EXISTENT_PROJECT_ID = "project-404"
NON_EXISTENT_SESSION_ID = str(uuid.uuid4())

# --- Mock Dependency Helper ---
def mock_project_exists(*args, **kwargs):
    project_id_arg = kwargs.get('project_id', args[0] if args else PROJECT_ID)
    if project_id_arg == NON_EXISTENT_PROJECT_ID:
         raise HTTPException(status_code=404, detail=f"Project {project_id_arg} not found")
    return ProjectRead(id=project_id_arg, name=f"Mock Project {project_id_arg}")

# --- Test Chat Session API Endpoints ---
# (Unchanged - Omitted for brevity)
@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True) # Target dependency import
@patch('app.api.v1.endpoints.chat_history.generate_uuid', return_value=SESSION_ID_1) # Mock UUID
def test_create_chat_session_success(mock_uuid, mock_project_dep, mock_file_svc):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    session_data_in = {"name": "My First Chat"}
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chat_sessions", json=session_data_in)
    assert response.status_code == status.HTTP_201_CREATED
    response_data = response.json()
    assert response_data["id"] == SESSION_ID_1
    assert response_data["project_id"] == PROJECT_ID
    assert response_data["name"] == session_data_in["name"]
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_file_svc.add_chat_session_metadata.assert_called_once_with(PROJECT_ID, SESSION_ID_1, session_data_in["name"])
    mock_file_svc.write_chat_session_history.assert_called_once_with(PROJECT_ID, SESSION_ID_1, [])

@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_create_chat_session_project_not_found(mock_project_dep):
    error_detail = f"Project {NON_EXISTENT_PROJECT_ID} not found"
    mock_project_dep.get_by_id.side_effect = HTTPException(status_code=404, detail=error_detail)
    session_data_in = {"name": "Lost Chat"}
    response = client.post(f"/api/v1/projects/{NON_EXISTENT_PROJECT_ID}/chat_sessions", json=session_data_in)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json() == {"detail": error_detail}

@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_create_chat_session_validation_error(mock_project_dep):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    invalid_data = {"name": ""}
    response = client.post(f"/api/v1/projects/{PROJECT_ID}/chat_sessions", json=invalid_data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()['detail'][0]['loc'] == ['body', 'name']

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_list_chat_sessions_success(mock_project_dep, mock_file_svc):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_sessions_meta = {
        SESSION_ID_1: {"name": "Session Alpha"},
        SESSION_ID_2: {"name": "Session Beta"}
    }
    mock_file_svc.get_chat_sessions_metadata.return_value = mock_sessions_meta
    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chat_sessions")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "sessions" in response_data
    assert len(response_data["sessions"]) == 2
    session_names = {s["name"] for s in response_data["sessions"]}
    session_ids = {s["id"] for s in response_data["sessions"]}
    assert session_names == {"Session Alpha", "Session Beta"}
    assert session_ids == {SESSION_ID_1, SESSION_ID_2}
    assert all(s["project_id"] == PROJECT_ID for s in response_data["sessions"])
    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_file_svc.get_chat_sessions_metadata.assert_called_once_with(PROJECT_ID)

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_list_chat_sessions_empty(mock_project_dep, mock_file_svc):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_file_svc.get_chat_sessions_metadata.return_value = {}
    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chat_sessions")
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["sessions"] == []

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rename_chat_session_success(mock_project_dep, mock_file_svc):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    update_data = {"name": "Updated Session Name"}
    mock_file_svc.get_chat_sessions_metadata.return_value = {SESSION_ID_1: {"name": "Old Name"}}
    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chat_sessions/{SESSION_ID_1}", json=update_data)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["id"] == SESSION_ID_1
    assert response_data["name"] == update_data["name"]
    assert response_data["project_id"] == PROJECT_ID
    mock_file_svc.get_chat_sessions_metadata.assert_called_once_with(PROJECT_ID)
    mock_file_svc.update_chat_session_metadata.assert_called_once_with(PROJECT_ID, SESSION_ID_1, update_data["name"])

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_rename_chat_session_not_found(mock_project_dep, mock_file_svc):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    update_data = {"name": "New Name"}
    mock_file_svc.get_chat_sessions_metadata.return_value = {}
    response = client.patch(f"/api/v1/projects/{PROJECT_ID}/chat_sessions/{NON_EXISTENT_SESSION_ID}", json=update_data)
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Chat session {NON_EXISTENT_SESSION_ID} not found" in response.json()["detail"]
    mock_file_svc.update_chat_session_metadata.assert_not_called()

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_delete_chat_session_success(mock_project_dep, mock_file_svc):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_file_svc.get_chat_sessions_metadata.return_value = {SESSION_ID_1: {"name": "To Delete"}}
    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/chat_sessions/{SESSION_ID_1}")
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == f"Chat session {SESSION_ID_1} deleted successfully."
    mock_file_svc.get_chat_sessions_metadata.assert_called_once_with(PROJECT_ID)
    mock_file_svc.delete_chat_session_history.assert_called_once_with(PROJECT_ID, SESSION_ID_1)
    mock_file_svc.delete_chat_session_metadata.assert_called_once_with(PROJECT_ID, SESSION_ID_1)

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_delete_chat_session_not_found(mock_project_dep, mock_file_svc):
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_file_svc.get_chat_sessions_metadata.return_value = {}
    mock_file_svc.read_chat_session_history.return_value = []
    response = client.delete(f"/api/v1/projects/{PROJECT_ID}/chat_sessions/{NON_EXISTENT_SESSION_ID}")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert f"Chat session {NON_EXISTENT_SESSION_ID} not found" in response.json()["detail"]
    mock_file_svc.delete_chat_session_history.assert_not_called()
    mock_file_svc.delete_chat_session_metadata.assert_not_called()

# --- Test Chat History API Endpoints (Modified) ---

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_get_chat_history_success(mock_project_dep, mock_file_svc):
    """Test getting chat history for a specific session."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    # --- MODIFIED: Construct expected response with full model structure ---
    mock_response_obj = AIQueryResponse(answer="a1", source_nodes=[], direct_sources=None)
    mock_history_from_file = [{"id": 0, "query": "q1", "response": mock_response_obj.model_dump()}]
    expected_response_history = [
        ChatHistoryEntry(id=0, query="q1", response=mock_response_obj, error=None).model_dump()
    ]
    # --- END MODIFIED ---
    mock_file_svc.read_chat_session_history.return_value = mock_history_from_file
    mock_file_svc.get_chat_sessions_metadata.return_value = {SESSION_ID_1: {"name": "Test Session"}}

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chat_history/{SESSION_ID_1}")

    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # --- MODIFIED: Assert against the fully constructed expected data ---
    assert response_data["history"] == expected_response_history
    # --- END MODIFIED ---

    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    mock_file_svc.read_chat_session_history.assert_called_once_with(PROJECT_ID, SESSION_ID_1)

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_get_chat_history_session_not_found(mock_project_dep, mock_file_svc):
    """Test getting history for a non-existent session (returns empty list)."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    mock_file_svc.read_chat_session_history.return_value = [] # Service returns empty list
    mock_file_svc.get_chat_sessions_metadata.return_value = {} # Metadata also missing

    response = client.get(f"/api/v1/projects/{PROJECT_ID}/chat_history/{NON_EXISTENT_SESSION_ID}")

    assert response.status_code == status.HTTP_200_OK
    assert response.json()["history"] == []

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_chat_history_success(mock_project_dep, mock_file_svc):
    """Test updating chat history for a specific session."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    # --- MODIFIED: Construct expected response with full model structure ---
    history_data_in = {"history": [{"id": 0, "query": "new q", "error": "new e"}]}
    expected_response_data = {"history": [
        ChatHistoryEntry(id=0, query="new q", response=None, error="new e").model_dump()
    ]}
    # --- END MODIFIED ---
    mock_file_svc.get_chat_sessions_metadata.return_value = {SESSION_ID_1: {"name": "Test Session"}}

    response = client.put(f"/api/v1/projects/{PROJECT_ID}/chat_history/{SESSION_ID_1}", json=history_data_in)

    assert response.status_code == status.HTTP_200_OK
    # --- MODIFIED: Assert against the fully constructed expected data ---
    assert response.json() == expected_response_data
    # --- END MODIFIED ---

    mock_project_dep.get_by_id.assert_called_once_with(project_id=PROJECT_ID)
    # Check the list of dicts passed to file_service (this remains the same)
    expected_history_list = [{"id": 0, "query": "new q", "response": None, "error": "new e"}]
    mock_file_svc.write_chat_session_history.assert_called_once_with(PROJECT_ID, SESSION_ID_1, expected_history_list)

@patch('app.api.v1.endpoints.chat_history.file_service', autospec=True)
@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_chat_history_session_metadata_missing(mock_project_dep, mock_file_svc):
    """Test updating history when session metadata is missing (should still work)."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    # --- MODIFIED: Construct expected response with full model structure ---
    history_data_in = {"history": [{"id": 0, "query": "q"}]}
    expected_response_data = {"history": [
        ChatHistoryEntry(id=0, query="q", response=None, error=None).model_dump()
    ]}
    # --- END MODIFIED ---
    mock_file_svc.get_chat_sessions_metadata.return_value = {} # Metadata missing

    response = client.put(f"/api/v1/projects/{PROJECT_ID}/chat_history/{SESSION_ID_1}", json=history_data_in)

    assert response.status_code == status.HTTP_200_OK
    # --- MODIFIED: Assert against the fully constructed expected data ---
    assert response.json() == expected_response_data
    # --- END MODIFIED ---
    expected_history_list = [{"id": 0, "query": "q", "response": None, "error": None}]
    mock_file_svc.write_chat_session_history.assert_called_once_with(PROJECT_ID, SESSION_ID_1, expected_history_list)

@patch('app.api.v1.endpoints.content_blocks.project_service', autospec=True)
def test_update_chat_history_validation_error(mock_project_dep):
    """Test updating history with invalid data format."""
    mock_project_dep.get_by_id.side_effect = mock_project_exists
    invalid_data = {"history": [{"id": "not-an-int", "query": "q"}]} # Invalid ID type

    response = client.put(f"/api/v1/projects/{PROJECT_ID}/chat_history/{SESSION_ID_1}", json=invalid_data)

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    assert response.json()['detail'][0]['loc'] == ['body', 'history', 0, 'id']