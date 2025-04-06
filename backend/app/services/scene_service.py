# backend/app/services/scene_service.py
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

from fastapi import HTTPException, status
from app.models.scene import SceneCreate, SceneUpdate, SceneRead, SceneList
from app.services.file_service import file_service
from app.services.chapter_service import chapter_service # To check chapter existence
from app.models.common import generate_uuid
from app.rag.index_manager import index_manager

class SceneService:

    def _read_chapter_meta(self, project_id: str, chapter_id: str) -> dict:
        """Reads chapter metadata."""
        metadata_path = file_service._get_chapter_metadata_path(project_id, chapter_id)
        try:
            return file_service.read_json_file(metadata_path)
        except HTTPException as e:
             if e.status_code == 404:
                 print(f"Warning: Chapter metadata file not found for existing chapter {chapter_id}")
                 return {"scenes": {}} # Default structure
             raise e

    def _write_chapter_meta(self, project_id: str, chapter_id: str, metadata: dict):
        """Writes chapter metadata."""
        metadata_path = file_service._get_chapter_metadata_path(project_id, chapter_id)
        file_service.write_json_file(metadata_path, metadata)

    def create(self, project_id: str, chapter_id: str, scene_in: SceneCreate) -> SceneRead:
        """Creates a new scene within a chapter."""
        # Ensure chapter exists first (this also checks project)
        chapter_service.get_by_id(project_id, chapter_id)

        scene_id = generate_uuid()
        scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)

        if file_service.path_exists(scene_path):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scene ID collision")

        # Create the scene markdown file with initial content
        file_service.write_text_file(scene_path, scene_in.content)

        # --- Index the new scene ---
        try:
            print(f"Indexing new scene: {scene_path}")
            index_manager.index_file(scene_path)
        except Exception as e:
            # Log indexing error but continue, as the file and metadata are created
            print(f"ERROR: Failed to index new scene {scene_id}: {e}")
            # Consider how critical indexing is - should we raise an error or just warn?
            # For now, we warn and continue.

        # Update chapter metadata (AFTER file write and indexing attempt)
        chapter_metadata = self._read_chapter_meta(project_id, chapter_id)
        if 'scenes' not in chapter_metadata: chapter_metadata['scenes'] = {}

        # Check for order conflicts
        for existing_id, data in chapter_metadata['scenes'].items():
             if data.get('order') == scene_in.order:
                 # Rollback file creation and index deletion? Or just raise? Let's just raise for now.
                 # file_service.delete_file(scene_path) # Optional rollback
                 # index_manager.delete_doc(scene_path) # Optional rollback
                 raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Scene order {scene_in.order} already exists for scene '{data.get('title', existing_id)}'"
                 )

        chapter_metadata['scenes'][scene_id] = {
            "title": scene_in.title,
            "order": scene_in.order
        }
        self._write_chapter_meta(project_id, chapter_id, chapter_metadata)

        return SceneRead(
            id=scene_id,
            project_id=project_id,
            chapter_id=chapter_id,
            title=scene_in.title,
            order=scene_in.order,
            content=scene_in.content
        )

    def get_by_id(self, project_id: str, chapter_id: str, scene_id: str) -> SceneRead:
        """Gets scene details and content by ID."""
        # Ensure chapter exists
        chapter_service.get_by_id(project_id, chapter_id)

        # Read metadata first
        chapter_metadata = self._read_chapter_meta(project_id, chapter_id)
        scene_data = chapter_metadata.get('scenes', {}).get(scene_id)

        if not scene_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} not found in chapter {chapter_id}")

        # Read content from file
        scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
        try:
             content = file_service.read_text_file(scene_path)
        except HTTPException as e:
             if e.status_code == 404:
                 print(f"Warning: Scene metadata exists for {scene_id} but file is missing.")
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} data missing") from e
             raise e # Re-raise other errors

        return SceneRead(
            id=scene_id,
            project_id=project_id,
            chapter_id=chapter_id,
            title=scene_data.get("title", f"Scene {scene_id}"),
            order=scene_data.get("order", -1),
            content=content
        )

    def get_all_for_chapter(self, project_id: str, chapter_id: str) -> SceneList:
        """Lists all scenes for a specific chapter."""
        # Ensure chapter exists
        chapter_service.get_by_id(project_id, chapter_id)

        chapter_metadata = self._read_chapter_meta(project_id, chapter_id)
        scenes_meta = chapter_metadata.get('scenes', {})

        scenes = []
        # We need content, so we must read each file
        for scene_id, data in scenes_meta.items():
            try:
                 # Use get_by_id to read content and handle missing file errors
                 scene_data = self.get_by_id(project_id, chapter_id, scene_id)
                 scenes.append(scene_data)
            except HTTPException as e:
                 if e.status_code == 404:
                     print(f"Warning: Skipping scene {scene_id} in list view: data missing.")
                 else:
                     print(f"Warning: Error fetching scene {scene_id} for list view: {e.detail}")
                 continue # Skip scenes with errors

        # Sort scenes by order
        scenes.sort(key=lambda s: s.order)

        return SceneList(scenes=scenes)

    def update(self, project_id: str, chapter_id: str, scene_id: str, scene_in: SceneUpdate) -> SceneRead:
        """Updates scene details or content."""
        # Ensure scene exists (this reads current data including content)
        existing_scene = self.get_by_id(project_id, chapter_id, scene_id)

        chapter_metadata = self._read_chapter_meta(project_id, chapter_id)
        scene_data = chapter_metadata.get('scenes', {}).get(scene_id)

        if not scene_data:
             # This case should technically be caught by get_by_id, but check anyway
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene metadata inconsistency during update")

        meta_updated = False
        if scene_in.title is not None and scene_in.title != scene_data.get("title"):
            scene_data["title"] = scene_in.title
            existing_scene.title = scene_in.title # Update the object we will return
            meta_updated = True

        if scene_in.order is not None and scene_in.order != scene_data.get("order"):
             # Check for order conflicts
            for other_id, data in chapter_metadata.get('scenes', {}).items():
                if other_id != scene_id and data.get('order') == scene_in.order:
                     raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Scene order {scene_in.order} already exists for scene '{data.get('title', other_id)}'"
                     )
            scene_data["order"] = scene_in.order
            existing_scene.order = scene_in.order # Update the object we will return
            meta_updated = True

        if meta_updated:
            self._write_chapter_meta(project_id, chapter_id, chapter_metadata)

        # Update content if provided and different
        content_updated = False
        if scene_in.content is not None and scene_in.content != existing_scene.content:
            scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
            file_service.write_text_file(scene_path, scene_in.content)
            existing_scene.content = scene_in.content # Update returned object
            content_updated = True # Flag that content changed

            # --- Trigger Re-indexing ONLY if content changed ---
            try:
                print(f"Content updated for scene {scene_id}, re-indexing...")
                index_manager.index_file(scene_path) # Index the updated content
            except Exception as e:
                print(f"ERROR: Failed to re-index updated scene {scene_id}: {e}")
                # Decide on error handling - maybe raise a warning?

        return existing_scene

    def delete(self, project_id: str, chapter_id: str, scene_id: str):
        """Deletes a scene."""
        # Ensure scene exists (checks chapter too)
        # We need the path even if get_by_id fails later due to inconsistency
        scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
        scene_exists_in_meta = False
        try:
            # Check metadata first
            chapter_metadata = self._read_chapter_meta(project_id, chapter_id)
            if scene_id in chapter_metadata.get('scenes', {}):
                 scene_exists_in_meta = True
            else:
                 # If not in meta, maybe file still exists? Check file system.
                 if not file_service.path_exists(scene_path):
                      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found in metadata or filesystem")
                 else:
                      print(f"Warning: Scene {scene_id} found on filesystem but not in metadata.")
                      # Proceed to delete file and attempt index deletion anyway

        except HTTPException as e:
             if e.status_code == 404: # Chapter meta might be missing if chapter was deleted inconsistently
                  if not file_service.path_exists(scene_path):
                       raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found (chapter meta missing)") from e
                  else: # File exists, proceed with deletion
                       print(f"Warning: Chapter metadata missing for {chapter_id}, but scene file exists.")
             else:
                  raise e # Re-raise other errors


        # --- Trigger Deletion from Index FIRST ---
        # Attempt even if metadata was inconsistent, in case file exists
        try:
            print(f"Attempting deletion from index for scene: {scene_path}")
            index_manager.delete_doc(scene_path)
        except Exception as e:
            # Log error but proceed with file/meta deletion
            print(f"Warning: Error deleting scene {scene_id} from index: {e}")

        # Delete the markdown file if it exists
        if file_service.path_exists(scene_path):
            try:
                 file_service.delete_file(scene_path)
            except HTTPException as e:
                 # Log if file deletion fails, but proceed to remove meta
                 print(f"Warning: Scene file {scene_path.name} found but failed to delete: {e.detail}")
                 # Re-raise only if it's not a 404 (already deleted?)
                 if e.status_code != 404:
                      raise e
        else:
             print(f"Info: Scene file {scene_path.name} was already deleted.")


        # Update chapter metadata if the scene was listed there
        if scene_exists_in_meta:
            # Re-read metadata in case it changed? Unlikely but safer.
            chapter_metadata = self._read_chapter_meta(project_id, chapter_id)
            if scene_id in chapter_metadata.get('scenes', {}):
                del chapter_metadata['scenes'][scene_id]
                self._write_chapter_meta(project_id, chapter_id, chapter_metadata)
            else:
                 # This shouldn't happen if scene_exists_in_meta was true, indicates race condition or bug
                 print(f"Warning: Scene {scene_id} was in metadata initially but disappeared before final write.")
        else:
             print(f"Info: Scene {scene_id} was not in chapter metadata during delete.")


# Create a single instance
scene_service = SceneService()