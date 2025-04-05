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
from app.models.content_block import ContentBlockRead, ContentBlockUpdate
# Import the specific service instances we need
from app.services.file_service import file_service
from app.services.project_service import project_service

router = APIRouter()

# --- Helper Dependency ---
# Using FastAPI's dependency injection is cleaner for checking project existence
async def get_project_dependency(project_id: str = Path(...)) -> str:
    """
    Dependency that checks if the project exists and returns the project_id.
    Raises HTTPException 404 if not found.
    """
    try:
        project_service.get_by_id(project_id) # Call the service to check
        return project_id
    except HTTPException as e:
        if e.status_code == 404:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project {project_id} not found"
            ) from e
        # Re-raise other unexpected errors from the service layer
        raise e


# --- Plan ---
@router.get("/plan", response_model=ContentBlockRead)
async def get_plan(project_id: str = Depends(get_project_dependency)):
    """
    Get the project plan content for the specified project.
    """
    file_path = file_service._get_content_block_path(project_id, "plan.md")
    try:
        content = file_service.read_text_file(file_path)
    except HTTPException as e:
        # Handle case where file might not exist even if project dir does (e.g., first access)
        if e.status_code == 404:
             # Return empty content if the specific file doesn't exist yet
             content = ""
        else:
             raise e # Re-raise other file read errors
    return ContentBlockRead(project_id=project_id, content=content)

@router.put("/plan", response_model=ContentBlockRead)
async def update_plan(content_in: ContentBlockUpdate = Body(...), project_id: str = Depends(get_project_dependency)):
    """
    Update (or create) the project plan content for the specified project.
    """
    file_path = file_service._get_content_block_path(project_id, "plan.md")
    # write_text_file handles creating parent dirs if necessary
    file_service.write_text_file(file_path, content_in.content)
    # Return the updated content along with the project_id
    return ContentBlockRead(project_id=project_id, content=content_in.content)


# --- Synopsis ---
@router.get("/synopsis", response_model=ContentBlockRead)
async def get_synopsis(project_id: str = Depends(get_project_dependency)):
    """
    Get the project synopsis content for the specified project.
    """
    file_path = file_service._get_content_block_path(project_id, "synopsis.md")
    try:
        content = file_service.read_text_file(file_path)
    except HTTPException as e:
        if e.status_code == 404:
             content = ""
        else:
             raise e
    return ContentBlockRead(project_id=project_id, content=content)

@router.put("/synopsis", response_model=ContentBlockRead)
async def update_synopsis(content_in: ContentBlockUpdate = Body(...), project_id: str = Depends(get_project_dependency)):
    """
    Update (or create) the project synopsis content for the specified project.
    """
    file_path = file_service._get_content_block_path(project_id, "synopsis.md")
    file_service.write_text_file(file_path, content_in.content)
    return ContentBlockRead(project_id=project_id, content=content_in.content)


# --- World ---
@router.get("/world", response_model=ContentBlockRead)
async def get_world_info(project_id: str = Depends(get_project_dependency)):
    """
    Get the worldbuilding info content for the specified project.
    """
    file_path = file_service._get_content_block_path(project_id, "world.md")
    try:
        content = file_service.read_text_file(file_path)
    except HTTPException as e:
        if e.status_code == 404:
             content = ""
        else:
             raise e
    return ContentBlockRead(project_id=project_id, content=content)

@router.put("/world", response_model=ContentBlockRead)
async def update_world_info(content_in: ContentBlockUpdate = Body(...), project_id: str = Depends(get_project_dependency)):
    """
    Update (or create) the worldbuilding info content for the specified project.
    """
    file_path = file_service._get_content_block_path(project_id, "world.md")
    file_service.write_text_file(file_path, content_in.content)
    return ContentBlockRead(project_id=project_id, content=content_in.content)