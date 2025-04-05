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

from fastapi import APIRouter, HTTPException, status, Body, Path
from typing import List
from app.models.character import CharacterCreate, CharacterUpdate, CharacterRead, CharacterList
from app.models.common import Message

router = APIRouter()

@router.post("/", response_model=CharacterRead, status_code=status.HTTP_201_CREATED)
async def create_character(project_id: str = Path(...), character_in: CharacterCreate = Body(...)):
    """ Create a new character profile for a project. """
    # TODO: Call character_service.create(project_id, character_in) -> Check project exists
    raise NotImplementedError("create_character not implemented")

@router.get("/", response_model=CharacterList)
async def list_characters(project_id: str = Path(...)):
    """ List all characters for a specific project. """
    # TODO: Call character_service.get_all_for_project(project_id)
    raise NotImplementedError("list_characters not implemented")

@router.get("/{character_id}", response_model=CharacterRead)
async def get_character(project_id: str = Path(...), character_id: str = Path(...)):
    """ Get details of a specific character. """
    # TODO: Call character_service.get_by_id(project_id, character_id) -> Handle not found
    raise NotImplementedError("get_character not implemented")

@router.patch("/{character_id}", response_model=CharacterRead)
async def update_character(project_id: str = Path(...), character_id: str = Path(...), character_in: CharacterUpdate = Body(...)):
    """ Update details of an existing character. """
    # TODO: Call character_service.update(project_id, character_id, character_in) -> Handle not found
    raise NotImplementedError("update_character not implemented")

@router.delete("/{character_id}", response_model=Message)
async def delete_character(project_id: str = Path(...), character_id: str = Path(...)):
    """ Delete a character profile. """
    # TODO: Call character_service.delete(project_id, character_id) -> Handle not found
    raise NotImplementedError("delete_character not implemented")