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

# --- Test SceneService Read Methods ---

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

# --- Tests for get_by_id ---

def test_get_scene_by_id_success(scene_service_with_mocks):
    """Test successfully getting a scene by ID."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-get-scene-1"
    chapter_id = "chap-get-scene-1"
    scene_id = "scene-get-ok"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    mock_chapter_metadata = {
        "scenes": {scene_id: {"title": "Found Scene", "order": 1}}
    }
    mock_scene_content = "This is the scene content."

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1) # Chapter exists
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = mock_scene_path
    mock_file_service.read_text_file.return_value = mock_scene_content

    scene = service.get_by_id(project_id, chapter_id, scene_id)

    # Assertions
    assert scene.id == scene_id
    assert scene.project_id == project_id
    assert scene.chapter_id == chapter_id
    assert scene.title == "Found Scene"
    assert scene.order == 1
    assert scene.content == mock_scene_content

    # Verify mocks
    mock_chapter_service.get_by_id.assert_called_once_with(project_id, chapter_id)
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_file_service._get_scene_path.assert_called_once_with(project_id, chapter_id, scene_id)
    mock_file_service.read_text_file.assert_called_once_with(mock_scene_path)

def test_get_scene_by_id_chapter_not_found(scene_service_with_mocks):
    """Test getting scene when chapter doesn't exist."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-get-scene-404c"
    chapter_id = "chap-get-scene-404c"
    scene_id = "scene-whatever"

    mock_chapter_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Chapter not found")

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, chapter_id, scene_id)

    assert exc_info.value.status_code == 404
    mock_chapter_service.get_by_id.assert_called_once_with(project_id, chapter_id)
    mock_file_service.read_chapter_metadata.assert_not_called()
    mock_file_service.read_text_file.assert_not_called()

def test_get_scene_by_id_scene_not_in_metadata(scene_service_with_mocks):
    """Test getting scene when it's missing from chapter metadata."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-get-scene-meta"
    chapter_id = "chap-get-scene-meta"
    scene_id = "scene-get-missing"
    mock_chapter_metadata = {"scenes": {}} # Empty scenes

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, chapter_id, scene_id)

    assert exc_info.value.status_code == 404
    assert f"Scene {scene_id} not found" in exc_info.value.detail
    mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
    mock_file_service._get_scene_path.assert_not_called() # Doesn't get this far
    mock_file_service.read_text_file.assert_not_called()

def test_get_scene_by_id_file_missing(scene_service_with_mocks):
    """Test getting scene when metadata exists but file is missing."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-get-scene-file"
    chapter_id = "chap-get-scene-file"
    scene_id = "scene-get-no-file"
    mock_scene_path = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene_id}.md")
    mock_chapter_metadata = {
        "scenes": {scene_id: {"title": "Ghost Scene", "order": 1}}
    }

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Test Chapter", order=1)
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    mock_file_service._get_scene_path.return_value = mock_scene_path
    # Simulate file not found when reading
    mock_file_service.read_text_file.side_effect = HTTPException(status_code=404, detail="File not found")

    with pytest.raises(HTTPException) as exc_info:
        service.get_by_id(project_id, chapter_id, scene_id)

    assert exc_info.value.status_code == 404
    assert f"Scene {scene_id} data missing" in exc_info.value.detail
    mock_file_service.read_text_file.assert_called_once_with(mock_scene_path)

# --- Tests for get_all_for_chapter ---

def test_get_all_scenes_success(scene_service_with_mocks):
    """Test listing scenes successfully."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-list-scene-1"
    chapter_id = "chap-list-scene-1"
    scene1_id, scene2_id = "scene-list-b", "scene-list-a"
    mock_chapter_metadata = {
        "scenes": {
            scene1_id: {"title": "Scene Two", "order": 2},
            scene2_id: {"title": "Scene One", "order": 1},
        }
    }
    mock_path1 = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene1_id}.md")
    mock_path2 = Path(f"user_projects/{project_id}/chapters/{chapter_id}/{scene2_id}.md")
    content1 = "Content for scene 2"
    content2 = "Content for scene 1"

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="List Chapter", order=1)
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata
    # Mock the internal calls to get_by_id made by get_all_for_chapter
    def get_by_id_side_effect(p_id, c_id, s_id):
        if s_id == scene1_id:
            return SceneRead(id=scene1_id, project_id=p_id, chapter_id=c_id, title="Scene Two", order=2, content=content1)
        elif s_id == scene2_id:
            return SceneRead(id=scene2_id, project_id=p_id, chapter_id=c_id, title="Scene One", order=1, content=content2)
        else:
            raise HTTPException(status_code=404)
    # Patch the service's *own* get_by_id method for this test
    with patch.object(service, 'get_by_id', side_effect=get_by_id_side_effect) as mock_internal_get:
        scene_list = service.get_all_for_chapter(project_id, chapter_id)

        # Assertions
        assert isinstance(scene_list, SceneList)
        assert len(scene_list.scenes) == 2
        # Check sorting by order
        assert scene_list.scenes[0].id == scene2_id
        assert scene_list.scenes[0].title == "Scene One"
        assert scene_list.scenes[0].order == 1
        assert scene_list.scenes[0].content == content2
        assert scene_list.scenes[1].id == scene1_id
        assert scene_list.scenes[1].title == "Scene Two"
        assert scene_list.scenes[1].order == 2
        assert scene_list.scenes[1].content == content1

        # Verify mocks
        mock_chapter_service.get_by_id.assert_called_once_with(project_id, chapter_id)
        mock_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)
        assert mock_internal_get.call_count == 2 # Internal get_by_id called for each scene

def test_get_all_scenes_empty(scene_service_with_mocks):
    """Test listing scenes when none exist in the chapter."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-list-scene-empty"
    chapter_id = "chap-list-scene-empty"
    mock_chapter_metadata = {"scenes": {}}

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Empty Chapter", order=1)
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata

    scene_list = service.get_all_for_chapter(project_id, chapter_id)

    assert isinstance(scene_list, SceneList)
    assert len(scene_list.scenes) == 0

def test_get_all_scenes_chapter_not_found(scene_service_with_mocks):
    """Test listing scenes when the chapter doesn't exist."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-list-scene-404c"
    chapter_id = "chap-list-scene-404c"
    mock_chapter_service.get_by_id.side_effect = HTTPException(status_code=404, detail="Chapter not found")

    with pytest.raises(HTTPException) as exc_info:
        service.get_all_for_chapter(project_id, chapter_id)

    assert exc_info.value.status_code == 404
    mock_file_service.read_chapter_metadata.assert_not_called()

def test_get_all_scenes_skips_missing_file(scene_service_with_mocks):
    """Test listing scenes skips one whose file is missing."""
    service, mock_file_service, mock_chapter_service = scene_service_with_mocks
    project_id = "proj-list-scene-skip"
    chapter_id = "chap-list-scene-skip"
    scene1_id, scene2_id = "scene-list-ok", "scene-list-missing"
    mock_chapter_metadata = {
        "scenes": {
            scene1_id: {"title": "Exists", "order": 1},
            scene2_id: {"title": "Missing File", "order": 2},
        }
    }
    content1 = "Content for scene 1"

    # Configure mocks
    mock_chapter_service.get_by_id.return_value = ChapterRead(id=chapter_id, project_id=project_id, title="Skip Chapter", order=1)
    mock_file_service.read_chapter_metadata.return_value = mock_chapter_metadata

    # Mock the internal calls to get_by_id
    def get_by_id_side_effect(p_id, c_id, s_id):
        if s_id == scene1_id:
            return SceneRead(id=scene1_id, project_id=p_id, chapter_id=c_id, title="Exists", order=1, content=content1)
        elif s_id == scene2_id:
            # Simulate the 404 that get_by_id would raise if the file is missing
            raise HTTPException(status_code=404, detail=f"Scene {s_id} data missing")
        else:
            raise HTTPException(status_code=404)

    with patch.object(service, 'get_by_id', side_effect=get_by_id_side_effect) as mock_internal_get:
        scene_list = service.get_all_for_chapter(project_id, chapter_id)

        # Assertions
        assert len(scene_list.scenes) == 1
        assert scene_list.scenes[0].id == scene1_id
        assert scene_list.scenes[0].title == "Exists"

        # Verify mocks
        assert mock_internal_get.call_count == 2 # Called for both scenes