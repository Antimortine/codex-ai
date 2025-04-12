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
import time # Import time for timestamps
from fastapi import HTTPException
import sys
from unittest.mock import patch, MagicMock, call, ANY # Import ANY

# Import the service instance we are testing
from app.services import file_service # Import the module itself
# Import BASE_PROJECT_DIR from config
from app.core.config import BASE_PROJECT_DIR
# Import index_manager's module to specify the correct patch target
import app.rag.index_manager

# --- Test Path Helper Methods ---
# (Unchanged - Omitted for brevity)
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

def test_get_chat_history_path():
    project_id = "test-project-id"
    expected_path = BASE_PROJECT_DIR / project_id / "chat_history.json"
    assert file_service.file_service._get_chat_history_path(project_id) == expected_path


# --- Test Basic File Operations using temp_project_dir ---
# (Unchanged - Omitted for brevity)
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
    list_json_path = file_service.file_service._get_project_path(project_id) / "list.json"
    list_json_path.write_text("[1, 2, 3]", encoding='utf-8')
    read_list = file_service.file_service.read_json_file(list_json_path)
    assert read_list == {}


# --- Tests for Index Interaction ---
# (Unchanged - Omitted for brevity)
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

# --- Listing and Setup Methods ---
# (Unchanged - Omitted for brevity)
def test_list_subdirectories(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "list-proj"
    proj_path = file_service.file_service._get_project_path(project_id)
    chapters_path = file_service.file_service._get_chapters_dir(project_id)
    chars_path = file_service.file_service._get_characters_dir(project_id)
    other_dir = proj_path / "other"
    file1 = proj_path / "file1.txt"
    proj_path.mkdir(parents=True, exist_ok=True)
    chapters_path.mkdir(exist_ok=True)
    chars_path.mkdir(exist_ok=True)
    other_dir.mkdir(exist_ok=True)
    file1.touch()
    subdirs = file_service.file_service.list_subdirectories(proj_path)
    assert sorted(subdirs) == sorted(["chapters", "characters", "other"])
    assert file_service.file_service.list_subdirectories(chapters_path) == []
    assert file_service.file_service.list_subdirectories(proj_path / "nonexistent") == []

def test_list_markdown_files(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "list-md-proj"
    chapter_id = "ch1"
    chapter_path = file_service.file_service._get_chapter_path(project_id, chapter_id)
    scene1_path = chapter_path / "scene1.md"
    scene2_path = chapter_path / "scene2.MD" # Test case insensitivity
    notes_path = chapter_path / "notes.txt"
    meta_path = chapter_path / "chapter_meta.json"
    subdir = chapter_path / "subdir"
    chapter_path.mkdir(parents=True, exist_ok=True)
    subdir.mkdir(exist_ok=True)
    scene1_path.touch()
    scene2_path.touch()
    notes_path.touch()
    meta_path.touch()
    md_files = file_service.file_service.list_markdown_files(chapter_path)
    assert sorted(md_files) == sorted(["scene1", "scene2"])
    assert file_service.file_service.list_markdown_files(subdir) == []
    assert file_service.file_service.list_markdown_files(chapter_path / "nonexistent") == []

def test_setup_chapter_structure(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "setup-chap-proj"
    chapter_id = "ch_setup"
    chapter_path = file_service.file_service._get_chapter_path(project_id, chapter_id)
    meta_path = file_service.file_service._get_chapter_metadata_path(project_id, chapter_id)
    assert not chapter_path.exists()
    assert not meta_path.exists()
    with patch('app.rag.index_manager.index_manager', autospec=True) as mock_index_mgr:
        file_service.file_service.setup_chapter_structure(project_id, chapter_id)
        mock_index_mgr.index_file.assert_not_called()
    assert chapter_path.exists()
    assert chapter_path.is_dir()
    assert meta_path.exists()
    assert meta_path.is_file()
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
    notes_path = file_service.file_service._get_notes_dir(project_id)
    plan_path = file_service.file_service._get_content_block_path(project_id, "plan.md")
    synopsis_path = file_service.file_service._get_content_block_path(project_id, "synopsis.md")
    world_path = file_service.file_service._get_content_block_path(project_id, "world.md")
    meta_path = file_service.file_service._get_project_metadata_path(project_id)
    chat_history_path = file_service.file_service._get_chat_history_path(project_id)

    assert not proj_path.exists()

    file_service.file_service.setup_project_structure(project_id)

    # Assert directories exist
    assert proj_path.exists() and proj_path.is_dir()
    assert chapters_path.exists() and chapters_path.is_dir()
    assert chars_path.exists() and chars_path.is_dir()
    assert notes_path.exists() and notes_path.is_dir()

    # Assert files exist and have empty content initially
    assert plan_path.exists() and plan_path.read_text() == ""
    assert synopsis_path.exists() and synopsis_path.read_text() == ""
    assert world_path.exists() and world_path.read_text() == ""
    assert meta_path.exists()
    meta_content = json.loads(meta_path.read_text())
    assert meta_content == {"project_name": "", "chapters": {}, "characters": {}, "chat_sessions": {}}
    assert chat_history_path.exists()
    chat_history_content = json.loads(chat_history_path.read_text())
    assert chat_history_content == {}

    # Assert index_manager was called for the .md files
    expected_index_calls = [call(plan_path), call(synopsis_path), call(world_path)]
    mock_index_mgr.index_file.assert_has_calls(expected_index_calls, any_order=True)
    assert mock_index_mgr.index_file.call_count == 3

# --- Chat History and Session Metadata Tests ---
# (Unchanged - Omitted for brevity)
def test_read_chat_history_file_success(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "chat-proj"
    history_path = file_service.file_service._get_chat_history_path(project_id)
    history_data = {
        "session1": [{"id": 0, "query": "q1", "response": {"answer": "a1"}}],
        "session2": [{"id": 0, "query": "q2", "error": "e2"}],
        "session3_invalid": "not a list" # Invalid entry
    }
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history_data), encoding='utf-8')
    read_data = file_service.file_service.read_chat_history_file(project_id)
    assert "session1" in read_data
    assert "session2" in read_data
    assert "session3_invalid" not in read_data
    assert read_data["session1"] == history_data["session1"]

def test_read_chat_history_file_not_found(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "chat-proj-404"
    read_data = file_service.file_service.read_chat_history_file(project_id)
    assert read_data == {}

def test_read_chat_history_file_not_dict(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "chat-proj-list"
    history_path = file_service.file_service._get_chat_history_path(project_id)
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps([1, 2, 3]), encoding='utf-8') # Write a list instead of dict
    read_data = file_service.file_service.read_chat_history_file(project_id)
    assert read_data == {}

def test_write_chat_history_file(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "chat-proj-write"
    history_path = file_service.file_service._get_chat_history_path(project_id)
    history_data = {
        "s1": [{"id": 0, "query": "q"}],
        "s2": []
    }
    file_service.file_service.write_chat_history_file(project_id, history_data)
    assert history_path.exists()
    read_back = json.loads(history_path.read_text(encoding='utf-8'))
    assert read_back == history_data

def test_read_write_delete_chat_session_history(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "chat-session-rw"
    session_id_1 = "sess_abc"
    session_id_2 = "sess_xyz"
    history1 = [{"id": 0, "query": "q1"}]
    history2 = [{"id": 0, "query": "q2"}]
    assert file_service.file_service.read_chat_session_history(project_id, session_id_1) == []
    file_service.file_service.write_chat_session_history(project_id, session_id_1, history1)
    assert file_service.file_service.read_chat_session_history(project_id, session_id_1) == history1
    assert file_service.file_service.read_chat_session_history(project_id, session_id_2) == []
    file_service.file_service.write_chat_session_history(project_id, session_id_2, history2)
    assert file_service.file_service.read_chat_session_history(project_id, session_id_1) == history1
    assert file_service.file_service.read_chat_session_history(project_id, session_id_2) == history2
    file_service.file_service.delete_chat_session_history(project_id, session_id_1)
    assert file_service.file_service.read_chat_session_history(project_id, session_id_1) == []
    assert file_service.file_service.read_chat_session_history(project_id, session_id_2) == history2
    file_service.file_service.delete_chat_session_history(project_id, "non-existent")
    assert file_service.file_service.read_chat_session_history(project_id, session_id_2) == history2


def test_get_chat_sessions_metadata_success(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "meta-proj"
    meta_path = file_service.file_service._get_project_metadata_path(project_id)
    meta_data = {
        "project_name": "Meta Test",
        "chapters": {},
        "characters": {},
        "chat_sessions": {
            "sess1": {"name": "Session One"},
            "sess2": {"name": "Session Two"}
        }
    }
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta_data), encoding='utf-8')
    sessions = file_service.file_service.get_chat_sessions_metadata(project_id)
    assert sessions == meta_data["chat_sessions"]

def test_get_chat_sessions_metadata_missing_key(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "meta-proj-nokey"
    meta_path = file_service.file_service._get_project_metadata_path(project_id)
    meta_data = {"project_name": "No Key"} # Missing chat_sessions
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    meta_path.write_text(json.dumps(meta_data), encoding='utf-8')
    sessions = file_service.file_service.get_chat_sessions_metadata(project_id)
    assert sessions == {} # Should return empty dict

def test_add_update_delete_chat_session_metadata(temp_project_dir: Path, monkeypatch):
    monkeypatch.setattr(file_service, 'BASE_PROJECT_DIR', temp_project_dir)
    project_id = "meta-crud"
    meta_path = file_service.file_service._get_project_metadata_path(project_id)
    session_id_1 = "crud_s1"
    session_id_2 = "crud_s2"
    meta_path.parent.mkdir(parents=True, exist_ok=True)
    file_service.file_service.write_project_metadata(project_id, {"chat_sessions": {}})
    file_service.file_service.add_chat_session_metadata(project_id, session_id_1, "First Session")
    meta = file_service.file_service.read_project_metadata(project_id)
    assert meta["chat_sessions"] == {session_id_1: {"name": "First Session"}}
    file_service.file_service.add_chat_session_metadata(project_id, session_id_2, "Second Session")
    meta = file_service.file_service.read_project_metadata(project_id)
    assert meta["chat_sessions"] == {
        session_id_1: {"name": "First Session"},
        session_id_2: {"name": "Second Session"}
    }
    file_service.file_service.update_chat_session_metadata(project_id, session_id_1, "Updated First")
    meta = file_service.file_service.read_project_metadata(project_id)
    assert meta["chat_sessions"][session_id_1]["name"] == "Updated First"
    assert meta["chat_sessions"][session_id_2]["name"] == "Second Session"
    file_service.file_service.delete_chat_session_metadata(project_id, session_id_2)
    meta = file_service.file_service.read_project_metadata(project_id)
    assert meta["chat_sessions"] == {session_id_1: {"name": "Updated First"}}
    file_service.file_service.delete_chat_session_metadata(project_id, "non-existent")
    meta = file_service.file_service.read_project_metadata(project_id)
    assert meta["chat_sessions"] == {session_id_1: {"name": "Updated First"}}

# --- ADDED: Tests for get_project_last_content_modification ---

def create_mock_path(path_str, is_dir, is_file, mtime, children=None, suffix='.txt', relative_parts=None):
    """Helper to create a mock Path object."""
    mock = MagicMock(spec=Path)
    mock.name = Path(path_str).name
    mock.is_dir.return_value = is_dir
    mock.is_file.return_value = is_file
    mock.stat.return_value.st_mtime = mtime
    mock.suffix = suffix
    mock.__str__.return_value = path_str
    mock.resolve.return_value = mock # Simple resolve for testing

    # Mock relative_to to return a mock object with parts
    mock_relative = MagicMock()
    mock_relative.parts = relative_parts if relative_parts is not None else Path(path_str).parts
    mock.relative_to.return_value = mock_relative

    # Mock rglob to return children if provided
    if children is not None:
        mock.rglob.return_value = children
    else:
        mock.rglob.return_value = []

    return mock

@patch('app.services.file_service.Path', autospec=True)
def test_get_last_content_modification_empty_dir(mock_path_cls):
    """Test with an empty directory."""
    dir_mtime = time.time() - 1000
    mock_project_path = create_mock_path("user_projects/proj_empty", is_dir=True, is_file=False, mtime=dir_mtime, children=[])
    mock_path_cls.return_value = mock_project_path # Mock Path() constructor

    # Mock path_exists used internally
    with patch.object(file_service.file_service, 'path_exists', return_value=True):
        result_mtime = file_service.file_service.get_project_last_content_modification(mock_project_path)

    assert result_mtime == dir_mtime # Should return the directory's own mtime

@patch('app.services.file_service.Path', autospec=True)
def test_get_last_content_modification_only_irrelevant_files(mock_path_cls):
    """Test with only files that should be ignored."""
    dir_mtime = time.time() - 2000
    file1_mtime = time.time() - 1500
    file2_mtime = time.time() - 1800 # Older than file1, newer than dir

    mock_file1 = create_mock_path("user_projects/proj_irrelevant/config.ini", is_dir=False, is_file=True, mtime=file1_mtime, suffix='.ini')
    mock_file2 = create_mock_path("user_projects/proj_irrelevant/image.jpg", is_dir=False, is_file=True, mtime=file2_mtime, suffix='.jpg')
    mock_project_path = create_mock_path("user_projects/proj_irrelevant", is_dir=True, is_file=False, mtime=dir_mtime, children=[mock_file1, mock_file2])
    mock_path_cls.return_value = mock_project_path

    with patch.object(file_service.file_service, 'path_exists', return_value=True):
        result_mtime = file_service.file_service.get_project_last_content_modification(mock_project_path)

    assert result_mtime == dir_mtime # Should return dir mtime as no relevant files found

@patch('app.services.file_service.Path', autospec=True)
def test_get_last_content_modification_finds_latest_md(mock_path_cls):
    """Test finding the latest among .md and .json files."""
    dir_mtime = time.time() - 3000
    plan_mtime = time.time() - 2500
    scene1_mtime = time.time() - 1000 # Latest
    meta_mtime = time.time() - 2800
    other_mtime = time.time() - 500 # Irrelevant but newest overall

    mock_plan = create_mock_path("user_projects/proj_latest/plan.md", is_dir=False, is_file=True, mtime=plan_mtime, suffix='.md')
    mock_scene1 = create_mock_path("user_projects/proj_latest/chapters/ch1/scene1.md", is_dir=False, is_file=True, mtime=scene1_mtime, suffix='.md')
    mock_meta = create_mock_path("user_projects/proj_latest/project_meta.json", is_dir=False, is_file=True, mtime=meta_mtime, suffix='.json')
    mock_other = create_mock_path("user_projects/proj_latest/temp.tmp", is_dir=False, is_file=True, mtime=other_mtime, suffix='.tmp')
    mock_project_path = create_mock_path("user_projects/proj_latest", is_dir=True, is_file=False, mtime=dir_mtime, children=[mock_plan, mock_scene1, mock_meta, mock_other])
    mock_path_cls.return_value = mock_project_path

    with patch.object(file_service.file_service, 'path_exists', return_value=True):
        result_mtime = file_service.file_service.get_project_last_content_modification(mock_project_path)

    assert result_mtime == scene1_mtime # Should return the mtime of the latest relevant file

@patch('app.services.file_service.Path', autospec=True)
def test_get_last_content_modification_skips_excluded_dirs(mock_path_cls):
    """Test that files within excluded directories are ignored."""
    dir_mtime = time.time() - 4000
    plan_mtime = time.time() - 3000 # This should be the latest relevant
    venv_file_mtime = time.time() - 1000 # Newest overall, but excluded
    chroma_file_mtime = time.time() - 2000 # Also excluded

    mock_plan = create_mock_path("user_projects/proj_exclude/plan.md", is_dir=False, is_file=True, mtime=plan_mtime, suffix='.md', relative_parts=('plan.md',))
    # Mock files within excluded dirs - need correct relative_parts
    mock_venv_file = create_mock_path("user_projects/proj_exclude/venv/lib/site.py", is_dir=False, is_file=True, mtime=venv_file_mtime, suffix='.py', relative_parts=('venv', 'lib', 'site.py'))
    mock_chroma_file = create_mock_path("user_projects/proj_exclude/chroma_db/data.log", is_dir=False, is_file=True, mtime=chroma_file_mtime, suffix='.log', relative_parts=('chroma_db', 'data.log'))
    mock_project_path = create_mock_path("user_projects/proj_exclude", is_dir=True, is_file=False, mtime=dir_mtime, children=[mock_plan, mock_venv_file, mock_chroma_file])
    mock_path_cls.return_value = mock_project_path

    with patch.object(file_service.file_service, 'path_exists', return_value=True):
        result_mtime = file_service.file_service.get_project_last_content_modification(mock_project_path)

    assert result_mtime == plan_mtime # Should ignore files in venv and chroma_db

@patch('app.services.file_service.Path', autospec=True)
def test_get_last_content_modification_handles_stat_error(mock_path_cls):
    """Test that it handles OSError when stating a file."""
    dir_mtime = time.time() - 3000
    plan_mtime = time.time() - 2000 # Should be the result
    error_file_mtime = time.time() - 1000 # Would be latest, but stat fails

    mock_plan = create_mock_path("user_projects/proj_stat_err/plan.md", is_dir=False, is_file=True, mtime=plan_mtime, suffix='.md')
    mock_error_file = create_mock_path("user_projects/proj_stat_err/error.json", is_dir=False, is_file=True, mtime=error_file_mtime, suffix='.json')
    # Make stat raise an error for this specific file
    mock_error_file.stat.side_effect = OSError("Permission denied")
    mock_project_path = create_mock_path("user_projects/proj_stat_err", is_dir=True, is_file=False, mtime=dir_mtime, children=[mock_plan, mock_error_file])
    mock_path_cls.return_value = mock_project_path

    with patch.object(file_service.file_service, 'path_exists', return_value=True):
        result_mtime = file_service.file_service.get_project_last_content_modification(mock_project_path)

    assert result_mtime == plan_mtime # Should ignore the file that caused stat error

@patch('app.services.file_service.Path', autospec=True)
def test_get_last_content_modification_non_existent_dir(mock_path_cls):
    """Test when the project path doesn't exist."""
    mock_project_path = create_mock_path("user_projects/proj_non_exist", is_dir=False, is_file=False, mtime=0)
    mock_path_cls.return_value = mock_project_path

    # Mock path_exists to return False
    with patch.object(file_service.file_service, 'path_exists', return_value=False):
        result_mtime = file_service.file_service.get_project_last_content_modification(mock_project_path)

    assert result_mtime is None

@patch('app.services.file_service.Path', autospec=True)
def test_get_last_content_modification_path_is_file(mock_path_cls):
    """Test when the provided path is a file, not a directory."""
    file_mtime = time.time() - 500
    mock_file_path = create_mock_path("user_projects/proj_is_file.md", is_dir=False, is_file=True, mtime=file_mtime, suffix='.md')
    mock_path_cls.return_value = mock_file_path

    # Mock path_exists to return True
    with patch.object(file_service.file_service, 'path_exists', return_value=True):
        result_mtime = file_service.file_service.get_project_last_content_modification(mock_file_path)

    assert result_mtime is None # Should return None as it expects a directory

# --- END ADDED ---