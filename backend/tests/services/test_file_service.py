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
from pathlib import Path
import json
from fastapi import HTTPException
import sys # Import sys

# Import the service instance we are testing
from app.services import file_service # Import the module itself
# --- MODIFIED: Import BASE_PROJECT_DIR from config ---
from app.core.config import BASE_PROJECT_DIR
# --- END MODIFIED ---

# --- Test Path Helper Methods ---

# These tests now use the imported BASE_PROJECT_DIR
def test_get_project_path():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id # Use imported constant
    assert file_service.file_service._get_project_path(project_id) == expected_path

def test_get_chapters_dir():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chapters" # Use imported constant
    assert file_service.file_service._get_chapters_dir(project_id) == expected_path

def test_get_chapter_path():
    project_id = "test-project-id"
    chapter_id = "test-chapter-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id # Use imported constant
    assert file_service.file_service._get_chapter_path(project_id, chapter_id) == expected_path

def test_get_scene_path():
    project_id = "test-project-id"
    chapter_id = "test-chapter-id"
    scene_id = "test-scene-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id / f"{scene_id}.md" # Use imported constant
    assert file_service.file_service._get_scene_path(project_id, chapter_id, scene_id) == expected_path

def test_get_characters_dir():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id / "characters" # Use imported constant
    assert file_service.file_service._get_characters_dir(project_id) == expected_path

def test_get_character_path():
    project_id = "test-project-id"
    character_id = "test-char-id"
    expected_path = BASE_PROJECT_DIR / project_id / "characters" / f"{character_id}.md" # Use imported constant
    assert file_service.file_service._get_character_path(project_id, character_id) == expected_path

def test_get_content_block_path():
    project_id = "test-project-id"
    expected_plan_path = BASE_PROJECT_DIR / project_id / "plan.md" # Use imported constant
    expected_synopsis_path = BASE_PROJECT_DIR / project_id / "synopsis.md" # Use imported constant
    expected_world_path = BASE_PROJECT_DIR / project_id / "world.md" # Use imported constant
    assert file_service.file_service._get_content_block_path(project_id, "plan.md") == expected_plan_path
    assert file_service.file_service._get_content_block_path(project_id, "synopsis.md") == expected_synopsis_path
    assert file_service.file_service._get_content_block_path(project_id, "world.md") == expected_world_path
    with pytest.raises(ValueError):
        file_service.file_service._get_content_block_path(project_id, "invalid_block.md")

def test_get_project_metadata_path():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id / "project_meta.json" # Use imported constant
    assert file_service.file_service._get_project_metadata_path(project_id) == expected_path

def test_get_chapter_metadata_path():
    project_id = "test-project-id"
    chapter_id = "test-chapter-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id / "chapter_meta.json" # Use imported constant
    assert file_service.file_service._get_chapter_metadata_path(project_id, chapter_id) == expected_path


# --- Test Basic File Operations using temp_project_dir ---

# Use monkeypatch fixture to temporarily change the module-level BASE_PROJECT_DIR
def test_create_directory(temp_project_dir: Path, monkeypatch):
    # Temporarily set the BASE_PROJECT_DIR used by the file_service module
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)

    project_id = "temp-proj"
    # Now _get_chapters_dir will use the monkeypatched BASE_PROJECT_DIR
    new_dir = file_service.file_service._get_chapters_dir(project_id)
    assert not new_dir.exists()
    file_service.file_service.create_directory(new_dir)
    assert new_dir.exists()
    assert new_dir.is_dir()
    # Test idempotency
    file_service.file_service.create_directory(new_dir)
    assert new_dir.exists()
    # monkeypatch automatically reverts the change after the test function exits

def test_write_read_text_file(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)

    project_id = "txt-proj"
    file_path = file_service.file_service._get_project_path(project_id) / "test_file.txt"
    content = "Hello, World!\nThis is a test."

    # Test writing (trigger_index=False to avoid mocking index_manager)
    file_service.file_service.write_text_file(file_path, content, trigger_index=False)
    assert file_path.exists()
    assert file_path.read_text(encoding='utf-8') == content

    # Test reading
    read_content = file_service.file_service.read_text_file(file_path)
    assert read_content == content

    # Test reading non-existent file
    non_existent_path = file_service.file_service._get_project_path(project_id) / "not_real.txt"
    with pytest.raises(HTTPException) as exc_info:
        file_service.file_service.read_text_file(non_existent_path)
    assert exc_info.value.status_code == 404

def test_write_read_json_file(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)

    project_id = "json-proj"
    file_path = file_service.file_service._get_project_metadata_path(project_id) # Use a json path helper
    data = {"name": "Test Project", "version": 1, "items": [1, "two", None]}

    # Test writing JSON
    file_service.file_service.write_json_file(file_path, data)
    assert file_path.exists()
    # Read back raw text to check formatting (optional)
    raw_content = file_path.read_text(encoding='utf-8')
    assert '"name": "Test Project"' in raw_content # Basic check

    # Test reading JSON
    read_data = file_service.file_service.read_json_file(file_path)
    assert read_data == data

    # Test reading non-existent JSON file (should raise 404 via read_text_file)
    non_existent_path = temp_project_dir / "non_existent.json"
    with pytest.raises(HTTPException) as exc_info:
        file_service.file_service.read_json_file(non_existent_path)
    assert exc_info.value.status_code == 404

    # Test reading invalid JSON file
    invalid_json_path = file_service.file_service._get_project_path(project_id) / "invalid.json"
    invalid_json_path.parent.mkdir(parents=True, exist_ok=True)
    invalid_json_path.write_text("{invalid json", encoding='utf-8')
    # Should log an error and return empty dict
    read_invalid = file_service.file_service.read_json_file(invalid_json_path)
    assert read_invalid == {}


# TODO: Add tests for delete_file, delete_directory (will require mocking index_manager.delete_doc)
# TODO: Add tests for write_text_file with trigger_index=True (will require mocking index_manager.index_file)
# TODO: Add tests for list_subdirectories, list_markdown_files
# TODO: Add tests for setup_project_structure, setup_chapter_structure