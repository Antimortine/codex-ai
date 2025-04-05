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
from app.models.scene import SceneCreate, SceneUpdate, SceneRead, SceneList
from app.models.common import Message
# Import the specific service instance
from app.services.scene_service import scene_service
# Import or define dependency to check chapter existence
from app.services.chapter_service import chapter_service # Need chapter service to check

router = APIRouter()

# --- Helper Dependency for Chapter Existence ---
# Could be moved to a shared deps.py later
async def get_chapter_dependency(
    project_id: str = Path(...),
    chapter_id: str = Path(...)
) -> tuple[str, str]:
    """Dependency that checks if project and chapter exist."""
    try:
        # Check chapter existence (which implicitly checks project existence via its own logic)
        chapter_service.get_by_id(project_id=project_id, chapter_id=chapter_id)
        return project_id, chapter_id
    except HTTPException as e:
         # Re-raise chapter/project not found errors cleanly
         if e.status_code == 404:
             detail = e.detail # Preserve original detail if possible
             if "Project" in detail:
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
             else:
                 # Assume chapter not found if project was okay
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Chapter {chapter_id} not found in project {project_id}")
         raise e # Re-raise other errors

# --- Endpoint Implementations ---

@router.post(
    "/",
    response_model=SceneRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Scene",
    description="Creates a new scene within the specified chapter."
)
async def create_scene(
    scene_in: SceneCreate = Body(...),
    ids: tuple[str, str] = Depends(get_chapter_dependency) # Ensures project & chapter exist
):
    """
    Creates a new scene for a given chapter.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the parent chapter (in path).
    - **scene_in**: SceneCreate model containing title, order, and initial content.
    """
    project_id, chapter_id = ids
    # Service layer handles potential order conflicts or other creation errors
    return scene_service.create(project_id=project_id, chapter_id=chapter_id, scene_in=scene_in)


@router.get(
    "/",
    response_model=SceneList,
    summary="List Scenes",
    description="Retrieves a list of all scenes within the specified chapter, sorted by order."
)
async def list_scenes(ids: tuple[str, str] = Depends(get_chapter_dependency)):
    """
    Lists all scenes for a specific chapter.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the parent chapter (in path).
    """
    project_id, chapter_id = ids
    return scene_service.get_all_for_chapter(project_id=project_id, chapter_id=chapter_id)


@router.get(
    "/{scene_id}",
    response_model=SceneRead,
    summary="Get Scene",
    description="Retrieves details and content of a specific scene by its ID."
)
async def get_scene(
    scene_id: str = Path(...),
    ids: tuple[str, str] = Depends(get_chapter_dependency) # Ensures project & chapter exist
):
    """
    Gets details and content of a specific scene.
    Raises 404 if the scene, chapter, or project is not found.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the parent chapter (in path).
    - **scene_id**: The UUID of the scene to retrieve (in path).
    """
    project_id, chapter_id = ids
    # Service layer handles 404 for the scene
    return scene_service.get_by_id(project_id=project_id, chapter_id=chapter_id, scene_id=scene_id)


@router.patch(
    "/{scene_id}",
    response_model=SceneRead,
    summary="Update Scene",
    description="Updates the details (title, order) or content of an existing scene."
)
async def update_scene(
    scene_id: str = Path(...),
    scene_in: SceneUpdate = Body(...),
    ids: tuple[str, str] = Depends(get_chapter_dependency) # Ensures project & chapter exist
):
    """
    Updates details or content of an existing scene.
    Raises 404 if the scene, chapter, or project is not found.
    Raises 409 if the new order conflicts with another scene.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the parent chapter (in path).
    - **scene_id**: The UUID of the scene to update (in path).
    - **scene_in**: SceneUpdate model containing fields to update.
    """
    project_id, chapter_id = ids
    # Service layer handles 404 and potential order conflicts (409)
    return scene_service.update(project_id=project_id, chapter_id=chapter_id, scene_id=scene_id, scene_in=scene_in)


@router.delete(
    "/{scene_id}",
    response_model=Message,
    status_code=status.HTTP_200_OK,
    summary="Delete Scene",
    description="Deletes a scene. This action is irreversible."
)
async def delete_scene(
    scene_id: str = Path(...),
    ids: tuple[str, str] = Depends(get_chapter_dependency) # Ensures project & chapter exist
):
    """
    Deletes a specific scene.
    Raises 404 if the scene, chapter, or project is not found.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the parent chapter (in path).
    - **scene_id**: The UUID of the scene to delete (in path).
    """
    project_id, chapter_id = ids
    # Service layer handles 404
    scene_service.delete(project_id=project_id, chapter_id=chapter_id, scene_id=scene_id)
    return Message(message=f"Scene {scene_id} deleted successfully")