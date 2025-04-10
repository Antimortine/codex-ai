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
from app.services.chapter_service import chapter_service
from app.models.common import generate_uuid
# No direct index_manager import needed here anymore
import logging

logger = logging.getLogger(__name__)

class SceneService:

    # --- REMOVED internal _read_chapter_meta and _write_chapter_meta ---

    def create(self, project_id: str, chapter_id: str, scene_in: SceneCreate) -> SceneRead:
        """Creates a new scene within a chapter."""
        chapter_service.get_by_id(project_id, chapter_id) # Ensure chapter exists

        scene_id = generate_uuid()
        scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)

        if file_service.path_exists(scene_path):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Scene ID collision")

        # --- MODIFICATION START: Handle optional order ---
        chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
        if 'scenes' not in chapter_metadata: chapter_metadata['scenes'] = {}
        existing_scenes = chapter_metadata['scenes']

        final_order: int
        if scene_in.order is None:
            # Calculate next available order
            max_order = 0
            if existing_scenes:
                orders = [data.get('order', 0) for data in existing_scenes.values() if isinstance(data.get('order'), int)]
                if orders:
                    max_order = max(orders)
            final_order = max_order + 1
            logger.info(f"Scene order not provided. Calculated next available order: {final_order}")
        else:
            # Check for conflicts if order *was* provided
            final_order = scene_in.order
            for existing_id, data in existing_scenes.items():
                 if data.get('order') == final_order:
                     raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Scene order {final_order} already exists for scene '{data.get('title', existing_id)}'"
                     )
        # --- MODIFICATION END ---

        # Create the scene markdown file and trigger indexing
        # Pass trigger_index=True
        file_service.write_text_file(scene_path, scene_in.content, trigger_index=True)

        # --- MODIFICATION START: Use final_order and check for cleanup on error ---
        try:
            # Update chapter metadata using file_service
            chapter_metadata['scenes'][scene_id] = {
                "title": scene_in.title,
                "order": final_order # Use the calculated or validated order
            }
            file_service.write_chapter_metadata(project_id, chapter_id, chapter_metadata) # JSON, no index trigger
        except Exception as meta_write_err:
             # Attempt to cleanup the created file if metadata write fails
             logger.error(f"Failed to write chapter metadata for new scene {scene_id}: {meta_write_err}", exc_info=True)
             try:
                  file_service.delete_file(scene_path) # This will also attempt index deletion
             except Exception as cleanup_err:
                  logger.error(f"Failed to cleanup scene file {scene_path} after metadata write error: {cleanup_err}")
             # Re-raise the original error or a generic one
             raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to save scene metadata."
             ) from meta_write_err
        # --- MODIFICATION END ---

        return SceneRead(
            id=scene_id,
            project_id=project_id,
            chapter_id=chapter_id,
            title=scene_in.title,
            order=final_order, # Return the final order used
            content=scene_in.content
        )

    def get_by_id(self, project_id: str, chapter_id: str, scene_id: str) -> SceneRead:
        """Gets scene details and content by ID."""
        chapter_service.get_by_id(project_id, chapter_id) # Ensure chapter exists

        chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
        scene_data = chapter_metadata.get('scenes', {}).get(scene_id)

        if not scene_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} not found in chapter {chapter_id}")

        scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
        try:
             content = file_service.read_text_file(scene_path)
        except HTTPException as e:
             if e.status_code == 404:
                 logger.warning(f"Scene metadata exists for {scene_id} but file is missing.")
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Scene {scene_id} data missing") from e
             raise e

        return SceneRead(
            id=scene_id,
            project_id=project_id,
            chapter_id=chapter_id,
            title=scene_data.get("title", f"Scene {scene_id}"),
            order=scene_data.get("order", -1), # Default if missing, though should exist
            content=content
        )

    def get_all_for_chapter(self, project_id: str, chapter_id: str) -> SceneList:
        """Lists all scenes for a specific chapter."""
        chapter_service.get_by_id(project_id, chapter_id) # Ensure chapter exists

        chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
        scenes_meta = chapter_metadata.get('scenes', {})

        scenes = []
        for scene_id, data in scenes_meta.items():
            try:
                 # Use get_by_id to read content and handle missing file errors
                 scene_data = self.get_by_id(project_id, chapter_id, scene_id)
                 scenes.append(scene_data)
            except HTTPException as e:
                 if e.status_code == 404:
                     logger.warning(f"Skipping scene {scene_id} in list view: data missing.")
                 else:
                     logger.warning(f"Error fetching scene {scene_id} for list view: {e.detail}")
                 continue

        scenes.sort(key=lambda s: s.order)
        return SceneList(scenes=scenes)

    def update(self, project_id: str, chapter_id: str, scene_id: str, scene_in: SceneUpdate) -> SceneRead:
        """Updates scene details or content."""
        existing_scene = self.get_by_id(project_id, chapter_id, scene_id) # Reads current data

        chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
        scene_data = chapter_metadata.get('scenes', {}).get(scene_id)

        if not scene_data:
             logger.error(f"Scene metadata inconsistency during update for {scene_id}")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene metadata inconsistency during update")

        meta_updated = False
        if scene_in.title is not None and scene_in.title != scene_data.get("title"):
            scene_data["title"] = scene_in.title
            existing_scene.title = scene_in.title
            meta_updated = True

        if scene_in.order is not None and scene_in.order != scene_data.get("order"):
            for other_id, data in chapter_metadata.get('scenes', {}).items():
                if other_id != scene_id and data.get('order') == scene_in.order:
                     raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Scene order {scene_in.order} already exists for scene '{data.get('title', other_id)}'"
                     )
            scene_data["order"] = scene_in.order
            existing_scene.order = scene_in.order
            meta_updated = True

        if meta_updated:
            file_service.write_chapter_metadata(project_id, chapter_id, chapter_metadata) # JSON, no index trigger

        content_updated = False
        if scene_in.content is not None and scene_in.content != existing_scene.content:
            scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
            # Write MD file and trigger indexing
            # Pass trigger_index=True
            file_service.write_text_file(scene_path, scene_in.content, trigger_index=True)
            existing_scene.content = scene_in.content
            content_updated = True
            # No need for separate index call here anymore

        return existing_scene

    def delete(self, project_id: str, chapter_id: str, scene_id: str):
        """Deletes a scene."""
        scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
        scene_exists_in_meta = False
        try:
            chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
            if scene_id in chapter_metadata.get('scenes', {}):
                 scene_exists_in_meta = True
            else:
                 if not file_service.path_exists(scene_path):
                      raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found in metadata or filesystem")
                 else:
                      logger.warning(f"Scene {scene_id} found on filesystem but not in metadata.")

        except HTTPException as e:
             if e.status_code == 404: # Chapter meta might be missing
                  if not file_service.path_exists(scene_path):
                       raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene not found (chapter meta missing)") from e
                  else:
                       logger.warning(f"Chapter metadata missing for {chapter_id}, but scene file exists.")
             else:
                  raise e

        # FileService delete_file handles index deletion now
        file_service.delete_file(scene_path)

        if scene_exists_in_meta:
            # Re-read metadata to avoid race conditions if possible, though unlikely here
            chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
            if scene_id in chapter_metadata.get('scenes', {}):
                del chapter_metadata['scenes'][scene_id]
                file_service.write_chapter_metadata(project_id, chapter_id, chapter_metadata) # JSON, no index
                logger.info(f"Scene {scene_id} removed from chapter metadata.")
            else:
                 logger.warning(f"Scene {scene_id} was in metadata initially but disappeared before final write.")
        else:
             logger.info(f"Scene {scene_id} was not in chapter metadata during delete.")


# Create a single instance
scene_service = SceneService()