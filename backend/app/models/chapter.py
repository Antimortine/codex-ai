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

# Properties required when creating a chapter
class ChapterCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the chapter")
    order: int = Field(..., ge=1, description="1-based order of the chapter within the project")
    # project_id will be a path parameter, not in the request body usually

# Properties required when updating a chapter
class ChapterUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    order: Optional[int] = Field(None, ge=1)

# Properties returned when reading a chapter
# --- MODIFIED: Remove inheritance from ChapterCreate ---
class ChapterRead(IDModel):
# --- END MODIFIED ---
    project_id: str = Field(..., description="ID of the parent project")
    # Define fields explicitly for reading
    title: str = Field(...)
    # Apply validation for reading - order should always be >= 1 if data is consistent
    order: int = Field(..., ge=1)
    pass

# Wrapper for list response
class ChapterList(BaseModel):
    chapters: list[ChapterRead] = []