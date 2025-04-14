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
from unittest.mock import patch, MagicMock
from fastapi import HTTPException

from app.services.chapter_service import ChapterService
from app.models.scene import SceneRead, SceneList
from app.models.chapter import ChapterRead
from app.models.project import ProjectRead


# Simple mock class for SceneList
class MockSceneList:
    def __init__(self, scenes):
        self.scenes = scenes


@pytest.fixture
def chapter_service():
    return ChapterService()


@pytest.fixture
def setup_mocks():
    # Create patches for all dependencies
    patches = [
        patch("app.services.project_service.project_service"),
        patch("app.services.scene_service.scene_service"),
        patch.object(ChapterService, "get_by_id")
    ]
    
    # Start all patches
    mocks = [p.start() for p in patches]
    
    # Set up default return values
    project_mock, scene_mock, get_by_id_mock = mocks
    
    # Project service mock
    project = ProjectRead(id="project-123", name="Test Project", description="Test Description")
    project_mock.get_by_id.return_value = project
    
    # Chapter service get_by_id mock
    chapter = ChapterRead(id="chapter-123", project_id="project-123", title="Test Chapter", order=1)
    get_by_id_mock.return_value = chapter
    
    # Scene service mock - will be configured in individual tests
    
    # Return all mocks for use in tests
    yield {
        "project_service": project_mock,
        "scene_service": scene_mock, 
        "get_by_id": get_by_id_mock
    }
    
    # Stop all patches
    for p in patches:
        p.stop()


def test_compile_content_default(chapter_service, setup_mocks):
    """Test compiling content with multiple scenes and default parameters."""
    # Setup mock scenes
    scenes = [
        SceneRead(id="scene1", project_id="project-123", chapter_id="chapter-123", title="Scene 1", content="Content of scene 1", order=1),
        SceneRead(id="scene2", project_id="project-123", chapter_id="chapter-123", title="Scene 2", content="Content of scene 2", order=2),
        SceneRead(id="scene3", project_id="project-123", chapter_id="chapter-123", title="Scene 3", content="Content of scene 3", order=3)
    ]
    setup_mocks["scene_service"].get_all_for_chapter.return_value = MockSceneList(scenes)
    
    # Call the method with default parameters
    result = chapter_service.compile_chapter_content("project-123", "chapter-123")
    
    # Assertions
    assert "filename" in result
    assert result["filename"] == "test-chapter.md"
    
    # Check content includes titles by default
    assert "## Scene 1\n\nContent of scene 1" in result["content"]
    assert "## Scene 2\n\nContent of scene 2" in result["content"]
    assert "## Scene 3\n\nContent of scene 3" in result["content"]
    
    # Check separator
    assert "\n\n---\n\n" in result["content"]
    
    # Verify correct methods were called
    setup_mocks["get_by_id"].assert_called_once_with("project-123", "chapter-123")
    setup_mocks["scene_service"].get_all_for_chapter.assert_called_once_with("project-123", "chapter-123")


def test_compile_content_without_titles(chapter_service, setup_mocks):
    """Test compiling content with multiple scenes but without including titles."""
    # Setup mock scenes
    scenes = [
        SceneRead(id="scene1", project_id="project-123", chapter_id="chapter-123", title="Scene 1", content="Content of scene 1", order=1),
        SceneRead(id="scene2", project_id="project-123", chapter_id="chapter-123", title="Scene 2", content="Content of scene 2", order=2)
    ]
    setup_mocks["scene_service"].get_all_for_chapter.return_value = MockSceneList(scenes)
    
    # Call the method with include_titles=False
    result = chapter_service.compile_chapter_content("project-123", "chapter-123", include_titles=False)
    
    # Assertions
    assert "## Scene 1" not in result["content"]
    assert "## Scene 2" not in result["content"]
    assert "Content of scene 1" in result["content"]
    assert "Content of scene 2" in result["content"]


def test_compile_content_custom_separator(chapter_service, setup_mocks):
    """Test compiling content with a custom separator."""
    # Setup mock scenes
    scenes = [
        SceneRead(id="scene1", project_id="project-123", chapter_id="chapter-123", title="Scene 1", content="Content of scene 1", order=1),
        SceneRead(id="scene2", project_id="project-123", chapter_id="chapter-123", title="Scene 2", content="Content of scene 2", order=2)
    ]
    setup_mocks["scene_service"].get_all_for_chapter.return_value = MockSceneList(scenes)
    
    # Custom separator
    custom_separator = "\n\n***\n\n"
    
    # Call the method with custom separator
    result = chapter_service.compile_chapter_content(
        "project-123", "chapter-123", separator=custom_separator
    )
    
    # Assertions
    assert custom_separator in result["content"]
    assert "\n\n---\n\n" not in result["content"]  # Default separator should not be used


def test_compile_content_no_scenes(chapter_service, setup_mocks):
    """Test compiling content for a chapter with no scenes."""
    # Mock scene service to return empty list
    setup_mocks["scene_service"].get_all_for_chapter.return_value = MockSceneList([])
    
    # Call the method
    result = chapter_service.compile_chapter_content("project-123", "chapter-123")
    
    # Assertions
    assert result["content"] == ""
    assert result["filename"] == "test-chapter-empty.md"


def test_compile_content_empty_scene_content(chapter_service, setup_mocks):
    """Test compiling content with scenes that have empty or None content."""
    # Mock scene service to return scenes with empty content
    scenes = [
        SceneRead(id="scene1", project_id="project-123", chapter_id="chapter-123", title="Scene 1", content="", order=1),
        # SceneRead requires content to be a string, not None
        SceneRead(id="scene2", project_id="project-123", chapter_id="chapter-123", title="Scene 2", content="", order=2),
        SceneRead(id="scene3", project_id="project-123", chapter_id="chapter-123", title="Scene 3", content="Valid content", order=3)
    ]
    setup_mocks["scene_service"].get_all_for_chapter.return_value = MockSceneList(scenes)
    
    # Call the method
    result = chapter_service.compile_chapter_content("project-123", "chapter-123")
    
    # Assertions
    assert "## Scene 1\n\n" in result["content"]  # Empty content
    assert "## Scene 2\n\n" in result["content"]  # Empty content (previously None)
    assert "## Scene 3\n\nValid content" in result["content"]  # Valid content


def test_compile_content_filename_format(chapter_service, setup_mocks):
    """Test the filename format generated by compile_content."""
    # Configure get_by_id to return a chapter with special chars in the title
    setup_mocks["get_by_id"].return_value = ChapterRead(
        id="chapter-123", 
        project_id="project-123", 
        title="Special & Chars: In Title!", 
        order=1
    )
    
    # Mock scene service to return at least one scene
    setup_mocks["scene_service"].get_all_for_chapter.return_value = MockSceneList([
        SceneRead(id="scene1", project_id="project-123", chapter_id="chapter-123", title="Scene 1", content="Content", order=1)
    ])
    
    # Call the method
    result = chapter_service.compile_chapter_content("project-123", "chapter-123")
    
    # Assertions - verify slugification
    assert result["filename"] == "special-chars-in-title.md"


def test_compile_content_chapter_not_found(chapter_service, setup_mocks):
    """Test the behavior when chapter is not found."""
    # Mock get_by_id to raise HTTPException
    setup_mocks["get_by_id"].side_effect = HTTPException(status_code=404, detail="Chapter not found")
    
    # Call the method and assert it raises the same exception
    with pytest.raises(HTTPException) as excinfo:
        chapter_service.compile_chapter_content("project-123", "non-existent-chapter")
    
    assert excinfo.value.status_code == 404
    assert "Chapter not found" in str(excinfo.value.detail)


def test_compile_content_project_not_found(chapter_service, setup_mocks):
    """Test the behavior when project is not found."""
    # Mock the ChapterService.get_by_id method to raise HTTPException
    # This is because compile_chapter_content calls self.get_by_id, not project_service.get_by_id directly
    exception = HTTPException(status_code=404, detail="Project not found")
    setup_mocks["get_by_id"].side_effect = exception
    
    # Ensure the mock is reset
    setup_mocks["get_by_id"].reset_mock()
    
    # Call the method and assert it raises the same exception
    with pytest.raises(HTTPException) as excinfo:
        chapter_service.compile_chapter_content("non-existent-project", "chapter-123")
    
    # Verify that get_by_id was called with the correct IDs
    setup_mocks["get_by_id"].assert_called_once_with("non-existent-project", "chapter-123")
    
    # Verify the exception details
    assert excinfo.value.status_code == 404
    assert "Project not found" in str(excinfo.value.detail)
