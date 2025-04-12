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
import copy # Import copy
import logging
from typing import List, Dict, Any, Callable

# Import the *class* we are testing
from app.services.scene_service import SceneService
# Import classes for dependencies
from app.services.file_service import FileService
from app.services.chapter_service import ChapterService
# --- ADDED: Import IndexManager for mocking ---
from app.rag.index_manager import IndexManager
# --- END ADDED ---
# Import models used
from app.models.scene import SceneCreate, SceneUpdate, SceneRead, SceneList
from app.models.chapter import ChapterRead # Needed for mocking chapter_service.get_by_id

# --- Test SceneService Write Methods ---

# Fixture to create a SceneService instance with mocked dependencies
@pytest.fixture
def scene_service_with_mocks():
    mock_file_service = MagicMock(spec=FileService)
    mock_chapter_service = MagicMock(spec=ChapterService)
    # --- ADDED: Mock index_manager ---
    mock_index_manager = MagicMock(spec=IndexManager)
    # --- END ADDED ---

    # Patch the singletons within the scene_service module's scope
    with patch('app.services.scene_service.file_service', mock_file_service), \
         patch('app.services.scene_service.chapter_service', mock_chapter_service), \
         patch('app.services.scene_service.index_manager', mock_index_manager): # Patch index_manager
        service_instance = SceneService()
        # Yield the instance and the mocks for use in tests
        yield service_instance, mock_file_service, mock_chapter_service, mock_index_manager # Yield index_manager mock

# --- Tests for create ---
# (create tests unchanged - omitted)
def test_create_scene_success(scene_service_with_mocks):
    """Test successful scene creation."""
    # --- Adjusted fixture unpacking ---
    service, mock_file_service, mock_chapter_service, _ = scene_service_with_mocks
    # --- End Adjustment ---
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
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    # --- Verify metadata write happens BEFORE file write ---
    # Check the data written to chapter metadata
    expected_meta_write = {
        "scenes": {mock_scene_id: {"title": scene_in.title, "order": scene_in.order}}
    }
    mock_file_service.write_chapter_metadata.assert_called_once_with(project_id, chapter_id, expected_meta_write)
    # Check write_text_file call (includes triggering index)
    mock_file_service.write_text_file.assert_called_once_with(mock_scene_path, scene_in.content, trigger_index=True)
    # Ensure metadata write was called before file write
    mock_calls = mock_file_service.mock_calls
    meta_write_index = -1
    file_write_index = -1
    for i, mock_call in enumerate(mock_calls):
        if mock_call == call.write_chapter_metadata(project_id, chapter_id, expected_meta_write):
            meta_write_index = i
        if mock_call == call.write_text_file(mock_scene_path, scene_in.content, trigger_index=True):
            file_write_index = i
    assert meta_write_index != -1, "write_chapter_metadata was not called"
    assert file_write_index != -1, "write_text_file was not called"
    assert meta_write_index < file_write_index, "Metadata should be written before the file"


def test_create_scene_chapter_not_found(scene_service_with_mocks):
    """Test scene creation when the chapter doesn't exist."""
    service, mock_file_service, mock_chapter_service, _ = scene_service_with_mocks
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
    service, mock_file_service, mock_chapter_service, _ = scene_service_with_mocks
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
    service, mock_file_service, mock_chapter_service, _ = scene_service_with_mocks
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
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata

    with patch('app.services.scene_service.generate_uuid', return_value=mock_scene_id):
        with pytest.raises(HTTPException) as exc_info:
            service.create(project_id, chapter_id, scene_in)

    assert exc_info.value.status_code == 409
    assert "Scene order 1 already exists" in exc_info.value.detail
    mock_file_service.write_text_file.assert_not_called()
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_file_service.write_chapter_metadata.assert_not_called()

# --- Tests for update ---

# Call order tracking helper class
class CallOrderTracker:
    """Helper class to track the order of function calls across different mock objects"""
    def __init__(self):
        self.call_log: List[str] = []
        self.tracked_calls: Dict[str, Dict[str, Any]] = {}
    
    def track(self, mock_obj, method_name: str, identifier: str) -> None:
        """Set up tracking for a specific method on a mock object"""
        original_method = getattr(mock_obj, method_name)
        
        # Create a tracking wrapper that logs when the method is called
        def tracking_wrapper(*args, **kwargs):
            self.call_log.append(identifier)
            self.tracked_calls[identifier] = {
                'args': args,
                'kwargs': kwargs,
                'call_index': len(self.call_log) - 1
            }
            return original_method(*args, **kwargs)
        
        # Replace the original method with our tracking wrapper
        setattr(mock_obj, method_name, tracking_wrapper)
    
    def called_before(self, first_id: str, second_id: str) -> bool:
        """Check if first call happened before second call"""
        if first_id not in self.call_log or second_id not in self.call_log:
            return False
        
        first_index = self.call_log.index(first_id)
        second_index = self.call_log.index(second_id)
        return first_index < second_index
    
    def get_call_args(self, identifier: str) -> tuple:
        """Get the args that were passed to a tracked call"""
        if identifier in self.tracked_calls:
            return self.tracked_calls[identifier]['args']
        return tuple()
    
    def get_call_kwargs(self, identifier: str) -> dict:
        """Get the kwargs that were passed to a tracked call"""
        if identifier in self.tracked_calls:
            return self.tracked_calls[identifier]['kwargs']
        return {}
    
    def was_called(self, identifier: str) -> bool:
        """Check if a tracked call was made"""
        return identifier in self.call_log

def test_update_scene_success_all_fields(scene_service_with_mocks):
    """Test successfully updating title, order, and content."""
    # --- Adjusted fixture unpacking ---
    service, mock_file_service, mock_chapter_service, mock_index_manager = scene_service_with_mocks
    # --- End Adjustment ---
    project_id = "proj-upd-scene-1"
    chapter_id = "chap-upd-scene-1"
    scene_id = "scene-upd-ok"
    scene_in = SceneUpdate(title="Updated Title", order=2, content="New content here.")
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    
    # Create a CallOrderTracker to track and assert the sequence of operations
    tracker = CallOrderTracker()
    
    # Track key operations we want to verify
    tracker.track(mock_file_service, "write_chapter_metadata", "write_metadata")
    tracker.track(mock_file_service, "write_text_file", "write_content")
    tracker.track(mock_index_manager, "index_file", "index_update")
    
    # Define test data
    mock_chapter_metadata = {
        "scenes": {scene_id: {"title": "Old Title", "order": 1}}
    }
    expected_meta_data_after = {
        "scenes": {scene_id: {"title": "Updated Title", "order": 2}}
    }
    old_content = "Old content."
    
    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(
        id=chapter_id, project_id=project_id, title="Test Chapter", order=1
    )
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.read_text_file.return_value = old_content
    mock_file_service.read_project_metadata.return_value = {
        "chapters": {chapter_id: {"title": "Test Chapter", "order": 1}}
    }

    # Call the service method being tested
    updated_scene = service.update(project_id, chapter_id, scene_id, scene_in)
    
    # Basic assertions about returned data
    assert updated_scene.id == scene_id
    assert updated_scene.title == scene_in.title
    assert updated_scene.order == scene_in.order
    assert updated_scene.content == scene_in.content
    
    # Verify basic operations were performed
    mock_chapter_service.get_by_id.assert_called_once_with(project_id, chapter_id)
    mock_file_service.read_chapter_metadata.assert_called_with(project_id, chapter_id)
    mock_file_service._get_scene_path.assert_called_with(project_id, chapter_id, scene_id)
    mock_file_service.read_text_file.assert_called_once_with(mock_scene_path)
    
    # Assert operations were tracked and occurred in the correct order
    assert tracker.was_called("write_metadata"), "write_chapter_metadata was not called"
    assert tracker.was_called("write_content"), "write_text_file was not called"
    assert tracker.was_called("index_update"), "index_file was not called"
    
    # Verify correct order of operations
    assert tracker.called_before("write_metadata", "write_content"), "Metadata write should happen before content write"
    assert tracker.called_before("write_content", "index_update"), "Content write should happen before index update"
    
    # Verify metadata write arguments
    metadata_args = tracker.get_call_args("write_metadata")
    assert len(metadata_args) >= 3, "Not enough arguments passed to write_chapter_metadata"
    assert metadata_args[0] == project_id, "Project ID mismatch in write_chapter_metadata"
    assert metadata_args[1] == chapter_id, "Chapter ID mismatch in write_chapter_metadata"
    
    # Verify the dictionary structure matches what we expect
    # Note: Deep comparison might be needed for more complex structures
    metadata_dict = metadata_args[2]
    assert "scenes" in metadata_dict, "Scenes key missing in metadata dict"
    assert scene_id in metadata_dict["scenes"], f"Scene ID {scene_id} missing in metadata scenes"
    assert metadata_dict["scenes"][scene_id]["title"] == "Updated Title", "Title not updated in metadata"
    assert metadata_dict["scenes"][scene_id]["order"] == 2, "Order not updated in metadata"
    
    # Verify content write arguments
    content_args = tracker.get_call_args("write_content")
    content_kwargs = tracker.get_call_kwargs("write_content")
    assert content_args[0] == mock_scene_path, "Scene path mismatch in write_text_file"
    assert content_args[1] == scene_in.content, "Content mismatch in write_text_file"
    assert content_kwargs.get("trigger_index") == False, "trigger_index should be False"
    
    # Verify index update with preloaded metadata
    index_args = tracker.get_call_args("index_update")
    index_kwargs = tracker.get_call_kwargs("index_update")
    assert index_args[0] == mock_scene_path, "Scene path mismatch in index_file"
    assert "preloaded_metadata" in index_kwargs, "preloaded_metadata missing in index_file"
    
    # Verify the preloaded metadata contains correct scene title
    preloaded_meta = index_kwargs["preloaded_metadata"]
    assert preloaded_meta["document_type"] == "Scene", "Incorrect document_type in preloaded metadata"
    assert preloaded_meta["document_title"] == "Updated Title", "Updated title not in preloaded metadata"
    assert preloaded_meta["chapter_id"] == chapter_id, "Chapter ID mismatch in preloaded metadata"


def test_update_scene_success_content_only(scene_service_with_mocks):
    """Test successfully updating only the scene content."""
    # --- Adjusted fixture unpacking ---
    service, mock_file_service, mock_chapter_service, mock_index_manager = scene_service_with_mocks
    # --- End Adjustment ---
    project_id = "proj-upd-scene-2"
    chapter_id = "chap-upd-scene-2"
    scene_id = "scene-upd-content"
    scene_in = SceneUpdate(content="Just new content.")
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    
    # Create a CallOrderTracker to track function call sequences
    tracker = CallOrderTracker()
    
    # Track key operations we want to verify
    tracker.track(mock_file_service, "write_chapter_metadata", "write_metadata")
    tracker.track(mock_file_service, "write_text_file", "write_content")
    tracker.track(mock_index_manager, "index_file", "index_update")
    
    # Define test data
    mock_chapter_metadata = {
        "scenes": {scene_id: {"title": "Content Scene", "order": 5}}
    }
    old_content = "Old content."

    # Configure mocks for the service calls
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.read_text_file.return_value = old_content # For get_by_id
    
    # Mock for project metadata (used in preloaded metadata)
    mock_project_metadata = {
        "chapters": {
            chapter_id: {
                "title": "Test Chapter",
                "order": 1
            }
        }
    }
    mock_file_service.read_project_metadata.return_value = mock_project_metadata

    # Call the service method being tested
    updated_scene = service.update(project_id, chapter_id, scene_id, scene_in)

    # Basic assertions about returned data
    assert updated_scene.title == "Content Scene" # Unchanged
    assert updated_scene.order == 5 # Unchanged
    assert updated_scene.content == scene_in.content # Updated

    # Verify operations occurred as expected
    assert not tracker.was_called("write_metadata"), "write_chapter_metadata should not have been called"
    assert tracker.was_called("write_content"), "write_text_file was not called"
    assert tracker.was_called("index_update"), "index_file was not called"
    
    # Verify correct order for operations that did occur
    assert tracker.called_before("write_content", "index_update"), "Content write should happen before index update"
    
    # Verify content write arguments
    content_args = tracker.get_call_args("write_content")
    content_kwargs = tracker.get_call_kwargs("write_content")
    assert content_args[0] == mock_scene_path, "Scene path mismatch in write_text_file"
    assert content_args[1] == scene_in.content, "Content mismatch in write_text_file"
    assert content_kwargs.get("trigger_index") == False, "trigger_index should be False"
    
    # Verify index update with preloaded metadata
    index_args = tracker.get_call_args("index_update")
    index_kwargs = tracker.get_call_kwargs("index_update")
    assert index_args[0] == mock_scene_path, "Scene path mismatch in index_file"
    assert "preloaded_metadata" in index_kwargs, "preloaded_metadata missing in index_file"
    
    # Verify the preloaded metadata contains correct scene title (unchanged in this case)
    preloaded_meta = index_kwargs["preloaded_metadata"]
    assert preloaded_meta["document_type"] == "Scene", "Incorrect document_type in preloaded metadata"
    assert preloaded_meta["document_title"] == "Content Scene", "Incorrect title in preloaded metadata"
    assert preloaded_meta["chapter_id"] == chapter_id, "Chapter ID mismatch in preloaded metadata"


def test_update_scene_no_change(scene_service_with_mocks):
    """Test update when no actual changes are provided."""
    # --- Adjusted fixture unpacking ---
    service, mock_file_service, mock_chapter_service, mock_index_manager = scene_service_with_mocks
    # --- End Adjustment ---
    project_id = "proj-upd-scene-no"
    chapter_id = "chap-upd-scene-no"
    scene_id = "scene-upd-no"
    # Provide same data as existing
    scene_in = SceneUpdate(title="Same Title", order=1, content="Same content.")
    mock_chapter_metadata = {
        "scenes": {scene_id: {"title": "Same Title", "order": 1}}
    }

    # Configure mocks for the *actual* service calls
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = Path("dummy") # Path needed for get_by_id
    mock_file_service.read_text_file.return_value = "Same content." # For get_by_id

    # Call the actual update method
    updated_scene = service.update(project_id, chapter_id, scene_id, scene_in)

    # Assertions
    assert updated_scene.title == "Same Title"
    assert updated_scene.order == 1
    assert updated_scene.content == "Same content."

    # Verify mocks
    mock_file_service.write_chapter_metadata.assert_not_called()
    mock_file_service.write_text_file.assert_not_called()
    # --- Verify index manager was NOT called ---
    mock_index_manager.index_file.assert_not_called()
    # --- End Verify ---


def test_update_scene_not_found(scene_service_with_mocks):
    """Test updating a scene that doesn't exist."""
    # --- Adjusted fixture unpacking ---
    service, mock_file_service, mock_chapter_service, mock_index_manager = scene_service_with_mocks
    # --- End Adjustment ---
    project_id = "proj-upd-scene-404"
    chapter_id = "chap-upd-scene-404"
    scene_id = "scene-upd-404"
    scene_in = SceneUpdate(title="Doesn't Matter")

    # Configure get_by_id (within chapter service) to raise 404
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    # Configure file service read_chapter_metadata to indicate scene not found
    mock_file_service.read_chapter_metadata.return_value = {"scenes": {}}

    with pytest.raises(HTTPException) as exc_info:
        service.update(project_id, chapter_id, scene_id, scene_in)

    assert exc_info.value.status_code == 404
    mock_file_service.write_chapter_metadata.assert_not_called()
    mock_file_service.write_text_file.assert_not_called()
    mock_index_manager.index_file.assert_not_called()


def test_update_scene_order_conflict(scene_service_with_mocks):
    """Test updating scene order causing a conflict."""
    # --- Adjusted fixture unpacking ---
    service, mock_file_service, mock_chapter_service, mock_index_manager = scene_service_with_mocks
    # --- End Adjustment ---
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

    # Configure mocks for the *actual* service calls
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = Path("dummy") # Path needed for get_by_id
    mock_file_service.read_text_file.return_value = "Content" # For get_by_id

    with pytest.raises(HTTPException) as exc_info:
        service.update(project_id, chapter_id, scene_id, scene_in)

    assert exc_info.value.status_code == 409
    assert "Scene order 2 already exists" in exc_info.value.detail
    mock_file_service.write_chapter_metadata.assert_not_called()
    mock_file_service.write_text_file.assert_not_called()
    mock_index_manager.index_file.assert_not_called()


# --- Tests for delete ---
# (delete tests unchanged - omitted)
def test_delete_scene_success(scene_service_with_mocks):
    """Test successfully deleting a scene."""
    service, mock_file_service, mock_chapter_service, _ = scene_service_with_mocks
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
        copy.deepcopy(mock_chapter_metadata_before), # For initial check
        copy.deepcopy(mock_chapter_metadata_before)  # For read before write
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
    service, mock_file_service, mock_chapter_service, _ = scene_service_with_mocks
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
    service, mock_file_service, mock_chapter_service, _ = scene_service_with_mocks
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
    service, mock_file_service, mock_chapter_service, _ = scene_service_with_mocks
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