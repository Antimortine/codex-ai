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
from app.services.character_service import CharacterService
# Import classes for dependencies
from app.services.file_service import FileService
from app.services.project_service import ProjectService
# Import models used
from app.models.character import CharacterCreate, CharacterUpdate, CharacterRead, CharacterList
from app.models.project import ProjectRead # Needed for mocking project_service.get_by_id

# --- Test CharacterService Methods ---

# Fixture to create a CharacterService instance with mocked dependencies
@pytest.fixture
def character_service_with_mocks():
    mock_file_service = MagicMock(spec=FileService)
    mock_project_service = MagicMock(spec=ProjectService)
    # Patch the singletons within the character_service module's scope
    with patch('app.services.character_service.file_service', mock_file_service), \
         patch('app.services.character_service.project_service', mock_project_service):
        service_instance = CharacterService()
        # Yield the instance and the mocks for use in tests
        yield service_instance, mock_file_service, mock_project_service

# --- Tests for create ---

def test_create_character_success(character_service_with_mocks):
    """Test successful character creation."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-create-char-1"
    char_in = CharacterCreate(name="Gandalf", description="A wizard.")
    mock_char_id = "new-char-uuid"
    mock_char_path = Path(f"user_projects/{project_id}/characters/{mock_char_id}.md")
    mock_project_metadata = {"project_name": "Test Proj", "chapters": {}, "characters": {}}

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service._get_character_path.return_value = mock_char_path
    mock_file_service.path_exists.return_value = False # No collision
    mock_file_service.read_project_metadata.return_value = mock_project_metadata

    # Mock generate_uuid
    with patch('app.services.character_service.generate_uuid', return_value=mock_char_id):
        created_char = service.create(project_id, char_in)

    # Assertions
    assert created_char.id == mock_char_id
    assert created_char.project_id == project_id
    assert created_char.name == char_in.name
    assert created_char.description == char_in.description

    # Verify mocks
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service._get_character_path.assert_called_once_with(project_id, mock_char_id)
    mock_file_service.path_exists.assert_called_once_with(mock_char_path)
    # Check write_text_file call (includes triggering index)
    mock_file_service.write_text_file.assert_called_once_with(mock_char_path, char_in.description, trigger_index=True)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    # Check the data written to project metadata
    expected_meta_write = {
        "project_name": "Test Proj",
        "chapters": {},
        "characters": {mock_char_id: {"name": char_in.name}}
    }
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, expected_meta_write)

def test_create_character_project_not_found(character_service_with_mocks):
    """Test character creation when the project doesn't exist."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-create-char-404p"
    char_in = CharacterCreate(name="Lost Character", description="")

    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")

    with pytest.raises(HTTPException) as exc_info:
        service.create(project_id, char_in)

    assert exc_info.value.status_code == 404
    mock_file_service.write_text_file.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_create_character_id_collision(character_service_with_mocks):
    """Test character creation ID collision (rare)."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-create-char-coll"
    char_in = CharacterCreate(name="Collision", description="")
    mock_char_id = "colliding-char-uuid"
    mock_char_path = Path(f"user_projects/{project_id}/characters/{mock_char_id}.md")

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service._get_character_path.return_value = mock_char_path
    mock_file_service.path_exists.return_value = True # Simulate collision

    with patch('app.services.character_service.generate_uuid', return_value=mock_char_id):
        with pytest.raises(HTTPException) as exc_info:
            service.create(project_id, char_in)

    assert exc_info.value.status_code == 409
    assert "Character ID collision" in exc_info.value.detail
    mock_file_service.write_text_file.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

# --- Tests for get_by_id ---

def test_get_character_by_id_success(character_service_with_mocks):
    """Test successfully getting a character by ID."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-get-char-1"
    char_id = "char-get-ok"
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")
    mock_project_metadata = {
        "characters": {char_id: {"name": "Found Character"}}
    }
    mock_description = "This is the character description."

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_character_path.return_value = mock_char_path
    mock_file_service.read_text_file.return_value = mock_description

    character = service.get_by_id(project_id, char_id)

    # Assertions
    assert character.id == char_id
    assert character.project_id == project_id
    assert character.name == "Found Character"
    assert character.description == mock_description

    # Verify mocks
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    mock_file_service._get_character_path.assert_called_once_with(project_id, char_id)
    mock_file_service.read_text_file.assert_called_once_with(mock_char_path)

def test_get_character_by_id_project_not_found(character_service_with_mocks):
    """Test getting character when project doesn't exist."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-get-char-404p"
    char_id = "char-whatever"

    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, char_id)

    assert exc_info.value.status_code == 404
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service.read_project_metadata.assert_not_called()
    mock_file_service.read_text_file.assert_not_called()

def test_get_character_by_id_not_in_metadata(character_service_with_mocks):
    """Test getting character when it's missing from project metadata."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-get-char-meta"
    char_id = "char-get-missing"
    mock_project_metadata = {"characters": {}} # Empty characters

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, char_id)

    assert exc_info.value.status_code == 404
    assert f"Character {char_id} not found" in exc_info.value.detail
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    mock_file_service._get_character_path.assert_not_called() # Doesn't get this far
    mock_file_service.read_text_file.assert_not_called()

def test_get_character_by_id_file_missing(character_service_with_mocks):
    """Test getting character when metadata exists but file is missing."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-get-char-file"
    char_id = "char-get-no-file"
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")
    mock_project_metadata = {
        "characters": {char_id: {"name": "Ghost Character"}}
    }

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Test Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_character_path.return_value = mock_char_path
    # Simulate file not found when reading
    mock_file_service.read_text_file.side_effect = HTTPException(status_code=404, detail="File not found")

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, char_id)

    assert exc_info.value.status_code == 404
    assert f"Character {char_id} data missing" in exc_info.value.detail
    mock_file_service.read_text_file.assert_called_once_with(mock_char_path)

# --- Tests for get_all_for_project ---

def test_get_all_characters_success(character_service_with_mocks):
    """Test listing characters successfully."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-list-char-1"
    char1_id, char2_id = "char-list-b", "char-list-a"
    mock_project_metadata = {
        "characters": {
            char1_id: {"name": "Bilbo"},
            char2_id: {"name": "Aragorn"},
        }
    }
    mock_path1 = Path(f"user_projects/{project_id}/characters/{char1_id}.md")
    mock_path2 = Path(f"user_projects/{project_id}/characters/{char2_id}.md")

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="List Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    # Simulate both files exist
    mock_file_service._get_character_path.side_effect = lambda p, c: mock_path1 if c == char1_id else mock_path2 if c == char2_id else None
    mock_file_service.path_exists.return_value = True

    char_list = service.get_all_for_project(project_id)

    # Assertions
    assert isinstance(char_list, CharacterList)
    assert len(char_list.characters) == 2
    # Check sorting by name
    assert char_list.characters[0].id == char2_id
    assert char_list.characters[0].name == "Aragorn"
    assert char_list.characters[0].description == "" # Description not included in list
    assert char_list.characters[1].id == char1_id
    assert char_list.characters[1].name == "Bilbo"
    assert char_list.characters[1].description == ""

    # Verify mocks
    mock_project_service.get_by_id.assert_called_once_with(project_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    assert mock_file_service._get_character_path.call_count == 2
    assert mock_file_service.path_exists.call_count == 2

def test_get_all_characters_empty(character_service_with_mocks):
    """Test listing characters when none exist."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-list-char-empty"
    mock_project_metadata = {"characters": {}}

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Empty Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata

    char_list = service.get_all_for_project(project_id)

    assert isinstance(char_list, CharacterList)
    assert len(char_list.characters) == 0
    mock_file_service._get_character_path.assert_not_called()
    mock_file_service.path_exists.assert_not_called()

def test_get_all_characters_project_not_found(character_service_with_mocks):
    """Test listing characters when project doesn't exist."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-list-char-404p"
    mock_project_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Project not found")

    with pytest.raises(HTTPException) as exc_info:
        service.get_all_for_project(project_id)

    assert exc_info.value.status_code == 404
    mock_file_service.read_project_metadata.assert_not_called()

def test_get_all_characters_skips_missing_file(character_service_with_mocks):
    """Test listing characters skips one whose file is missing."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-list-char-skip"
    char1_id, char2_id = "char-list-ok", "char-list-missing"
    mock_project_metadata = {
        "characters": {
            char1_id: {"name": "Exists"},
            char2_id: {"name": "Missing File"},
        }
    }
    mock_path1 = Path(f"user_projects/{project_id}/characters/{char1_id}.md")
    mock_path2 = Path(f"user_projects/{project_id}/characters/{char2_id}.md")

    # Configure mocks
    mock_project_service.get_by_id.return_value = ProjectRead(id=project_id, name="Skip Proj")
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_character_path.side_effect = lambda p, c: mock_path1 if c == char1_id else mock_path2 if c == char2_id else None
    # Simulate path exists for char1, but not for char2
    mock_file_service.path_exists.side_effect = lambda path: path == mock_path1

    char_list = service.get_all_for_project(project_id)

    # Assertions
    assert len(char_list.characters) == 1
    assert char_list.characters[0].id == char1_id
    assert char_list.characters[0].name == "Exists"

    # Verify mocks
    assert mock_file_service.path_exists.call_count == 2 # Checked both

# --- Tests for update ---

def test_update_character_success_name_only(character_service_with_mocks):
    """Test successfully updating only the character name."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-upd-char-1"
    char_id = "char-upd-name"
    char_in = CharacterUpdate(name="New Name")
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")
    mock_project_metadata_before = {
        "characters": {char_id: {"name": "Old Name"}}
    }
    mock_project_metadata_after = { # Expected state after update
        "characters": {char_id: {"name": "New Name"}}
    }
    old_description = "Description stays the same."

    # Mock the get_by_id call made at the start of update
    # This needs to return the full CharacterRead including description
    mock_get_by_id = MagicMock(return_value=CharacterRead(
        id=char_id, project_id=project_id, name="Old Name", description=old_description
    ))

    # Configure file service mocks
    mock_file_service.read_project_metadata.return_value = mock_project_metadata_before
    mock_file_service._get_character_path.return_value = mock_char_path # Needed if description was updated

    with patch.object(service, 'get_by_id', mock_get_by_id):
        updated_char = service.update(project_id, char_id, char_in)

    # Assertions
    assert updated_char.id == char_id
    assert updated_char.name == "New Name" # Updated
    assert updated_char.description == old_description # Unchanged

    # Verify mocks
    mock_get_by_id.assert_called_once_with(project_id, char_id)
    mock_file_service.read_project_metadata.assert_called_once_with(project_id)
    # Check metadata write
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, mock_project_metadata_after)
    # Check content write (should NOT be called)
    mock_file_service.write_text_file.assert_not_called()

def test_update_character_success_description_only(character_service_with_mocks):
    """Test successfully updating only the character description."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-upd-char-2"
    char_id = "char-upd-desc"
    char_in = CharacterUpdate(description="New description.")
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")
    mock_project_metadata = {
        "characters": {char_id: {"name": "Desc Char"}}
    }
    old_description = "Old description."

    # Mock get_by_id
    mock_get_by_id = MagicMock(return_value=CharacterRead(
        id=char_id, project_id=project_id, name="Desc Char", description=old_description
    ))

    # Configure file service mocks
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_character_path.return_value = mock_char_path

    with patch.object(service, 'get_by_id', mock_get_by_id):
        updated_char = service.update(project_id, char_id, char_in)

    # Assertions
    assert updated_char.name == "Desc Char" # Unchanged
    assert updated_char.description == "New description." # Updated

    # Verify mocks
    mock_file_service.write_project_metadata.assert_not_called() # Metadata not changed
    mock_file_service.write_text_file.assert_called_once_with(mock_char_path, "New description.", trigger_index=True)

def test_update_character_success_both(character_service_with_mocks):
    """Test successfully updating both name and description."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-upd-char-3"
    char_id = "char-upd-both"
    char_in = CharacterUpdate(name="New Both", description="New Desc Both")
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")
    mock_project_metadata_before = {"characters": {char_id: {"name": "Old Both"}}}
    mock_project_metadata_after = {"characters": {char_id: {"name": "New Both"}}}
    old_description = "Old Desc Both"

    mock_get_by_id = MagicMock(return_value=CharacterRead(
        id=char_id, project_id=project_id, name="Old Both", description=old_description
    ))
    mock_file_service.read_project_metadata.return_value = mock_project_metadata_before
    mock_file_service._get_character_path.return_value = mock_char_path

    with patch.object(service, 'get_by_id', mock_get_by_id):
        updated_char = service.update(project_id, char_id, char_in)

    assert updated_char.name == "New Both"
    assert updated_char.description == "New Desc Both"
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, mock_project_metadata_after)
    mock_file_service.write_text_file.assert_called_once_with(mock_char_path, "New Desc Both", trigger_index=True)


def test_update_character_no_change(character_service_with_mocks):
    """Test update when no actual changes are provided."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-upd-char-no"
    char_id = "char-upd-no"
    # Provide same data as existing
    char_in = CharacterUpdate(name="Same Name", description="Same description.")
    mock_project_metadata = {"characters": {char_id: {"name": "Same Name"}}}

    # Mock get_by_id
    mock_get_by_id = MagicMock(return_value=CharacterRead(
        id=char_id, project_id=project_id, name="Same Name", description="Same description."
    ))
    mock_file_service.read_project_metadata.return_value = mock_project_metadata

    with patch.object(service, 'get_by_id', mock_get_by_id):
        updated_char = service.update(project_id, char_id, char_in)

    # Assertions
    assert updated_char.name == "Same Name"
    assert updated_char.description == "Same description."

    # Verify mocks
    mock_file_service.write_project_metadata.assert_not_called()
    mock_file_service.write_text_file.assert_not_called()

def test_update_character_not_found(character_service_with_mocks):
    """Test updating a character that doesn't exist."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-upd-char-404"
    char_id = "char-upd-404"
    char_in = CharacterUpdate(name="Doesn't Matter")

    # Configure get_by_id to raise 404
    mock_get_by_id = MagicMock(side_effect=HTTPException(status_code=404, detail="Character not found"))

    with patch.object(service, 'get_by_id', mock_get_by_id):
        with pytest.raises(HTTPException) as exc_info:
            service.update(project_id, char_id, char_in)

    assert exc_info.value.status_code == 404
    mock_file_service.write_project_metadata.assert_not_called()
    mock_file_service.write_text_file.assert_not_called()

# --- Tests for delete ---

def test_delete_character_success(character_service_with_mocks):
    """Test successfully deleting a character."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-del-char-1"
    char_id = "char-del-ok"
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")
    mock_project_metadata_before = {
        "characters": {char_id: {"name": "To Delete"}}
    }
    mock_project_metadata_after = { # Expected state after delete
        "characters": {}
    }

    # Configure mocks
    # No need to mock get_by_id for delete, it checks metadata directly
    mock_file_service.read_project_metadata.side_effect = [
        mock_project_metadata_before, # For initial check
        mock_project_metadata_before  # For read before write
    ]
    mock_file_service._get_character_path.return_value = mock_char_path
    # delete_file is mocked implicitly by patching the file_service instance

    service.delete(project_id, char_id)

    # Verify mocks
    mock_file_service._get_character_path.assert_called_once_with(project_id, char_id)
    mock_file_service.delete_file.assert_called_once_with(mock_char_path) # delete_file handles index
    # Check metadata write
    mock_file_service.write_project_metadata.assert_called_once_with(project_id, mock_project_metadata_after)

def test_delete_character_not_found_meta_and_file(character_service_with_mocks):
    """Test deleting a character that doesn't exist in metadata or filesystem."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-del-char-404"
    char_id = "char-del-404"
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")
    mock_project_metadata = {"characters": {}} # Character not in metadata

    # Configure mocks
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_character_path.return_value = mock_char_path
    mock_file_service.path_exists.return_value = False # File also doesn't exist

    with pytest.raises(HTTPException) as exc_info:
        service.delete(project_id, char_id)

    assert exc_info.value.status_code == 404
    assert "Character not found" in exc_info.value.detail
    mock_file_service.delete_file.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()

def test_delete_character_not_found_meta_but_file_exists(character_service_with_mocks):
    """Test deleting character when file exists but metadata is missing (cleanup)."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-del-char-file"
    char_id = "char-del-file"
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")
    mock_project_metadata = {"characters": {}} # Character not in metadata

    # Configure mocks
    mock_file_service.read_project_metadata.return_value = mock_project_metadata
    mock_file_service._get_character_path.return_value = mock_char_path
    mock_file_service.path_exists.return_value = True # File *does* exist

    # Should still proceed to delete the file
    service.delete(project_id, char_id)

    # Verify mocks
    mock_file_service.delete_file.assert_called_once_with(mock_char_path)
    mock_file_service.write_project_metadata.assert_not_called() # Metadata wasn't changed

def test_delete_character_project_meta_missing(character_service_with_mocks):
    """Test deleting character when project metadata itself is missing."""
    service, mock_file_service, mock_project_service = character_service_with_mocks
    project_id = "proj-del-char-projmeta"
    char_id = "char-del-projmeta"
    mock_char_path = Path(f"user_projects/{project_id}/characters/{char_id}.md")

    # Configure mocks
    mock_file_service.read_project_metadata.side_effect = HTTPException(status_code=404, detail="Project meta not found")
    mock_file_service._get_character_path.return_value = mock_char_path
    mock_file_service.path_exists.return_value = False # Assume character file also missing

    with pytest.raises(HTTPException) as exc_info:
        service.delete(project_id, char_id)

    assert exc_info.value.status_code == 404
    # The service will raise 404 from read_project_metadata before specific char checks
    # Depending on how error bubbles, detail might be from the underlying read error
    assert "Project meta not found" in exc_info.value.detail
    mock_file_service.delete_file.assert_not_called()
    mock_file_service.write_project_metadata.assert_not_called()