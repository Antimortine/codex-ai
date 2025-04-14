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

from fastapi import APIRouter, Depends, HTTPException, status, Body, Path
from typing import List
from app.models.note import (
    NoteCreate, NoteUpdate, NoteRead, NoteList, NoteReadBasic,
    NoteTree, FolderRenameRequest, FolderDeleteRequest # Import new models
)
from app.models.common import Message
# Import the service instance
from app.services.note_service import note_service
# Import project dependency check
from app.api.v1.endpoints.content_blocks import get_project_dependency
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Endpoint Definitions ---
# IMPORTANT: Define specific paths BEFORE paths with parameters to avoid routing conflicts

@router.get(
    "/tree",
    response_model=NoteTree,
    summary="Get Note Tree",
    description="Retrieves the hierarchical structure of notes and virtual folders for the project.",
)
async def get_note_tree(
    project_id: str = Depends(get_project_dependency),
):
    """
    Retrieves the note structure as a tree, including virtual folders.

    - **project_id**: The UUID of the project.
    """
    logger.info(f"API: Received request to get note tree for project {project_id}")
    try:
        # Delegate tree building to the service layer
        note_tree = note_service.get_note_tree(project_id=project_id)
        logger.info(f"API: Successfully built note tree for project {project_id}")
        return note_tree
    except HTTPException as http_exc:
        logger.warning(f"API: HTTPException during note tree retrieval for project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"API: Unexpected error getting note tree for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error getting note tree: {e}"
        )

@router.patch(
    "/folders",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Rename Virtual Folder",
    description="Renames a virtual folder by updating the metadata of all contained notes.",
)
async def rename_folder(
    request: FolderRenameRequest = Body(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Renames a virtual folder. This updates the `folder_path` metadata for all notes
    currently residing in the `old_path` or any of its virtual subdirectories.

    - **project_id**: The UUID of the project.
    - **request**: Contains `old_path` and `new_path`.
    """
    logger.info(f"API: Received request to rename folder from '{request.old_path}' to '{request.new_path}' in project {project_id}")
    try:
        note_service.rename_folder(
            project_id=project_id,
            old_path=request.old_path,
            new_path=request.new_path
        )
        logger.info(f"API: Successfully processed rename folder request for '{request.old_path}' in project {project_id}")
        return Message(message=f"Folder '{request.old_path}' renamed to '{request.new_path}' successfully.")
    except HTTPException as http_exc:
        logger.warning(f"API: HTTPException during folder rename for '{request.old_path}' in project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"API: Unexpected error renaming folder '{request.old_path}' in project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error renaming folder: {e}"
        )

@router.delete(
    "/folders",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Delete Virtual Folder",
    description="Deletes a virtual folder. If recursive is true, deletes all contained notes and subfolders.",
)
async def delete_folder(
    request: FolderDeleteRequest = Body(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Deletes a virtual folder.

    - If `recursive` is `false`, the operation will fail if the folder contains any notes.
    - If `recursive` is `true`, all notes within the specified `path` (and its virtual subdirectories) will be deleted (files and metadata).

    - **project_id**: The UUID of the project.
    - **request**: Contains `path` and `recursive` flag.
    """
    logger.info(f"API: Received request to delete folder '{request.path}' (recursive={request.recursive}) in project {project_id}")
    try:
        note_service.delete_folder(
            project_id=project_id,
            path=request.path,
            recursive=request.recursive
        )
        logger.info(f"API: Successfully processed delete folder request for '{request.path}' in project {project_id}")
        return Message(message=f"Folder '{request.path}' deleted successfully.")
    except HTTPException as http_exc:
        logger.warning(f"API: HTTPException during folder delete for '{request.path}' in project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"API: Unexpected error deleting folder '{request.path}' in project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error deleting folder: {e}"
        )

# --- Note CRUD Endpoints ---

@router.post(
    "/",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Note",
    description="Creates a new note within the project, optionally specifying a virtual folder path.",
)
async def create_note(
    note_in: NoteCreate = Body(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Creates a new note associated with the project.

    - **project_id**: The UUID of the project.
    - **note_in**: The note data (title, optional initial content, optional folder_path).
    """
    logger.info(f"API: Received request to create note in project {project_id} with title '{note_in.title}' in path '{note_in.folder_path}'")
    try:
        # Delegate creation to the service layer
        created_note = note_service.create(project_id=project_id, note_in=note_in)
        logger.info(f"API: Successfully created note {created_note.id} in project {project_id}")
        return created_note
    except HTTPException as http_exc:
        # Re-raise known HTTP exceptions from the service layer (e.g., project not found, invalid path)
        logger.warning(f"API: HTTPException during note creation for project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"API: Unexpected error creating note in project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error creating note: {e}"
        )

@router.get(
    "/",
    response_model=NoteList,
    summary="List Notes",
    description="Retrieves a list of all notes for the project (basic details including folder path), sorted by last modified.",
)
async def list_notes(
    project_id: str = Depends(get_project_dependency),
):
    """
    Retrieves all notes for a specific project, sorted by last modification date (newest first).
    Includes basic details like id, title, folder_path, and last_modified.

    - **project_id**: The UUID of the project.
    """
    logger.info(f"API: Received request to list notes in project {project_id}")
    try:
        # Delegate listing to the service layer
        notes = note_service.get_all_for_project(project_id=project_id)
        logger.info(f"API: Successfully retrieved {len(notes.notes)} notes for project {project_id}")
        return notes
    except HTTPException as http_exc:
        logger.warning(f"API: HTTPException during note listing for project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"API: Unexpected error listing notes in project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error listing notes: {e}"
        )

@router.get(
    "/{note_id}",
    response_model=NoteRead,
    summary="Get Note",
    description="Retrieves details, content, and folder path of a specific note.",
)
async def get_note(
    note_id: str = Path(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Retrieves a specific note by its ID, including its folder path.

    - **project_id**: The UUID of the project.
    - **note_id**: The UUID of the note to retrieve.
    """
    logger.info(f"API: Received request to get note {note_id} in project {project_id}")
    try:
        # Delegate retrieval to the service layer
        note = note_service.get_by_id(project_id=project_id, note_id=note_id)
        logger.info(f"API: Successfully retrieved note {note_id} for project {project_id}")
        return note
    except HTTPException as http_exc:
        # Handle 404 Not Found specifically if needed, otherwise re-raise
        if http_exc.status_code == status.HTTP_404_NOT_FOUND:
            logger.warning(f"API: Note {note_id} not found in project {project_id}.")
        else:
            logger.warning(f"API: HTTPException during note retrieval for {note_id} in project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"API: Unexpected error getting note {note_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error getting note: {e}"
        )


@router.patch(
    "/{note_id}",
    response_model=NoteRead,
    summary="Update Note",
    description="Updates the title, content, or virtual folder path of an existing note.",
)
async def update_note(
    note_id: str = Path(...),
    note_in: NoteUpdate = Body(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Updates an existing note. Only fields provided in the request body will be updated.
    Allows changing the title, content, or moving the note by changing its folder_path.

    - **project_id**: The UUID of the project.
    - **note_id**: The UUID of the note to update.
    - **note_in**: The note data fields to update (title, content, folder_path).
    """
    logger.info(f"API: Received request to update note {note_id} in project {project_id}")
    # Check if at least one field is provided for update
    if note_in.model_dump(exclude_unset=True) == {}:
         raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields provided for update.",
        )
    try:
        # Delegate update to the service layer
        updated_note = note_service.update(project_id=project_id, note_id=note_id, note_in=note_in)
        logger.info(f"API: Successfully updated note {note_id} in project {project_id}")
        return updated_note
    except HTTPException as http_exc:
        if http_exc.status_code == status.HTTP_404_NOT_FOUND:
            logger.warning(f"API: Note {note_id} not found for update in project {project_id}.")
        else:
            logger.warning(f"API: HTTPException during note update for {note_id} in project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"API: Unexpected error updating note {note_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error updating note: {e}"
        )


@router.delete(
    "/{note_id}",
    response_model=Message,
    status_code=status.HTTP_200_OK, # Use 200 OK with message body
    summary="Delete Note",
    description="Deletes a specific note (file and metadata).",
)
async def delete_note(
    note_id: str = Path(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Deletes a specific note by its ID.

    - **project_id**: The UUID of the project.
    - **note_id**: The UUID of the note to delete.
    """
    logger.info(f"API: Received request to delete note {note_id} in project {project_id}")
    try:
        # Delegate deletion to the service layer
        note_service.delete(project_id=project_id, note_id=note_id)
        logger.info(f"API: Successfully deleted note {note_id} in project {project_id}")
        return Message(message=f"Note {note_id} deleted successfully")
    except HTTPException as http_exc:
        if http_exc.status_code == status.HTTP_404_NOT_FOUND:
            logger.warning(f"API: Note {note_id} not found for deletion in project {project_id}.")
        else:
            logger.warning(f"API: HTTPException during note deletion for {note_id} in project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        logger.error(f"API: Unexpected error deleting note {note_id} in project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal error deleting note: {e}"
        )