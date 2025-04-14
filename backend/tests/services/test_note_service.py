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
from unittest.mock import patch, MagicMock, call, ANY
from fastapi import HTTPException, status
import time
from pathlib import Path

# Import the service instance we are testing
from app.services.note_service import note_service, NoteService
from app.models.note import NoteCreate, NoteUpdate, NoteRead, NoteList, NoteReadBasic, NoteTree, NoteTreeNode
from app.models.project import ProjectRead # For mocking project service
from app.core.config import BASE_PROJECT_DIR

# --- Fixtures ---

@pytest.fixture
def mock_project_service():
    with patch('app.services.note_service.project_service', autospec=True) as mock_ps:
        mock_ps.get_by_id.return_value = ProjectRead(id="test_proj_id", name="Test Project", last_modified=time.time())
        yield mock_ps

@pytest.fixture
def mock_file_service():
    with patch('app.services.note_service.file_service', autospec=True) as mock_fs:
        # Default mock behaviors (can be overridden in tests)
        mock_fs.read_project_metadata.return_value = {"notes": {}}
        mock_fs.write_project_metadata.return_value = None
        mock_fs.write_text_file.return_value = None
        mock_fs.read_text_file.return_value = "Default note content"
        mock_fs.delete_file.return_value = None
        mock_fs.path_exists.return_value = True # Assume paths exist by default
        mock_fs._get_note_path.side_effect = lambda project_id, note_id: BASE_PROJECT_DIR / project_id / "notes" / f"{note_id}.md"
        mock_fs.get_file_mtime.return_value = time.time()
        yield mock_fs

@pytest.fixture
def mock_uuid():
    with patch('app.services.note_service.generate_uuid') as mock_gen_uuid:
        mock_gen_uuid.return_value = "mock_note_uuid_1"
        yield mock_gen_uuid

# --- Test _validate_folder_path ---

def test_validate_folder_path_valid():
    assert note_service._validate_folder_path("/") == "/"
    assert note_service._validate_folder_path("/folder") == "/folder"
    assert note_service._validate_folder_path("/folder/sub") == "/folder/sub"
    assert note_service._validate_folder_path(" /folder/sub ") == "/folder/sub" # Strips whitespace
    assert note_service._validate_folder_path("/folder/sub/") == "/folder/sub" # Removes trailing slash
    assert note_service._validate_folder_path(None) == "/" # Handles None
    assert note_service._validate_folder_path("") == "/" # Handles empty string
    assert note_service._validate_folder_path("  ") == "/" # Handles whitespace string

def test_validate_folder_path_invalid():
    with pytest.raises(HTTPException) as excinfo:
        note_service._validate_folder_path("folder") # Missing leading slash
    assert excinfo.value.status_code == 400

    with pytest.raises(HTTPException) as excinfo:
        note_service._validate_folder_path("/folder//sub") # Contains //
    assert excinfo.value.status_code == 400

# --- Test CRUD Operations with folder_path ---

def test_create_note_success(mock_project_service, mock_file_service, mock_uuid):
    project_id = "test_proj_id"
    note_in = NoteCreate(title="My Note", content="Note details", folder_path="/Ideas")
    mock_file_service.read_project_metadata.return_value = {"notes": {}} # Start empty
    current_time = time.time()
    mock_file_service.get_file_mtime.return_value = current_time

    created_note = note_service.create(project_id=project_id, note_in=note_in)

    assert created_note.id == "mock_note_uuid_1"
    assert created_note.title == note_in.title
    assert created_note.content == note_in.content
    assert created_note.folder_path == "/Ideas" # Validated path
    assert created_note.last_modified == current_time
    assert created_note.project_id == project_id

    mock_project_service.get_by_id.assert_called_once_with(project_id=project_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id=project_id)
    mock_file_service.write_project_metadata.assert_called_once_with(
        project_id=project_id,
        data={"notes": {"mock_note_uuid_1": {"title": "My Note", "folder_path": "/Ideas"}}}
    )
    expected_path = BASE_PROJECT_DIR / project_id / "notes" / "mock_note_uuid_1.md"
    mock_file_service.write_text_file.assert_called_once_with(path=expected_path, content=note_in.content, trigger_index=True)
    mock_file_service.get_file_mtime.assert_called_once_with(expected_path)

def test_create_note_default_folder_path(mock_project_service, mock_file_service, mock_uuid):
    project_id = "test_proj_id"
    note_in = NoteCreate(title="Root Note", content="Details") # No folder_path provided
    mock_file_service.read_project_metadata.return_value = {"notes": {}}

    created_note = note_service.create(project_id=project_id, note_in=note_in)

    assert created_note.folder_path == "/"
    mock_file_service.write_project_metadata.assert_called_once_with(
        project_id=project_id,
        data={"notes": {"mock_note_uuid_1": {"title": "Root Note", "folder_path": "/"}}}
    )

def test_get_note_by_id_success(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    note_id = "note1"
    mock_file_service.read_project_metadata.return_value = {
        "notes": {note_id: {"title": "Existing Note", "folder_path": "/ExistingFolder"}}
    }
    mock_file_service.read_text_file.return_value = "Content of note 1"
    current_time = time.time()
    mock_file_service.get_file_mtime.return_value = current_time
    expected_path = BASE_PROJECT_DIR / project_id / "notes" / f"{note_id}.md"

    note = note_service.get_by_id(project_id=project_id, note_id=note_id)

    assert note.id == note_id
    assert note.title == "Existing Note"
    assert note.content == "Content of note 1"
    assert note.folder_path == "/ExistingFolder"
    assert note.last_modified == current_time
    assert note.project_id == project_id

    mock_project_service.get_by_id.assert_called_once_with(project_id=project_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id=project_id)
    mock_file_service.read_text_file.assert_called_once_with(path=expected_path)
    mock_file_service.get_file_mtime.assert_called_once_with(expected_path)

def test_get_note_by_id_missing_folder_path_in_meta(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    note_id = "note_old_meta"
    mock_file_service.read_project_metadata.return_value = {
        "notes": {note_id: {"title": "Old Note"}} # Missing folder_path
    }
    note = note_service.get_by_id(project_id=project_id, note_id=note_id)
    assert note.folder_path == "/" # Should default to root

def test_get_all_notes_success(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    time1 = time.time() - 100
    time2 = time.time() - 50
    mock_file_service.read_project_metadata.return_value = {
        "notes": {
            "note1": {"title": "Note One", "folder_path": "/FolderA"},
            "note2": {"title": "Note Two", "folder_path": "/"},
            "note3": {"title": "Note Three"} # Missing path
        }
    }
    # Mock mtime to control sorting
    mock_file_service.get_file_mtime.side_effect = [time1, time2, 0.0] # note2 is newest, note3 has no mtime

    note_list = note_service.get_all_for_project(project_id=project_id)

    assert len(note_list.notes) == 3
    # Check sorting (note2 newest, then note1, then note3 with 0.0 mtime)
    assert note_list.notes[0].id == "note2"
    assert note_list.notes[1].id == "note1"
    assert note_list.notes[2].id == "note3"

    # Check content
    assert note_list.notes[0].title == "Note Two"
    assert note_list.notes[0].folder_path == "/"
    assert note_list.notes[0].last_modified == time2

    assert note_list.notes[1].title == "Note One"
    assert note_list.notes[1].folder_path == "/FolderA"
    assert note_list.notes[1].last_modified == time1

    assert note_list.notes[2].title == "Note Three"
    assert note_list.notes[2].folder_path == "/" # Defaulted
    assert note_list.notes[2].last_modified == 0.0

    mock_project_service.get_by_id.assert_called_once_with(project_id=project_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id=project_id)
    assert mock_file_service.get_file_mtime.call_count == 3

def test_update_note_folder_path(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    note_id = "note_to_move"
    initial_meta = {
        "notes": {note_id: {"title": "Move Me", "folder_path": "/OldFolder"}}
    }
    mock_file_service.read_project_metadata.return_value = initial_meta
    mock_file_service.read_text_file.return_value = "Content"
    mock_file_service.get_file_mtime.return_value = time.time()

    update_data = NoteUpdate(folder_path="/NewFolder/Sub")

    updated_note = note_service.update(project_id=project_id, note_id=note_id, note_in=update_data)

    assert updated_note.folder_path == "/NewFolder/Sub"
    assert updated_note.title == "Move Me" # Title not updated
    assert updated_note.content == "Content" # Content not updated

    # Check that metadata write was called with updated path
    mock_file_service.write_project_metadata.assert_called_once()
    args, kwargs = mock_file_service.write_project_metadata.call_args
    assert kwargs['project_id'] == project_id
    assert kwargs['data']['notes'][note_id]['folder_path'] == "/NewFolder/Sub"
    assert kwargs['data']['notes'][note_id]['title'] == "Move Me"

    # Check that content file write was NOT called
    mock_file_service.write_text_file.assert_not_called()

def test_update_note_all_fields(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    note_id = "note_update_all"
    initial_meta = {
        "notes": {note_id: {"title": "Old Title", "folder_path": "/Old"}}
    }
    mock_file_service.read_project_metadata.return_value = initial_meta
    mock_file_service.read_text_file.return_value = "Old Content"
    mock_file_service.get_file_mtime.return_value = time.time()

    update_data = NoteUpdate(title="New Title", content="New Content", folder_path="/New")

    updated_note = note_service.update(project_id=project_id, note_id=note_id, note_in=update_data)

    assert updated_note.title == "New Title"
    assert updated_note.content == "New Content"
    assert updated_note.folder_path == "/New"

    # Check metadata write
    mock_file_service.write_project_metadata.assert_called_once()
    args, kwargs = mock_file_service.write_project_metadata.call_args
    assert kwargs['data']['notes'][note_id]['title'] == "New Title"
    assert kwargs['data']['notes'][note_id]['folder_path'] == "/New"

    # Check content file write
    expected_path = BASE_PROJECT_DIR / project_id / "notes" / f"{note_id}.md"
    mock_file_service.write_text_file.assert_called_once_with(path=expected_path, content="New Content", trigger_index=True)

def test_delete_note_success(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    note_id = "note_to_delete"
    initial_meta = {
        "notes": {note_id: {"title": "Delete Me", "folder_path": "/"}}
    }
    mock_file_service.read_project_metadata.return_value = initial_meta
    mock_file_service.path_exists.return_value = True # File exists

    note_service.delete(project_id=project_id, note_id=note_id)

    # Check file deletion was called
    expected_path = BASE_PROJECT_DIR / project_id / "notes" / f"{note_id}.md"
    mock_file_service.delete_file.assert_called_once_with(path=expected_path)

    # Check metadata write was called with note removed
    mock_file_service.write_project_metadata.assert_called_once()
    args, kwargs = mock_file_service.write_project_metadata.call_args
    assert note_id not in kwargs['data']['notes']

# --- Test get_note_tree ---

def test_get_note_tree_empty(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    mock_file_service.read_project_metadata.return_value = {"notes": {}}
    tree = note_service.get_note_tree(project_id=project_id)
    assert tree.tree == []

def test_get_note_tree_flat(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    time1 = time.time() - 10
    time2 = time.time() - 5
    mock_file_service.read_project_metadata.return_value = {
        "notes": {
            "note_b": {"title": "Note B", "folder_path": "/"},
            "note_a": {"title": "Note A", "folder_path": "/"},
        }
    }
    mock_file_service.get_file_mtime.side_effect = lambda path: time1 if "note_a" in str(path) else time2
    tree = note_service.get_note_tree(project_id=project_id)

    assert len(tree.tree) == 2
    # Check sorting (alphabetical for notes at same level)
    assert tree.tree[0].id == "note_a"
    assert tree.tree[0].name == "Note A"
    assert tree.tree[0].type == "note"
    assert tree.tree[0].path == "/"
    assert tree.tree[0].note_id == "note_a"
    assert tree.tree[0].last_modified == time1
    assert tree.tree[0].children == []

    assert tree.tree[1].id == "note_b"
    assert tree.tree[1].name == "Note B"
    assert tree.tree[1].type == "note"
    assert tree.tree[1].path == "/"
    assert tree.tree[1].note_id == "note_b"
    assert tree.tree[1].last_modified == time2
    assert tree.tree[1].children == []

def test_get_note_tree_nested(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    mock_file_service.read_project_metadata.return_value = {
        "notes": {
            "note_root": {"title": "Root Note", "folder_path": "/"},
            "note_c1": {"title": "C1 Note", "folder_path": "/FolderC"},
            "note_a1": {"title": "A1 Note", "folder_path": "/FolderA"},
            "note_a2": {"title": "A2 Note", "folder_path": "/FolderA/SubA"},
            "note_b1": {"title": "B1 Note", "folder_path": "/FolderB"},
        }
    }
    # Mock mtime just to return something
    mock_file_service.get_file_mtime.return_value = time.time()

    tree = note_service.get_note_tree(project_id=project_id)

    assert len(tree.tree) == 4 # 3 Folders + 1 Root Note
    # Check sorting (Folders first, then notes, then alpha)
    assert tree.tree[0].type == "folder"
    assert tree.tree[0].name == "FolderA"
    assert tree.tree[0].path == "/FolderA"
    assert tree.tree[0].id == "/FolderA"

    assert tree.tree[1].type == "folder"
    assert tree.tree[1].name == "FolderB"
    assert tree.tree[1].path == "/FolderB"

    assert tree.tree[2].type == "folder"
    assert tree.tree[2].name == "FolderC"
    assert tree.tree[2].path == "/FolderC"

    assert tree.tree[3].type == "note"
    assert tree.tree[3].name == "Root Note"
    assert tree.tree[3].path == "/"
    assert tree.tree[3].id == "note_root"

    # Check children of FolderA (Subfolder first, then note, alpha)
    folder_a_node = tree.tree[0]
    assert len(folder_a_node.children) == 2
    assert folder_a_node.children[0].type == "folder"
    assert folder_a_node.children[0].name == "SubA"
    assert folder_a_node.children[0].path == "/FolderA/SubA"
    assert folder_a_node.children[1].type == "note"
    assert folder_a_node.children[1].name == "A1 Note"
    assert folder_a_node.children[1].path == "/FolderA" # Note path is parent folder
    assert folder_a_node.children[1].id == "note_a1"

    # Check children of SubA
    sub_a_node = folder_a_node.children[0]
    assert len(sub_a_node.children) == 1
    assert sub_a_node.children[0].type == "note"
    assert sub_a_node.children[0].name == "A2 Note"
    assert sub_a_node.children[0].id == "note_a2"

    # Check children of FolderB
    folder_b_node = tree.tree[1]
    assert len(folder_b_node.children) == 1
    assert folder_b_node.children[0].type == "note"
    assert folder_b_node.children[0].name == "B1 Note"

    # Check children of FolderC
    folder_c_node = tree.tree[2]
    assert len(folder_c_node.children) == 1
    assert folder_c_node.children[0].type == "note"
    assert folder_c_node.children[0].name == "C1 Note"


# --- Test rename_folder ---

def test_rename_folder_success(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    initial_meta = {
        "notes": {
            "note1": {"title": "N1", "folder_path": "/Old"},
            "note2": {"title": "N2", "folder_path": "/Old/Sub"},
            "note3": {"title": "N3", "folder_path": "/Other"},
        }
    }
    mock_file_service.read_project_metadata.return_value = initial_meta

    note_service.rename_folder(project_id=project_id, old_path="/Old", new_path="/New")

    mock_file_service.write_project_metadata.assert_called_once()
    args, kwargs = mock_file_service.write_project_metadata.call_args
    updated_meta = kwargs['data']

    assert updated_meta['notes']['note1']['folder_path'] == "/New"
    assert updated_meta['notes']['note2']['folder_path'] == "/New/Sub"
    assert updated_meta['notes']['note3']['folder_path'] == "/Other" # Unchanged

def test_rename_folder_no_notes_found(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    initial_meta = { "notes": { "note1": {"title": "N1", "folder_path": "/Other"} } }
    mock_file_service.read_project_metadata.return_value = initial_meta

    # Attempt to rename a folder that doesn't contain any notes
    note_service.rename_folder(project_id=project_id, old_path="/NonExistent", new_path="/New")

    # Should not write metadata if no changes were made
    mock_file_service.write_project_metadata.assert_not_called()

def test_rename_folder_invalid_paths(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    with pytest.raises(HTTPException) as excinfo:
        note_service.rename_folder(project_id=project_id, old_path="/", new_path="/New")
    assert excinfo.value.status_code == 400
    assert "Cannot rename the root folder" in excinfo.value.detail

    with pytest.raises(HTTPException) as excinfo:
        note_service.rename_folder(project_id=project_id, old_path="/Old", new_path="/")
    assert excinfo.value.status_code == 400
    assert "Cannot rename a folder to root" in excinfo.value.detail

    with pytest.raises(HTTPException) as excinfo:
        note_service.rename_folder(project_id=project_id, old_path="/Same", new_path="/Same")
    assert excinfo.value.status_code == 400
    assert "Old and new paths are the same" in excinfo.value.detail

def test_rename_folder_conflict(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    initial_meta = {
        "notes": {
            "note1": {"title": "N1", "folder_path": "/Old"},
            "note2": {"title": "N2", "folder_path": "/Existing"}, # Target path exists
        }
    }
    mock_file_service.read_project_metadata.return_value = initial_meta

    with pytest.raises(HTTPException) as excinfo:
        note_service.rename_folder(project_id=project_id, old_path="/Old", new_path="/Existing")
    assert excinfo.value.status_code == 409 # Conflict
    assert "conflicts with an existing folder" in excinfo.value.detail


# --- Test delete_folder ---

def test_delete_folder_empty(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    initial_meta = { "notes": { "note1": {"title": "N1", "folder_path": "/Other"} } }
    mock_file_service.read_project_metadata.return_value = initial_meta

    # Delete a folder path not referenced by any notes
    note_service.delete_folder(project_id=project_id, path="/EmptyFolder", recursive=False)

    # No files should be deleted, no metadata written
    mock_file_service.delete_file.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_delete_folder_not_empty_non_recursive(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    initial_meta = { "notes": { "note1": {"title": "N1", "folder_path": "/NotEmpty"} } }
    mock_file_service.read_project_metadata.return_value = initial_meta

    with pytest.raises(HTTPException) as excinfo:
        note_service.delete_folder(project_id=project_id, path="/NotEmpty", recursive=False)
    assert excinfo.value.status_code == 409 # Conflict
    assert "Folder '/NotEmpty' is not empty" in excinfo.value.detail

    mock_file_service.delete_file.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_delete_folder_not_empty_recursive_success(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    initial_meta = {
        "notes": {
            "note1": {"title": "N1", "folder_path": "/ToDelete"},
            "note2": {"title": "N2", "folder_path": "/ToDelete/Sub"},
            "note3": {"title": "N3", "folder_path": "/Other"},
        }
    }
    mock_file_service.read_project_metadata.return_value = initial_meta
    mock_file_service.path_exists.return_value = True # Files exist

    note_service.delete_folder(project_id=project_id, path="/ToDelete", recursive=True)

    # Check that delete_file was called for note1 and note2
    expected_path1 = BASE_PROJECT_DIR / project_id / "notes" / "note1.md"
    expected_path2 = BASE_PROJECT_DIR / project_id / "notes" / "note2.md"
    mock_file_service.delete_file.assert_has_calls([
        call(path=expected_path1),
        call(path=expected_path2)
    ], any_order=True)
    assert mock_file_service.delete_file.call_count == 2

    # Check metadata write removed note1 and note2
    mock_file_service.write_project_metadata.assert_called_once()
    args, kwargs = mock_file_service.write_project_metadata.call_args
    updated_meta = kwargs['data']
    assert "note1" not in updated_meta['notes']
    assert "note2" not in updated_meta['notes']
    assert "note3" in updated_meta['notes'] # note3 should remain

def test_delete_folder_recursive_file_delete_error(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    initial_meta = {
        "notes": {
            "note1": {"title": "N1", "folder_path": "/ToDelete"}, # This one fails delete
            "note2": {"title": "N2", "folder_path": "/ToDelete/Sub"}, # This one succeeds
        }
    }
    mock_file_service.read_project_metadata.return_value = initial_meta
    mock_file_service.path_exists.return_value = True

    # Make delete_file fail for note1
    expected_path1 = BASE_PROJECT_DIR / project_id / "notes" / "note1.md"
    expected_path2 = BASE_PROJECT_DIR / project_id / "notes" / "note2.md"
    def delete_side_effect(path):
        if path == expected_path1:
            raise HTTPException(status_code=500, detail="Disk error")
        elif path == expected_path2:
            return None # Success
        else:
            pytest.fail(f"Unexpected call to delete_file with path: {path}")
    mock_file_service.delete_file.side_effect = delete_side_effect

    # Service should log the error but continue and update metadata for successful deletions
    note_service.delete_folder(project_id=project_id, path="/ToDelete", recursive=True)

    # Check delete_file was called for both
    mock_file_service.delete_file.assert_has_calls([
        call(path=expected_path1),
        call(path=expected_path2)
    ], any_order=True)

    # Check metadata write removed only note2 (since note1 failed deletion)
    mock_file_service.write_project_metadata.assert_called_once()
    args, kwargs = mock_file_service.write_project_metadata.call_args
    updated_meta = kwargs['data']
    assert "note1" in updated_meta['notes'] # note1 remains because delete failed
    assert "note2" not in updated_meta['notes'] # note2 removed

def test_delete_folder_root(mock_project_service, mock_file_service):
    project_id = "test_proj_id"
    with pytest.raises(HTTPException) as excinfo:
        note_service.delete_folder(project_id=project_id, path="/", recursive=True)
    assert excinfo.value.status_code == 400
    assert "Cannot delete the root folder" in excinfo.value.detail