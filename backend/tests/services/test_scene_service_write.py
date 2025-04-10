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

# Import the *class* we are testing
from app.services.scene_service import SceneService
# Import classes for dependencies
from app.services.file_service import FileService
from app.services.chapter_service import ChapterService
# Import models used
from app.models.scene import SceneCreate, SceneUpdate, SceneRead, SceneList
from app.models.chapter import ChapterRead # Needed for mocking chapter_service.get_by_id

# --- Test SceneService Write Methods ---

# Fixture to create a SceneService instance with mocked dependencies
@pytest.fixture
def scene_service_with_mocks():
    mock_file_service = MagicMock(spec=FileService)
    mock_chapter_service = MagicMock(spec=ChapterService)
    # Patch the singletons within the scene_service module's scope
    with patch('app.services.scene_service.file_service', mock_file_service), \
         patch('app.services.scene_service.chapter_service', mock_chapter_service):
        service_instance = SceneService()
        # Yield the instance and the mocks for use in tests
        yield service_instance, mock_file_service, mock_chapter_service

# --- Tests for create ---

def test_create_scene_success(scene_service_with_mocks):
    """Test successful scene creation."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-create-scene-1"
    chapter_id = "chap-create-scene-1"
    scene_in = SceneCreate(title="The First Step", order=1, content="He opened the door.")
    mock_scene_id = "new-scene-uuid"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{mock_scene_id}.md")
    mock_chapter_metadata = {"scenes": {}} # Start with empty scenes

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.path_exists.return_value = False # No collision
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata

    # Mock generate_uuid
    with patch('app.services.scene_service.generate_uuid', return_value=mock_scene_id):
        created_scene = service.create(project_id, chapter_id, scene_in)

    # Assertions
    assert created_scene.id == mock_scene_id
    assert created_scene.project_id == project_id
    assert created_scene.chapter_id == chapter_id
    assert created_scene.title == scene_in.title
    assert created_scene.order == scene_in.order
    assert created_scene.content == scene_in.content

    # Verify mocks
    mock_chapter_service.get_by_id.assert_called_once_with(project_id, chapter_id)
    mock_file_service._get_scene_path.assert_called_once_with(project_id, chapter_id, mock_scene_id)
    mock_file_service.path_exists.assert_called_once_with(mock_scene_path)
    # Check write_text_file call (includes triggering index)
    mock_file_service.write_text_file.assert_called_once_with(mock_scene_path, scene_in.content, trigger_index=True)
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    # Check the data written to chapter metadata
    expected_meta_write = {
        "scenes": {mock_scene_id: {"title": scene_in.title, "order": scene_in.order}}
    }
    mock_file_service.write_chapter_metadata.assert_called_once_with(project_id, chapter_id, expected_meta_write)

def test_create_scene_chapter_not_found(scene_service_with_mocks):
    """Test scene creation when the chapter doesn't exist."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-create-scene-404c"
    chapter_id = "chap-create-scene-404c"
    scene_in = SceneCreate(title="Lost Scene", order=1, content="")

    mock_chapter_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Chapter not found")

    with pytest.raises(HTTPException) as exc_info:
        service.create(project_id, chapter_id, scene_in)

    assert exc_info.value.status_code == 404
    mock_file_service.write_text_file.assert_not_called()
    mock_file_service.write_chapter_metadata.assert_not_called()

def test_create_scene_id_collision(scene_service_with_mocks):
    """Test scene creation ID collision (rare)."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-create-scene-coll"
    chapter_id = "chap-create-scene-coll"
    scene_in = SceneCreate(title="Collision", order=1, content="")
    mock_scene_id = "colliding-scene-uuid"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{mock_scene_id}.md")

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.path_exists.return_value = True # Simulate collision

    with patch('app.services.scene_service.generate_uuid', return_value=mock_scene_id):
        with pytest.raises(HTTPException) as exc_info:
            service.create(project_id, chapter_id, scene_in)

    assert exc_info.value.status_code == 409
    assert "Scene ID collision" in exc_info.value.detail
    mock_file_service.write_text_file.assert_not_called()
    mock_file_service.write_chapter_metadata.assert_not_called()

def test_create_scene_order_conflict(scene_service_with_mocks):
    """Test scene creation when the desired order already exists."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-create-scene-order"
    chapter_id = "chap-create-scene-order"
    scene_in = SceneCreate(title="Second Scene 1", order=1, content="")
    mock_scene_id = "new-scene-uuid"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{mock_scene_id}.md")
    mock_chapter_metadata = {
        "scenes": {"existing-scene": {"title": "First Scene 1", "order": 1}}
    }

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.path_exists.return_value = False
    # --- REMOVED: write_text_file mock setup (it shouldn't be called) ---
    # mock_file_service.write_text_file.return_value = None
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    # --- REMOVED: delete_file mock setup (it shouldn't be called) ---
    # mock_file_service.delete_file.return_value = None

    with patch('app.services.scene_service.generate_uuid', return_value=mock_scene_id):
        with pytest.raises(HTTPException) as exc_info:
            service.create(project_id, chapter_id, scene_in)

    assert exc_info.value.status_code == 409
    assert "Scene order 1 already exists" in exc_info.value.detail
    # --- MODIFIED: Assert write_text_file was NOT called ---
    mock_file_service.write_text_file.assert_not_called()
    # --- END MODIFIED ---
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_file_service.write_chapter_metadata.assert_not_called()
    # --- REMOVED: delete_file assertion ---
    # mock_file_service.delete_file.assert_called_once_with(mock_scene_path)
    # --- END REMOVED ---

# --- Tests for update ---

def test_update_scene_success_all_fields(scene_service_with_mocks):
    """Test successfully updating title, order, and content."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-upd-scene-1"
    chapter_id = "chap-upd-scene-1"
    scene_id = "scene-upd-ok"
    scene_in = SceneUpdate(title="Updated Title", order=2, content="New content here.")
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    mock_chapter_metadata_before = {
        "scenes": {scene_id: {"title": "Old Title", "order": 1}}
    }
    mock_chapter_metadata_after = { # Expected state after update
        "scenes": {scene_id: {"title": "Updated Title", "order": 2}}
    }
    old_content = "Old content."

    # Mock the get_by_id call made at the start of update
    mock_get_by_id = MagicMock(return_value=SceneRead(
        id=scene_id, project_id=project_id, chapter_id=chapter_id,
        title="Old Title", order=1, content=old_content
    ))

    # Configure file service mocks
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata_before
    mock_file_service._get_scene_path.return_value = mock_scene_path

    with patch.object(service, 'get_by_id', mock_get_by_id):
        updated_scene = service.update(project_id, chapter_id, scene_id, scene_in)

    # Assertions
    assert updated_scene.id == scene_id
    assert updated_scene.title == scene_in.title
    assert updated_scene.order == scene_in.order
    assert updated_scene.content == scene_in.content

    # Verify mocks
    mock_get_by_id.assert_called_once_with(project_id, chapter_id, scene_id)
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    # Check metadata write
    mock_file_service.write_chapter_metadata.assert_called_once_with(project_id, chapter_id, mock_chapter_metadata_after)
    # Check content write (with index trigger)
    mock_file_service.write_text_file.assert_called_once_with(mock_scene_path, scene_in.content, trigger_index=True)

def test_update_scene_success_content_only(scene_service_with_mocks):
    """Test successfully updating only the scene content."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-upd-scene-2"
    chapter_id = "chap-upd-scene-2"
    scene_id = "scene-upd-content"
    scene_in = SceneUpdate(content="Just new content.")
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    mock_chapter_metadata = {
        "scenes": {scene_id: {"title": "Content Scene", "order": 5}}
    }
    old_content = "Old content."

    # Mock get_by_id
    mock_get_by_id = MagicMock(return_value=SceneRead(
        id=scene_id, project_id=project_id, chapter_id=chapter_id,
        title="Content Scene", order=5, content=old_content
    ))

    # Configure file service mocks
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = mock_scene_path

    with patch.object(service, 'get_by_id', mock_get_by_id):
        updated_scene = service.update(project_id, chapter_id, scene_id, scene_in)

    # Assertions
    assert updated_scene.title == "Content Scene" # Unchanged
    assert updated_scene.order == 5 # Unchanged
    assert updated_scene.content == scene_in.content # Updated

    # Verify mocks
    mock_file_service.write_chapter_metadata.assert_not_called() # Metadata not changed
    mock_file_service.write_text_file.assert_called_once_with(mock_scene_path, scene_in.content, trigger_index=True)

def test_update_scene_no_change(scene_service_with_mocks):
    """Test update when no actual changes are provided."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-upd-scene-no"
    chapter_id = "chap-upd-scene-no"
    scene_id = "scene-upd-no"
    # Provide same data as existing
    scene_in = SceneUpdate(title="Same Title", order=1, content="Same content.")
    mock_chapter_metadata = {
        "scenes": {scene_id: {"title": "Same Title", "order": 1}}
    }

    # Mock get_by_id
    mock_get_by_id = MagicMock(return_value=SceneRead(
        id=scene_id, project_id=project_id, chapter_id=chapter_id,
        title="Same Title", order=1, content="Same content."
    ))
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata

    with patch.object(service, 'get_by_id', mock_get_by_id):
        updated_scene = service.update(project_id, chapter_id, scene_id, scene_in)

    # Assertions
    assert updated_scene.title == "Same Title"
    assert updated_scene.order == 1
    assert updated_scene.content == "Same content."

    # Verify mocks
    mock_file_service.write_chapter_metadata.assert_not_called()
    mock_file_service.write_text_file.assert_not_called()

def test_update_scene_not_found(scene_service_with_mocks):
    """Test updating a scene that doesn't exist."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-upd-scene-404"
    chapter_id = "chap-upd-scene-404"
    scene_id = "scene-upd-404"
    scene_in = SceneUpdate(title="Doesn't Matter")

    # Configure get_by_id to raise 404
    mock_get_by_id = MagicMock(side_effect=HTTPException(status_code=404, detail="Scene not found"))

    with patch.object(service, 'get_by_id', mock_get_by_id):
        with pytest.raises(HTTPException) as exc_info:
            service.update(project_id, chapter_id, scene_id, scene_in)

    assert exc_info.value.status_code == 404
    mock_file_service.write_chapter_metadata.assert_not_called()
    mock_file_service.write_text_file.assert_not_called()

def test_update_scene_order_conflict(scene_service_with_mocks):
    """Test updating scene order causing a conflict."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-upd-scene-conflict"
    chapter_id = "chap-upd-scene-conflict"
    scene_id = "scene-upd-conflict"
    scene_in = SceneUpdate(order=2) # Try to change order to 2
    mock_chapter_metadata = {
        "scenes": {
            scene_id: {"title": "To Be Updated", "order": 1},
            "other-scene": {"title": "Existing Order 2", "order": 2} # Conflict
        }
    }

    # Mock get_by_id
    mock_get_by_id = MagicMock(return_value=SceneRead(
        id=scene_id, project_id=project_id, chapter_id=chapter_id,
        title="To Be Updated", order=1, content="Content"
    ))
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata

    with patch.object(service, 'get_by_id', mock_get_by_id):
        with pytest.raises(HTTPException) as exc_info:
            service.update(project_id, chapter_id, scene_id, scene_in)

    assert exc_info.value.status_code == 409
    assert "Scene order 2 already exists" in exc_info.value.detail
    mock_file_service.write_chapter_metadata.assert_not_called()
    mock_file_service.write_text_file.assert_not_called()

# --- Tests for delete ---

def test_delete_scene_success(scene_service_with_mocks):
    """Test successfully deleting a scene."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-del-scene-1"
    chapter_id = "chap-del-scene-1"
    scene_id = "scene-del-ok"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    mock_chapter_metadata_before = {
        "scenes": {scene_id: {"title": "To Delete", "order": 1}}
    }
    mock_chapter_metadata_after = { # Expected state after delete
        "scenes": {}
    }

    # Configure mocks
    # No need to mock get_by_id for delete, it checks metadata directly
    mock_file_service.read_chapter_metadata.side_effect = [
        mock_chapter_metadata_before, # For initial check
        mock_chapter_metadata_before  # For read before write
    ]
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.path_exists.return_value = True # File exists

    service.delete(project_id, chapter_id, scene_id)

    # Verify mocks
    mock_file_service._get_scene_path.assert_called_once_with(project_id, chapter_id, scene_id)
    mock_file_service.delete_file.assert_called_once_with(mock_scene_path) # delete_file handles index
    # Check metadata write
    mock_file_service.write_chapter_metadata.assert_called_once_with(project_id, chapter_id, mock_chapter_metadata_after)

def test_delete_scene_not_found_meta_and_file(scene_service_with_mocks):
    """Test deleting a scene that doesn't exist in metadata or filesystem."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-del-scene-404"
    chapter_id = "chap-del-scene-404"
    scene_id = "scene-del-404"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    mock_chapter_metadata = {"scenes": {}} # Scene not in metadata

    # Configure mocks
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.path_exists.return_value = False # File also doesn't exist

    with pytest.raises(HTTPException) as exc_info:
        service.delete(project_id, chapter_id, scene_id)

    assert exc_info.value.status_code == 404
    assert "Scene not found" in exc_info.value.detail
    mock_file_service.delete_file.assert_not_called()
    mock_file_service.write_chapter_metadata.assert_not_called()

def test_delete_scene_not_found_meta_but_file_exists(scene_service_with_mocks):
    """Test deleting scene when file exists but metadata is missing (cleanup)."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-del-scene-file"
    chapter_id = "chap-del-scene-file"
    scene_id = "scene-del-file"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    mock_chapter_metadata = {"scenes": {}} # Scene not in metadata

    # Configure mocks
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.path_exists.return_value = True # File *does* exist

    # Should still proceed to delete the file
    service.delete(project_id, chapter_id, scene_id)

    # Verify mocks
    mock_file_service.delete_file.assert_called_once_with(mock_scene_path)
    mock_file_service.write_chapter_metadata.assert_not_called() # Metadata wasn't changed

def test_delete_scene_chapter_meta_missing(scene_service_with_mocks):
    """Test deleting scene when chapter metadata itself is missing."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-del-scene-chapmeta"
    chapter_id = "chap-del-scene-chapmeta"
    scene_id = "scene-del-chapmeta"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")

    # Configure mocks
    mock_file_service.read_chapter_metadata.side_effect = HTTPException(status_code=404, detail="Chapter meta not found")
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.path_exists.return_value = False # Assume scene file also missing

    with pytest.raises(HTTPException) as exc_info:
        service.delete(project_id, chapter_id, scene_id)

    assert exc_info.value.status_code == 404
    assert "Scene not found (chapter meta missing)" in exc_info.value.detail
    mock_file_service.delete_file.assert_not_called()
    mock_file_service.write_chapter_metadata.assert_not_called()