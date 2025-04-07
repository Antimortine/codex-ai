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

from fastapi import APIRouter, HTTPException, status, Body, Depends
from typing import List
from app.models.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList
from app.models.common import Message
# Import the specific service instance
from app.services.project_service import project_service
import logging # Import logging

router = APIRouter()
logger = logging.getLogger(__name__) # Get logger for this module

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
    logger.info(f"Received request to create project with name: {project_in.name}")
    try:
        result = project_service.create(project_in=project_in)
        logger.info(f"Successfully created project {result.id}")
        return result
    except Exception as e:
        logger.error(f"Error creating project: {e}", exc_info=True)
        # Re-raise HTTPException or convert other exceptions
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error creating project: {e}")


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
    # --- ADDED LOGGING ---
    logger.info("Received request to list projects (GET /api/v1/projects/)")
    try:
        result = project_service.get_all()
        logger.info(f"Successfully retrieved {len(result.projects)} projects.")
        return result
    except Exception as e:
        logger.error(f"Error listing projects in endpoint: {e}", exc_info=True)
        # Ensure even unexpected errors return a proper HTTP response
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error listing projects: {e}")
    # --- END ADDED LOGGING ---


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
    logger.info(f"Received request to get project ID: {project_id}")
    # Service layer handles the 404 HTTPException
    try:
        result = project_service.get_by_id(project_id=project_id)
        logger.info(f"Successfully retrieved project {project_id}")
        return result
    except HTTPException as e:
        # Log and re-raise known HTTP exceptions (like 404)
        logger.warning(f"HTTPException getting project {project_id}: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error getting project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error getting project {project_id}: {e}")


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
    logger.info(f"Received request to update project ID: {project_id} with data: {project_in.model_dump(exclude_unset=True)}")
    # Service layer handles the 404 HTTPException
    try:
        result = project_service.update(project_id=project_id, project_in=project_in)
        logger.info(f"Successfully updated project {project_id}")
        return result
    except HTTPException as e:
        logger.warning(f"HTTPException updating project {project_id}: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error updating project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error updating project {project_id}: {e}")


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
    logger.info(f"Received request to delete project ID: {project_id}")
    # Service layer handles the 404 HTTPException
    try:
        project_service.delete(project_id=project_id)
        logger.info(f"Successfully deleted project {project_id}")
        return Message(message=f"Project {project_id} deleted successfully")
    except HTTPException as e:
        logger.warning(f"HTTPException deleting project {project_id}: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        logger.error(f"Unexpected error deleting project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Internal error deleting project {project_id}: {e}")