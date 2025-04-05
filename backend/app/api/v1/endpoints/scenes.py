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
from app.models.scene import SceneCreate, SceneUpdate, SceneRead, SceneList
from app.models.common import Message

router = APIRouter()

@router.post("/", response_model=SceneRead, status_code=status.HTTP_201_CREATED)
async def create_scene(project_id: str = Path(...), chapter_id: str = Path(...), scene_in: SceneCreate = Body(...)):
    """ Create a new scene within a chapter. """
    # TODO: Call scene_service.create(project_id, chapter_id, scene_in) -> Check chapter exists
    raise NotImplementedError("create_scene not implemented")

@router.get("/", response_model=SceneList)
async def list_scenes(project_id: str = Path(...), chapter_id: str = Path(...)):
    """ List all scenes within a specific chapter. """
    # TODO: Call scene_service.get_all_for_chapter(project_id, chapter_id)
    raise NotImplementedError("list_scenes not implemented")

@router.get("/{scene_id}", response_model=SceneRead)
async def get_scene(project_id: str = Path(...), chapter_id: str = Path(...), scene_id: str = Path(...)):
    """ Get details and content of a specific scene. """
    # TODO: Call scene_service.get_by_id(project_id, chapter_id, scene_id) -> Handle not found
    raise NotImplementedError("get_scene not implemented")

@router.patch("/{scene_id}", response_model=SceneRead)
async def update_scene(project_id: str = Path(...), chapter_id: str = Path(...), scene_id: str = Path(...), scene_in: SceneUpdate = Body(...)):
    """ Update details or content of an existing scene. """
    # TODO: Call scene_service.update(project_id, chapter_id, scene_id, scene_in) -> Handle not found
    raise NotImplementedError("update_scene not implemented")

@router.delete("/{scene_id}", response_model=Message)
async def delete_scene(project_id: str = Path(...), chapter_id: str = Path(...), scene_id: str = Path(...)):
    """ Delete a scene. """
    # TODO: Call scene_service.delete(project_id, chapter_id, scene_id) -> Handle not found
    raise NotImplementedError("delete_scene not implemented")