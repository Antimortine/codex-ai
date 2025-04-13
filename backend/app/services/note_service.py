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
from app.models.note import NoteCreate, NoteUpdate, NoteRead, NoteList, NoteReadBasic
from app.services.file_service import file_service
from app.services.project_service import project_service
# Import index_manager if needed for explicit calls (though FileService handles it now)
# from app.rag.index_manager import index_manager
from app.models.common import generate_uuid
import logging
from typing import List, Optional # Added Optional

logger = logging.getLogger(__name__)

class NoteService:

    def _get_note_mtime(self, project_id: str, note_id: str) -> float | None:
        """Internal helper to get the modification time of a note file."""
        note_path = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords
        return file_service.get_file_mtime(note_path)

    def create(self, project_id: str, note_in: NoteCreate) -> NoteRead:
        """Creates a new note within a project."""
        logger.info(f"Creating note '{note_in.title}' in project {project_id}")
        # Use keyword argument
        project_service.get_by_id(project_id=project_id)

        note_id = generate_uuid()
        note_path = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords

        # 1. Update project metadata (do this first)
        try:
            project_metadata = file_service.read_project_metadata(project_id=project_id) # Use keyword
            if 'notes' not in project_metadata: project_metadata['notes'] = {} # Should exist due to FileService defaults

            project_metadata['notes'][note_id] = {"title": note_in.title}
            file_service.write_project_metadata(project_id=project_id, data=project_metadata) # Use keywords
            logger.debug(f"Updated project metadata for new note {note_id}")
        except Exception as meta_err:
            logger.error(f"Failed to update project metadata for new note in {project_id}: {meta_err}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save note metadata.") from meta_err

        # 2. Write the note file (triggers indexing)
        try:
            # Ensure content is properly normalized for UTF-8 encoding
            normalized_content = note_in.content
            if normalized_content.startswith('\ufeff'):  # Remove UTF-8 BOM if present
                normalized_content = normalized_content[1:]
                logger.info(f"Removed UTF-8 BOM from note content before saving")
                
            # Write with explicit UTF-8 encoding
            file_service.write_text_file(path=note_path, content=normalized_content, trigger_index=True) # Use keywords
            logger.debug(f"Wrote note file {note_path} with UTF-8 encoding")
        except Exception as file_err:
            logger.error(f"Failed to write note file {note_path} after metadata update: {file_err}", exc_info=True)
            # Attempt to rollback metadata change
            try:
                logger.warning(f"Attempting metadata rollback for note {note_id}")
                project_metadata_rollback = file_service.read_project_metadata(project_id=project_id) # Use keyword
                if note_id in project_metadata_rollback.get('notes', {}):
                    del project_metadata_rollback['notes'][note_id]
                    file_service.write_project_metadata(project_id=project_id, data=project_metadata_rollback) # Use keywords
                    logger.info(f"Metadata rollback successful for note {note_id}")
            except Exception as rollback_err:
                # Log rollback failure but raise original error
                logger.error(f"Failed to rollback metadata for note {note_id}: {rollback_err}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save note content file.") from file_err

        # 3. Get modification time
        last_modified = self._get_note_mtime(project_id=project_id, note_id=note_id) # Use keywords

        logger.info(f"Successfully created note {note_id} in project {project_id}")
        return NoteRead(
            id=note_id,
            project_id=project_id,
            title=note_in.title,
            content=note_in.content,
            last_modified=last_modified
        )

    def get_by_id(self, project_id: str, note_id: str) -> NoteRead:
        """Gets note details and content by ID."""
        logger.debug(f"Getting note {note_id} in project {project_id}")
        # Use keyword argument
        project_service.get_by_id(project_id=project_id)

        # 1. Read metadata for title
        project_metadata = file_service.read_project_metadata(project_id=project_id) # Use keyword
        note_meta = project_metadata.get('notes', {}).get(note_id)
        if not note_meta:
            logger.warning(f"Note {note_id} not found in metadata for project {project_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note {note_id} not found")
        note_title = note_meta.get("title", f"Note {note_id}") # Fallback title

        # 2. Read file content
        note_path = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords
        try:
            note_content = file_service.read_text_file(path=note_path) # Use keyword
        except HTTPException as e:
            if e.status_code == 404:
                logger.error(f"Note metadata exists for {note_id} but file {note_path} is missing.")
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note {note_id} data file missing") from e
            raise e # Re-raise other file read errors

        # 3. Get modification time
        last_modified = self._get_note_mtime(project_id=project_id, note_id=note_id) # Use keywords

        return NoteRead(
            id=note_id,
            project_id=project_id,
            title=note_title,
            content=note_content,
            last_modified=last_modified
        )


    def get_all_for_project(self, project_id: str) -> NoteList:
        """Lists all notes for a specific project, sorted by last modified."""
        logger.debug(f"Listing notes for project {project_id}")
        # Use keyword argument
        project_service.get_by_id(project_id=project_id)

        project_metadata = file_service.read_project_metadata(project_id=project_id) # Use keyword
        notes_meta = project_metadata.get('notes', {})

        notes_with_mtime: List[NoteReadBasic] = []
        for note_id, meta_data in notes_meta.items():
            last_modified = self._get_note_mtime(project_id=project_id, note_id=note_id) # Use keywords
            if last_modified is None:
                logger.warning(f"Could not get mtime for note {note_id} file; excluding from list or sorting last.")
                last_modified = 0.0 # Sort notes with missing files/mtime first/last

            notes_with_mtime.append(NoteReadBasic(
                id=note_id,
                project_id=project_id,
                title=meta_data.get("title", f"Note {note_id}"),
                last_modified=last_modified
            ))

        # Sort by last_modified descending (most recent first)
        notes_with_mtime.sort(key=lambda note: note.last_modified or 0.0, reverse=True)

        logger.info(f"Found {len(notes_with_mtime)} notes for project {project_id}")
        return NoteList(notes=notes_with_mtime)

    def update(self, project_id: str, note_id: str, note_in: NoteUpdate) -> NoteRead:
        """Updates note title or content."""
        logger.info(f"Updating note {note_id} in project {project_id}")

        # Use get_by_id to ensure note exists and get current state
        try:
            current_note = self.get_by_id(project_id=project_id, note_id=note_id) # Use keywords
        except HTTPException as e:
            if e.status_code == 404:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note {note_id} not found for update")
            raise e

        project_metadata = file_service.read_project_metadata(project_id=project_id) # Use keyword
        note_meta = project_metadata.get('notes', {}).get(note_id)
        if not note_meta:
             logger.error(f"Metadata inconsistency: Note {note_id} missing from metadata during update.")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note {note_id} metadata inconsistent")


        meta_updated = False
        content_updated = False
        new_title = current_note.title
        new_content = current_note.content

        # Update Title in Metadata if changed
        if note_in.title is not None and note_in.title != note_meta.get("title"):
            logger.debug(f"Updating title for note {note_id} to '{note_in.title}'")
            note_meta["title"] = note_in.title
            new_title = note_in.title
            meta_updated = True

        if meta_updated:
            try:
                file_service.write_project_metadata(project_id=project_id, data=project_metadata) # Use keywords
                logger.debug(f"Successfully updated metadata for note {note_id}")
            except Exception as meta_err:
                logger.error(f"Failed to write updated project metadata for note {note_id}: {meta_err}", exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save updated note metadata.") from meta_err

        # Update Content File if changed
        note_path = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords
        if note_in.content is not None and note_in.content != current_note.content:
            logger.debug(f"Updating content for note {note_id} in file {note_path}")
            try:
                # Ensure content is properly normalized for UTF-8 encoding
                normalized_content = note_in.content
                if normalized_content.startswith('\ufeff'):  # Remove UTF-8 BOM if present
                    normalized_content = normalized_content[1:]
                    logger.info(f"Removed UTF-8 BOM from note content before updating")
                
                # Write file AND trigger index update with explicit UTF-8 encoding
                file_service.write_text_file(path=note_path, content=normalized_content, trigger_index=True) # Use keywords
                new_content = normalized_content
                content_updated = True
                logger.debug(f"Successfully updated content file for note {note_id} with UTF-8 encoding")
                
                # If this is a previously corrupted file, log the fix
                if current_note.content and (current_note.content.startswith('\ufeff') or current_note.content.startswith('ÿþ')):
                    logger.info(f"Fixed encoding for previously corrupted note {note_id}")
            except Exception as file_err:
                logger.error(f"Failed to write updated content file for note {note_id}: {file_err}", exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save updated note content.") from file_err

        # Get the final modification time
        final_mtime = self._get_note_mtime(project_id=project_id, note_id=note_id) # Use keywords

        logger.info(f"Successfully updated note {note_id}")
        return NoteRead(
            id=note_id,
            project_id=project_id,
            title=new_title,
            content=new_content,
            last_modified=final_mtime
        )


    def delete(self, project_id: str, note_id: str):
        """Deletes a note."""
        logger.info(f"Deleting note {note_id} from project {project_id}")
        # Use keyword argument
        project_service.get_by_id(project_id=project_id)

        # 1. Check if note exists in metadata first
        project_metadata = file_service.read_project_metadata(project_id=project_id) # Use keyword
        if note_id not in project_metadata.get('notes', {}):
            logger.warning(f"Note {note_id} not found in metadata for deletion.")
            note_path_check = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords
            if not file_service.path_exists(path=note_path_check): # Use keyword
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note {note_id} not found")
            else:
                logger.warning(f"Note file exists for {note_id} but missing from metadata. Proceeding with file deletion.")


        # 2. Delete the note file (FileService handles index deletion)
        note_path = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords
        try:
            file_service.delete_file(path=note_path) # Use keyword
            logger.debug(f"Deleted note file {note_path}")
        except HTTPException as e:
            if e.status_code == 404:
                logger.warning(f"Note file {note_path} not found during delete operation (may have been deleted already).")
            else:
                logger.error(f"Error deleting note file {note_path}: {e.detail}", exc_info=True)
                raise e # Re-raise other errors

        # 3. Remove entry from metadata if it exists
        if note_id in project_metadata.get('notes', {}):
            try:
                del project_metadata['notes'][note_id]
                file_service.write_project_metadata(project_id=project_id, data=project_metadata) # Use keywords
                logger.debug(f"Removed note {note_id} from project metadata.")
            except Exception as meta_err:
                logger.error(f"Failed to write updated project metadata after deleting note {note_id}: {meta_err}", exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update metadata after note deletion.") from meta_err
        else:
             logger.info(f"Note {note_id} was not in metadata, no metadata update needed.")

        logger.info(f"Successfully completed delete operation for note {note_id}")
        # No return value on successful delete


# Create a single instance
note_service = NoteService()