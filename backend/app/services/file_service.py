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
from app.core.config import BASE_PROJECT_DIR
# ---- REMOVE the direct import of index_manager here ----
# from app.rag.index_manager import index_manager
import logging
# --- ADDED: Import List type hint ---
from typing import List

logger = logging.getLogger(__name__)

class FileService:

    # --- Path Helper Methods ---
    # ... (existing helpers unchanged) ...
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
        # In our current structure, scenes are directly in the chapter dir
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
        allowed_blocks = {"plan.md", "synopsis.md", "world.md"}
        if block_name not in allowed_blocks:
            raise ValueError(f"Invalid content block name: {block_name}")
        return self._get_project_path(project_id) / block_name

    def _get_project_metadata_path(self, project_id: str) -> Path:
        """Path to the project's metadata file."""
        return self._get_project_path(project_id) / "project_meta.json"

    def _get_chapter_metadata_path(self, project_id: str, chapter_id: str) -> Path:
         """Path to the chapter's metadata file (contains scene info)."""
         return self._get_chapter_path(project_id, chapter_id) / "chapter_meta.json"

    # --- ADDED: Chat History Path Helper ---
    def _get_chat_history_path(self, project_id: str) -> Path:
        """Path to the project's chat history file."""
        return self._get_project_path(project_id) / "chat_history.json"
    # --- END ADDED ---


    # --- Core File Operations ---
    # ... (existing methods unchanged) ...
    def path_exists(self, path: Path) -> bool:
        """Checks if a path exists."""
        return path.exists()

    def create_directory(self, path: Path):
        """Creates a directory, including parent directories."""
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Error creating directory {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not create directory structure for {path.name}")

    def read_text_file(self, path: Path) -> str:
        """Reads content from a text file."""
        if not self.path_exists(path):
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path.name} not found")
        try:
            return path.read_text(encoding='utf-8')
        except IOError as e:
            logger.error(f"Error reading file {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not read {path.name}")

    def write_text_file(self, path: Path, content: str, trigger_index: bool = False):
        """
        Writes content to a text file, creating parent dirs if needed.
        Optionally triggers indexing if trigger_index is True and it's a markdown file.
        """
        self.create_directory(path.parent)
        try:
            path.write_text(content, encoding='utf-8')
            logger.debug(f"Wrote text file: {path}")

            # --- Trigger Indexing Conditionally ---
            if trigger_index and path.suffix.lower() == '.md' and BASE_PROJECT_DIR.resolve() in path.resolve().parents:
                 # ---- Local Import ----
                 from app.rag.index_manager import index_manager
                 # ---------------------
                 try:
                     logger.info(f"Content updated for {path.name}, triggering indexing...")
                     # Call index_file asynchronously if it becomes async, otherwise call directly
                     # await index_manager.index_file(path) # If index_file is async
                     index_manager.index_file(path) # If index_file is sync
                 except Exception as e:
                     # Log error but don't necessarily fail the write operation
                     logger.error(f"ERROR: Failed to trigger indexing for {path.name}: {e}", exc_info=True)

        except IOError as e:
            logger.error(f"Error writing file {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not write to {path.name}")

    def read_json_file(self, path: Path) -> dict:
        """Reads content from a JSON file."""
        content = self.read_text_file(path) # Handles 404
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {path}: {e}")
            logger.warning(f"Returning empty dict for potentially corrupt JSON file: {path}")
            return {}

    def write_json_file(self, path: Path, data: dict):
        """Writes data to a JSON file. Does NOT trigger indexing."""
        try:
            content = json.dumps(data, indent=4)
            # Use write_text_file WITHOUT triggering index for JSON
            self.write_text_file(path, content, trigger_index=False)
            logger.debug(f"Successfully wrote JSON file: {path}")
        except TypeError as e:
            logger.error(f"Error encoding JSON for {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not format data for {path.name}")

    def delete_file(self, path: Path):
        """Deletes a file and triggers index deletion if applicable."""
        should_delete_from_index = path.suffix.lower() == '.md' and BASE_PROJECT_DIR.resolve() in path.resolve().parents

        if should_delete_from_index:
             # ---- Local Import ----
             from app.rag.index_manager import index_manager
             # ---------------------
             try:
                 logger.info(f"Attempting deletion from index before deleting file: {path}")
                 # await index_manager.delete_doc(path) # If delete_doc is async
                 index_manager.delete_doc(path) # If delete_doc is sync
             except Exception as e:
                 logger.warning(f"Error deleting document {path.name} from index during file delete: {e}")

        if not self.path_exists(path):
             if should_delete_from_index:
                 logger.info(f"File {path.name} not found for deletion (might have been deleted after index removal attempt).")
                 return
             else:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{path.name} not found")

        if not path.is_file():
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{path.name} is not a file")
        try:
            path.unlink()
            logger.info(f"Successfully deleted file: {path}")
        except OSError as e:
            logger.error(f"Error deleting file {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete {path.name}")

    def delete_directory(self, path: Path):
        """Deletes a directory and its contents recursively, including index cleanup."""
        if self.path_exists(path) and path.is_dir():
            logger.info(f"Attempting index deletion for all .md files within directory: {path}")
             # ---- Local Import ----
            from app.rag.index_manager import index_manager
             # ---------------------
            markdown_files = list(path.rglob('*.md'))
            for md_file in markdown_files:
                if BASE_PROJECT_DIR.resolve() in md_file.resolve().parents:
                    try:
                        logger.info(f"Attempting deletion from index for: {md_file}")
                         # await index_manager.delete_doc(md_file) # If delete_doc is async
                        index_manager.delete_doc(md_file) # If delete_doc is sync
                    except Exception as e:
                        logger.warning(f"Error deleting document {md_file.name} from index during directory delete: {e}")

        if not self.path_exists(path):
             logger.info(f"Directory {path.name} not found for deletion (might have been deleted after index removal attempt).")
             return

        if not path.is_dir():
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"{path.name} is not a directory")
        try:
            shutil.rmtree(path)
            logger.info(f"Successfully deleted directory: {path}")
        except OSError as e:
            logger.error(f"Error deleting directory {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not delete {path.name}")

    def list_subdirectories(self, path: Path) -> list[str]:
        """Lists names of immediate subdirectories."""
        if not self.path_exists(path) or not path.is_dir(): return []
        try: return [d.name for d in path.iterdir() if d.is_dir()]
        except OSError as e: logger.error(f"Error listing directories in {path}: {e}"); return []

    def list_markdown_files(self, path: Path) -> list[str]:
        """Lists names of markdown files (without extension) in a directory."""
        if not self.path_exists(path) or not path.is_dir(): return []
        try: return [f.stem for f in path.iterdir() if f.is_file() and f.suffix.lower() == '.md']
        except OSError as e: logger.error(f"Error listing markdown files in {path}: {e}"); return []


    # --- Specific Structure Creators ---
    def setup_project_structure(self, project_id: str):
        """Creates the basic directory structure for a new project."""
        project_path = self._get_project_path(project_id)
        self.create_directory(project_path)
        self.create_directory(self._get_chapters_dir(project_id))
        self.create_directory(self._get_characters_dir(project_id))
        # Write initial files - use trigger_index=True for content blocks
        self.write_text_file(self._get_content_block_path(project_id, "plan.md"), "", trigger_index=True)
        self.write_text_file(self._get_content_block_path(project_id, "synopsis.md"), "", trigger_index=True)
        self.write_text_file(self._get_content_block_path(project_id, "world.md"), "", trigger_index=True)
        # Write metadata (JSON files don't get indexed)
        self.write_project_metadata(project_id, {"project_name": "", "chapters": {}, "characters": {}})


    def setup_chapter_structure(self, project_id: str, chapter_id: str):
         """Creates the basic directory structure for a new chapter."""
         chapter_path = self._get_chapter_path(project_id, chapter_id)
         self.create_directory(chapter_path)
         self.write_chapter_metadata(project_id, chapter_id, {"scenes": {}}) # JSON, no index trigger

    # --- Methods for Content Blocks with Indexing ---
    def write_content_block_file(self, project_id: str, block_name: str, content: str):
        """Writes content block file AND triggers indexing."""
        path = self._get_content_block_path(project_id, block_name)
        # Pass trigger_index=True to the core write method
        self.write_text_file(path, content, trigger_index=True)

    def read_content_block_file(self, project_id: str, block_name: str) -> str:
         """Reads content block file."""
         path = self._get_content_block_path(project_id, block_name)
         return self.read_text_file(path)

    # --- Centralized Metadata I/O Methods ---
    def read_project_metadata(self, project_id: str) -> dict:
        """Reads the project_meta.json file for a given project."""
        metadata_path = self._get_project_metadata_path(project_id)
        try:
            # Use the core read_json_file which handles 404 and decode errors
            return self.read_json_file(metadata_path)
        except HTTPException as e:
            # If meta file not found, it might be an inconsistency or first access
            if e.status_code == 404:
                 logger.warning(f"Project metadata file not found for project {project_id}. Returning default structure.")
                 # Return default structure to allow potential recovery/creation
                 return {"project_name": f"Project {project_id}", "chapters": {}, "characters": {}}
            logger.error(f"Unexpected error reading project metadata for {project_id}: {e.detail}")
            raise e # Re-raise other file read errors (like 500)

    def write_project_metadata(self, project_id: str, data: dict):
        """Writes data to the project_meta.json file."""
        metadata_path = self._get_project_metadata_path(project_id)
        try:
            # Use the core write_json_file
            self.write_json_file(metadata_path, data)
            logger.debug(f"Successfully wrote project metadata for {project_id}")
        except HTTPException as e:
            # Log and re-raise errors from write_json_file
            logger.error(f"Failed to write project metadata for {project_id}: {e.detail}")
            raise e

    def read_chapter_metadata(self, project_id: str, chapter_id: str) -> dict:
        """Reads the chapter_meta.json file for a given chapter."""
        metadata_path = self._get_chapter_metadata_path(project_id, chapter_id)
        try:
            return self.read_json_file(metadata_path)
        except HTTPException as e:
            if e.status_code == 404:
                 logger.warning(f"Chapter metadata file not found for chapter {chapter_id} in project {project_id}. Returning default structure.")
                 return {"scenes": {}} # Default structure
            logger.error(f"Unexpected error reading chapter metadata for {chapter_id} in {project_id}: {e.detail}")
            raise e

    def write_chapter_metadata(self, project_id: str, chapter_id: str, data: dict):
        """Writes data to the chapter_meta.json file."""
        metadata_path = self._get_chapter_metadata_path(project_id, chapter_id)
        try:
            self.write_json_file(metadata_path, data)
            logger.debug(f"Successfully wrote chapter metadata for {chapter_id} in {project_id}")
        except HTTPException as e:
            logger.error(f"Failed to write chapter metadata for {chapter_id} in {project_id}: {e.detail}")
            raise e

    # --- ADDED: Chat History Methods ---
    def read_chat_history(self, project_id: str) -> List[dict]:
        """Reads the chat_history.json file for a given project."""
        history_path = self._get_chat_history_path(project_id)
        try:
            # Use read_json_file which handles 404 and decode errors
            data = self.read_json_file(history_path)
            # Ensure the top-level structure is a list (or default to empty list)
            if isinstance(data, list):
                return data
            elif isinstance(data, dict) and 'history' in data and isinstance(data['history'], list):
                 # Handle potential old format if we saved {'history': [...]} previously
                 logger.warning(f"Reading chat history from potentially old format for project {project_id}")
                 return data['history']
            else:
                 logger.warning(f"Chat history file for project {project_id} does not contain a list. Returning empty history.")
                 return []
        except HTTPException as e:
            if e.status_code == 404:
                 logger.info(f"Chat history file not found for project {project_id}. Returning empty list.")
                 return [] # Return empty list if file doesn't exist
            logger.error(f"Unexpected error reading chat history for {project_id}: {e.detail}")
            raise e # Re-raise other errors

    def write_chat_history(self, project_id: str, history_data: List[dict]):
        """Writes data to the chat_history.json file."""
        history_path = self._get_chat_history_path(project_id)
        try:
            # Directly write the list as the root JSON object
            self.write_json_file(history_path, history_data)
            logger.debug(f"Successfully wrote chat history for {project_id}")
        except HTTPException as e:
            logger.error(f"Failed to write chat history for {project_id}: {e.detail}")
            raise e
    # --- END ADDED ---


# Create a single instance
file_service = FileService()