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
    order: int = Field(..., ge=0, description="Order of the chapter within the project")
    # project_id will be a path parameter, not in the request body usually

# Properties required when updating a chapter
class ChapterUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    order: Optional[int] = Field(None, ge=0)

# Properties returned when reading a chapter
class ChapterRead(IDModel, ChapterCreate):
    project_id: str = Field(..., description="ID of the parent project")
    # Inherits id, title, order
    pass

# Wrapper for list response
class ChapterList(BaseModel):
    chapters: list[ChapterRead] = []