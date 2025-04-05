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

# Properties required when creating a character
class CharacterCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the character")
    description: str = Field("", description="Markdown description of the character")
    # project_id will be a path parameter

# Properties required when updating a character
class CharacterUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1)
    description: Optional[str] = None

# Properties returned when reading a character
class CharacterRead(IDModel, CharacterCreate):
    project_id: str = Field(..., description="ID of the parent project")
    # Inherits id, name, description
    pass

# Wrapper for list response
class CharacterList(BaseModel):
    characters: list[CharacterRead] = []