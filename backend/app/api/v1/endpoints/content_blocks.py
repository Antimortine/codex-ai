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
from app.models.content_block import ContentBlockRead, ContentBlockUpdate

router = APIRouter()

# --- Plan ---
@router.get("/plan", response_model=ContentBlockRead)
async def get_plan(project_id: str = Path(...)):
    """ Get the project plan content. """
    # TODO: Call file_service.read_content(project_id, "plan.md")
    raise NotImplementedError("get_plan not implemented")

@router.put("/plan", response_model=ContentBlockRead)
async def update_plan(project_id: str = Path(...), content_in: ContentBlockUpdate = Body(...)):
    """ Update the project plan content. """
    # TODO: Call file_service.write_content(project_id, "plan.md", content_in.content)
    raise NotImplementedError("update_plan not implemented")

# --- Synopsis ---
@router.get("/synopsis", response_model=ContentBlockRead)
async def get_synopsis(project_id: str = Path(...)):
    """ Get the project synopsis content. """
    # TODO: Call file_service.read_content(project_id, "synopsis.md")
    raise NotImplementedError("get_synopsis not implemented")

@router.put("/synopsis", response_model=ContentBlockRead)
async def update_synopsis(project_id: str = Path(...), content_in: ContentBlockUpdate = Body(...)):
    """ Update the project synopsis content. """
    # TODO: Call file_service.write_content(project_id, "synopsis.md", content_in.content)
    raise NotImplementedError("update_synopsis not implemented")

# --- World ---
@router.get("/world", response_model=ContentBlockRead)
async def get_world_info(project_id: str = Path(...)):
    """ Get the worldbuilding info content. """
    # TODO: Call file_service.read_content(project_id, "world.md")
    raise NotImplementedError("get_world_info not implemented")

@router.put("/world", response_model=ContentBlockRead)
async def update_world_info(project_id: str = Path(...), content_in: ContentBlockUpdate = Body(...)):
    """ Update the worldbuilding info content. """
    # TODO: Call file_service.write_content(project_id, "world.md", content_in.content)
    raise NotImplementedError("update_world_info not implemented")