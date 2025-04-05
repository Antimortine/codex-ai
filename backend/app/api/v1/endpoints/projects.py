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

from fastapi import APIRouter, HTTPException, status, Body
from typing import List
from app.models.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList
from app.models.common import Message # For delete response

router = APIRouter()

# Placeholder for actual service logic
async def get_project_service(): # Replace with actual dependency injection later
    pass

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project(project_in: ProjectCreate = Body(...)):
    """ Create a new writing project. """
    # TODO: Call project_service.create(project_in)
    raise NotImplementedError("create_project not implemented")

@router.get("/", response_model=ProjectList)
async def list_projects():
    """ Retrieve a list of all projects. """
    # TODO: Call project_service.get_all()
    raise NotImplementedError("list_projects not implemented")

@router.get("/{project_id}", response_model=ProjectRead)
async def get_project(project_id: str):
    """ Get details of a specific project by its ID. """
    # TODO: Call project_service.get_by_id(project_id) -> Handle not found
    raise NotImplementedError("get_project not implemented")

@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project(project_id: str, project_in: ProjectUpdate = Body(...)):
    """ Update details of an existing project. """
    # TODO: Call project_service.update(project_id, project_in) -> Handle not found
    raise NotImplementedError("update_project not implemented")

@router.delete("/{project_id}", response_model=Message)
async def delete_project(project_id: str):
    """ Delete a project and all its associated data. """
    # TODO: Call project_service.delete(project_id) -> Handle not found
    # Return {"message": f"Project {project_id} deleted successfully"}
    raise NotImplementedError("delete_project not implemented")