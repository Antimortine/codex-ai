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
from unittest.mock import MagicMock, patch, call, ANY
from fastapi import HTTPException, status
from pathlib import Path
import uuid
import re # Import re
import copy # Import copy

# Import the *class* we are testing, not the singleton instance
from app.services.chapter_service import ChapterService
# Import classes for dependencies
from app.services.file_service import FileService
from app.services.project_service import ProjectService
# --- ADDED: Import SceneService for mocking ---
from app.services.scene_service import SceneService
# --- END ADDED ---
# Import models used in responses/arguments
from app.models.chapter import ChapterCreate, ChapterUpdate, ChapterRead, ChapterList
from app.models.project import ProjectRead # Needed for mocking project_service.get_by_id
# --- ADDED: Import SceneRead ---
from app.models.scene import SceneRead, SceneList # Also import SceneList
# --- END ADDED ---


# --- Test ChapterService Methods ---

# Fixture to create a ChapterService instance with mocked dependencies
@pytest.fixture
def chapter_service_with_mocks():
    mock_file_service = MagicMock(spec=FileService)
    mock_project_service = MagicMock(spec=ProjectService)
    # --- ADDED: Mock SceneService ---
    mock_scene_service = MagicMock(spec=SceneService)
    # --- END ADDED ---

    # Patch the singletons within the chapter_service module's scope AND the scene_service singleton source
    with patch('app.services.chapter_service.file_service', mock_file_service), \
         patch('app.services.chapter_service.project_service', mock_project_service), \
         patch('app.services.scene_service.scene_service', mock_scene_service): # <-- CORRECTED PATCH TARGET
        service_instance = ChapterService()
        # Yield the instance and the mocks for use in tests
        yield service_instance, mock_file_service, mock_project_service, mock_scene_service # Yield scene_service mock

# --- Tests for create ---
# (Unchanged)
def test_create_chapter_success(chapter_service_with_mocks):
    """Test successful chapter creation."""
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-uuid-1"
    chapter_in = ChapterCreate(title="The Beginning", order=1)
    mock_chapter_id = "new-chap-uuid"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{mock_chapter_id}")
    mock_project_metadata = {"project_name": "Test Proj", "chapters": {}, "characters": {}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = False
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    with patch('app.services.chapter_service.generate_uuid', return_value=mock_chapter_id):
        created_chapter = service.create(project_id, chapter_in)
    assert created_chapter.id == mock_chapter_id
    assert created_chapter.project_id == project_id
    assert created_chapter.title == chapter_in.title
    assert created_chapter.order == chapter_in.order
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service._get_chapter_path.assert_called_once_with(project_id, mock_chapter_id)
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path)
    mock_file_service.setup_chapter_structure.assert_called_once_with(project_id, mock_chapter_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    expected_meta_write = {
        "project_name": "Test Proj",
        "chapters": {mock_chapter_id: {"title": chapter_in.title, "order": chapter_in.order}},
        "characters": {}
    }
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, expected_meta_write)

def test_create_chapter_project_not_found(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-uuid-404"
    chapter_in = ChapterCreate(title="Lost Chapter", order=1)
    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")
    with pytest.raises(HTTPException) as exc_info: service.create(project_id, chapter_in)
    assert exc_info.value.status_code == 404
    mock_file_service.setup_chapter_structure.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_create_chapter_id_collision(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-uuid-collide"
    chapter_in = ChapterCreate(title="Collision Course", order=1)
    mock_chapter_id = "colliding-chap-uuid"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{mock_chapter_id}")
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True
    with patch('app.services.chapter_service.generate_uuid', return_value=mock_chapter_id):
        with pytest.raises(HTTPException) as exc_info: service.create(project_id, chapter_in)
    assert exc_info.value.status_code == 409
    mock_file_service.setup_chapter_structure.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_create_chapter_order_conflict(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-uuid-order"
    chapter_in = ChapterCreate(title="Second Chapter 1", order=1)
    mock_chapter_id = "new-chap-uuid"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{mock_chapter_id}")
    mock_project_metadata = {"chapters": {"existing-chap-uuid": {"title": "First Chapter 1", "order": 1}}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = False
    mock_file_service.setup_chapter_structure.return_value = None
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    with patch('app.services.chapter_service.generate_uuid', return_value=mock_chapter_id):
        with pytest.raises(HTTPException) as exc_info: service.create(project_id, chapter_in)
    assert exc_info.value.status_code == 409
    mock_file_service.setup_chapter_structure.assert_called_once_with(project_id, mock_chapter_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    mock_file_service.write_project_metadata.assert_not_called()


# --- Tests for get_by_id ---
# (Unchanged)
def test_get_chapter_by_id_success(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-get-1"
    chapter_id = "chap-get-ok"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"chapters": {chapter_id: {"title": "Found Chapter", "order": 2}}} # Added order
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Get Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True
    chapter = service.get_by_id(project_id, chapter_id)
    assert chapter.id == chapter_id
    assert chapter.title == "Found Chapter"
    assert chapter.order == 2
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    mock_file_service._get_chapter_path.assert_called_once_with(project_id, chapter_id)
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path)

def test_get_chapter_by_id_project_not_found(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-get-404"
    chapter_id = "chap-get-whatever"
    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")
    with pytest.raises(HTTPException) as exc_info: service.get_by_id(project_id, chapter_id)
    assert exc_info.value.status_code == 404
    mock_file_service.read_project_metadata.assert_not_called()

def test_get_chapter_by_id_chapter_not_in_metadata(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-get-meta"
    chapter_id = "chap-get-missing"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"chapters": {}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Meta Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = False
    with pytest.raises(HTTPException) as exc_info: service.get_by_id(project_id, chapter_id)
    assert exc_info.value.status_code == 404
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path)

def test_get_chapter_by_id_directory_missing(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-get-dir"
    chapter_id = "chap-get-no-dir"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"chapters": {chapter_id: {"title": "Ghost Chapter", "order": 1}}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Dir Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = False
    with pytest.raises(HTTPException) as exc_info: service.get_by_id(project_id, chapter_id)
    assert exc_info.value.status_code == 404
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path)

# --- Tests for get_all_for_project ---
# (Unchanged)
def test_get_all_chapters_success(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-list-1"
    chap1_id, chap2_id = "chap-list-b", "chap-list-a"
    # Add order to mock data
    mock_project_metadata = {"chapters": {chap1_id: {"title": "Chapter Two", "order": 2}, chap2_id: {"title": "Chapter One", "order": 1}}}
    mock_path1 = Path(f"user_projects/{project_id}/chapters/{chap1_id}")
    mock_path2 = Path(f"user_projects/{project_id}/chapters/{chap2_id}")
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="List Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.side_effect = lambda p, c: mock_path1 if c == chap1_id else mock_path2 if c == chap2_id else None
    mock_file_service.path_exists.return_value = True
    chapter_list = service.get_all_for_project(project_id)
    assert len(chapter_list.chapters) == 2
    assert chapter_list.chapters[0].id == chap2_id # Order 1
    assert chapter_list.chapters[0].order == 1
    assert chapter_list.chapters[1].id == chap1_id # Order 2
    assert chapter_list.chapters[1].order == 2
    assert mock_file_service.path_exists.call_count == 2

def test_get_all_chapters_empty(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-list-empty"
    mock_project_metadata = {"chapters": {}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Empty Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    chapter_list = service.get_all_for_project(project_id)
    assert len(chapter_list.chapters) == 0
    mock_file_service._get_chapter_path.assert_not_called()
    mock_file_service.path_exists.assert_not_called()

def test_get_all_chapters_project_not_found(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-list-404"
    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")
    with pytest.raises(HTTPException) as exc_info: service.get_all_for_project(project_id)
    assert exc_info.value.status_code == 404
    mock_file_service.read_project_metadata.assert_not_called()

def test_get_all_chapters_skips_missing_dir(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-list-skip"
    chap1_id, chap2_id = "chap-list-ok", "chap-list-missing"
    mock_project_metadata = {"chapters": {chap1_id: {"title": "Exists", "order": 1}, chap2_id: {"title": "Missing Dir", "order": 2}}}
    mock_path1 = Path(f"user_projects/{project_id}/chapters/{chap1_id}")
    mock_path2 = Path(f"user_projects/{project_id}/chapters/{chap2_id}")
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Skip Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.side_effect = lambda p, c: mock_path1 if c == chap1_id else mock_path2 if c == chap2_id else None
    mock_file_service.path_exists.side_effect = lambda path: path == mock_path1
    chapter_list = service.get_all_for_project(project_id)
    assert len(chapter_list.chapters) == 1
    assert chapter_list.chapters[0].id == chap1_id
    assert mock_file_service.path_exists.call_count == 2


# --- Tests for update ---
# (Unchanged)
def test_update_chapter_success_title(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-upd-1"
    chapter_id = "chap-upd-title"
    chapter_in = ChapterUpdate(title="New Title")
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"chapters": {chapter_id: {"title": "Old Title", "order": 1}}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True
    updated_chapter = service.update(project_id, chapter_id, chapter_in)
    assert updated_chapter.title == "New Title"
    assert updated_chapter.order == 1
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, ANY)
    args, kwargs = mock_file_service.write_project_metadata.call_args
    assert args[1]['chapters'][chapter_id]['title'] == "New Title"

def test_update_chapter_success_order(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-upd-2"
    chapter_id = "chap-upd-order"
    chapter_in = ChapterUpdate(order=3)
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"chapters": {chapter_id: {"title": "Some Title", "order": 1}, "other-chap": {"title": "Another", "order": 2}}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True
    updated_chapter = service.update(project_id, chapter_id, chapter_in)
    assert updated_chapter.title == "Some Title"
    assert updated_chapter.order == 3
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, ANY)
    args, kwargs = mock_file_service.write_project_metadata.call_args
    assert args[1]['chapters'][chapter_id]['order'] == 3

def test_update_chapter_success_both(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-upd-3"
    chapter_id = "chap-upd-both"
    chapter_in = ChapterUpdate(title="New Title Both", order=5)
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"chapters": {chapter_id: {"title": "Old Title Both", "order": 4}}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True
    updated_chapter = service.update(project_id, chapter_id, chapter_in)
    assert updated_chapter.title == "New Title Both"
    assert updated_chapter.order == 5
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, ANY)
    args, kwargs = mock_file_service.write_project_metadata.call_args
    assert args[1]['chapters'][chapter_id]['title'] == "New Title Both"
    assert args[1]['chapters'][chapter_id]['order'] == 5

def test_update_chapter_no_change(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-upd-no"
    chapter_id = "chap-upd-no"
    chapter_in = ChapterUpdate(title="Same Title", order=1)
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"chapters": {chapter_id: {"title": "Same Title", "order": 1}}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True
    updated_chapter = service.update(project_id, chapter_id, chapter_in)
    assert updated_chapter.title == "Same Title"
    assert updated_chapter.order == 1
    mock_file_service.write_project_metadata.assert_not_called()

def test_update_chapter_not_found(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-upd-404"
    chapter_id = "chap-upd-404"
    chapter_in = ChapterUpdate(title="Doesn't Matter")
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = {"chapters": {}}
    mock_file_service._get_chapter_path.return_value = Path("dummy")
    mock_file_service.path_exists.return_value = False
    with pytest.raises(HTTPException) as exc_info: service.update(project_id, chapter_id, chapter_in)
    assert exc_info.value.status_code == 404
    mock_file_service.write_project_metadata.assert_not_called()

def test_update_chapter_order_conflict(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-upd-conflict"
    chapter_id = "chap-upd-conflict"
    chapter_in = ChapterUpdate(order=2)
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"chapters": {chapter_id: {"title": "To Be Updated", "order": 1}, "other-chap": {"title": "Existing Order 2", "order": 2}}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True
    with pytest.raises(HTTPException) as exc_info: service.update(project_id, chapter_id, chapter_in)
    assert exc_info.value.status_code == 409
    mock_file_service.write_project_metadata.assert_not_called()

# --- Tests for delete ---
# (Unchanged)
def test_delete_chapter_success(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-del-1"
    chapter_id = "chap-del-ok"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata_before = {"project_name": "Delete Proj", "chapters": {chapter_id: {"title": "To Delete", "order": 1}}, "characters": {}}
    mock_project_metadata_read2 = copy.deepcopy(mock_project_metadata_before)
    mock_project_metadata_after = {"project_name": "Delete Proj", "chapters": {}, "characters": {}}
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Delete Proj")
    mock_file_service.read_project_metadata.side_effect = [mock_project_metadata_before, mock_project_metadata_read2]
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True
    service.delete(project_id, chapter_id)
    mock_file_service.delete_directory.assert_called_once_with(mock_chapter_path)
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, mock_project_metadata_after)

def test_delete_chapter_not_found(chapter_service_with_mocks):
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-del-404"
    chapter_id = "chap-del-404"
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Delete Proj")
    mock_file_service.read_project_metadata.return_value = {"chapters": {}}
    mock_file_service._get_chapter_path.return_value = Path("dummy")
    mock_file_service.path_exists.return_value = False
    with pytest.raises(HTTPException) as exc_info: service.delete(project_id, chapter_id)
    assert exc_info.value.status_code == 404
    mock_file_service.delete_directory.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_delete_chapter_renumbers_correctly(chapter_service_with_mocks):
    """Test deleting a chapter correctly renumbers subsequent chapters."""
    service, mock_file_service, mock_project_service, _ = chapter_service_with_mocks
    project_id = "proj-del-renumber"
    ch1, ch2, ch3 = "chap1", "chap2", "chap3"
    mock_chapter_path2 = Path(f"user_projects/{project_id}/chapters/{ch2}")
    mock_project_metadata_before = {
        "project_name": "Renumber Proj",
        "chapters": {
            ch1: {"title": "C1", "order": 1},
            ch2: {"title": "C2", "order": 2}, # Delete this one
            ch3: {"title": "C3", "order": 3},
        },
        "characters": {}
    }
    # Make a copy for the second read, which will be modified by the service
    mock_project_metadata_read2 = copy.deepcopy(mock_project_metadata_before)

    mock_project_metadata_final_write = { # Expected final state after delete + renumber
        "project_name": "Renumber Proj",
        "chapters": {
            ch1: {"title": "C1", "order": 1}, # Should remain 1
            ch3: {"title": "C3", "order": 2}, # Should become 2
        },
        "characters": {}
    }
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Renumber Proj")
    mock_file_service.read_project_metadata.side_effect = [mock_project_metadata_before, mock_project_metadata_read2]
    mock_file_service._get_chapter_path.return_value = mock_chapter_path2
    mock_file_service.path_exists.return_value = True

    service.delete(project_id, ch2) # Call the delete method

    mock_file_service.delete_directory.assert_called_once_with(mock_chapter_path2)
    # Check that the write was called with the correctly renumbered dictionary
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, mock_project_metadata_final_write)


# --- Tests for compile_chapter_content ---
# (Unchanged)
def test_compile_chapter_content_success(chapter_service_with_mocks):
    """Test compiling chapter content with default options."""
    service, mock_file_service, mock_project_service, mock_scene_service = chapter_service_with_mocks
    project_id = "proj-compile-1"
    chapter_id = "chap-compile-ok"
    chapter_title = "The Compiled Chapter"
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Compile Proj")
    mock_file_service.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title, "order": 1}}} # Need valid order
    mock_file_service.path_exists.return_value = True
    scene1 = SceneRead(id="s1", project_id=project_id, chapter_id=chapter_id, title="Scene Alpha", order=1, content="Content alpha.")
    scene2 = SceneRead(id="s2", project_id=project_id, chapter_id=chapter_id, title="Scene Beta", order=2, content="Content beta.")
    mock_scene_list = MagicMock(spec=SceneList)
    mock_scene_list.scenes = [scene1, scene2]
    mock_scene_service.get_all_for_chapter.return_value = mock_scene_list
    result = service.compile_chapter_content(project_id, chapter_id)
    expected_content = f"## Scene Alpha\n\nContent alpha.\n\n---\n\n## Scene Beta\n\nContent beta."
    expected_filename = "the-compiled-chapter.md"
    assert result["filename"] == expected_filename
    assert result["content"] == expected_content
    mock_scene_service.get_all_for_chapter.assert_called_once_with(project_id, chapter_id)

def test_compile_chapter_content_no_titles(chapter_service_with_mocks):
    """Test compiling chapter content without titles."""
    service, mock_file_service, mock_project_service, mock_scene_service = chapter_service_with_mocks
    project_id = "proj-compile-2"
    chapter_id = "chap-compile-no-titles"
    chapter_title = "Chapter No Titles"
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Compile Proj")
    mock_file_service.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title, "order": 1}}} # Need valid order
    mock_file_service.path_exists.return_value = True
    scene1 = SceneRead(id="s1", project_id=project_id, chapter_id=chapter_id, title="S1", order=1, content="Content 1.")
    scene2 = SceneRead(id="s2", project_id=project_id, chapter_id=chapter_id, title="S2", order=2, content="Content 2.")
    mock_scene_list = MagicMock(spec=SceneList)
    mock_scene_list.scenes = [scene1, scene2]
    mock_scene_service.get_all_for_chapter.return_value = mock_scene_list
    result = service.compile_chapter_content(project_id, chapter_id, include_titles=False)
    expected_content = f"Content 1.\n\n---\n\nContent 2."
    expected_filename = "chapter-no-titles.md"
    assert result["filename"] == expected_filename
    assert result["content"] == expected_content

def test_compile_chapter_content_custom_separator(chapter_service_with_mocks):
    """Test compiling chapter content with a custom separator."""
    service, mock_file_service, mock_project_service, mock_scene_service = chapter_service_with_mocks
    project_id = "proj-compile-3"
    chapter_id = "chap-compile-sep"
    chapter_title = "Custom Sep"
    custom_sep = "\n\n***\n\n"
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Compile Proj")
    mock_file_service.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title, "order": 1}}} # Need valid order
    mock_file_service.path_exists.return_value = True
    scene1 = SceneRead(id="s1", project_id=project_id, chapter_id=chapter_id, title="S A", order=1, content="CA.")
    scene2 = SceneRead(id="s2", project_id=project_id, chapter_id=chapter_id, title="S B", order=2, content="CB.")
    mock_scene_list = MagicMock(spec=SceneList)
    mock_scene_list.scenes = [scene1, scene2]
    mock_scene_service.get_all_for_chapter.return_value = mock_scene_list
    result = service.compile_chapter_content(project_id, chapter_id, include_titles=True, separator=custom_sep)
    expected_content = f"## S A\n\nCA.\n\n***\n\n## S B\n\nCB."
    expected_filename = "custom-sep.md"
    assert result["filename"] == expected_filename
    assert result["content"] == expected_content

def test_compile_chapter_content_empty(chapter_service_with_mocks):
    """Test compiling an empty chapter."""
    service, mock_file_service, mock_project_service, mock_scene_service = chapter_service_with_mocks
    project_id = "proj-compile-4"
    chapter_id = "chap-compile-empty"
    chapter_title = "Empty Chapter"
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Compile Proj")
    mock_file_service.read_project_metadata.return_value = {"chapters": {chapter_id: {"title": chapter_title, "order": 1}}} # Need valid order
    mock_file_service.path_exists.return_value = True
    mock_scene_list = MagicMock(spec=SceneList)
    mock_scene_list.scenes = []
    mock_scene_service.get_all_for_chapter.return_value = mock_scene_list
    result = service.compile_chapter_content(project_id, chapter_id)
    expected_filename = "empty-chapter-empty.md"
    assert result["filename"] == expected_filename
    assert result["content"] == ""

def test_compile_chapter_content_chapter_not_found(chapter_service_with_mocks):
    """Test compiling when the chapter doesn't exist."""
    service, mock_file_service, mock_project_service, mock_scene_service = chapter_service_with_mocks
    project_id = "proj-compile-5"
    chapter_id = "chap-compile-404"
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Compile Proj")
    mock_file_service.read_project_metadata.return_value = {"chapters": {}}
    mock_file_service._get_chapter_path.return_value = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_file_service.path_exists.return_value = False
    with pytest.raises(HTTPException) as exc_info: service.compile_chapter_content(project_id, chapter_id)
    assert exc_info.value.status_code == 404
    mock_scene_service.get_all_for_chapter.assert_not_called()

def test_slugify_function(chapter_service_with_mocks):
    """Test the internal _slugify helper."""
    service, _, _, _ = chapter_service_with_mocks
    assert service._slugify("Simple Title") == "simple-title"
    assert service._slugify("Title with Spaces") == "title-with-spaces"
    assert service._slugify("Title with !@#$%^&*()_+|}{:\"?><") == "title-with-_"
    # --- REVISED: Correct expectation for this case ---
    assert service._slugify("  Leading/Trailing Spaces/Hyphens-- ") == "leading-trailing-spaces-hyphens"
    # --- END REVISED ---
    assert service._slugify("Consecutive---Hyphens") == "consecutive-hyphens"
    assert service._slugify(" Already-loweRCasE_with_underscore ") == "already-lowercase_with_underscore"
    assert service._slugify("") == "untitled-chapter"
    assert service._slugify("!@#$%^") == "untitled-chapter"
    assert service._slugify(None) == "untitled-chapter"