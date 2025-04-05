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

from pydantic import BaseModel, Field
from typing import Optional
from .common import IDModel

# Properties required when creating a project
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the writing project")

# Properties required when updating a project (all optional)
class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, description="New name for the project")

# Properties returned when reading a project (includes ID)
class ProjectRead(IDModel, ProjectCreate):
    # Inherits id from IDModel and name from ProjectCreate
    # Add other fields if needed, e.g., created_at, updated_at
    pass

# Wrapper for list response
class ProjectList(BaseModel):
    projects: list[ProjectRead] = []