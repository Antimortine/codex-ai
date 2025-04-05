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

from fastapi import APIRouter, HTTPException, status, Body, Depends
from typing import List
from app.models.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList
from app.models.common import Message
# Import the specific service instance
from app.services.project_service import project_service

router = APIRouter()

# --- Endpoint Implementations ---

@router.post(
    "/",
    response_model=ProjectRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create Project",
    description="Creates a new writing project directory structure and metadata."
)
async def create_project(project_in: ProjectCreate = Body(...)):
    """
    Creates a new writing project.

    - **name**: The name of the project (required).
    """
    # The service layer handles potential ID collisions and file system errors
    return project_service.create(project_in=project_in)


@router.get(
    "/",
    response_model=ProjectList,
    summary="List Projects",
    description="Retrieves a list of all available writing projects."
)
async def list_projects():
    """
    Retrieves a list of all projects, reading their basic metadata.
    """
    return project_service.get_all()


@router.get(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Get Project",
    description="Retrieves details of a specific project by its ID."
)
async def get_project(project_id: str):
    """
    Gets details of a specific project.
    Raises 404 if the project is not found.

    - **project_id**: The UUID of the project to retrieve.
    """
    # Service layer handles the 404 HTTPException
    return project_service.get_by_id(project_id=project_id)


@router.patch(
    "/{project_id}",
    response_model=ProjectRead,
    summary="Update Project",
    description="Updates the details (e.g., name) of an existing project."
)
async def update_project(project_id: str, project_in: ProjectUpdate = Body(...)):
    """
    Updates details of an existing project. Currently only supports updating the name.
    Raises 404 if the project is not found.

    - **project_id**: The UUID of the project to update.
    - **project_in**: ProjectUpdate model containing fields to update (only name currently).
    """
    # Service layer handles the 404 HTTPException
    return project_service.update(project_id=project_id, project_in=project_in)


@router.delete(
    "/{project_id}",
    response_model=Message,
    status_code=status.HTTP_200_OK, # Or 204 No Content if you prefer not to return a body
    summary="Delete Project",
    description="Deletes a project and all its associated data (chapters, scenes, etc.). This action is irreversible."
)
async def delete_project(project_id: str):
    """
    Deletes a specific project.
    Raises 404 if the project is not found.

    - **project_id**: The UUID of the project to delete.
    """
    # Service layer handles the 404 HTTPException
    project_service.delete(project_id=project_id)
    return Message(message=f"Project {project_id} deleted successfully")