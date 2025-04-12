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
from unittest.mock import MagicMock, patch, call, ANY # Import ANY
from fastapi import HTTPException, status
from pathlib import Path
import uuid # Import uuid
import time # Import time for timestamps

# Import the class we are testing
from app.services.project_service import ProjectService
# Import the dependency class/instance to mock it
from app.services.file_service import FileService # Import the class for spec
# Import models for type checking and creating instances
from app.models.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList

# --- Test ProjectService Methods ---

# Fixture to create a ProjectService instance with a mocked file_service
@pytest.fixture
def project_service_with_mocks():
    # Create a mock instance of FileService with the same interface
    mock_file_service_instance = MagicMock(spec=FileService)
    # Patch the singleton 'file_service' instance within the project_service module's scope
    with patch('app.services.project_service.file_service', mock_file_service_instance):
        service_instance = ProjectService()
        # Yield the instance and the mock for use in tests
        yield service_instance, mock_file_service_instance

# --- Tests for create ---
# (Unchanged - Omitted for brevity)
@patch('app.services.project_service.generate_uuid', return_value="new-uuid-123") # Mock UUID generation
def test_create_project_success(mock_uuid, project_service_with_mocks):
    """Test successful project creation."""
    service, mock_file_service = project_service_with_mocks
    project_in = ProjectCreate(name="Test Project")
    project_id = "new-uuid-123"
    mock_project_path = Path("user_projects") / project_id
    mock_meta_path = mock_project_path / "project_meta.json"
    mock_empty_meta = {"chapters": {}, "characters": {}} # What read might return after setup

    # Configure mock file_service behavior
    mock_file_service._get_project_path.return_value = mock_project_path
    mock_file_service.path_exists.return_value = False # No collision
    mock_file_service.setup_project_structure.return_value = None # Assume setup succeeds
    # Simulate read_json_file returning empty dict after setup creates the file
    mock_file_service.read_json_file.return_value = mock_empty_meta
    mock_file_service._get_project_metadata_path.return_value = mock_meta_path

    created_project = service.create(project_in)

    # Assertions
    assert isinstance(created_project, ProjectRead)
    assert created_project.id == project_id
    assert created_project.name == project_in.name

    # Verify mock calls
    mock_uuid.assert_called_once()
    mock_file_service._get_project_path.assert_called_once_with(project_id)
    mock_file_service.path_exists.assert_called_once_with(mock_project_path)
    mock_file_service.setup_project_structure.assert_called_once_with(project_id)
    mock_file_service._get_project_metadata_path.assert_called_once_with(project_id)
    mock_file_service.read_json_file.assert_called_once_with(mock_meta_path)
    # Verify the final metadata written
    expected_final_meta = {"project_name": project_in.name, "chapters": {}, "characters": {}}
    mock_file_service.write_json_file.assert_called_once_with(mock_meta_path, expected_final_meta)

@patch('app.services.project_service.generate_uuid', return_value="existing-uuid-456")
def test_create_project_collision(mock_uuid, project_service_with_mocks):
    """Test project creation failure due to ID collision (rare)."""
    service, mock_file_service = project_service_with_mocks
    project_in = ProjectCreate(name="Collision Project")
    project_id = "existing-uuid-456"
    mock_project_path = Path("user_projects") / project_id

    # Configure mock file_service behavior
    mock_file_service._get_project_path.return_value = mock_project_path
    mock_file_service.path_exists.return_value = True # Simulate collision

    # Call and assert exception
    with pytest.raises(HTTPException) as exc_info:
        service.create(project_in)

    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    mock_uuid.assert_called_once()
    mock_file_service._get_project_path.assert_called_once_with(project_id)
    mock_file_service.path_exists.assert_called_once_with(mock_project_path)
    mock_file_service.setup_project_structure.assert_not_called()
    mock_file_service.write_json_file.assert_not_called()

# --- Tests for get_by_id ---
# (Unchanged - Omitted for brevity)
@patch('pathlib.Path.is_dir', return_value=True)
def test_get_project_by_id_success(mock_is_dir, project_service_with_mocks): # Add mock_is_dir arg
    """Test successfully getting a project by ID."""
    service, mock_file_service = project_service_with_mocks
    project_id = "get-uuid-1"
    project_name = "Found Project"
    mock_project_path = Path("user_projects") / project_id
    mock_meta_path = mock_project_path / "project_meta.json"
    mock_metadata = {"project_name": project_name, "chapters": {}, "characters": {}}

    # Configure mocks
    mock_file_service._get_project_path.return_value = mock_project_path
    mock_file_service.path_exists.return_value = True # Project dir exists
    mock_file_service._get_project_metadata_path.return_value = mock_meta_path
    mock_file_service.read_json_file.return_value = mock_metadata

    project = service.get_by_id(project_id)

    # Assertions
    assert isinstance(project, ProjectRead)
    assert project.id == project_id
    assert project.name == project_name

    # Verify mocks
    mock_file_service._get_project_path.assert_called_once_with(project_id)
    mock_file_service.path_exists.assert_called_once_with(mock_project_path)
    # --- CORRECTED: Verify is_dir call on the Path object returned by _get_project_path ---
    mock_project_path.is_dir.assert_called_once()
    # --- END CORRECTED ---
    mock_file_service._get_project_metadata_path.assert_called_once_with(project_id)
    mock_file_service.read_json_file.assert_called_once_with(mock_meta_path)


def test_get_project_by_id_not_found_dir(project_service_with_mocks):
    """Test getting project when directory doesn't exist."""
    service, mock_file_service = project_service_with_mocks
    project_id = "get-uuid-404"
    mock_project_path = Path("user_projects") / project_id

    # Configure mocks
    mock_file_service._get_project_path.return_value = mock_project_path
    mock_file_service.path_exists.return_value = False # Directory does not exist

    # Call and assert exception
    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id)

    assert exc_info.value.status_code == status.HTTP_404_NOT_FOUND
    mock_file_service._get_project_path.assert_called_once_with(project_id)
    mock_file_service.path_exists.assert_called_once_with(mock_project_path)
    mock_file_service.read_json_file.assert_not_called()


@patch('pathlib.Path.is_dir', return_value=True)
def test_get_project_by_id_metadata_missing(mock_is_dir, project_service_with_mocks): # Add mock_is_dir arg
    """Test getting project when metadata file is missing (should use default name)."""
    service, mock_file_service = project_service_with_mocks
    project_id = "get-uuid-meta-404"
    mock_project_path = Path("user_projects") / project_id
    mock_meta_path = mock_project_path / "project_meta.json"

    # Configure mocks
    mock_file_service._get_project_path.return_value = mock_project_path
    mock_file_service.path_exists.return_value = True # Dir exists
    mock_file_service._get_project_metadata_path.return_value = mock_meta_path
    # Simulate metadata file not found
    mock_file_service.read_json_file.side_effect = HTTPException(status_code=404)

    project = service.get_by_id(project_id)

    # Assertions - Should return default name
    assert project.id == project_id
    assert project.name == f"Project {project_id}"

    # Verify mocks
    # --- CORRECTED: Verify is_dir call on the Path object returned by _get_project_path ---
    mock_project_path.is_dir.assert_called_once()
    # --- END CORRECTED ---
    mock_file_service._get_project_metadata_path.assert_called_once_with(project_id)
    mock_file_service.read_json_file.assert_called_once_with(mock_meta_path)

# --- Tests for get_all ---

def test_get_all_projects_success_and_sorted(project_service_with_mocks):
    """Test listing projects successfully and verifying sorting by last content mtime."""
    service, mock_file_service = project_service_with_mocks
    proj1_id = str(uuid.uuid4()) # Oldest
    proj2_id = str(uuid.uuid4()) # Newest
    proj3_id = str(uuid.uuid4()) # Middle
    invalid_dir_name = "not-a-uuid"
    proj_missing_meta_id = str(uuid.uuid4()) # Oldest missing meta

    mock_subdirs = [proj1_id, proj2_id, invalid_dir_name, proj3_id, proj_missing_meta_id]

    # Mock paths
    path1 = Path(f"user_projects/{proj1_id}")
    path2 = Path(f"user_projects/{proj2_id}")
    path3 = Path(f"user_projects/{proj3_id}")
    path_missing = Path(f"user_projects/{proj_missing_meta_id}")

    # Mock timestamps (Unix epoch floats)
    time_now = time.time()
    ts1 = time_now - 2000 # Oldest
    ts2 = time_now # Newest
    ts3 = time_now - 1000 # Middle
    ts_missing = time_now - 3000 # Oldest missing meta

    # Configure mocks
    mock_file_service.list_subdirectories.return_value = mock_subdirs
    mock_file_service._get_project_path.side_effect = lambda pid: {
        proj1_id: path1, proj2_id: path2, proj3_id: path3, proj_missing_meta_id: path_missing
    }.get(pid)

    # --- MODIFIED: Mock get_project_last_content_modification ---
    mock_file_service.get_project_last_content_modification.side_effect = lambda p: {
        path1: ts1, path2: ts2, path3: ts3, path_missing: ts_missing
    }.get(p)
    # --- END MODIFIED ---

    # Mock the behavior of get_by_id called internally
    def mock_get_by_id(pid):
        if pid == proj1_id: return ProjectRead(id=pid, name="Project One")
        if pid == proj2_id: return ProjectRead(id=pid, name="Project Two")
        if pid == proj3_id: return ProjectRead(id=pid, name="Project Three")
        if pid == proj_missing_meta_id: return ProjectRead(id=pid, name=f"Project {pid}") # Default name
        raise ValueError(f"get_by_id called unexpectedly for {pid}")

    # Patch the service's *own* get_by_id method for this test
    with patch.object(service, 'get_by_id', side_effect=mock_get_by_id) as mock_internal_get:
        project_list = service.get_all()

        # Assertions
        assert isinstance(project_list, ProjectList)
        assert len(project_list.projects) == 4 # proj1, proj2, proj3, proj_missing_meta
        # Verify the order is descending by timestamp (ts2 > ts3 > ts1 > ts_missing)
        assert project_list.projects[0].id == proj2_id # Newest
        assert project_list.projects[1].id == proj3_id # Middle
        assert project_list.projects[2].id == proj1_id # Oldest with meta
        assert project_list.projects[3].id == proj_missing_meta_id # Oldest missing meta

        # Verify mocks
        mock_file_service.list_subdirectories.assert_called_once_with(ANY)
        assert mock_internal_get.call_count == 4
        # --- MODIFIED: Verify new method call ---
        assert mock_file_service.get_project_last_content_modification.call_count == 4 # Called for each valid UUID dir
        # --- END MODIFIED ---

def test_get_all_projects_empty(project_service_with_mocks):
    """Test listing projects when the base directory is empty."""
    service, mock_file_service = project_service_with_mocks
    mock_file_service.list_subdirectories.return_value = [] # No subdirectories

    project_list = service.get_all()

    assert isinstance(project_list, ProjectList)
    assert len(project_list.projects) == 0
    mock_file_service.list_subdirectories.assert_called_once_with(ANY)
    # --- MODIFIED: Verify new method not called ---
    mock_file_service.get_project_last_content_modification.assert_not_called()
    # --- END MODIFIED ---

def test_get_all_projects_list_dir_error(project_service_with_mocks):
    """Test listing projects when listing subdirectories fails."""
    service, mock_file_service = project_service_with_mocks
    mock_file_service.list_subdirectories.side_effect = OSError("Permission denied")

    with pytest.raises(HTTPException) as exc_info:
        service.get_all()

    assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    assert "Error reading project directory" in exc_info.value.detail
    # --- MODIFIED: Verify new method not called ---
    mock_file_service.get_project_last_content_modification.assert_not_called()
    # --- END MODIFIED ---

# --- Tests for update ---
# (Unchanged - Omitted for brevity)
@patch('pathlib.Path.is_dir', return_value=True)
def test_update_project_success(mock_is_dir, project_service_with_mocks): # Add mock_is_dir arg
    """Test successfully updating a project name."""
    service, mock_file_service = project_service_with_mocks
    project_id = "update-uuid-1"
    old_name = "Old Project Name"
    new_name = "New Project Name"
    project_in = ProjectUpdate(name=new_name)
    mock_project_path = Path("user_projects") / project_id # Path needs to be mocked for is_dir call inside get_by_id
    mock_meta_path = mock_project_path / "project_meta.json"
    mock_metadata_before = {"project_name": old_name, "chapters": {}, "characters": {}}
    mock_metadata_after = {"project_name": new_name, "chapters": {}, "characters": {}}

    # Mock the get_by_id call made at the start of update
    mock_get_by_id = MagicMock(return_value=ProjectRead(id=project_id, name=old_name))

    # Configure file service mocks
    mock_file_service._get_project_metadata_path.return_value = mock_meta_path
    mock_file_service.read_json_file.return_value = mock_metadata_before
    # Mock the path used inside get_by_id
    mock_file_service._get_project_path.return_value = mock_project_path

    # Patch the service's *own* get_by_id method
    with patch.object(service, 'get_by_id', mock_get_by_id):
        updated_project = service.update(project_id, project_in)

        # Assertions
        assert isinstance(updated_project, ProjectRead)
        assert updated_project.id == project_id
        assert updated_project.name == new_name

        # Verify mocks
        mock_get_by_id.assert_called_once_with(project_id)
        # mock_is_dir is called inside the mocked get_by_id, so we don't check it directly here
        mock_file_service._get_project_metadata_path.assert_called_once_with(project_id)
        mock_file_service.read_json_file.assert_called_once_with(mock_meta_path)
        mock_file_service.write_json_file.assert_called_once_with(mock_meta_path, mock_metadata_after)

@patch('pathlib.Path.is_dir', return_value=True)
def test_update_project_no_change(mock_is_dir, project_service_with_mocks): # Add mock_is_dir arg
    """Test update when name is None or the same."""
    service, mock_file_service = project_service_with_mocks
    project_id = "update-uuid-nochange"
    current_name = "Current Name"
    mock_project_path = Path("user_projects") / project_id # Path needs to be mocked

    # Mock get_by_id
    mock_get_by_id = MagicMock(return_value=ProjectRead(id=project_id, name=current_name))
    # Mock the path used inside get_by_id
    mock_file_service._get_project_path.return_value = mock_project_path

    # Patch the service's own get_by_id method
    with patch.object(service, 'get_by_id', mock_get_by_id):
        # Test with None name
        updated_project_none = service.update(project_id, ProjectUpdate(name=None))
        assert updated_project_none.name == current_name

        # Test with same name
        updated_project_same = service.update(project_id, ProjectUpdate(name=current_name))
        assert updated_project_same.name == current_name

        # Assertions
        assert mock_get_by_id.call_count == 2
        mock_file_service.read_json_file.assert_not_called()
        mock_file_service.write_json_file.assert_not_called()

def test_update_project_not_found(project_service_with_mocks):
    """Test updating a project that doesn't exist."""
    service, mock_file_service = project_service_with_mocks
    project_id = "update-uuid-404"
    project_in = ProjectUpdate(name="New Name")

    # Configure get_by_id to raise 404
    mock_get_by_id = MagicMock(side_effect=HTTPException(status_code=404, detail="Project not found"))

    with patch.object(service, 'get_by_id', mock_get_by_id):
        with pytest.raises(HTTPException) as exc_info:
            service.update(project_id, project_in)

        assert exc_info.value.status_code == 404
        mock_get_by_id.assert_called_once_with(project_id)
        mock_file_service.write_json_file.assert_not_called()

# --- Tests for delete ---
# (Unchanged - Omitted for brevity)
@patch('pathlib.Path.is_dir', return_value=True)
def test_delete_project_success(mock_is_dir, project_service_with_mocks): # Add mock_is_dir arg
    """Test successfully deleting a project."""
    service, mock_file_service = project_service_with_mocks
    project_id = "delete-uuid-1"
    mock_project_path = Path("user_projects") / project_id

    # Mock get_by_id (just needs to not raise 404)
    mock_get_by_id = MagicMock(return_value=ProjectRead(id=project_id, name="ToDelete"))

    # Configure file service mocks
    mock_file_service._get_project_path.return_value = mock_project_path

    with patch.object(service, 'get_by_id', mock_get_by_id):
        service.delete(project_id)

        # Verify mocks
        mock_get_by_id.assert_called_once_with(project_id)
        mock_file_service._get_project_path.assert_called_once_with(project_id)
        # Verify delete_directory was called (which handles index cleanup)
        mock_file_service.delete_directory.assert_called_once_with(mock_project_path)

def test_delete_project_not_found(project_service_with_mocks):
    """Test deleting a project that doesn't exist."""
    service, mock_file_service = project_service_with_mocks
    project_id = "delete-uuid-404"

    # Configure get_by_id to raise 404
    mock_get_by_id = MagicMock(side_effect=HTTPException(status_code=404, detail="Project not found"))

    with patch.object(service, 'get_by_id', mock_get_by_id):
        with pytest.raises(HTTPException) as exc_info:
            service.delete(project_id)

        assert exc_info.value.status_code == 404
        mock_get_by_id.assert_called_once_with(project_id)
        mock_file_service.delete_directory.assert_not_called()