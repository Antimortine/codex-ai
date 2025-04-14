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
from app.models.note import (
    NoteCreate, NoteUpdate, NoteRead, NoteList, NoteReadBasic,
    NoteTree, NoteTreeNode # Import new models
)
from app.services.file_service import file_service
from app.services.project_service import project_service
# Import index_manager if needed for explicit calls (though FileService handles it now)
# from app.rag.index_manager import index_manager
from app.models.common import generate_uuid
import logging
from typing import List, Optional, Dict # Added Dict

logger = logging.getLogger(__name__)

class NoteService:

    def _validate_folder_path(self, path: Optional[str]) -> str:
        """Validates and normalizes a virtual folder path."""
        if path is None:
            return "/" # Default to root if None is passed

        path = path.strip()
        if not path:
            return "/" # Treat empty string as root

        if not path.startswith('/'):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder path must start with '/'")

        if path != '/' and path.endswith('/'):
            path = path.rstrip('/') # Remove trailing slash unless it's the root

        if '//' in path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Folder path cannot contain '//'")

        # Add more validation if needed (e.g., allowed characters)

        return path

    def _get_note_mtime(self, project_id: str, note_id: str) -> float | None:
        """Internal helper to get the modification time of a note file."""
        note_path = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords
        return file_service.get_file_mtime(note_path)

    def create(self, project_id: str, note_in: NoteCreate) -> NoteRead:
        """Creates a new note within a project."""
        logger.info(f"Creating note '{note_in.title}' in project {project_id}")
        # Use keyword argument
        project_service.get_by_id(project_id=project_id)

        # Validate folder path
        folder_path = self._validate_folder_path(note_in.folder_path)

        note_id = generate_uuid()
        note_path = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords

        # 1. Update project metadata (do this first)
        try:
            project_metadata = file_service.read_project_metadata(project_id=project_id) # Use keyword
            if 'notes' not in project_metadata: project_metadata['notes'] = {} # Should exist due to FileService defaults

            # Store title and folder path
            project_metadata['notes'][note_id] = {
                "title": note_in.title,
                "folder_path": folder_path
            }
            file_service.write_project_metadata(project_id=project_id, data=project_metadata) # Use keywords
            logger.debug(f"Updated project metadata for new note {note_id} in path '{folder_path}'")
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
            folder_path=folder_path, # Include folder_path
            last_modified=last_modified
        )

    def get_by_id(self, project_id: str, note_id: str) -> NoteRead:
        """Gets note details and content by ID."""
        logger.debug(f"Getting note {note_id} in project {project_id}")
        # Use keyword argument
        project_service.get_by_id(project_id=project_id)

        # 1. Read metadata for title and folder_path
        project_metadata = file_service.read_project_metadata(project_id=project_id) # Use keyword
        note_meta = project_metadata.get('notes', {}).get(note_id)
        if not note_meta:
            logger.warning(f"Note {note_id} not found in metadata for project {project_id}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note {note_id} not found")
        note_title = note_meta.get("title", f"Note {note_id}") # Fallback title
        folder_path = note_meta.get("folder_path", "/") # Default to root if missing

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
            folder_path=folder_path, # Include folder_path
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

            folder_path = meta_data.get("folder_path", "/") # Default to root if missing

            notes_with_mtime.append(NoteReadBasic(
                id=note_id,
                project_id=project_id,
                title=meta_data.get("title", f"Note {note_id}"),
                folder_path=folder_path, # Include folder_path
                last_modified=last_modified
            ))

        # Sort by last_modified descending (most recent first)
        notes_with_mtime.sort(key=lambda note: note.last_modified or 0.0, reverse=True)

        logger.info(f"Found {len(notes_with_mtime)} notes for project {project_id}")
        return NoteList(notes=notes_with_mtime)

    def update(self, project_id: str, note_id: str, note_in: NoteUpdate) -> NoteRead:
        """Updates note title, content, or folder path."""
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
        new_folder_path = current_note.folder_path

        # Update Title in Metadata if changed
        if note_in.title is not None and note_in.title != note_meta.get("title"):
            logger.debug(f"Updating title for note {note_id} to '{note_in.title}'")
            note_meta["title"] = note_in.title
            new_title = note_in.title
            meta_updated = True

        # Update Folder Path in Metadata if changed
        if note_in.folder_path is not None:
            validated_path = self._validate_folder_path(note_in.folder_path)
            if validated_path != note_meta.get("folder_path"):
                logger.debug(f"Updating folder path for note {note_id} to '{validated_path}'")
                note_meta["folder_path"] = validated_path
                new_folder_path = validated_path
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
            folder_path=new_folder_path, # Include folder_path
            last_modified=final_mtime
        )


    def delete(self, project_id: str, note_id: str):
        """Deletes a note (file and metadata)."""
        logger.info(f"Deleting note {note_id} from project {project_id}")
        # Use keyword argument
        project_service.get_by_id(project_id=project_id)

        # 1. Check if note exists in metadata first
        project_metadata = file_service.read_project_metadata(project_id=project_id) # Use keyword
        note_exists_in_meta = note_id in project_metadata.get('notes', {})

        # 2. Delete the note file (FileService handles index deletion)
        note_path = file_service._get_note_path(project_id=project_id, note_id=note_id) # Use keywords
        file_existed = file_service.path_exists(path=note_path)
        if file_existed:
            try:
                file_service.delete_file(path=note_path) # Use keyword
                logger.debug(f"Deleted note file {note_path}")
            except HTTPException as e:
                # Log error but proceed to metadata cleanup if possible
                logger.error(f"Error deleting note file {note_path}: {e.detail}", exc_info=True)
                if e.status_code != 404: # Don't raise if it was already gone
                    raise e
        elif not note_exists_in_meta:
             # If neither file nor metadata exists, raise 404
             logger.warning(f"Note {note_id} not found in metadata or filesystem for deletion.")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note {note_id} not found")
        else:
             logger.warning(f"Note file {note_path} not found, but metadata exists. Proceeding with metadata cleanup.")


        # 3. Remove entry from metadata if it exists
        if note_exists_in_meta:
            try:
                del project_metadata['notes'][note_id]
                file_service.write_project_metadata(project_id=project_id, data=project_metadata) # Use keywords
                logger.debug(f"Removed note {note_id} from project metadata.")
            except Exception as meta_err:
                logger.error(f"Failed to write updated project metadata after deleting note {note_id}: {meta_err}", exc_info=True)
                # If file deletion succeeded but metadata failed, we are in an inconsistent state.
                # Raising an error is appropriate.
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to update metadata after note deletion.") from meta_err
        else:
             logger.info(f"Note {note_id} was not in metadata, no metadata update needed.")

        logger.info(f"Successfully completed delete operation for note {note_id}")
        # No return value on successful delete

    def get_note_tree(self, project_id: str) -> NoteTree:
        """Builds and returns the hierarchical note tree structure."""
        logger.debug(f"Building note tree for project {project_id}")
        project_service.get_by_id(project_id=project_id) # Check project exists

        project_metadata = file_service.read_project_metadata(project_id=project_id)
        notes_meta = project_metadata.get('notes', {})

        nodes_by_path: Dict[str, NoteTreeNode] = {}
        # Initialize root node
        root_node = NoteTreeNode(id='/', name='Root', type='folder', path='/')
        nodes_by_path['/'] = root_node

        # --- Build tree from notes ---
        for note_id, meta_data in notes_meta.items():
            folder_path = self._validate_folder_path(meta_data.get("folder_path", "/"))
            title = meta_data.get("title", f"Note {note_id}")
            last_modified = self._get_note_mtime(project_id=project_id, note_id=note_id)

            parent_node = root_node
            current_path_segments = []

            # Ensure parent folders exist
            if folder_path != '/':
                segments = folder_path.strip('/').split('/')
                for i, segment in enumerate(segments):
                    current_path_segments.append(segment)
                    current_path = '/' + '/'.join(current_path_segments)

                    if current_path not in nodes_by_path:
                        # Create new folder node
                        new_folder_node = NoteTreeNode(
                            id=current_path, # Use path as ID for folders
                            name=segment,
                            type='folder',
                            path=current_path
                        )
                        nodes_by_path[current_path] = new_folder_node
                        # Add to parent's children
                        parent_node.children.append(new_folder_node)
                        parent_node = new_folder_node # Update parent for next level
                    else:
                        parent_node = nodes_by_path[current_path] # Existing folder becomes parent

            # Create and add the note node
            note_node = NoteTreeNode(
                id=note_id, # Use note_id as ID for notes
                name=title,
                type='note',
                path=folder_path, # Note's path is its containing folder path
                note_id=note_id,
                last_modified=last_modified
            )
            parent_node.children.append(note_node)

        # --- Sort the tree recursively ---
        def sort_children(node: NoteTreeNode):
            if node.type == 'folder':
                # Sort children: folders first, then notes, then alphabetically by name
                node.children.sort(key=lambda x: (0 if x.type == 'folder' else 1, x.name.lower()))
                for child in node.children:
                    sort_children(child)

        sort_children(root_node)

        logger.info(f"Successfully built note tree for project {project_id}")
        return NoteTree(tree=root_node.children) # Return children of the root


    def rename_folder(self, project_id: str, old_path: str, new_path: str):
        """Renames a virtual folder by updating metadata of contained notes."""
        logger.info(f"Renaming virtual folder from '{old_path}' to '{new_path}' in project {project_id}")
        project_service.get_by_id(project_id=project_id)

        old_path = self._validate_folder_path(old_path)
        new_path = self._validate_folder_path(new_path)

        if old_path == '/':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot rename the root folder.")
        if new_path == '/':
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot rename a folder to root.")
        if old_path == new_path:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Old and new paths are the same.")

        project_metadata = file_service.read_project_metadata(project_id=project_id)
        notes_meta = project_metadata.get('notes', {})
        updated_count = 0
        paths_to_check = set(meta.get("folder_path", "/") for meta in notes_meta.values())

        # Basic conflict check: Ensure new_path isn't an existing folder path or a prefix of one
        # More robust checking might be needed depending on desired behavior
        if new_path in paths_to_check or any(p.startswith(new_path + '/') for p in paths_to_check if p != new_path):
             # Allow renaming if new_path only exists because it's part of the old_path structure being renamed
             is_part_of_rename = any(p == old_path or p.startswith(old_path + '/') for p in paths_to_check if p == new_path or p.startswith(new_path + '/'))
             if not is_part_of_rename:
                 raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Target path '{new_path}' conflicts with an existing folder or note path.")


        for note_id, meta_data in notes_meta.items():
            current_folder_path = meta_data.get("folder_path", "/")
            path_updated = False
            if current_folder_path == old_path:
                meta_data["folder_path"] = new_path
                path_updated = True
            elif current_folder_path.startswith(old_path + '/'):
                meta_data["folder_path"] = new_path + current_folder_path[len(old_path):]
                path_updated = True

            if path_updated:
                updated_count += 1

        if updated_count > 0:
            try:
                file_service.write_project_metadata(project_id=project_id, data=project_metadata)
                logger.info(f"Successfully renamed folder '{old_path}' to '{new_path}', updated {updated_count} note paths.")
            except Exception as e:
                logger.error(f"Failed to write metadata after renaming folder: {e}", exc_info=True)
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save metadata after folder rename.") from e
        else:
             logger.info(f"No notes found within folder '{old_path}' to rename.")
             # Optionally raise 404 if the old_path didn't correspond to any notes? For now, just log.


    def delete_folder(self, project_id: str, path: str, recursive: bool):
        """Deletes a virtual folder and optionally its contents."""
        logger.info(f"Deleting virtual folder '{path}' in project {project_id} (recursive={recursive})")
        project_service.get_by_id(project_id=project_id)

        path = self._validate_folder_path(path)
        if path == '/':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot delete the root folder.")

        project_metadata = file_service.read_project_metadata(project_id=project_id)
        notes_meta = project_metadata.get('notes', {})
        notes_to_delete_ids = []

        # Find notes within the target path
        for note_id, meta_data in notes_meta.items():
            current_folder_path = meta_data.get("folder_path", "/")
            if current_folder_path == path or current_folder_path.startswith(path + '/'):
                notes_to_delete_ids.append(note_id)

        if not notes_to_delete_ids:
            logger.info(f"Virtual folder '{path}' is empty or does not exist. No action taken.")
            return # Nothing to delete

        if not recursive:
            logger.warning(f"Attempted to delete non-empty folder '{path}' non-recursively.")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=f"Folder '{path}' is not empty. Use recursive=true to delete.")

        # --- Recursive Deletion ---
        logger.info(f"Recursively deleting {len(notes_to_delete_ids)} notes from folder '{path}' and its subfolders.")

        # 1. Delete files first (log errors but continue)
        deleted_files_count = 0
        failed_file_deletions = []
        for note_id in notes_to_delete_ids:
            note_file_path = file_service._get_note_path(project_id=project_id, note_id=note_id)
            try:
                # FileService delete_file handles index deletion
                file_service.delete_file(path=note_file_path)
                deleted_files_count += 1
            except HTTPException as e:
                 if e.status_code == 404:
                     logger.warning(f"Note file {note_file_path} not found during recursive delete (might have been deleted already).")
                 else:
                     logger.error(f"Failed to delete note file {note_file_path} during recursive folder delete: {e.detail}", exc_info=True)
                     failed_file_deletions.append(note_id)
            except Exception as e:
                 logger.error(f"Unexpected error deleting note file {note_file_path}: {e}", exc_info=True)
                 failed_file_deletions.append(note_id)


        # 2. Update metadata (remove entries for successfully deleted files)
        notes_meta_updated = {
            note_id: meta for note_id, meta in notes_meta.items()
            if note_id not in notes_to_delete_ids or note_id in failed_file_deletions
        }

        if len(notes_meta_updated) < len(notes_meta):
            project_metadata['notes'] = notes_meta_updated
            try:
                file_service.write_project_metadata(project_id=project_id, data=project_metadata)
                logger.info(f"Successfully removed metadata for {len(notes_to_delete_ids) - len(failed_file_deletions)} notes during folder delete.")
            except Exception as e:
                logger.error(f"Failed to write metadata after recursive folder delete: {e}", exc_info=True)
                # Raise error, as metadata is now potentially inconsistent with deleted files
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to save metadata after recursive folder delete.") from e
        else:
            logger.warning("Metadata update skipped as no notes were successfully deleted.")

        if failed_file_deletions:
             logger.error(f"Completed recursive delete for folder '{path}', but failed to delete files/metadata for notes: {failed_file_deletions}")
             # Optionally raise an error here to indicate partial failure?
             # For now, logging the error might be sufficient.

        logger.info(f"Successfully completed recursive delete operation for folder '{path}'.")


# Create a single instance
note_service = NoteService()