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

# Import the *class* we are testing, not the singleton instance
from app.services.chapter_service import ChapterService
# Import classes for dependencies
from app.services.file_service import FileService
from app.services.project_service import ProjectService
# Import models used in responses/arguments
from app.models.chapter import ChapterCreate, ChapterUpdate, ChapterRead, ChapterList
from app.models.project import ProjectRead # Needed for mocking project_service.get_by_id

# --- Test ChapterService Methods ---

# Fixture to create a ChapterService instance with mocked dependencies
@pytest.fixture
def chapter_service_with_mocks():
    mock_file_service = MagicMock(spec=FileService)
    mock_project_service = MagicMock(spec=ProjectService)
    # Patch the singletons within the chapter_service module's scope
    with patch('app.services.chapter_service.file_service', mock_file_service), \
         patch('app.services.chapter_service.project_service', mock_project_service):
        service_instance = ChapterService()
        # Yield the instance and the mocks for use in tests
        yield service_instance, mock_file_service, mock_project_service

# --- Tests for create ---

def test_create_chapter_success(chapter_service_with_mocks):
    """Test successful chapter creation."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-uuid-1"
    chapter_in = ChapterCreate(title="The Beginning", order=1)
    mock_chapter_id = "new-chap-uuid"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{mock_chapter_id}")
    mock_project_metadata = {"project_name": "Test Proj", "chapters": {}, "characters": {}}

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj") # Simulate project exists
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = False # No collision
    mock_file_service.read_project_metadata.return_value = mock_project_metadata

    # Mock generate_uuid if needed for predictable ID (optional, but good for assertion)
    with patch('app.services.chapter_service.generate_uuid', return_value=mock_chapter_id):
        created_chapter = service.create(project_id, chapter_in)

    # Assertions
    assert created_chapter.id == mock_chapter_id
    assert created_chapter.project_id == project_id
    assert created_chapter.title == chapter_in.title
    assert created_chapter.order == chapter_in.order

    # Verify mocks
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service._get_chapter_path.assert_called_once_with(project_id, mock_chapter_id)
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path)
    mock_file_service.setup_chapter_structure.assert_called_once_with(project_id, mock_chapter_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    # Check the data written to project metadata
    expected_meta_write = {
        "project_name": "Test Proj",
        "chapters": {mock_chapter_id: {"title": chapter_in.title, "order": chapter_in.order}},
        "characters": {}
    }
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, expected_meta_write)

def test_create_chapter_project_not_found(chapter_service_with_mocks):
    """Test chapter creation when the project doesn't exist."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-uuid-404"
    chapter_in = ChapterCreate(title="Lost Chapter", order=1)

    # Configure mocks
    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")

    # Call and assert exception
    with pytest.raises(HTTPException) as exc_info:
        service.create(project_id, chapter_in)

    assert exc_info.value.status_code == 404
    assert "Project not found" in exc_info.value.detail
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service.setup_chapter_structure.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_create_chapter_id_collision(chapter_service_with_mocks):
    """Test chapter creation when a generated ID surprisingly collides."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-uuid-collide"
    chapter_in = ChapterCreate(title="Collision Course", order=1)
    mock_chapter_id = "colliding-chap-uuid"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{mock_chapter_id}")

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True # Simulate collision

    with patch('app.services.chapter_service.generate_uuid', return_value=mock_chapter_id):
        with pytest.raises(HTTPException) as exc_info:
            service.create(project_id, chapter_in)

    assert exc_info.value.status_code == 409
    assert "Chapter ID collision" in exc_info.value.detail
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path)
    mock_file_service.setup_chapter_structure.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_create_chapter_order_conflict(chapter_service_with_mocks):
    """Test chapter creation when the desired order already exists."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-uuid-order"
    chapter_in = ChapterCreate(title="Second Chapter 1", order=1)
    mock_chapter_id = "new-chap-uuid"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{mock_chapter_id}")
    mock_project_metadata = {
        "project_name": "Test Proj",
        "chapters": {"existing-chap-uuid": {"title": "First Chapter 1", "order": 1}},
        "characters": {}
    }

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = False
    mock_file_service.setup_chapter_structure.return_value = None # Called before conflict check
    mock_file_service.read_project_metadata.return_value = mock_project_metadata

    with patch('app.services.chapter_service.generate_uuid', return_value=mock_chapter_id):
        with pytest.raises(HTTPException) as exc_info:
            service.create(project_id, chapter_in)

    assert exc_info.value.status_code == 409
    assert "Chapter order 1 already exists" in exc_info.value.detail
    mock_file_service.setup_chapter_structure.assert_called_once_with(project_id, mock_chapter_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    mock_file_service.write_project_metadata.assert_not_called()

# --- Tests for get_by_id ---

def test_get_chapter_by_id_success(chapter_service_with_mocks):
    """Test successfully getting a chapter by ID."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-get-1"
    chapter_id = "chap-get-ok"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {
        "project_name": "Get Proj",
        "chapters": {chapter_id: {"title": "Found Chapter", "order": 2}},
        "characters": {}
    }

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Get Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True # Directory exists

    chapter = service.get_by_id(project_id, chapter_id)

    # Assertions
    assert chapter.id == chapter_id
    assert chapter.project_id == project_id
    assert chapter.title == "Found Chapter"
    assert chapter.order == 2

    # Verify mocks
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    mock_file_service._get_chapter_path.assert_called_once_with(project_id, chapter_id)
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path)

def test_get_chapter_by_id_project_not_found(chapter_service_with_mocks):
    """Test getting chapter when project doesn't exist."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-get-404"
    chapter_id = "chap-get-whatever"

    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, chapter_id)

    assert exc_info.value.status_code == 404
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service.read_project_metadata.assert_not_called()

def test_get_chapter_by_id_chapter_not_in_metadata(chapter_service_with_mocks):
    """Test getting chapter when it's missing from project metadata."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-get-meta"
    chapter_id = "chap-get-missing"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"project_name": "Meta Proj", "chapters": {}, "characters": {}} # Empty chapters

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Meta Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = False # Assume dir also doesn't exist

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, chapter_id)

    assert exc_info.value.status_code == 404
    assert f"Chapter {chapter_id} not found" in exc_info.value.detail
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path) # Called in the exception path

def test_get_chapter_by_id_directory_missing(chapter_service_with_mocks):
    """Test getting chapter when metadata exists but directory is missing."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-get-dir"
    chapter_id = "chap-get-no-dir"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {
        "project_name": "Dir Proj",
        "chapters": {chapter_id: {"title": "Ghost Chapter", "order": 1}},
        "characters": {}
    }

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Dir Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = False # Directory missing

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, chapter_id)

    assert exc_info.value.status_code == 404
    assert f"Chapter {chapter_id} data missing" in exc_info.value.detail
    mock_file_service.path_exists.assert_called_once_with(mock_chapter_path)

# --- Tests for get_all_for_project ---

def test_get_all_chapters_success(chapter_service_with_mocks):
    """Test listing chapters successfully."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-list-1"
    chap1_id, chap2_id = "chap-list-b", "chap-list-a"
    mock_project_metadata = {
        "project_name": "List Proj",
        "chapters": {
            chap1_id: {"title": "Chapter Two", "order": 2},
            chap2_id: {"title": "Chapter One", "order": 1},
        },
        "characters": {}
    }
    mock_path1 = Path(f"user_projects/{project_id}/chapters/{chap1_id}")
    mock_path2 = Path(f"user_projects/{project_id}/chapters/{chap2_id}")

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="List Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    # Simulate both directories exist
    mock_file_service._get_chapter_path.side_effect = lambda p, c: mock_path1 if c == chap1_id else mock_path2 if c == chap2_id else None
    mock_file_service.path_exists.return_value = True

    chapter_list = service.get_all_for_project(project_id)

    # Assertions
    assert isinstance(chapter_list, ChapterList)
    assert len(chapter_list.chapters) == 2
    # Check sorting by order
    assert chapter_list.chapters[0].id == chap2_id
    assert chapter_list.chapters[0].title == "Chapter One"
    assert chapter_list.chapters[0].order == 1
    assert chapter_list.chapters[1].id == chap1_id
    assert chapter_list.chapters[1].title == "Chapter Two"
    assert chapter_list.chapters[1].order == 2

    # Verify mocks
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    assert mock_file_service._get_chapter_path.call_count == 2
    assert mock_file_service.path_exists.call_count == 2

def test_get_all_chapters_empty(chapter_service_with_mocks):
    """Test listing chapters when none exist."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-list-empty"
    mock_project_metadata = {"project_name": "Empty Proj", "chapters": {}, "characters": {}}

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Empty Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata

    chapter_list = service.get_all_for_project(project_id)

    assert isinstance(chapter_list, ChapterList)
    assert len(chapter_list.chapters) == 0
    mock_file_service._get_chapter_path.assert_not_called()
    mock_file_service.path_exists.assert_not_called()

def test_get_all_chapters_project_not_found(chapter_service_with_mocks):
    """Test listing chapters when project doesn't exist."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-list-404"
    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")

    with pytest.raises(HTTPException) as exc_info:
        service.get_all_for_project(project_id)

    assert exc_info.value.status_code == 404
    mock_file_service.read_project_metadata.assert_not_called()

def test_get_all_chapters_skips_missing_dir(chapter_service_with_mocks):
    """Test listing chapters skips one whose directory is missing."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-list-skip"
    chap1_id, chap2_id = "chap-list-ok", "chap-list-missing"
    mock_project_metadata = {
        "project_name": "Skip Proj",
        "chapters": {
            chap1_id: {"title": "Exists", "order": 1},
            chap2_id: {"title": "Missing Dir", "order": 2},
        },
        "characters": {}
    }
    mock_path1 = Path(f"user_projects/{project_id}/chapters/{chap1_id}")
    mock_path2 = Path(f"user_projects/{project_id}/chapters/{chap2_id}")

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Skip Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.side_effect = lambda p, c: mock_path1 if c == chap1_id else mock_path2 if c == chap2_id else None
    # Simulate path exists for chap1, but not for chap2
    mock_file_service.path_exists.side_effect = lambda path: path == mock_path1

    chapter_list = service.get_all_for_project(project_id)

    # Assertions
    assert len(chapter_list.chapters) == 1
    assert chapter_list.chapters[0].id == chap1_id
    assert chapter_list.chapters[0].title == "Exists"

    # Verify mocks
    assert mock_file_service.path_exists.call_count == 2 # Checked both

# --- Tests for update ---

def test_update_chapter_success_title(chapter_service_with_mocks):
    """Test successfully updating only the chapter title."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-upd-1"
    chapter_id = "chap-upd-title"
    chapter_in = ChapterUpdate(title="New Title")
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {
        "project_name": "Update Proj",
        "chapters": {chapter_id: {"title": "Old Title", "order": 1}},
        "characters": {}
    }

    # Configure mocks for get_by_id call within update
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True

    updated_chapter = service.update(project_id, chapter_id, chapter_in)

    # Assertions
    assert updated_chapter.id == chapter_id
    assert updated_chapter.title == "New Title" # Updated
    assert updated_chapter.order == 1 # Unchanged

    # Verify mocks
    assert mock_file_service.read_project_metadata.call_count == 2 # Once in get_by_id, once in update
    expected_meta_write = {
        "project_name": "Update Proj",
        "chapters": {chapter_id: {"title": "New Title", "order": 1}},
        "characters": {}
    }
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, expected_meta_write)

def test_update_chapter_success_order(chapter_service_with_mocks):
    """Test successfully updating only the chapter order (no conflict)."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-upd-2"
    chapter_id = "chap-upd-order"
    chapter_in = ChapterUpdate(order=3)
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {
        "project_name": "Update Proj",
        "chapters": {
            chapter_id: {"title": "Some Title", "order": 1},
            "other-chap": {"title": "Another", "order": 2}
        },
        "characters": {}
    }

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True

    updated_chapter = service.update(project_id, chapter_id, chapter_in)

    # Assertions
    assert updated_chapter.id == chapter_id
    assert updated_chapter.title == "Some Title" # Unchanged
    assert updated_chapter.order == 3 # Updated

    # Verify mocks
    expected_meta_write = {
        "project_name": "Update Proj",
        "chapters": {
            chapter_id: {"title": "Some Title", "order": 3},
            "other-chap": {"title": "Another", "order": 2}
        },
        "characters": {}
    }
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, expected_meta_write)

def test_update_chapter_success_both(chapter_service_with_mocks):
    """Test successfully updating both title and order."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-upd-3"
    chapter_id = "chap-upd-both"
    chapter_in = ChapterUpdate(title="New Title Both", order=5)
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {
        "project_name": "Update Proj",
        "chapters": {chapter_id: {"title": "Old Title Both", "order": 4}},
        "characters": {}
    }

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True

    updated_chapter = service.update(project_id, chapter_id, chapter_in)

    # Assertions
    assert updated_chapter.title == "New Title Both"
    assert updated_chapter.order == 5

    # Verify mocks
    expected_meta_write = {
        "project_name": "Update Proj",
        "chapters": {chapter_id: {"title": "New Title Both", "order": 5}},
        "characters": {}
    }
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, expected_meta_write)

def test_update_chapter_no_change(chapter_service_with_mocks):
    """Test update when no actual changes are provided."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-upd-no"
    chapter_id = "chap-upd-no"
    chapter_in = ChapterUpdate(title="Same Title", order=1) # Same as existing
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {
        "project_name": "Update Proj",
        "chapters": {chapter_id: {"title": "Same Title", "order": 1}},
        "characters": {}
    }

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True

    updated_chapter = service.update(project_id, chapter_id, chapter_in)

    # Assertions
    assert updated_chapter.title == "Same Title"
    assert updated_chapter.order == 1

    # Verify mocks
    mock_file_service.write_project_metadata.assert_not_called() # No write if no change

def test_update_chapter_not_found(chapter_service_with_mocks):
    """Test updating a chapter that doesn't exist."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-upd-404"
    chapter_id = "chap-upd-404"
    chapter_in = ChapterUpdate(title="Doesn't Matter")

    # Configure get_by_id to raise 404
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj") # Project exists
    mock_file_service.read_project_metadata.return_value = {"chapters": {}} # Chapter doesn't
    mock_file_service._get_chapter_path.return_value = Path("dummy")
    mock_file_service.path_exists.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        service.update(project_id, chapter_id, chapter_in)

    assert exc_info.value.status_code == 404
    mock_file_service.write_project_metadata.assert_not_called()

def test_update_chapter_order_conflict(chapter_service_with_mocks):
    """Test updating chapter order causing a conflict."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-upd-conflict"
    chapter_id = "chap-upd-conflict"
    chapter_in = ChapterUpdate(order=2) # Try to change order to 2
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {
        "project_name": "Update Proj",
        "chapters": {
            chapter_id: {"title": "To Be Updated", "order": 1},
            "other-chap": {"title": "Existing Order 2", "order": 2} # Conflict
        },
        "characters": {}
    }

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Update Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True

    with pytest.raises(HTTPException) as exc_info:
        service.update(project_id, chapter_id, chapter_in)

    assert exc_info.value.status_code == 409
    assert "Chapter order 2 already exists" in exc_info.value.detail
    mock_file_service.write_project_metadata.assert_not_called()

# --- Tests for delete ---

def test_delete_chapter_success(chapter_service_with_mocks):
    """Test successfully deleting a chapter."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-del-1"
    chapter_id = "chap-del-ok"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata_before = {
        "project_name": "Delete Proj",
        "chapters": {chapter_id: {"title": "To Delete", "order": 1}},
        "characters": {}
    }
    mock_project_metadata_after = { # Same object, modified by service
        "project_name": "Delete Proj",
        "chapters": {},
        "characters": {}
    }

    # Configure mocks for get_by_id call within delete
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Delete Proj")
    mock_file_service.read_project_metadata.side_effect = [
        mock_project_metadata_before, # For get_by_id check
        mock_project_metadata_before # For the read before delete in metadata
    ]
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True

    service.delete(project_id, chapter_id)

    # Verify mocks
    mock_file_service._get_chapter_path.assert_called_with(project_id, chapter_id) # Called twice? Once in get_by_id, once in delete
    assert mock_file_service._get_chapter_path.call_count >= 1 # Check at least once
    mock_file_service.delete_directory.assert_called_once_with(mock_chapter_path)
    # Check metadata write
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, mock_project_metadata_after)

def test_delete_chapter_not_found(chapter_service_with_mocks):
    """Test deleting a chapter that doesn't exist."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-del-404"
    chapter_id = "chap-del-404"

    # Configure get_by_id to raise 404
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Delete Proj") # Project exists
    mock_file_service.read_project_metadata.return_value = {"chapters": {}} # Chapter doesn't
    mock_file_service._get_chapter_path.return_value = Path("dummy")
    mock_file_service.path_exists.return_value = False

    with pytest.raises(HTTPException) as exc_info:
        service.delete(project_id, chapter_id)

    assert exc_info.value.status_code == 404
    mock_file_service.delete_directory.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_delete_chapter_metadata_already_missing(chapter_service_with_mocks):
    """Test deleting chapter when directory exists but metadata is already gone."""
    service, mock_file_service, mock_project_service = chapter_service_with_mocks
    project_id = "proj-del-meta"
    chapter_id = "chap-del-meta"
    mock_chapter_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}")
    mock_project_metadata = {"project_name": "Delete Proj", "chapters": {}, "characters": {}} # Missing

    # Configure mocks for get_by_id call within delete
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Delete Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_chapter_path.return_value = mock_chapter_path
    mock_file_service.path_exists.return_value = True # Directory exists

    # get_by_id will raise 404 because metadata is missing
    with pytest.raises(HTTPException) as exc_info:
         service.delete(project_id, chapter_id)

    assert exc_info.value.status_code == 404
    # Even though get_by_id failed, let's ensure delete_directory wasn't called
    mock_file_service.delete_directory.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()