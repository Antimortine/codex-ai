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
from app.services.chapter_service import chapter_service
from app.models.common import generate_uuid
from app.rag.index_manager import index_manager
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

        # Create the scene markdown file (basic write)
        file_service.write_text_file(scene_path, scene_in.content)

        try:
            logger.info(f"Indexing new scene: {scene_path}")
            index_manager.index_file(scene_path)
        except Exception as e:
            logger.error(f"ERROR: Failed to index new scene {scene_id}: {e}")

        # Update chapter metadata using file_service
        chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
        if 'scenes' not in chapter_metadata: chapter_metadata['scenes'] = {}

        for existing_id, data in chapter_metadata['scenes'].items():
             if data.get('order') == scene_in.order:
                 # Consider rollback? For now, just raise.
                 logger.error(f"Scene order conflict: Order {scene_in.order} exists for scene '{data.get('title', existing_id)}'")
                 # Attempt to clean up the created file if order conflicts
                 try:
                      file_service.delete_file(scene_path) # This will also attempt index deletion
                 except Exception as cleanup_err:
                      logger.error(f"Failed to cleanup scene file {scene_path} after order conflict: {cleanup_err}")
                 raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Scene order {scene_in.order} already exists for scene '{data.get('title', existing_id)}'"
                 )

        chapter_metadata['scenes'][scene_id] = {
            "title": scene_in.title,
            "order": scene_in.order
        }
        file_service.write_chapter_metadata(project_id, chapter_id, chapter_metadata)

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
            order=scene_data.get("order", -1),
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
                 # This implicitly uses the updated get_by_id which uses file_service for meta
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
            file_service.write_chapter_metadata(project_id, chapter_id, chapter_metadata)

        content_updated = False
        if scene_in.content is not None and scene_in.content != existing_scene.content:
            scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
            file_service.write_text_file(scene_path, scene_in.content) # Basic write
            existing_scene.content = scene_in.content
            content_updated = True

            try:
                logger.info(f"Content updated for scene {scene_id}, re-indexing...")
                index_manager.index_file(scene_path)
            except Exception as e:
                logger.error(f"ERROR: Failed to re-index updated scene {scene_id}: {e}")

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
            chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
            if scene_id in chapter_metadata.get('scenes', {}):
                del chapter_metadata['scenes'][scene_id]
                file_service.write_chapter_metadata(project_id, chapter_id, chapter_metadata)
                logger.info(f"Scene {scene_id} removed from chapter metadata.")
            else:
                 logger.warning(f"Scene {scene_id} was in metadata initially but disappeared before final write.")
        else:
             logger.info(f"Scene {scene_id} was not in chapter metadata during delete.")


# Create a single instance
scene_service = SceneService()