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
from app.models.ai import ChatHistoryRead, ChatHistoryWrite, ChatHistoryEntry
# Import the specific service instances we need
from app.services.file_service import file_service
# Import the project existence dependency
from app.api.v1.endpoints.content_blocks import get_project_dependency
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get(
    "/chat_history",
    response_model=ChatHistoryRead,
    summary="Get Chat History",
    description="Retrieves the saved chat history for the specified project."
)
async def get_chat_history(project_id: str = Depends(get_project_dependency)):
    """
    Retrieves the chat history for a project.

    - **project_id**: The UUID of the project.
    """
    logger.info(f"Received request to get chat history for project {project_id}")
    try:
        history_list = file_service.read_chat_history(project_id)
        # Validate data conforms to ChatHistoryEntry model? Pydantic handles response validation.
        return ChatHistoryRead(history=history_list)
    except Exception as e:
        logger.error(f"Error getting chat history for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error getting chat history: {e}")


@router.put(
    "/chat_history",
    response_model=ChatHistoryRead, # Return the saved history
    status_code=status.HTTP_200_OK,
    summary="Update Chat History",
    description="Overwrites the entire chat history for the specified project."
)
async def update_chat_history(
    history_in: ChatHistoryWrite = Body(...),
    project_id: str = Depends(get_project_dependency)
):
    """
    Updates (replaces) the chat history for a project.

    - **project_id**: The UUID of the project.
    - **history_in**: The complete chat history list to save.
    """
    logger.info(f"Received request to update chat history for project {project_id} with {len(history_in.history)} entries.")
    try:
        # Convert Pydantic models back to dicts for JSON serialization if needed by file_service
        # (Our current file_service handles dicts directly via json.dumps)
        history_to_write = [entry.model_dump() for entry in history_in.history]
        file_service.write_chat_history(project_id, history_to_write)
        logger.info(f"Successfully updated chat history for project {project_id}")
        # Return the data that was just saved
        return ChatHistoryRead(history=history_in.history)
    except Exception as e:
        logger.error(f"Error updating chat history for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error updating chat history: {e}")