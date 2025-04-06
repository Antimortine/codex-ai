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
from app.core.config import settings
from app.rag.index_manager import index_manager

# Define a base path for storing projects
BASE_PROJECT_DIR = Path(getattr(settings, "BASE_PROJECT_DIR", "user_projects"))

# Ensure the base directory exists on startup
BASE_PROJECT_DIR.mkdir(parents=True, exist_ok=True)

class FileService:

    # --- Path Helper Methods ---
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

    # Original write_text_file - kept for non-indexed writes (like JSON metadata)
    def write_text_file(self, path: Path, content: str):
        """Writes content to a text file, creating parent dirs if needed. Does NOT index."""
        self.create_directory(path.parent)
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
            return {} # Return default empty dict

    def write_json_file(self, path: Path, data: dict):
        """Writes data to a JSON file using the non-indexing write_text_file."""
        try:
            content = json.dumps(data, indent=4)
            # Use the basic write_text_file for JSON metadata
            self.write_text_file(path, content)
        except TypeError as e:
             print(f"Error encoding JSON for {path}: {e}")
             raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not format data for {path.name}")

    def delete_file(self, path: Path):
        # --- ADD INDEX DELETION BEFORE FILE DELETION ---
        # Check if it's a markdown file we might have indexed
        # (More robust check might involve checking if path is within project structure)
        should_delete_from_index = path.suffix.lower() == '.md' and BASE_PROJECT_DIR in path.parents

        if should_delete_from_index:
            try:
                print(f"Attempting deletion from index before deleting file: {path}")
                index_manager.delete_doc(path)
            except Exception as e:
                # Log error but proceed with file deletion attempt
                print(f"Warning: Error deleting document {path.name} from index during file delete: {e}")

        # --- Original delete logic ---
        if not self.path_exists(path):
             # If we attempted index deletion above, the file might already be gone
             # Avoid raising 404 if index deletion succeeded but file was missing
             if should_delete_from_index:
                 print(f"Info: File {path.name} not found for deletion (might have been deleted after index removal attempt).")
                 return # Exit gracefully
             else:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path.name} not found")

        if not path.is_file():
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{path.name} is not a file")
        try:
            path.unlink()
            print(f"Successfully deleted file: {path}")
        except OSError as e:
            print(f"Error deleting file {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete {path.name}")

    def delete_directory(self, path: Path):
        """Deletes a directory and its contents recursively."""
        # --- ADD INDEX DELETION FOR ALL MARKDOWN FILES WITHIN ---
        # Recursively find all .md files and delete them from index first
        if self.path_exists(path) and path.is_dir():
            print(f"Attempting index deletion for all .md files within directory: {path}")
            markdown_files = list(path.rglob('*.md')) # Find all .md files recursively
            for md_file in markdown_files:
                try:
                    print(f"Attempting deletion from index for: {md_file}")
                    index_manager.delete_doc(md_file)
                except Exception as e:
                    print(f"Warning: Error deleting document {md_file.name} from index during directory delete: {e}")
                    # Continue deleting other files/index entries

        # --- Original delete logic ---
        if not self.path_exists(path):
             # Avoid error if directory was already gone after index cleanup attempts
             print(f"Info: Directory {path.name} not found for deletion (might have been deleted after index removal attempt).")
             return # Exit gracefully

        if not path.is_dir():
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{path.name} is not a directory")
        try:
            shutil.rmtree(path)
            print(f"Successfully deleted directory: {path}")
        except OSError as e:
            print(f"Error deleting directory {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete {path.name}")

    def list_subdirectories(self, path: Path) -> list[str]:
        """Lists names of immediate subdirectories."""
        # Keep as is
        if not self.path_exists(path) or not path.is_dir(): return []
        try: return [d.name for d in path.iterdir() if d.is_dir()]
        except OSError as e: print(f"Error listing directories in {path}: {e}"); return []

    def list_markdown_files(self, path: Path) -> list[str]:
        """Lists names of markdown files (without extension) in a directory."""
        # Keep as is
        if not self.path_exists(path) or not path.is_dir(): return []
        try: return [f.stem for f in path.iterdir() if f.is_file() and f.suffix.lower() == '.md']
        except OSError as e: print(f"Error listing markdown files in {path}: {e}"); return []

    # --- Specific Structure Creators ---

    def setup_project_structure(self, project_id: str):
        """Creates the basic directory structure for a new project."""
        project_path = self._get_project_path(project_id)
        self.create_directory(project_path)
        self.create_directory(self._get_chapters_dir(project_id))
        self.create_directory(self._get_characters_dir(project_id))
        # Use the new method for content blocks to ensure they get indexed initially
        self.write_content_block_file(project_id, "plan.md", "")
        self.write_content_block_file(project_id, "synopsis.md", "")
        self.write_content_block_file(project_id, "world.md", "")
        # Use non-indexing write for metadata
        self.write_json_file(self._get_project_metadata_path(project_id), {"project_name": "", "chapters": {}, "characters": {}}) # Added project_name key


    def setup_chapter_structure(self, project_id: str, chapter_id: str):
         """Creates the basic directory structure for a new chapter."""
         chapter_path = self._get_chapter_path(project_id, chapter_id)
         self.create_directory(chapter_path)
         # Use non-indexing write for metadata
         self.write_json_file(self._get_chapter_metadata_path(project_id, chapter_id), {"scenes": {}})

    # --- NEW METHOD for Content Blocks ---
    def write_content_block_file(self, project_id: str, block_name: str, content: str):
        """Writes content block file AND triggers indexing."""
        path = self._get_content_block_path(project_id, block_name)
        # Write the file first
        self.write_text_file(path, content) # Use the basic non-indexing write here
        # Then trigger indexing
        try:
            print(f"Content updated for {path.name}, indexing...")
            index_manager.index_file(path)
        except Exception as e:
            print(f"ERROR: Failed to index content block {path.name}: {e}")
            # Warn and continue

    # --- NEW METHOD for reading content blocks (optional, but consistent) ---
    def read_content_block_file(self, project_id: str, block_name: str) -> str:
         """Reads content block file."""
         path = self._get_content_block_path(project_id, block_name)
         return self.read_text_file(path) # Handles 404

# Create a single instance
file_service = FileService()