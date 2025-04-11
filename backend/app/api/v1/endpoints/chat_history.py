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

from fastapi import APIRouter, HTTPException, status, Body, Path, Depends
from typing import List
# --- MODIFIED: Import session models ---
from app.models.ai import (
    ChatHistoryRead, ChatHistoryWrite, ChatHistoryEntry,
    ChatSessionCreate, ChatSessionRead, ChatSessionList, ChatSessionUpdate
)
from app.models.common import Message, generate_uuid
# --- END MODIFIED ---
from app.services.file_service import file_service
from app.api.v1.endpoints.content_blocks import get_project_dependency
import logging

# --- MODIFIED: Router prefix and tags ---
router = APIRouter()
logger = logging.getLogger(__name__)

# --- Session Management Endpoints ---

@router.post(
    "/chat_sessions",
    response_model=ChatSessionRead,
    status_code=status.HTTP_201_CREATED,
    tags=["Chat Sessions"],
    summary="Create Chat Session",
    description="Creates a new, empty chat session for the project."
)
async def create_chat_session(
    session_in: ChatSessionCreate = Body(...),
    project_id: str = Depends(get_project_dependency)
):
    """
    Creates a new chat session metadata entry.

    - **project_id**: The UUID of the project.
    - **session_in**: Contains the initial name for the session.
    """
    logger.info(f"Received request to create chat session '{session_in.name}' for project {project_id}")
    try:
        session_id = generate_uuid()
        # Add metadata to project_meta.json
        file_service.add_chat_session_metadata(project_id, session_id, session_in.name)
        # Initialize history file if it doesn't exist (write_chat_session_history does this implicitly)
        file_service.write_chat_session_history(project_id, session_id, [])
        logger.info(f"Created chat session {session_id} ('{session_in.name}') for project {project_id}")
        return ChatSessionRead(id=session_id, name=session_in.name, project_id=project_id)
    except Exception as e:
        logger.error(f"Error creating chat session for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error creating chat session: {e}")

@router.get(
    "/chat_sessions",
    response_model=ChatSessionList,
    tags=["Chat Sessions"],
    summary="List Chat Sessions",
    description="Retrieves metadata (ID and name) for all chat sessions in the project."
)
async def list_chat_sessions(project_id: str = Depends(get_project_dependency)):
    """
    Lists all chat sessions for a project.

    - **project_id**: The UUID of the project.
    """
    logger.info(f"Received request to list chat sessions for project {project_id}")
    try:
        sessions_metadata = file_service.get_chat_sessions_metadata(project_id)
        session_list = [
            ChatSessionRead(id=session_id, name=data.get("name", f"Session {session_id}"), project_id=project_id)
            for session_id, data in sessions_metadata.items()
        ]
        # Optionally sort sessions, e.g., by name
        session_list.sort(key=lambda s: s.name)
        return ChatSessionList(sessions=session_list)
    except Exception as e:
        logger.error(f"Error listing chat sessions for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error listing chat sessions: {e}")

@router.patch(
    "/chat_sessions/{session_id}",
    response_model=ChatSessionRead,
    tags=["Chat Sessions"],
    summary="Rename Chat Session",
    description="Updates the name of a specific chat session."
)
async def rename_chat_session(
    session_id: str = Path(...),
    session_update: ChatSessionUpdate = Body(...),
    project_id: str = Depends(get_project_dependency)
):
    """
    Renames a chat session.

    - **project_id**: The UUID of the project.
    - **session_id**: The UUID of the chat session to rename.
    - **session_update**: Contains the new name for the session.
    """
    if not session_update.name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New session name cannot be empty.")

    logger.info(f"Received request to rename chat session {session_id} to '{session_update.name}' for project {project_id}")
    try:
        # Check if session exists first
        sessions_metadata = file_service.get_chat_sessions_metadata(project_id)
        if session_id not in sessions_metadata:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat session {session_id} not found.")

        file_service.update_chat_session_metadata(project_id, session_id, session_update.name)
        logger.info(f"Renamed chat session {session_id} to '{session_update.name}' for project {project_id}")
        return ChatSessionRead(id=session_id, name=session_update.name, project_id=project_id)
    except HTTPException as e:
        raise e # Re-raise known errors
    except Exception as e:
        logger.error(f"Error renaming chat session {session_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error renaming chat session: {e}")

@router.delete(
    "/chat_sessions/{session_id}",
    response_model=Message,
    tags=["Chat Sessions"],
    summary="Delete Chat Session",
    description="Deletes a specific chat session, including its history."
)
async def delete_chat_session(
    session_id: str = Path(...),
    project_id: str = Depends(get_project_dependency)
):
    """
    Deletes a chat session and its history.

    - **project_id**: The UUID of the project.
    - **session_id**: The UUID of the chat session to delete.
    """
    logger.info(f"Received request to delete chat session {session_id} for project {project_id}")
    try:
        # Check if session exists first
        sessions_metadata = file_service.get_chat_sessions_metadata(project_id)
        if session_id not in sessions_metadata:
            # Check if history exists anyway (consistency check)
            history = file_service.read_chat_session_history(project_id, session_id)
            if not history:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chat session {session_id} not found.")
            else:
                 logger.warning(f"Deleting chat session {session_id} history which was missing from metadata.")

        # Delete history first, then metadata
        file_service.delete_chat_session_history(project_id, session_id)
        file_service.delete_chat_session_metadata(project_id, session_id) # Handles non-existence gracefully

        logger.info(f"Deleted chat session {session_id} for project {project_id}")
        return Message(message=f"Chat session {session_id} deleted successfully.")
    except HTTPException as e:
        raise e # Re-raise known errors
    except Exception as e:
        logger.error(f"Error deleting chat session {session_id} for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error deleting chat session: {e}")


# --- History Management Endpoints (Modified) ---

@router.get(
    "/chat_history/{session_id}", # Use session_id in path
    response_model=ChatHistoryRead,
    tags=["Chat History"],
    summary="Get Chat History for Session",
    description="Retrieves the saved chat history for a specific session within the project."
)
async def get_chat_history(
    session_id: str = Path(...),
    project_id: str = Depends(get_project_dependency)
):
    """
    Retrieves the chat history for a specific session.

    - **project_id**: The UUID of the project.
    - **session_id**: The UUID of the chat session.
    """
    logger.info(f"Received request to get chat history for session {session_id} in project {project_id}")
    try:
        # Check if session metadata exists (optional, but good practice)
        sessions_metadata = file_service.get_chat_sessions_metadata(project_id)
        if session_id not in sessions_metadata:
             logger.warning(f"Attempting to get history for session {session_id} which has no metadata in project {project_id}")
             # Allow reading history even if metadata is missing, might be inconsistent state

        history_list = file_service.read_chat_session_history(project_id, session_id)
        # If session didn't exist in file, read_chat_session_history returns [], which is fine.
        return ChatHistoryRead(history=history_list)
    except Exception as e:
        logger.error(f"Error getting chat history for session {session_id}, project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error getting chat history: {e}")


@router.put(
    "/chat_history/{session_id}", # Use session_id in path
    response_model=ChatHistoryRead,
    status_code=status.HTTP_200_OK,
    tags=["Chat History"],
    summary="Update Chat History for Session",
    description="Overwrites the entire chat history for a specific session within the project."
)
async def update_chat_history(
    session_id: str = Path(...),
    history_in: ChatHistoryWrite = Body(...),
    project_id: str = Depends(get_project_dependency)
):
    """
    Updates (replaces) the chat history for a specific session.

    - **project_id**: The UUID of the project.
    - **session_id**: The UUID of the chat session.
    - **history_in**: The complete chat history list for this session.
    """
    logger.info(f"Received request to update chat history for session {session_id}, project {project_id} with {len(history_in.history)} entries.")
    try:
        # Check if session metadata exists (optional, but good practice)
        sessions_metadata = file_service.get_chat_sessions_metadata(project_id)
        if session_id not in sessions_metadata:
             logger.warning(f"Attempting to update history for session {session_id} which has no metadata in project {project_id}")
             # Allow updating history even if metadata is missing

        history_to_write = [entry.model_dump() for entry in history_in.history]
        file_service.write_chat_session_history(project_id, session_id, history_to_write)
        logger.info(f"Successfully updated chat history for session {session_id}, project {project_id}")
        # Return the data that was just saved
        return ChatHistoryRead(history=history_in.history)
    except Exception as e:
        logger.error(f"Error updating chat history for session {session_id}, project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error updating chat history: {e}")