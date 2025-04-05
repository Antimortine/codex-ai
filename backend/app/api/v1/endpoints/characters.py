# Copyright 2025 Antimortine (antimortine@gmail.com)
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
from app.models.character import CharacterCreate, CharacterUpdate, CharacterRead, CharacterList
from app.models.common import Message
# Import the specific service instance
from app.services.character_service import character_service
# Import the project existence dependency
from app.api.v1.endpoints.content_blocks import get_project_dependency

router = APIRouter()

# --- Endpoint Implementations ---

@router.post(
    "/",
    response_model=CharacterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Character",
    description="Creates a new character profile within the specified project."
)
async def create_character(
    character_in: CharacterCreate = Body(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Creates a new character profile for a given project.

    - **project_id**: The UUID of the parent project (in path).
    - **character_in**: CharacterCreate model containing name and description.
    """
    # Service layer handles potential name conflicts (optional) or other creation errors
    return character_service.create(project_id=project_id, character_in=character_in)


@router.get(
    "/",
    response_model=CharacterList,
    summary="List Characters",
    description="Retrieves a list of all character profiles for the specified project."
)
async def list_characters(project_id: str = Depends(get_project_dependency)):
    """
    Lists all characters for a specific project.

    - **project_id**: The UUID of the parent project (in path).
    """
    return character_service.get_all_for_project(project_id=project_id)


@router.get(
    "/{character_id}",
    response_model=CharacterRead,
    summary="Get Character",
    description="Retrieves details and description of a specific character by its ID."
)
async def get_character(
    character_id: str = Path(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Gets details and description of a specific character.
    Raises 404 if the character or project is not found.

    - **project_id**: The UUID of the parent project (in path).
    - **character_id**: The UUID of the character to retrieve (in path).
    """
    # Service layer handles 404 for the character
    return character_service.get_by_id(project_id=project_id, character_id=character_id)


@router.patch(
    "/{character_id}",
    response_model=CharacterRead,
    summary="Update Character",
    description="Updates the name or description of an existing character profile."
)
async def update_character(
    character_id: str = Path(...),
    character_in: CharacterUpdate = Body(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Updates details of an existing character.
    Raises 404 if the character or project is not found.

    - **project_id**: The UUID of the parent project (in path).
    - **character_id**: The UUID of the character to update (in path).
    - **character_in**: CharacterUpdate model containing fields to update.
    """
    # Service layer handles 404
    return character_service.update(project_id=project_id, character_id=character_id, character_in=character_in)


@router.delete(
    "/{character_id}",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Delete Character",
    description="Deletes a character profile. This action is irreversible."
)
async def delete_character(
    character_id: str = Path(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Deletes a specific character profile.
    Raises 404 if the character or project is not found.

    - **project_id**: The UUID of the parent project (in path).
    - **character_id**: The UUID of the character to delete (in path).
    """
    # Service layer handles 404
    character_service.delete(project_id=project_id, character_id=character_id)
    return Message(message=f"Character {character_id} deleted successfully")