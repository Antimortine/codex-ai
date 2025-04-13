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
import os # Import os for path.getmtime
from pathlib import Path
from fastapi import HTTPException, status
from app.core.config import BASE_PROJECT_DIR
import logging
from typing import List, Dict, Optional # Import Dict, Optional

logger = logging.getLogger(__name__)

# Define files/dirs to exclude when checking for last content modification
# Adjust as needed, similar to .gitignore logic but simpler for this purpose
EXCLUDED_FOR_MTIME = {'.git', 'venv', '.venv', 'node_modules', '__pycache__', 'chroma_db', '.chroma'}

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

    # --- MODIFIED: Added Notes Path Helpers ---
    def _get_notes_dir(self, project_id: str) -> Path:
        """Returns the path to the notes directory within a project."""
        return self._get_project_path(project_id) / "notes"

    def _get_note_path(self, project_id: str, note_id: str) -> Path:
        """Returns the path to a specific note file."""
        # Assuming note_id includes '.md' if needed, or adjust as necessary
        # Current design uses UUID without extension, so add it here.
        return self._get_notes_dir(project_id) / f"{note_id}.md"
    # --- END MODIFIED ---

    def _get_content_block_path(self, project_id: str, block_name: str) -> Path:
        """Returns the path to a project-level content block file (plan, synopsis, world)."""
        allowed_blocks = {"plan.md", "synopsis.md", "world.md"}
        if block_name not in allowed_blocks:
            raise ValueError(f"Invalid project-level content block name: {block_name}")
        return self._get_project_path(project_id) / block_name

    def _get_chapter_plan_path(self, project_id: str, chapter_id: str) -> Path:
        """Returns the path to the plan.md file within a specific chapter directory."""
        return self._get_chapter_path(project_id, chapter_id) / "plan.md"

    def _get_chapter_synopsis_path(self, project_id: str, chapter_id: str) -> Path:
        """Returns the path to the synopsis.md file within a specific chapter directory."""
        return self._get_chapter_path(project_id, chapter_id) / "synopsis.md"

    def _get_project_metadata_path(self, project_id: str) -> Path:
        """Path to the project's metadata file."""
        return self._get_project_path(project_id) / "project_meta.json"

    def _get_chapter_metadata_path(self, project_id: str, chapter_id: str) -> Path:
         """Path to the chapter's metadata file (contains scene info)."""
         return self._get_chapter_path(project_id, chapter_id) / "chapter_meta.json"

    def _get_chat_history_path(self, project_id: str) -> Path:
        """Path to the project's chat history file."""
        return self._get_project_path(project_id) / "chat_history.json"


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

            if trigger_index and path.suffix.lower() == '.md' and BASE_PROJECT_DIR.resolve() in path.resolve().parents:
                 from app.rag.index_manager import index_manager
                 if index_manager:
                     try:
                         logger.info(f"Content updated for {path.name}, triggering indexing...")
                         # Pass preloaded metadata if available from the calling service (e.g., NoteService.update)
                         # For now, we don't have easy access to it here, so IndexManager will read it.
                         index_manager.index_file(path)
                     except Exception as e:
                         logger.error(f"ERROR: Failed to trigger indexing for {path.name}: {e}", exc_info=True)
                 else:
                     logger.error("IndexManager not available, skipping indexing trigger.")

        except IOError as e:
            logger.error(f"Error writing file {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not write to {path.name}")

    def read_json_file(self, path: Path) -> dict:
        """Reads content from a JSON file."""
        content = self.read_text_file(path) # Handles 404
        try:
            data = json.loads(content)
            if not isinstance(data, dict): # Ensure it's a dictionary
                logger.warning(f"JSON file {path} did not contain a dictionary. Returning empty dict.")
                return {}
            return data
        except json.JSONDecodeError as e:
            logger.error(f"Error decoding JSON from {path}: {e}")
            logger.warning(f"Returning empty dict for potentially corrupt JSON file: {path}")
            return {}

    def write_json_file(self, path: Path, data: dict):
        """Writes data to a JSON file. Does NOT trigger indexing."""
        try:
            content = json.dumps(data, indent=4)
            self.write_text_file(path, content, trigger_index=False)
            logger.debug(f"Successfully wrote JSON file: {path}")
        except TypeError as e:
            logger.error(f"Error encoding JSON for {path}: {e}")
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Could not format data for {path.name}")

    def delete_file(self, path: Path):
        """Deletes a file and triggers index deletion if applicable."""
        should_delete_from_index = path.suffix.lower() == '.md' and BASE_PROJECT_DIR.resolve() in path.resolve().parents

        if should_delete_from_index:
             from app.rag.index_manager import index_manager
             if index_manager:
                 try:
                     logger.info(f"Attempting deletion from index before deleting file: {path}")
                     index_manager.delete_doc(path)
                 except Exception as e:
                     logger.warning(f"Error deleting document {path.name} from index during file delete: {e}")
             else:
                 logger.error("IndexManager not available, skipping index deletion trigger.")

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
            from app.rag.index_manager import index_manager
            if index_manager:
                markdown_files = list(path.rglob('*.md'))
                for md_file in markdown_files:
                    if BASE_PROJECT_DIR.resolve() in md_file.resolve().parents:
                        try:
                            logger.info(f"Attempting deletion from index for: {md_file}")
                            index_manager.delete_doc(md_file)
                        except Exception as e:
                            logger.warning(f"Error deleting document {md_file.name} from index during directory delete: {e}")
            else:
                logger.error("IndexManager not available, skipping index deletion during directory delete.")

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

    def get_all_markdown_paths(self, project_id: str) -> List[Path]:
        """Recursively finds all .md files within a project directory."""
        project_path = self._get_project_path(project_id)
        if not self.path_exists(project_path) or not project_path.is_dir():
            logger.warning(f"Project path not found or not a directory: {project_path}")
            return []
        try:
            md_paths = list(project_path.rglob('*.md'))
            logger.info(f"Found {len(md_paths)} markdown files in project {project_id}")
            return md_paths
        except Exception as e:
            logger.error(f"Error finding markdown files in {project_path}: {e}", exc_info=True)
            return []

    def get_project_last_content_modification(self, project_path: Path) -> Optional[float]:
        """
        Recursively finds the last modification time (Unix timestamp) of any relevant
        file (.md, .json) within the project directory, excluding specified folders.
        Returns the timestamp of the most recently modified relevant file,
        or the directory's own mtime if no relevant files are found,
        or None if the directory doesn't exist or an error occurs.
        """
        if not self.path_exists(project_path) or not project_path.is_dir():
            logger.warning(f"Project path {project_path} not found or not a directory for mtime check.")
            return None

        latest_mtime = 0.0
        try:
            # Initialize with the directory's own mtime as a baseline
            latest_mtime = project_path.stat().st_mtime

            for item in project_path.rglob('*'):
                # Check if the item's path parts contain any excluded directory names
                relative_parts = item.relative_to(project_path).parts
                if any(part in EXCLUDED_FOR_MTIME for part in relative_parts):
                    continue # Skip this item and its potential children

                if item.is_file():
                    # Consider relevant file types (e.g., markdown and metadata)
                    if item.suffix.lower() in ['.md', '.json']:
                        try:
                            item_mtime = item.stat().st_mtime
                            latest_mtime = max(latest_mtime, item_mtime)
                        except OSError as e:
                            logger.warning(f"Could not stat file {item} during mtime check: {e}")
            return latest_mtime
        except OSError as e:
            logger.error(f"Error getting last modification time for project {project_path}: {e}")
            return None # Return None on error
        except Exception as e:
             logger.error(f"Unexpected error getting last modification time for project {project_path}: {e}", exc_info=True)
             return None

    # --- MODIFIED: Added get_file_mtime ---
    def get_file_mtime(self, path: Path) -> Optional[float]:
        """Gets the last modification time (Unix timestamp) of a file."""
        if not self.path_exists(path) or not path.is_file():
            logger.warning(f"Cannot get mtime: Path {path} not found or not a file.")
            return None
        try:
            return path.stat().st_mtime
        except OSError as e:
            logger.error(f"Error getting mtime for file {path}: {e}")
            return None
    # --- END MODIFIED ---


    # --- Specific Structure Creators ---
    # --- MODIFIED: Added Notes setup ---
    def setup_project_structure(self, project_id: str):
        """Creates the basic directory structure for a new project."""
        project_path = self._get_project_path(project_id)
        self.create_directory(project_path)
        self.create_directory(self._get_chapters_dir(project_id))
        self.create_directory(self._get_characters_dir(project_id))
        self.create_directory(self._get_notes_dir(project_id)) # Create notes dir
        self.write_text_file(self._get_content_block_path(project_id, "plan.md"), "", trigger_index=True)
        self.write_text_file(self._get_content_block_path(project_id, "synopsis.md"), "", trigger_index=True)
        self.write_text_file(self._get_content_block_path(project_id, "world.md"), "", trigger_index=True)
        # Initialize notes key in metadata
        self.write_project_metadata(project_id, {
            "project_name": "",
            "chapters": {},
            "characters": {},
            "chat_sessions": {},
            "notes": {} # Add notes key
        })
        self.write_chat_history_file(project_id, {}) # Write empty dict initially
    # --- END MODIFIED ---


    def setup_chapter_structure(self, project_id: str, chapter_id: str):
         """Creates the basic directory structure for a new chapter."""
         chapter_path = self._get_chapter_path(project_id, chapter_id)
         self.create_directory(chapter_path)
         self.write_chapter_metadata(project_id, chapter_id, {"scenes": {}})
         # Note: We don't create chapter plan/synopsis by default

    # --- Methods for Content Blocks with Indexing ---
    def write_content_block_file(self, project_id: str, block_name: str, content: str):
        """Writes project-level content block file AND triggers indexing."""
        path = self._get_content_block_path(project_id, block_name)
        self.write_text_file(path, content, trigger_index=True)

    def read_content_block_file(self, project_id: str, block_name: str) -> str:
         """Reads project-level content block file."""
         path = self._get_content_block_path(project_id, block_name)
         return self.read_text_file(path)

    def read_chapter_plan_file(self, project_id: str, chapter_id: str) -> Optional[str]:
        """Reads chapter-level plan.md file, returning None if not found."""
        path = self._get_chapter_plan_path(project_id, chapter_id)
        try:
            return self.read_text_file(path)
        except HTTPException as e:
            if e.status_code == 404:
                logger.debug(f"Chapter plan file not found: {path}")
                return None
            logger.error(f"Error reading chapter plan file {path}: {e.detail}")
            raise e # Re-raise other errors

    def read_chapter_synopsis_file(self, project_id: str, chapter_id: str) -> Optional[str]:
        """Reads chapter-level synopsis.md file, returning None if not found."""
        path = self._get_chapter_synopsis_path(project_id, chapter_id)
        try:
            return self.read_text_file(path)
        except HTTPException as e:
            if e.status_code == 404:
                logger.debug(f"Chapter synopsis file not found: {path}")
                return None
            logger.error(f"Error reading chapter synopsis file {path}: {e.detail}")
            raise e # Re-raise other errors

    # --- ADDED: Chapter-Level Plan/Synopsis Write Methods ---
    def write_chapter_plan_file(self, project_id: str, chapter_id: str, content: str):
        """Writes chapter-level plan.md file AND triggers indexing."""
        path = self._get_chapter_plan_path(project_id, chapter_id)
        # Ensure chapter directory exists (write_text_file handles this)
        self.write_text_file(path, content, trigger_index=True)
        logger.info(f"Wrote and triggered index for chapter plan: {path}")

    def write_chapter_synopsis_file(self, project_id: str, chapter_id: str, content: str):
        """Writes chapter-level synopsis.md file AND triggers indexing."""
        path = self._get_chapter_synopsis_path(project_id, chapter_id)
        # Ensure chapter directory exists (write_text_file handles this)
        self.write_text_file(path, content, trigger_index=True)
        logger.info(f"Wrote and triggered index for chapter synopsis: {path}")
    # --- END ADDED ---

    # --- Centralized Metadata I/O Methods ---
    # --- MODIFIED: Added Notes key default ---
    def read_project_metadata(self, project_id: str) -> dict:
        """Reads the project_meta.json file for a given project."""
        metadata_path = self._get_project_metadata_path(project_id)
        try:
            data = self.read_json_file(metadata_path)
            # Ensure default keys exist
            if 'chat_sessions' not in data: data['chat_sessions'] = {}
            if 'notes' not in data: data['notes'] = {} # Add notes default
            if 'chapters' not in data: data['chapters'] = {}
            if 'characters' not in data: data['characters'] = {}
            return data
        except HTTPException as e:
            if e.status_code == 404:
                 logger.warning(f"Project metadata file not found for project {project_id}. Returning default structure.")
                 # Return full default structure including notes
                 return {"project_name": f"Project {project_id}", "chapters": {}, "characters": {}, "chat_sessions": {}, "notes": {}}
            logger.error(f"Unexpected error reading project metadata for {project_id}: {e.detail}")
            raise e
    # --- END MODIFIED ---

    # --- MODIFIED: Added Notes key default ---
    def write_project_metadata(self, project_id: str, data: dict):
        """Writes data to the project_meta.json file."""
        metadata_path = self._get_project_metadata_path(project_id)
        try:
            # Ensure default keys exist before writing
            if 'chat_sessions' not in data: data['chat_sessions'] = {}
            if 'notes' not in data: data['notes'] = {} # Add notes default
            if 'chapters' not in data: data['chapters'] = {}
            if 'characters' not in data: data['characters'] = {}
            self.write_json_file(metadata_path, data)
            logger.debug(f"Successfully wrote project metadata for {project_id}")
        except HTTPException as e:
            logger.error(f"Failed to write project metadata for {project_id}: {e.detail}")
            raise e
    # --- END MODIFIED ---

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

    # --- Chat History Methods (REVISED) ---
    def read_chat_history_file(self, project_id: str) -> Dict[str, List[dict]]:
        """Reads the entire chat_history.json file (all sessions)."""
        history_path = self._get_chat_history_path(project_id)
        try:
            data = self.read_json_file(history_path)
            # Ensure the top-level structure is a dict
            if isinstance(data, dict):
                # Basic validation: ensure values are lists (can add more checks)
                validated_data = {}
                for session_id, history_list in data.items():
                    if isinstance(history_list, list):
                        validated_data[session_id] = history_list
                    else:
                        logger.warning(f"Invalid history format for session {session_id} in project {project_id}. Skipping.")
                return validated_data
            else:
                 logger.warning(f"Chat history file for project {project_id} does not contain a dictionary. Returning empty history.")
                 return {}
        except HTTPException as e:
            if e.status_code == 404:
                 logger.info(f"Chat history file not found for project {project_id}. Returning empty dict.")
                 return {} # Return empty dict if file doesn't exist
            logger.error(f"Unexpected error reading chat history file for {project_id}: {e.detail}")
            raise e # Re-raise other errors

    def write_chat_history_file(self, project_id: str, all_sessions_data: Dict[str, List[dict]]):
        """Writes the entire chat history data (all sessions) to chat_history.json."""
        history_path = self._get_chat_history_path(project_id)
        try:
            # Directly write the dictionary as the root JSON object
            self.write_json_file(history_path, all_sessions_data)
            logger.debug(f"Successfully wrote chat history file for {project_id}")
        except HTTPException as e:
            logger.error(f"Failed to write chat history file for {project_id}: {e.detail}")
            raise e

    def read_chat_session_history(self, project_id: str, session_id: str) -> List[dict]:
        """Reads the history list for a specific chat session."""
        all_sessions = self.read_chat_history_file(project_id)
        return all_sessions.get(session_id, []) # Return empty list if session_id not found

    def write_chat_session_history(self, project_id: str, session_id: str, history_data: List[dict]):
        """Writes the history list for a specific chat session."""
        all_sessions = self.read_chat_history_file(project_id)
        all_sessions[session_id] = history_data # Update or add the session
        self.write_chat_history_file(project_id, all_sessions)

    def delete_chat_session_history(self, project_id: str, session_id: str):
        """Deletes the history list for a specific chat session."""
        all_sessions = self.read_chat_history_file(project_id)
        if session_id in all_sessions:
            del all_sessions[session_id]
            self.write_chat_history_file(project_id, all_sessions)
            logger.info(f"Deleted chat history for session {session_id} in project {project_id}")
        else:
            logger.warning(f"Attempted to delete non-existent chat session history: {session_id} in project {project_id}")

    # --- Chat Session Metadata Methods ---
    def get_chat_sessions_metadata(self, project_id: str) -> Dict[str, Dict[str, str]]:
        """Reads the chat session metadata (ID -> {name}) from project_meta.json."""
        project_metadata = self.read_project_metadata(project_id)
        # Ensure the key exists and is a dictionary
        sessions_meta = project_metadata.get('chat_sessions', {})
        if not isinstance(sessions_meta, dict):
            logger.warning(f"chat_sessions in project {project_id} metadata is not a dict. Returning empty.")
            return {}
        return sessions_meta

    def add_chat_session_metadata(self, project_id: str, session_id: str, name: str):
        """Adds metadata for a new chat session to project_meta.json."""
        project_metadata = self.read_project_metadata(project_id)
        # Ensure chat_sessions key exists and is a dict
        if 'chat_sessions' not in project_metadata or not isinstance(project_metadata['chat_sessions'], dict):
            project_metadata['chat_sessions'] = {}
        if session_id in project_metadata['chat_sessions']:
            logger.warning(f"Chat session metadata for {session_id} already exists in project {project_id}. Overwriting.")
        project_metadata['chat_sessions'][session_id] = {"name": name}
        self.write_project_metadata(project_id, project_metadata)

    def update_chat_session_metadata(self, project_id: str, session_id: str, name: str):
        """Updates the name of an existing chat session in project_meta.json."""
        project_metadata = self.read_project_metadata(project_id)
        if 'chat_sessions' in project_metadata and session_id in project_metadata['chat_sessions']:
            project_metadata['chat_sessions'][session_id]['name'] = name
            self.write_project_metadata(project_id, project_metadata)
        else:
            logger.error(f"Attempted to update non-existent chat session metadata: {session_id} in project {project_id}")
            # Optionally raise an error here? For now, just log.
            # raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat session {session_id} metadata not found.")

    def delete_chat_session_metadata(self, project_id: str, session_id: str):
        """Deletes the metadata for a chat session from project_meta.json."""
        project_metadata = self.read_project_metadata(project_id)
        if 'chat_sessions' in project_metadata and session_id in project_metadata['chat_sessions']:
            del project_metadata['chat_sessions'][session_id]
            self.write_project_metadata(project_id, project_metadata)
            logger.info(f"Deleted chat session metadata for {session_id} in project {project_id}")
        else:
            logger.warning(f"Attempted to delete non-existent chat session metadata: {session_id} in project {project_id}")


# Create a single instance
file_service = FileService()