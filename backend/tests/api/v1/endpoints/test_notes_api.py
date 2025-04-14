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
from unittest.mock import patch, MagicMock, ANY
import time
from fastapi import HTTPException # Import HTTPException for mocking side effects

# Import the FastAPI app instance and models
from app.main import app
from app.models.note import NoteCreate, NoteUpdate, NoteRead, NoteList, NoteReadBasic, NoteTree, NoteTreeNode
from app.models.common import Message
from app.services.note_service import note_service # Import the actual service instance to mock its methods

# --- Fixtures ---

@pytest.fixture(scope="module")
def client():
    # Mock the project dependency check for all tests in this module
    # This prevents API tests from failing if the underlying project service/file service
    # isn't fully mocked or set up for the specific project ID used in tests.
    async def override_get_project_dependency(project_id: str):
        # Simply return the project_id, assuming it exists for the purpose of these API tests
        # The service layer tests should handle actual project existence checks.
        return project_id

    from app.api.v1.endpoints.content_blocks import get_project_dependency
    app.dependency_overrides[get_project_dependency] = override_get_project_dependency
    yield TestClient(app)
    # Clean up the override after tests are done
    app.dependency_overrides = {}


@pytest.fixture(autouse=True)
def mock_note_service_methods():
    """Automatically mock all methods of the note_service instance before each test."""
    with patch.object(note_service, 'create', autospec=True) as mock_create, \
         patch.object(note_service, 'get_all_for_project', autospec=True) as mock_get_all, \
         patch.object(note_service, 'get_by_id', autospec=True) as mock_get_by_id, \
         patch.object(note_service, 'update', autospec=True) as mock_update, \
         patch.object(note_service, 'delete', autospec=True) as mock_delete, \
         patch.object(note_service, 'get_note_tree', autospec=True) as mock_get_tree, \
         patch.object(note_service, 'rename_folder', autospec=True) as mock_rename, \
         patch.object(note_service, 'delete_folder', autospec=True) as mock_delete_folder:

        # Provide default return values (can be overridden in tests)
        mock_create.return_value = NoteRead(id="new_note", project_id="proj1", title="New", content="...", folder_path="/", last_modified=time.time())
        mock_get_all.return_value = NoteList(notes=[])
        mock_get_by_id.return_value = NoteRead(id="note1", project_id="proj1", title="Test", content="...", folder_path="/", last_modified=time.time())
        mock_update.return_value = NoteRead(id="note1", project_id="proj1", title="Updated", content="...", folder_path="/New", last_modified=time.time())
        mock_delete.return_value = None # Delete returns None on success
        mock_get_tree.return_value = NoteTree(tree=[])
        mock_rename.return_value = None
        mock_delete_folder.return_value = None

        yield {
            "create": mock_create,
            "get_all": mock_get_all,
            "get_by_id": mock_get_by_id,
            "update": mock_update,
            "delete": mock_delete,
            "get_tree": mock_get_tree,
            "rename_folder": mock_rename,
            "delete_folder": mock_delete_folder,
        }

# --- Test CRUD Endpoints (Updated for folder_path) ---

def test_create_note_api(client: TestClient, mock_note_service_methods):
    project_id = "proj_create"
    note_data = {"title": "API Note", "content": "API Content", "folder_path": "/API_Folder"}
    mock_note_service_methods["create"].return_value = NoteRead(
        id="api_note_1", project_id=project_id, title=note_data["title"],
        content=note_data["content"], folder_path=note_data["folder_path"], last_modified=time.time()
    )

    response = client.post(f"/api/v1/projects/{project_id}/notes/", json=note_data)

    assert response.status_code == 201
    data = response.json()
    assert data["id"] == "api_note_1"
    assert data["title"] == note_data["title"]
    assert data["content"] == note_data["content"]
    assert data["folder_path"] == note_data["folder_path"]
    assert data["project_id"] == project_id
    mock_note_service_methods["create"].assert_called_once_with(project_id=project_id, note_in=ANY)
    # Check the NoteCreate object passed to the service
    call_args, call_kwargs = mock_note_service_methods["create"].call_args
    assert call_kwargs['note_in'].title == note_data["title"]
    assert call_kwargs['note_in'].content == note_data["content"]
    assert call_kwargs['note_in'].folder_path == note_data["folder_path"]

def test_list_notes_api(client: TestClient, mock_note_service_methods):
    project_id = "proj_list"
    notes_data = [
        NoteReadBasic(id="n1", project_id=project_id, title="N1", folder_path="/", last_modified=time.time()),
        NoteReadBasic(id="n2", project_id=project_id, title="N2", folder_path="/Sub", last_modified=time.time()-10),
    ]
    mock_note_service_methods["get_all"].return_value = NoteList(notes=notes_data)

    response = client.get(f"/api/v1/projects/{project_id}/notes/")

    assert response.status_code == 200
    data = response.json()
    assert len(data["notes"]) == 2
    assert data["notes"][0]["id"] == "n1"
    assert data["notes"][0]["folder_path"] == "/"
    assert data["notes"][1]["id"] == "n2"
    assert data["notes"][1]["folder_path"] == "/Sub"
    mock_note_service_methods["get_all"].assert_called_once_with(project_id=project_id)

def test_get_note_api(client: TestClient, mock_note_service_methods):
    project_id = "proj_get"
    note_id = "note_abc"
    note_data = NoteRead(
        id=note_id, project_id=project_id, title="Get Me", content="Details...",
        folder_path="/GetFolder", last_modified=time.time()
    )
    mock_note_service_methods["get_by_id"].return_value = note_data

    response = client.get(f"/api/v1/projects/{project_id}/notes/{note_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == note_id
    assert data["title"] == note_data.title
    assert data["content"] == note_data.content
    assert data["folder_path"] == note_data.folder_path
    mock_note_service_methods["get_by_id"].assert_called_once_with(project_id=project_id, note_id=note_id)

def test_update_note_api(client: TestClient, mock_note_service_methods):
    project_id = "proj_update"
    note_id = "note_xyz"
    update_data = {"title": "Updated Title", "folder_path": "/UpdatedPath"}
    updated_note_data = NoteRead(
        id=note_id, project_id=project_id, title=update_data["title"], content="Original Content",
        folder_path=update_data["folder_path"], last_modified=time.time()
    )
    mock_note_service_methods["update"].return_value = updated_note_data

    response = client.patch(f"/api/v1/projects/{project_id}/notes/{note_id}", json=update_data)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == note_id
    assert data["title"] == update_data["title"]
    assert data["folder_path"] == update_data["folder_path"]
    mock_note_service_methods["update"].assert_called_once_with(project_id=project_id, note_id=note_id, note_in=ANY)
    # Check the NoteUpdate object passed to the service
    call_args, call_kwargs = mock_note_service_methods["update"].call_args
    assert call_kwargs['note_in'].title == update_data["title"]
    assert call_kwargs['note_in'].folder_path == update_data["folder_path"]
    assert call_kwargs['note_in'].content is None # Content was not in update_data

def test_delete_note_api(client: TestClient, mock_note_service_methods):
    project_id = "proj_delete"
    note_id = "note_todelete"

    # DELETE for a specific note ID does NOT have a body, so client.delete is fine
    response = client.delete(f"/api/v1/projects/{project_id}/notes/{note_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Note {note_id} deleted successfully"
    mock_note_service_methods["delete"].assert_called_once_with(project_id=project_id, note_id=note_id)

# --- Test New Folder Management Endpoints ---

def test_get_note_tree_api(client: TestClient, mock_note_service_methods):
    project_id = "proj_tree"
    tree_data = NoteTree(tree=[
        NoteTreeNode(id="/FolderA", name="FolderA", type="folder", path="/FolderA", children=[
            NoteTreeNode(id="note1", name="Note 1", type="note", path="/FolderA", note_id="note1", last_modified=time.time())
        ]),
        NoteTreeNode(id="note_root", name="Root Note", type="note", path="/", note_id="note_root", last_modified=time.time())
    ])
    mock_note_service_methods["get_tree"].return_value = tree_data

    response = client.get(f"/api/v1/projects/{project_id}/notes/tree")

    assert response.status_code == 200
    data = response.json()
    assert len(data["tree"]) == 2
    assert data["tree"][0]["id"] == "/FolderA"
    assert data["tree"][0]["type"] == "folder"
    assert len(data["tree"][0]["children"]) == 1
    assert data["tree"][0]["children"][0]["id"] == "note1"
    assert data["tree"][1]["id"] == "note_root"
    assert data["tree"][1]["type"] == "note"
    mock_note_service_methods["get_tree"].assert_called_once_with(project_id=project_id)

def test_rename_folder_api(client: TestClient, mock_note_service_methods):
    project_id = "proj_rename"
    rename_data = {"old_path": "/OldName", "new_path": "/NewName"}

    # PATCH uses json parameter correctly
    response = client.patch(f"/api/v1/projects/{project_id}/notes/folders", json=rename_data)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Folder '{rename_data['old_path']}' renamed to '{rename_data['new_path']}' successfully."
    mock_note_service_methods["rename_folder"].assert_called_once_with(
        project_id=project_id,
        old_path=rename_data["old_path"],
        new_path=rename_data["new_path"]
    )

def test_delete_folder_api_non_recursive(client: TestClient, mock_note_service_methods):
    project_id = "proj_delete_folder"
    delete_data = {"path": "/ToDelete", "recursive": False}
    url = f"/api/v1/projects/{project_id}/notes/folders"

    # Use client.request for DELETE with body
    response = client.request("DELETE", url, json=delete_data)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Folder '{delete_data['path']}' deleted successfully."
    mock_note_service_methods["delete_folder"].assert_called_once_with(
        project_id=project_id,
        path=delete_data["path"],
        recursive=delete_data["recursive"]
    )

def test_delete_folder_api_recursive(client: TestClient, mock_note_service_methods):
    project_id = "proj_delete_folder_rec"
    delete_data = {"path": "/ToDeleteRec", "recursive": True}
    url = f"/api/v1/projects/{project_id}/notes/folders"

    # Use client.request for DELETE with body
    response = client.request("DELETE", url, json=delete_data)

    assert response.status_code == 200
    data = response.json()
    assert data["message"] == f"Folder '{delete_data['path']}' deleted successfully."
    mock_note_service_methods["delete_folder"].assert_called_once_with(
        project_id=project_id,
        path=delete_data["path"],
        recursive=delete_data["recursive"]
    )

# --- Test Error Handling ---

def test_get_note_api_not_found(client: TestClient, mock_note_service_methods):
    project_id = "proj_get_404"
    note_id = "not_found_note"
    mock_note_service_methods["get_by_id"].side_effect = HTTPException(status_code=404, detail=f"Note {note_id} not found")

    response = client.get(f"/api/v1/projects/{project_id}/notes/{note_id}")

    assert response.status_code == 404
    assert note_id in response.json()["detail"]
    mock_note_service_methods["get_by_id"].assert_called_once_with(project_id=project_id, note_id=note_id)

def test_rename_folder_api_conflict(client: TestClient, mock_note_service_methods):
    project_id = "proj_rename_409"
    rename_data = {"old_path": "/Old", "new_path": "/Conflict"}
    mock_note_service_methods["rename_folder"].side_effect = HTTPException(status_code=409, detail="Target path '/Conflict' conflicts")

    response = client.patch(f"/api/v1/projects/{project_id}/notes/folders", json=rename_data)

    assert response.status_code == 409
    assert "conflicts" in response.json()["detail"]
    mock_note_service_methods["rename_folder"].assert_called_once_with(
        project_id=project_id, old_path=rename_data["old_path"], new_path=rename_data["new_path"]
    )

def test_delete_folder_api_not_empty_non_recursive(client: TestClient, mock_note_service_methods):
    project_id = "proj_delete_409"
    delete_data = {"path": "/NotEmpty", "recursive": False}
    url = f"/api/v1/projects/{project_id}/notes/folders"
    mock_note_service_methods["delete_folder"].side_effect = HTTPException(status_code=409, detail="Folder '/NotEmpty' is not empty")

    # Use client.request for DELETE with body
    response = client.request("DELETE", url, json=delete_data)

    assert response.status_code == 409
    assert "not empty" in response.json()["detail"]
    mock_note_service_methods["delete_folder"].assert_called_once_with(
        project_id=project_id, path=delete_data["path"], recursive=delete_data["recursive"]
    )

def test_create_note_api_invalid_path(client: TestClient, mock_note_service_methods):
    project_id = "proj_create_invalid"
    note_data = {"title": "Invalid Path Note", "folder_path": "no-leading-slash"}
    # Mock the service to raise the validation error
    mock_note_service_methods["create"].side_effect = HTTPException(status_code=400, detail="Folder path must start with '/'")

    response = client.post(f"/api/v1/projects/{project_id}/notes/", json=note_data)

    assert response.status_code == 400
    assert "Folder path must start with '/'" in response.json()["detail"]
    mock_note_service_methods["create"].assert_called_once() # Service method was called

def test_update_note_api_no_fields(client: TestClient, mock_note_service_methods):
    project_id = "proj_update_empty"
    note_id = "note_empty_update"
    update_data = {} # Empty update body

    response = client.patch(f"/api/v1/projects/{project_id}/notes/{note_id}", json=update_data)

    assert response.status_code == 400 # Should be caught by the endpoint itself
    assert "No fields provided for update" in response.json()["detail"]
    mock_note_service_methods["update"].assert_not_called() # Service should not be called