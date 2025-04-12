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
from app.models.chapter import ChapterCreate, ChapterUpdate, ChapterRead, ChapterList
# --- ADDED: Import ContentBlock models ---
from app.models.content_block import ContentBlockRead, ContentBlockUpdate
# --- END ADDED ---
from app.models.common import Message
# Import the specific service instance
from app.services.chapter_service import chapter_service
# --- ADDED: Import file_service ---
from app.services.file_service import file_service
# --- END ADDED ---
# Import the project existence dependency from content_blocks or define it here/in deps.py
from app.api.v1.endpoints.content_blocks import get_project_dependency
# --- ADDED: Import chapter dependency ---
from app.api.v1.endpoints.scenes import get_chapter_dependency
# --- END ADDED ---

router = APIRouter()

# --- Endpoint Implementations ---

@router.post(
    "/",
    response_model=ChapterRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Chapter",
    description="Creates a new chapter within the specified project."
)
async def create_chapter(
    chapter_in: ChapterCreate = Body(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Creates a new chapter for a given project.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_in**: ChapterCreate model containing title and order.
    """
    # Service layer handles potential order conflicts or other creation errors
    return chapter_service.create(project_id=project_id, chapter_in=chapter_in)


@router.get(
    "/",
    response_model=ChapterList,
    summary="List Chapters",
    description="Retrieves a list of all chapters within the specified project, sorted by order."
)
async def list_chapters(project_id: str = Depends(get_project_dependency)):
    """
    Lists all chapters for a specific project.

    - **project_id**: The UUID of the parent project (in path).
    """
    return chapter_service.get_all_for_project(project_id=project_id)


@router.get(
    "/{chapter_id}",
    response_model=ChapterRead,
    summary="Get Chapter",
    description="Retrieves details of a specific chapter by its ID."
)
async def get_chapter(
    chapter_id: str = Path(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Gets details of a specific chapter.
    Raises 404 if the chapter or project is not found.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the chapter to retrieve (in path).
    """
    # Service layer handles 404 for the chapter
    return chapter_service.get_by_id(project_id=project_id, chapter_id=chapter_id)


@router.patch(
    "/{chapter_id}",
    response_model=ChapterRead,
    summary="Update Chapter",
    description="Updates the details (title, order) of an existing chapter."
)
async def update_chapter(
    chapter_id: str = Path(...),
    chapter_in: ChapterUpdate = Body(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Updates details of an existing chapter.
    Raises 404 if the chapter or project is not found.
    Raises 409 if the new order conflicts with another chapter.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the chapter to update (in path).
    - **chapter_in**: ChapterUpdate model containing fields to update.
    """
    # Service layer handles 404 and potential order conflicts (409)
    return chapter_service.update(project_id=project_id, chapter_id=chapter_id, chapter_in=chapter_in)


@router.delete(
    "/{chapter_id}",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Delete Chapter",
    description="Deletes a chapter and all its scenes. This action is irreversible."
)
async def delete_chapter(
    chapter_id: str = Path(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Deletes a specific chapter.
    Raises 404 if the chapter or project is not found.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the chapter to delete (in path).
    """
    # Service layer handles 404
    chapter_service.delete(project_id=project_id, chapter_id=chapter_id)
    return Message(message=f"Chapter {chapter_id} deleted successfully")

# --- ADDED: Chapter Plan Endpoints ---
@router.get(
    "/{chapter_id}/plan",
    response_model=ContentBlockRead,
    tags=["Chapters", "Content Blocks"],
    summary="Get Chapter Plan",
    description="Retrieves the plan content for a specific chapter."
)
async def get_chapter_plan(ids: tuple[str, str] = Depends(get_chapter_dependency)):
    """
    Gets the plan.md content for a specific chapter.
    Returns empty content if the file doesn't exist.
    """
    project_id, chapter_id = ids
    content = file_service.read_chapter_plan_file(project_id, chapter_id)
    return ContentBlockRead(project_id=project_id, content=content or "")

@router.put(
    "/{chapter_id}/plan",
    response_model=ContentBlockRead,
    tags=["Chapters", "Content Blocks"],
    summary="Update Chapter Plan",
    description="Updates (or creates) the plan content for a specific chapter. Triggers indexing."
)
async def update_chapter_plan(
    content_in: ContentBlockUpdate = Body(...),
    ids: tuple[str, str] = Depends(get_chapter_dependency)
):
    """
    Updates the plan.md content for a specific chapter.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the parent chapter (in path).
    - **content_in**: ContentBlockUpdate model containing the new content.
    """
    project_id, chapter_id = ids
    try:
        file_service.write_chapter_plan_file(project_id, chapter_id, content_in.content)
    except HTTPException as e:
        raise e # Re-raise file/index errors
    return ContentBlockRead(project_id=project_id, content=content_in.content)
# --- END ADDED ---

# --- ADDED: Chapter Synopsis Endpoints ---
@router.get(
    "/{chapter_id}/synopsis",
    response_model=ContentBlockRead,
    tags=["Chapters", "Content Blocks"],
    summary="Get Chapter Synopsis",
    description="Retrieves the synopsis content for a specific chapter."
)
async def get_chapter_synopsis(ids: tuple[str, str] = Depends(get_chapter_dependency)):
    """
    Gets the synopsis.md content for a specific chapter.
    Returns empty content if the file doesn't exist.
    """
    project_id, chapter_id = ids
    content = file_service.read_chapter_synopsis_file(project_id, chapter_id)
    return ContentBlockRead(project_id=project_id, content=content or "")

@router.put(
    "/{chapter_id}/synopsis",
    response_model=ContentBlockRead,
    tags=["Chapters", "Content Blocks"],
    summary="Update Chapter Synopsis",
    description="Updates (or creates) the synopsis content for a specific chapter. Triggers indexing."
)
async def update_chapter_synopsis(
    content_in: ContentBlockUpdate = Body(...),
    ids: tuple[str, str] = Depends(get_chapter_dependency)
):
    """
    Updates the synopsis.md content for a specific chapter.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the parent chapter (in path).
    - **content_in**: ContentBlockUpdate model containing the new content.
    """
    project_id, chapter_id = ids
    try:
        file_service.write_chapter_synopsis_file(project_id, chapter_id, content_in.content)
    except HTTPException as e:
        raise e # Re-raise file/index errors
    return ContentBlockRead(project_id=project_id, content=content_in.content)
# --- END ADDED ---