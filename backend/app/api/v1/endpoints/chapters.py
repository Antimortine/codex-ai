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
from app.models.chapter import ChapterCreate, ChapterUpdate, ChapterRead, ChapterList
from app.models.common import Message

router = APIRouter()

@router.post("/", response_model=ChapterRead, status_code=status.HTTP_201_CREATED)
async def create_chapter(project_id: str = Path(...), chapter_in: ChapterCreate = Body(...)):
    """ Create a new chapter within a project. """
    # TODO: Call chapter_service.create(project_id, chapter_in) -> Check project exists
    raise NotImplementedError("create_chapter not implemented")

@router.get("/", response_model=ChapterList)
async def list_chapters(project_id: str = Path(...)):
    """ List all chapters within a specific project. """
    # TODO: Call chapter_service.get_all_for_project(project_id)
    raise NotImplementedError("list_chapters not implemented")

@router.get("/{chapter_id}", response_model=ChapterRead)
async def get_chapter(project_id: str = Path(...), chapter_id: str = Path(...)):
    """ Get details of a specific chapter. """
    # TODO: Call chapter_service.get_by_id(project_id, chapter_id) -> Handle not found
    raise NotImplementedError("get_chapter not implemented")

@router.patch("/{chapter_id}", response_model=ChapterRead)
async def update_chapter(project_id: str = Path(...), chapter_id: str = Path(...), chapter_in: ChapterUpdate = Body(...)):
    """ Update details of an existing chapter. """
    # TODO: Call chapter_service.update(project_id, chapter_id, chapter_in) -> Handle not found
    raise NotImplementedError("update_chapter not implemented")

@router.delete("/{chapter_id}", response_model=Message)
async def delete_chapter(project_id: str = Path(...), chapter_id: str = Path(...)):
    """ Delete a chapter and all its scenes. """
    # TODO: Call chapter_service.delete(project_id, chapter_id) -> Handle not found
    raise NotImplementedError("delete_chapter not implemented")