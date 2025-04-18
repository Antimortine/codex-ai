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
from app.services.file_service import file_service, BASE_PROJECT_DIR
from app.services.project_service import project_service
# --- REMOVED: SceneService import from top level ---
# from app.services.scene_service import scene_service
# --- END REMOVED ---
from app.models.common import generate_uuid
import logging
# --- ADDED: Import re for slugification ---
import re
# --- END ADDED ---

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

        # --- FIX: Provide a default valid order if missing, or raise error ---
        # Option 1: Raise error (stricter, assumes data should be valid)
        # order = chapter_data.get("order")
        # if order is None or not isinstance(order, int) or order < 1:
        #     logger.error(f"Invalid or missing 'order' in metadata for chapter {chapter_id}")
        #     # Or potentially try to recover/renumber here? For now, error is safer.
        #     raise HTTPException(status_code=500, detail=f"Corrupt metadata: Missing or invalid order for chapter {chapter_id}")

        # Option 2: Default to a valid value (e.g., 1) if missing, log warning (more lenient)
        order = chapter_data.get("order")
        if order is None or not isinstance(order, int) or order < 1:
            logger.warning(f"Invalid or missing 'order' in metadata for chapter {chapter_id}. Defaulting to 1 for read operation.")
            order = 1 # Assign a valid default

        return ChapterRead(
            id=chapter_id,
            project_id=project_id,
            title=chapter_data.get("title", f"Chapter {chapter_id}"),
            order=order # Use the validated/defaulted order
        )
        # --- END FIX ---

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
                 # --- FIX: Provide default valid order if missing ---
                 order = data.get("order")
                 if order is None or not isinstance(order, int) or order < 1:
                     logger.warning(f"Invalid or missing 'order' in metadata for chapter {chapter_id} during list. Defaulting to 1.")
                     order = 1
                 # --- END FIX ---
                 chapters.append(ChapterRead(
                    id=chapter_id,
                    project_id=project_id,
                    title=data.get("title", f"Chapter {chapter_id}"),
                    order=order # Use validated/defaulted order
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

        # --- FIX: Modify metadata DICTIONARY DIRECTLY before writing ---
        project_metadata = file_service.read_project_metadata(project_id) # Read fresh copy
        chapters_dict = project_metadata.get('chapters', {})

        if chapter_id in chapters_dict:
            # --- Keep track of the order of the deleted chapter ---
            # deleted_order = chapters_dict[chapter_id].get('order', float('inf')) # Not strictly needed for simple renumbering
            # --- Delete the chapter ---
            del chapters_dict[chapter_id]
            logger.info(f"Chapter {chapter_id} removed from project metadata dictionary.")

            # --- Renumbering Logic ---
            if chapters_dict:
                logger.info(f"Renumbering remaining chapters for project {project_id}...")
                remaining_chapters = sorted(
                    chapters_dict.items(),
                    key=lambda item: item[1].get('order', float('inf'))
                )

                # Create a new dictionary to avoid modifying during iteration (safer)
                renumbered_chapters = {}
                current_order = 1
                for chap_id, chap_data in remaining_chapters:
                     # Always assign the new sequential order
                     logger.debug(f"  - Chapter '{chap_data.get('title', chap_id)}' (ID: {chap_id}) order changing from {chap_data.get('order')} to {current_order}")
                     chap_data['order'] = current_order
                     renumbered_chapters[chap_id] = chap_data # Add potentially updated data
                     current_order += 1


                # Update the original metadata dictionary
                project_metadata['chapters'] = renumbered_chapters
                logger.info("Chapter renumbering complete.")
            else:
                logger.info("No remaining chapters to renumber.")
            # --- End Renumbering Logic ---

            file_service.write_project_metadata(project_id, project_metadata) # Write the modified dict
            logger.info(f"Project metadata updated after chapter deletion and renumbering.")
        else:
            logger.warning(f"Chapter {chapter_id} was deleted but already missing from project metadata.")
        # --- END FIX ---

    # --- ADDED: Compile Chapter Content ---
    def compile_chapter_content(self, project_id: str, chapter_id: str, include_titles: bool = True, separator: str = "\n\n---\n\n") -> dict:
        """
        Compiles the content of all scenes within a chapter into a single string.

        Args:
            project_id: The project ID.
            chapter_id: The chapter ID.
            include_titles: Whether to include scene titles as Markdown H2 headings.
            separator: The string to use between scene blocks.

        Returns:
            A dictionary containing 'filename' and 'content'.
            Raises HTTPException 404 if the chapter is not found.
        """
        # --- MOVED IMPORT: Import scene_service locally to break cycle ---
        from app.services.scene_service import scene_service
        # --- END MOVED IMPORT ---

        logger.info(f"Compiling content for chapter {chapter_id} in project {project_id} (Titles: {include_titles}, Separator: '{repr(separator)}')")

        # Validate chapter and get title
        chapter_data = self.get_by_id(project_id, chapter_id)
        chapter_title = chapter_data.title

        # Get sorted scenes with content
        scenes = scene_service.get_all_for_chapter(project_id, chapter_id).scenes

        if not scenes:
            logger.info(f"Chapter {chapter_id} has no scenes to compile.")
            filename = f"{self._slugify(chapter_title)}-empty.md" if chapter_title else f"{chapter_id}-empty.md"
            return {"filename": filename, "content": ""}

        compiled_blocks = []
        for scene in scenes:
            scene_block = ""
            if include_titles:
                scene_block += f"## {scene.title}\n\n"
            scene_block += scene.content
            compiled_blocks.append(scene_block)

        compiled_content = separator.join(compiled_blocks)

        # Generate filename
        slug = self._slugify(chapter_title) if chapter_title else chapter_id
        filename = f"{slug}.md"

        logger.info(f"Compiled {len(scenes)} scenes for chapter {chapter_id}. Filename: {filename}")
        return {"filename": filename, "content": compiled_content}

    def _slugify(self, text: str) -> str:
        """Simple slugification: lowercase, replace spaces/non-alphanum with hyphens."""
        if not text:
            return "untitled-chapter"
        # --- REVISED SLUGIFY LOGIC V2 ---
        text = str(text).lower().strip()
        # Replace sequences of non-alphanumeric chars (excluding _ and -) with a single hyphen
        text = re.sub(r'[^\w_-]+', '-', text)
        # Replace whitespace sequences (just in case any remain) with a single hyphen
        text = re.sub(r'\s+', '-', text)
        # Collapse consecutive hyphens
        text = re.sub(r'-+', '-', text)
        # Remove leading/trailing hyphens
        text = text.strip('-')
        # --- END REVISED SLUGIFY LOGIC V2 ---
        return text or "untitled-chapter" # Fallback if everything is stripped
    # --- END ADDED ---


# Create a single instance
chapter_service = ChapterService()