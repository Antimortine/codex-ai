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
from app.models.note import NoteCreate, NoteUpdate, NoteRead, NoteList, NoteReadBasic
from app.models.common import Message
# Import the service instance
from app.services.note_service import note_service
# Import project dependency check
from app.api.v1.endpoints.content_blocks import get_project_dependency
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Endpoint Definitions ---

@router.post(
    "/",
    response_model=NoteRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Note",
    description="Creates a new note within the project.",
)
async def create_note(
    note_in: NoteCreate = Body(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Creates a new note associated with the project.

    - **project_id**: The UUID of the project.
    - **note_in**: The note data (title, optional initial content).
    """
    logger.info(f"API: Received request to create note in project {project_id} with title '{note_in.title}'")
    try:
        # Delegate creation to the service layer
        created_note = note_service.create(project_id=project_id, note_in=note_in)
        logger.info(f"API: Successfully created note {created_note.id} in project {project_id}")
        return created_note
    except HTTPException as http_exc:
        # Re-raise known HTTP exceptions from the service layer (e.g., project not found)
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
    description="Retrieves a list of all notes for the project, sorted by last modified.",
)
async def list_notes(
    project_id: str = Depends(get_project_dependency),
):
    """
    Retrieves all notes for a specific project, sorted by last modification date (newest first).

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
    description="Retrieves details and content of a specific note.",
)
async def get_note(
    note_id: str = Path(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Retrieves a specific note by its ID.

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
    description="Updates the title or content of an existing note.",
)
async def update_note(
    note_id: str = Path(...),
    note_in: NoteUpdate = Body(...),
    project_id: str = Depends(get_project_dependency),
):
    """
    Updates an existing note. Only fields provided in the request body will be updated.

    - **project_id**: The UUID of the project.
    - **note_id**: The UUID of the note to update.
    - **note_in**: The note data fields to update (title, content).
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
    description="Deletes a specific note.",
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