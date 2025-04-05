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

import shutil
import json
from pathlib import Path
from fastapi import HTTPException, status
from app.core.config import settings # We'll add BASE_PROJECT_DIR to config later

# Define a base path for storing projects (relative to the backend root or absolute)
# Let's assume it's defined in settings, defaulting to 'user_projects'
BASE_PROJECT_DIR = Path(getattr(settings, "BASE_PROJECT_DIR", "user_projects"))

# Ensure the base directory exists on startup
BASE_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

class FileService:

    def _get_project_path(self, project_id: str) -> Path:
        """Returns the path to the project directory."""
        return BASE_PROJECT_DIR / project_id

    def _get_chapters_dir(self, project_id: str) -> Path:
        """Returns the path to the chapters directory within a project."""
        return self._get_project_path(project_id) / "chapters"

    def _get_chapter_path(self, project_id: str, chapter_id: str) -> Path:
        """Returns the path to a specific chapter directory."""
        return self._get_chapters_dir(project_id) / chapter_id

    def _get_scenes_dir(self, project_id: str, chapter_id: str) -> Path:
        """Returns the path to the scenes directory within a chapter."""
        # Scenes are stored directly in chapter dir for simplicity now
        return self._get_chapter_path(project_id, chapter_id)

    def _get_scene_path(self, project_id: str, chapter_id: str, scene_id: str) -> Path:
        """Returns the path to a specific scene file."""
        return self._get_scenes_dir(project_id, chapter_id) / f"{scene_id}.md"

    def _get_characters_dir(self, project_id: str) -> Path:
        """Returns the path to the characters directory within a project."""
        return self._get_project_path(project_id) / "characters"

    def _get_character_path(self, project_id: str, character_id: str) -> Path:
        """Returns the path to a specific character file."""
        return self._get_characters_dir(project_id) / f"{character_id}.md"

    def _get_content_block_path(self, project_id: str, block_name: str) -> Path:
        """Returns the path to a content block file (plan, synopsis, world)."""
        # Ensure block_name is one of the allowed ones
        allowed_blocks = {"plan.md", "synopsis.md", "world.md"}
        if block_name not in allowed_blocks:
            # This is an internal error, should not happen if called correctly
            raise ValueError(f"Invalid content block name: {block_name}")
        return self._get_project_path(project_id) / block_name

    def _get_project_metadata_path(self, project_id: str) -> Path:
        """Path to the project's metadata file."""
        return self._get_project_path(project_id) / "project_meta.json"

    def _get_chapter_metadata_path(self, project_id: str, chapter_id: str) -> Path:
         """Path to the chapter's metadata file (contains scene info)."""
         return self._get_chapter_path(project_id, chapter_id) / "chapter_meta.json"

    # --- Core File Operations ---

    def path_exists(self, path: Path) -> bool:
        """Checks if a path exists."""
        return path.exists()

    def create_directory(self, path: Path):
        """Creates a directory, including parent directories."""
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            # Handle potential errors during directory creation
            print(f"Error creating directory {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not create directory structure for {path.name}")

    def read_text_file(self, path: Path) -> str:
        """Reads content from a text file."""
        if not self.path_exists(path):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path.name} not found")
        try:
            return path.read_text(encoding='utf-8')
        except IOError as e:
            print(f"Error reading file {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not read {path.name}")

    def write_text_file(self, path: Path, content: str):
        """Writes content to a text file, creating parent dirs if needed."""
        self.create_directory(path.parent) # Ensure parent directory exists
        try:
            path.write_text(content, encoding='utf-8')
        except IOError as e:
            print(f"Error writing file {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not write to {path.name}")

    def read_json_file(self, path: Path) -> dict:
        """Reads content from a JSON file."""
        content = self.read_text_file(path) # Handles 404
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from {path}: {e}")
            # Return default structure if file is corrupt or empty? Or raise error?
            # Let's return default empty dict for metadata for robustness
            return {}
            # Or raise:
            # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Invalid format in {path.name}")

    def write_json_file(self, path: Path, data: dict):
        """Writes data to a JSON file."""
        try:
            content = json.dumps(data, indent=4) # Pretty print JSON
            self.write_text_file(path, content)
        except TypeError as e:
             print(f"Error encoding JSON for {path}: {e}")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not format data for {path.name}")

    def delete_file(self, path: Path):
        """Deletes a file."""
        if not self.path_exists(path):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path.name} not found")
        if not path.is_file():
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{path.name} is not a file")
        try:
            path.unlink()
        except OSError as e:
            print(f"Error deleting file {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete {path.name}")

    def delete_directory(self, path: Path):
        """Deletes a directory and its contents recursively."""
        if not self.path_exists(path):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path.name} not found")
        if not path.is_dir():
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{path.name} is not a directory")
        try:
            shutil.rmtree(path)
        except OSError as e:
            print(f"Error deleting directory {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete {path.name}")

    def list_subdirectories(self, path: Path) -> list[str]:
        """Lists names of immediate subdirectories."""
        if not self.path_exists(path) or not path.is_dir():
            return [] # Return empty list if path doesn't exist or isn't a dir
        try:
            return [d.name for d in path.iterdir() if d.is_dir()]
        except OSError as e:
             print(f"Error listing directories in {path}: {e}")
             # Decide: return empty list or raise? Let's return empty.
             return []

    def list_markdown_files(self, path: Path) -> list[str]:
        """Lists names of markdown files (without extension) in a directory."""
        if not self.path_exists(path) or not path.is_dir():
            return []
        try:
            # Return just the stem (filename without extension)
            return [f.stem for f in path.iterdir() if f.is_file() and f.suffix.lower() == '.md']
        except OSError as e:
             print(f"Error listing markdown files in {path}: {e}")
             return []

    # --- Specific Structure Creators ---

    def setup_project_structure(self, project_id: str):
        """Creates the basic directory structure for a new project."""
        project_path = self._get_project_path(project_id)
        self.create_directory(project_path)
        self.create_directory(self._get_chapters_dir(project_id))
        self.create_directory(self._get_characters_dir(project_id))
        # Create empty content block files? Optional, but helps avoid 404s on first read.
        self.write_text_file(self._get_content_block_path(project_id, "plan.md"), "")
        self.write_text_file(self._get_content_block_path(project_id, "synopsis.md"), "")
        self.write_text_file(self._get_content_block_path(project_id, "world.md"), "")
        # Create empty project metadata file
        self.write_json_file(self._get_project_metadata_path(project_id), {"chapters": {}, "characters": {}})


    def setup_chapter_structure(self, project_id: str, chapter_id: str):
         """Creates the basic directory structure for a new chapter."""
         chapter_path = self._get_chapter_path(project_id, chapter_id)
         self.create_directory(chapter_path)
         # Create empty chapter metadata file (will store scene info)
         self.write_json_file(self._get_chapter_metadata_path(project_id, chapter_id), {"scenes": {}})

# Create a single instance for potential use with dependency injection later
file_service = FileService()