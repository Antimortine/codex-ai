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
import sys
from unittest.mock import patch, MagicMock, call # Import patch and MagicMock

# Import the service instance we are testing
from app.services import file_service # Import the module itself
# Import BASE_PROJECT_DIR from config
from app.core.config import BASE_PROJECT_DIR
# Import index_manager's module to specify the correct patch target
import app.rag.index_manager

# --- Test Path Helper Methods ---
# (These remain unchanged - Omitted for brevity)
def test_get_project_path():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id
    assert file_service.file_service._get_project_path(project_id) == expected_path

def test_get_chapters_dir():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chapters"
    assert file_service.file_service._get_chapters_dir(project_id) == expected_path

def test_get_chapter_path():
    project_id = "test-project-id"
    chapter_id = "test-chapter-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id
    assert file_service.file_service._get_chapter_path(project_id, chapter_id) == expected_path

def test_get_scene_path():
    project_id = "test-project-id"
    chapter_id = "test-chapter-id"
    scene_id = "test-scene-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id / f"{scene_id}.md"
    assert file_service.file_service._get_scene_path(project_id, chapter_id, scene_id) == expected_path

def test_get_characters_dir():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id / "characters"
    assert file_service.file_service._get_characters_dir(project_id) == expected_path

def test_get_character_path():
    project_id = "test-project-id"
    character_id = "test-char-id"
    expected_path = BASE_PROJECT_DIR / project_id / "characters" / f"{character_id}.md"
    assert file_service.file_service._get_character_path(project_id, character_id) == expected_path

def test_get_content_block_path():
    project_id = "test-project-id"
    expected_plan_path = BASE_PROJECT_DIR / project_id / "plan.md"
    expected_synopsis_path = BASE_PROJECT_DIR / project_id / "synopsis.md"
    expected_world_path = BASE_PROJECT_DIR / project_id / "world.md"
    assert file_service.file_service._get_content_block_path(project_id, "plan.md") == expected_plan_path
    assert file_service.file_service._get_content_block_path(project_id, "synopsis.md") == expected_synopsis_path
    assert file_service.file_service._get_content_block_path(project_id, "world.md") == expected_world_path
    with pytest.raises(ValueError):
        file_service.file_service._get_content_block_path(project_id, "invalid_block.md")

def test_get_project_metadata_path():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id / "project_meta.json"
    assert file_service.file_service._get_project_metadata_path(project_id) == expected_path

def test_get_chapter_metadata_path():
    project_id = "test-project-id"
    chapter_id = "test-chapter-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id / "chapter_meta.json"
    assert file_service.file_service._get_chapter_metadata_path(project_id, chapter_id) == expected_path


# --- Test Basic File Operations using temp_project_dir ---
# (These remain unchanged - Omitted for brevity)
def test_create_directory(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "temp-proj"
    new_dir = file_service.file_service._get_chapters_dir(project_id)
    assert not new_dir.exists()
    file_service.file_service.create_directory(new_dir)
    assert new_dir.exists()
    assert new_dir.is_dir()
    file_service.file_service.create_directory(new_dir)
    assert new_dir.exists()

@patch('app.rag.index_manager.index_manager', autospec=True)
def test_write_read_text_file_no_trigger(mock_index_mgr: MagicMock, temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "txt-proj"
    file_path = file_service.file_service._get_project_path(project_id) / "test_file.txt"
    content = "Hello, World!\nThis is a test."
    file_service.file_service.write_text_file(file_path, content, trigger_index=False)
    mock_index_mgr.index_file.assert_not_called()
    assert file_path.exists()
    assert file_path.read_text(encoding='utf-8') == content
    read_content = file_service.file_service.read_text_file(file_path)
    assert read_content == content
    non_existent_path = file_service.file_service._get_project_path(project_id) / "not_real.txt"
    with pytest.raises(HTTPException) as exc_info:
        file_service.file_service.read_text_file(non_existent_path)
    assert exc_info.value.status_code == 404

@patch('app.rag.index_manager.index_manager', autospec=True)
def test_write_read_json_file(mock_index_mgr: MagicMock, temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "json-proj"
    file_path = file_service.file_service._get_project_metadata_path(project_id)
    data = {"name": "Test Project", "version": 1, "items": [1, "two", None]}
    file_service.file_service.write_json_file(file_path, data)
    mock_index_mgr.index_file.assert_not_called()
    assert file_path.exists()
    raw_content = file_path.read_text(encoding='utf-8')
    assert '"name": "Test Project"' in raw_content
    read_data = file_service.file_service.read_json_file(file_path)
    assert read_data == data
    non_existent_path = temp_project_dir / "non_existent.json"
    with pytest.raises(HTTPException) as exc_info:
        file_service.file_service.read_json_file(non_existent_path)
    assert exc_info.value.status_code == 404
    invalid_json_path = file_service.file_service._get_project_path(project_id) / "invalid.json"
    invalid_json_path.parent.mkdir(parents=True, exist_ok=True)
    invalid_json_path.write_text("{invalid json", encoding='utf-8')
    read_invalid = file_service.file_service.read_json_file(invalid_json_path)
    assert read_invalid == {}

# --- Tests for Index Interaction ---
# (These remain unchanged - Omitted for brevity)
@patch('app.rag.index_manager.index_manager', autospec=True)
def test_write_text_file_triggers_index(mock_index_mgr: MagicMock, temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "index-proj"
    file_path = file_service.file_service._get_project_path(project_id) / "plan.md"
    content = "Index this content."
    file_service.file_service.write_text_file(file_path, content, trigger_index=True)
    assert file_path.exists()
    assert file_path.read_text(encoding='utf-8') == content
    mock_index_mgr.index_file.assert_called_once_with(file_path)

@patch('app.rag.index_manager.index_manager', autospec=True)
def test_write_text_file_no_trigger_for_non_md(mock_index_mgr: MagicMock, temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "index-proj-non-md"
    file_path = file_service.file_service._get_project_path(project_id) / "notes.txt"
    content = "Some notes."
    file_service.file_service.write_text_file(file_path, content, trigger_index=True)
    assert file_path.exists()
    mock_index_mgr.index_file.assert_not_called()

@patch('app.rag.index_manager.index_manager', autospec=True)
def test_write_text_file_no_trigger_outside_base(mock_index_mgr: MagicMock, tmp_path: Path):
    file_path = tmp_path / "outside_file.md"
    content = "Outside content."
    assert not str(file_path.resolve()).startswith(str(BASE_PROJECT_DIR.resolve()))
    file_service.file_service.write_text_file(file_path, content, trigger_index=True)
    assert file_path.exists()
    mock_index_mgr.index_file.assert_not_called()

@patch('app.rag.index_manager.index_manager', autospec=True)
def test_delete_file_triggers_index_delete(mock_index_mgr: MagicMock, temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "delete-proj"
    file_path = file_service.file_service._get_project_path(project_id) / "to_delete.md"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("Delete me", encoding='utf-8')
    assert file_path.exists()
    file_service.file_service.delete_file(file_path)
    assert not file_path.exists()
    mock_index_mgr.delete_doc.assert_called_once_with(file_path)

@patch('app.rag.index_manager.index_manager', autospec=True)
def test_delete_file_no_trigger_for_non_md(mock_index_mgr: MagicMock, temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "delete-proj-non-md"
    file_path = file_service.file_service._get_project_path(project_id) / "notes.txt"
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text("Delete me", encoding='utf-8')
    assert file_path.exists()
    file_service.file_service.delete_file(file_path)
    assert not file_path.exists()
    mock_index_mgr.delete_doc.assert_not_called()

@patch('app.rag.index_manager.index_manager', autospec=True)
def test_delete_directory_triggers_index_delete(mock_index_mgr: MagicMock, temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "delete-dir-proj"
    chapter_id = "ch1"
    dir_path = file_service.file_service._get_chapter_path(project_id, chapter_id)
    scene1_path = dir_path / "scene1.md"
    scene2_path = dir_path / "scene2.md"
    notes_path = dir_path / "notes.txt"
    sub_dir = dir_path / "subdir"
    sub_scene_path = sub_dir / "sub_scene.md"
    dir_path.mkdir(parents=True, exist_ok=True)
    sub_dir.mkdir(exist_ok=True)
    scene1_path.write_text("Scene 1", encoding='utf-8')
    scene2_path.write_text("Scene 2", encoding='utf-8')
    notes_path.write_text("Notes", encoding='utf-8')
    sub_scene_path.write_text("Sub Scene", encoding='utf-8')
    assert dir_path.exists()
    assert scene1_path.exists()
    assert sub_scene_path.exists()
    file_service.file_service.delete_directory(dir_path)
    assert not dir_path.exists()
    expected_calls = [call(scene1_path), call(scene2_path), call(sub_scene_path)]
    mock_index_mgr.delete_doc.assert_has_calls(expected_calls, any_order=True)
    assert mock_index_mgr.delete_doc.call_count == len(expected_calls)

# --- NEW: Tests for Listing and Setup Methods ---

def test_list_subdirectories(temp_project_dir: Path, monkeypatch):
    """Test listing subdirectories."""
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "list-proj"
    proj_path = file_service.file_service._get_project_path(project_id)
    chapters_path = file_service.file_service._get_chapters_dir(project_id)
    chars_path = file_service.file_service._get_characters_dir(project_id)
    other_dir = proj_path / "other"
    file1 = proj_path / "file1.txt"

    # Create structure
    proj_path.mkdir(parents=True, exist_ok=True)
    chapters_path.mkdir(exist_ok=True)
    chars_path.mkdir(exist_ok=True)
    other_dir.mkdir(exist_ok=True)
    file1.touch()

    # List subdirs of project path
    subdirs = file_service.file_service.list_subdirectories(proj_path)
    assert sorted(subdirs) == sorted(["chapters", "characters", "other"])

    # List subdirs of an empty dir
    assert file_service.file_service.list_subdirectories(chapters_path) == []

    # List subdirs of non-existent path
    assert file_service.file_service.list_subdirectories(proj_path / "nonexistent") == []

def test_list_markdown_files(temp_project_dir: Path, monkeypatch):
    """Test listing markdown files (stems)."""
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "list-md-proj"
    chapter_id = "ch1"
    chapter_path = file_service.file_service._get_chapter_path(project_id, chapter_id)
    scene1_path = chapter_path / "scene1.md"
    scene2_path = chapter_path / "scene2.MD" # Test case insensitivity
    notes_path = chapter_path / "notes.txt"
    meta_path = chapter_path / "chapter_meta.json"
    subdir = chapter_path / "subdir"

    # Create structure
    chapter_path.mkdir(parents=True, exist_ok=True)
    subdir.mkdir(exist_ok=True)
    scene1_path.touch()
    scene2_path.touch()
    notes_path.touch()
    meta_path.touch()

    # List md files
    md_files = file_service.file_service.list_markdown_files(chapter_path)
    assert sorted(md_files) == sorted(["scene1", "scene2"])

    # List md files of an empty dir
    assert file_service.file_service.list_markdown_files(subdir) == []

    # List md files of non-existent path
    assert file_service.file_service.list_markdown_files(chapter_path / "nonexistent") == []

def test_setup_chapter_structure(temp_project_dir: Path, monkeypatch):
    """Test setting up the chapter structure."""
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "setup-chap-proj"
    chapter_id = "ch_setup"
    chapter_path = file_service.file_service._get_chapter_path(project_id, chapter_id)
    meta_path = file_service.file_service._get_chapter_metadata_path(project_id, chapter_id)

    assert not chapter_path.exists()
    assert not meta_path.exists()

    # Patch index_manager to ensure it's NOT called for JSON write
    with patch('app.rag.index_manager.index_manager', autospec=True) as mock_index_mgr:
        file_service.file_service.setup_chapter_structure(project_id, chapter_id)
        mock_index_mgr.index_file.assert_not_called() # Should not be called by setup_chapter

    assert chapter_path.exists()
    assert chapter_path.is_dir()
    assert meta_path.exists()
    assert meta_path.is_file()
    # Check content of metadata file
    meta_content = json.loads(meta_path.read_text())
    assert meta_content == {"scenes": {}}

@patch('app.rag.index_manager.index_manager', autospec=True)
def test_setup_project_structure(mock_index_mgr: MagicMock, temp_project_dir: Path, monkeypatch):
    """Test setting up the project structure and initial file indexing."""
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "setup-proj"
    proj_path = file_service.file_service._get_project_path(project_id)
    chapters_path = file_service.file_service._get_chapters_dir(project_id)
    chars_path = file_service.file_service._get_characters_dir(project_id)
    plan_path = file_service.file_service._get_content_block_path(project_id, "plan.md")
    synopsis_path = file_service.file_service._get_content_block_path(project_id, "synopsis.md")
    world_path = file_service.file_service._get_content_block_path(project_id, "world.md")
    meta_path = file_service.file_service._get_project_metadata_path(project_id)

    assert not proj_path.exists()

    file_service.file_service.setup_project_structure(project_id)

    # Assert directories exist
    assert proj_path.exists() and proj_path.is_dir()
    assert chapters_path.exists() and chapters_path.is_dir()
    assert chars_path.exists() and chars_path.is_dir()

    # Assert files exist and have empty content initially (write_text_file handles this)
    assert plan_path.exists() and plan_path.read_text() == ""
    assert synopsis_path.exists() and synopsis_path.read_text() == ""
    assert world_path.exists() and world_path.read_text() == ""
    assert meta_path.exists()
    meta_content = json.loads(meta_path.read_text())
    assert meta_content == {"project_name": "", "chapters": {}, "characters": {}, "chat_sessions": {}}

    # Assert index_manager was called for the .md files
    expected_index_calls = [call(plan_path), call(synopsis_path), call(world_path)]
    mock_index_mgr.index_file.assert_has_calls(expected_index_calls, any_order=True)
    assert mock_index_mgr.index_file.call_count == 3