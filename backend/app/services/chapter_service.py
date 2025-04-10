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
from app.services.file_service import file_service
from app.services.project_service import project_service
from app.models.common import generate_uuid
import logging

logger = logging.getLogger(__name__)

class ChapterService:

    # --- REMOVED internal _read_project_meta and _write_project_meta ---

    def create(self, project_id: str, chapter_in: ChapterCreate) -> ChapterRead:
        """Creates a new chapter within a project."""
        project_service.get_by_id(project_id) # Ensure project exists

        chapter_id = generate_uuid()
        chapter_path = file_service._get_chapter_path(project_id, chapter_id) # Keep using internal path helper

        if file_service.path_exists(chapter_path):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Chapter ID collision")

        # Create chapter directory and initial metadata file (using file_service method)
        file_service.setup_chapter_structure(project_id, chapter_id)

        # Update project metadata (project_meta.json) using file_service
        project_metadata = file_service.read_project_metadata(project_id)
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
        file_service.write_project_metadata(project_id, project_metadata)

        return ChapterRead(
            id=chapter_id,
            project_id=project_id,
            title=chapter_in.title,
            order=chapter_in.order
        )

    def get_by_id(self, project_id: str, chapter_id: str) -> ChapterRead:
        """Gets chapter details by ID."""
        project_service.get_by_id(project_id)

        project_metadata = file_service.read_project_metadata(project_id)
        chapter_data = project_metadata.get('chapters', {}).get(chapter_id)

        if not chapter_data:
            chapter_path = file_service._get_chapter_path(project_id, chapter_id)
            if file_service.path_exists(chapter_path):
                 logger.warning(f"Chapter directory exists for {chapter_id} but missing from project metadata.")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chapter {chapter_id} not found in project {project_id}")

        chapter_path = file_service._get_chapter_path(project_id, chapter_id)
        if not file_service.path_exists(chapter_path):
             logger.warning(f"Chapter metadata exists for {chapter_id} but directory is missing.")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chapter {chapter_id} data missing for project {project_id}")

        return ChapterRead(
            id=chapter_id,
            project_id=project_id,
            title=chapter_data.get("title", f"Chapter {chapter_id}"),
            order=chapter_data.get("order", -1)
        )

    def get_all_for_project(self, project_id: str) -> ChapterList:
        """Lists all chapters for a specific project."""
        project_service.get_by_id(project_id) # Ensure project exists

        project_metadata = file_service.read_project_metadata(project_id)
        chapters_meta = project_metadata.get('chapters', {})

        chapters = []
        for chapter_id, data in chapters_meta.items():
            # Basic validation: check if dir exists before adding to list
            chapter_path = file_service._get_chapter_path(project_id, chapter_id)
            if file_service.path_exists(chapter_path):
                 chapters.append(ChapterRead(
                    id=chapter_id,
                    project_id=project_id,
                    title=data.get("title", f"Chapter {chapter_id}"),
                    order=data.get("order", -1)
                ))
            else:
                logger.warning(f"Skipping chapter {chapter_id} in list view: directory missing.")

        chapters.sort(key=lambda c: c.order)
        return ChapterList(chapters=chapters)

    def update(self, project_id: str, chapter_id: str, chapter_in: ChapterUpdate) -> ChapterRead:
        """Updates chapter details (title, order)."""
        existing_chapter = self.get_by_id(project_id, chapter_id) # Ensures chapter exists

        project_metadata = file_service.read_project_metadata(project_id)
        chapter_data = project_metadata.get('chapters', {}).get(chapter_id)

        if not chapter_data:
             # This should be caught by get_by_id, but defensive check
             logger.error(f"Chapter metadata inconsistency during update for {chapter_id}")
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
            file_service.write_project_metadata(project_id, project_metadata)

        return existing_chapter

    def delete(self, project_id: str, chapter_id: str):
        """Deletes a chapter directory and its contents, including index cleanup, and renumbers remaining chapters."""
        self.get_by_id(project_id, chapter_id) # Ensures chapter exists

        chapter_path = file_service._get_chapter_path(project_id, chapter_id)

        logger.info(f"Deleting chapter directory and cleaning index for: {chapter_path}")
        file_service.delete_directory(chapter_path) # FileService handles index cleanup within
        logger.info(f"Chapter directory {chapter_id} deleted.")

        # Update project metadata (remove chapter entry AND renumber)
        project_metadata = file_service.read_project_metadata(project_id)
        chapters_dict = project_metadata.get('chapters', {})

        if chapter_id in chapters_dict:
            del chapters_dict[chapter_id]
            logger.info(f"Chapter {chapter_id} removed from project metadata dictionary.")

            # --- Renumbering Logic ---
            if chapters_dict: # Only renumber if there are remaining chapters
                logger.info(f"Renumbering remaining chapters for project {project_id}...")
                # Sort remaining chapters by current order
                remaining_chapters = sorted(
                    chapters_dict.items(),
                    key=lambda item: item[1].get('order', float('inf')) # Sort by order, put chapters without order last
                )

                # Create a new dictionary with renumbered chapters
                renumbered_chapters = {}
                for index, (chap_id, chap_data) in enumerate(remaining_chapters):
                    new_order = index + 1
                    chap_data['order'] = new_order # Update order in the data dictionary
                    renumbered_chapters[chap_id] = chap_data # Add to the new dictionary
                    logger.debug(f"  - Chapter '{chap_data.get('title', chap_id)}' (ID: {chap_id}) renumbered to order {new_order}")

                project_metadata['chapters'] = renumbered_chapters # Replace old dict with renumbered one
                logger.info("Chapter renumbering complete.")
            else:
                logger.info("No remaining chapters to renumber.")
            # --- End Renumbering Logic ---

            file_service.write_project_metadata(project_id, project_metadata)
            logger.info(f"Project metadata updated after chapter deletion and renumbering.")
        else:
            logger.warning(f"Chapter {chapter_id} was deleted but already missing from project metadata.")


# Create a single instance
chapter_service = ChapterService()