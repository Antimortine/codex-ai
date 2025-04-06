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
from app.models.chapter import ChapterCreate, ChapterUpdate, ChapterRead, ChapterList
from app.services.file_service import file_service # Import the instance
from app.services.project_service import project_service # To check project existence
from app.models.common import generate_uuid
# No need to import index_manager directly here, as file_service handles it

class ChapterService:

    def _read_project_meta(self, project_id: str) -> dict:
        """Reads project metadata, handling potential errors."""
        metadata_path = file_service._get_project_metadata_path(project_id)
        try:
            return file_service.read_json_file(metadata_path)
        except HTTPException as e:
            # If meta file not found but project dir exists, it's an inconsistency
            if e.status_code == 404:
                 print(f"Warning: Project metadata file not found for existing project {project_id}")
                 # Return default structure to allow potential recovery/creation
                 return {"project_name": f"Project {project_id}", "chapters": {}, "characters": {}}
            raise e # Re-raise other file read errors

    def _write_project_meta(self, project_id: str, metadata: dict):
        """Writes project metadata."""
        metadata_path = file_service._get_project_metadata_path(project_id)
        file_service.write_json_file(metadata_path, metadata)

    def create(self, project_id: str, chapter_in: ChapterCreate) -> ChapterRead:
        """Creates a new chapter within a project."""
        project_service.get_by_id(project_id) # Ensure project exists

        chapter_id = generate_uuid()
        chapter_path = file_service._get_chapter_path(project_id, chapter_id)

        if file_service.path_exists(chapter_path):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Chapter ID collision")

        # Create chapter directory and initial metadata file (chapter_meta.json)
        file_service.setup_chapter_structure(project_id, chapter_id)

        # Update project metadata (project_meta.json)
        project_metadata = self._read_project_meta(project_id)
        if 'chapters' not in project_metadata: project_metadata['chapters'] = {}

        # Check for order conflicts
        for existing_id, data in project_metadata['chapters'].items():
            if data.get('order') == chapter_in.order:
                 raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Chapter order {chapter_in.order} already exists for chapter '{data.get('title', existing_id)}'"
                 )

        project_metadata['chapters'][chapter_id] = {
            "title": chapter_in.title,
            "order": chapter_in.order
        }
        self._write_project_meta(project_id, project_metadata)

        # No content files directly in chapter need indexing at creation time
        # Scenes will be indexed when they are created within the chapter

        return ChapterRead(
            id=chapter_id,
            project_id=project_id,
            title=chapter_in.title,
            order=chapter_in.order
        )

    def get_by_id(self, project_id: str, chapter_id: str) -> ChapterRead:
        """Gets chapter details by ID."""
        project_service.get_by_id(project_id) # Ensure project exists

        project_metadata = self._read_project_meta(project_id)
        chapter_data = project_metadata.get('chapters', {}).get(chapter_id)

        if not chapter_data:
            # Also check if directory physically exists - inconsistency if meta is gone but dir exists
            chapter_path = file_service._get_chapter_path(project_id, chapter_id)
            if file_service.path_exists(chapter_path):
                 print(f"Warning: Chapter directory exists for {chapter_id} but missing from project metadata.")
                 # Could try to recover, but let's treat as not found for now
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chapter {chapter_id} not found in project {project_id}")

        # Verify directory exists as a sanity check
        chapter_path = file_service._get_chapter_path(project_id, chapter_id)
        if not file_service.path_exists(chapter_path):
             print(f"Warning: Chapter metadata exists for {chapter_id} but directory is missing.")
             # Treat as not found
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chapter {chapter_id} data missing for project {project_id}")

        return ChapterRead(
            id=chapter_id,
            project_id=project_id,
            title=chapter_data.get("title", f"Chapter {chapter_id}"),
            order=chapter_data.get("order", -1) # Use -1 or similar for missing order
        )

    def get_all_for_project(self, project_id: str) -> ChapterList:
        """Lists all chapters for a specific project."""
        project_service.get_by_id(project_id) # Ensure project exists

        project_metadata = self._read_project_meta(project_id)
        chapters_meta = project_metadata.get('chapters', {})

        chapters = []
        for chapter_id, data in chapters_meta.items():
            # Basic validation: check if dir exists before adding to list
            chapter_path = file_service._get_chapter_path(project_id, chapter_id)
            if file_service.path_exists(chapter_path): # Check if dir exists
                 chapters.append(ChapterRead(
                    id=chapter_id,
                    project_id=project_id,
                    title=data.get("title", f"Chapter {chapter_id}"),
                    order=data.get("order", -1)
                ))
            else:
                print(f"Warning: Skipping chapter {chapter_id} in list view: directory missing.")

        # Sort chapters by order
        chapters.sort(key=lambda c: c.order)
        return ChapterList(chapters=chapters)

    def update(self, project_id: str, chapter_id: str, chapter_in: ChapterUpdate) -> ChapterRead:
        """Updates chapter details (title, order)."""
        existing_chapter = self.get_by_id(project_id, chapter_id) # Ensures chapter exists

        project_metadata = self._read_project_meta(project_id)
        chapter_data = project_metadata.get('chapters', {}).get(chapter_id)

        if not chapter_data:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Chapter metadata inconsistency during update")

        updated = False
        if chapter_in.title is not None and chapter_in.title != chapter_data.get("title"):
            chapter_data["title"] = chapter_in.title
            existing_chapter.title = chapter_in.title
            updated = True

        if chapter_in.order is not None and chapter_in.order != chapter_data.get("order"):
            # Check for order conflicts before updating
            for other_id, data in project_metadata.get('chapters', {}).items():
                if other_id != chapter_id and data.get('order') == chapter_in.order:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=f"Chapter order {chapter_in.order} already exists for chapter '{data.get('title', other_id)}'"
                    )
            chapter_data["order"] = chapter_in.order
            existing_chapter.order = chapter_in.order
            updated = True

        if updated:
            self._write_project_meta(project_id, project_metadata)

        # Note: Updating chapter title/order does NOT require re-indexing anything,
        # as only content files (scenes within the chapter) are indexed.

        return existing_chapter

    def delete(self, project_id: str, chapter_id: str):
        """Deletes a chapter directory and its contents, including index cleanup."""
        # Ensure chapter exists (implicitly checks project too)
        self.get_by_id(project_id, chapter_id)

        chapter_path = file_service._get_chapter_path(project_id, chapter_id)

        # --- Call the enhanced delete_directory ---
        # This method in FileService now handles deleting scene docs from the index
        # *before* removing the chapter directory structure.
        print(f"Deleting chapter directory and cleaning index for: {chapter_path}")
        file_service.delete_directory(chapter_path)
        print(f"Chapter directory {chapter_id} deleted.")

        # Update project metadata (remove chapter entry)
        project_metadata = self._read_project_meta(project_id)
        if chapter_id in project_metadata.get('chapters', {}):
            del project_metadata['chapters'][chapter_id]
            self._write_project_meta(project_id, project_metadata)
            print(f"Chapter {chapter_id} removed from project metadata.")
        else:
            # Log inconsistency if chapter was found by get_by_id but missing in meta now
            print(f"Warning: Chapter {chapter_id} was deleted but already missing from project metadata.")


# Create a single instance
chapter_service = ChapterService()