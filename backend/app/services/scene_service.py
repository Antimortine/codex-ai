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

        # Update chapter metadata
        chapter_metadata = self._read_chapter_meta(project_id, chapter_id)
        if 'scenes' not in chapter_metadata: chapter_metadata['scenes'] = {}

        # Check for order conflicts
        for existing_id, data in chapter_metadata['scenes'].items():
             if data.get('order') == scene_in.order:
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
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Scene metadata inconsistency")

        meta_updated = False
        if scene_in.title is not None and scene_in.title != scene_data.get("title"):
            scene_data["title"] = scene_in.title
            existing_scene.title = scene_in.title
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
            existing_scene.order = scene_in.order
            meta_updated = True

        if meta_updated:
            self._write_chapter_meta(project_id, chapter_id, chapter_metadata)

        # Update content if provided
        if scene_in.content is not None and scene_in.content != existing_scene.content:
            scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
            file_service.write_text_file(scene_path, scene_in.content)
            existing_scene.content = scene_in.content # Update returned object

        return existing_scene

    def delete(self, project_id: str, chapter_id: str, scene_id: str):
        """Deletes a scene."""
        # Ensure scene exists (checks chapter too)
        self.get_by_id(project_id, chapter_id, scene_id)

        # Delete the markdown file
        scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id)
        try:
             file_service.delete_file(scene_path)
        except HTTPException as e:
             # Log if file was already missing, but proceed to remove meta
             if e.status_code == 404:
                 print(f"Warning: Scene file {scene_path.name} not found during delete, removing metadata anyway.")
             else:
                 raise e # Re-raise other delete errors

        # Update chapter metadata
        chapter_metadata = self._read_chapter_meta(project_id, chapter_id)
        if scene_id in chapter_metadata.get('scenes', {}):
            del chapter_metadata['scenes'][scene_id]
            self._write_chapter_meta(project_id, chapter_id, chapter_metadata)
        else:
            print(f"Warning: Scene {scene_id} was deleted but already missing from chapter metadata.")


# Create a single instance
scene_service = SceneService()