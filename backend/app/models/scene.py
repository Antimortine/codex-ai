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

# --- REMOVED: Problematic self-import ---
# from app.models.scene import SceneCreate, SceneUpdate, SceneRead, SceneList
# --- END REMOVED ---

# Properties required when creating a scene
class SceneCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Title or brief description of the scene")
    # --- MODIFIED: Make order optional ---
    order: Optional[int] = Field(None, ge=1, description="Optional: 1-based order. If None, backend calculates next available.")
    # --- END MODIFIED ---
    content: str = Field("", description="Markdown content of the scene") # Default to empty
    # project_id and chapter_id will be path parameters

# Properties required when updating a scene
class SceneUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    order: Optional[int] = Field(None, ge=1)
    content: Optional[str] = None # Allow updating content

# Properties returned when reading a scene
class SceneRead(IDModel): # Removed inheritance from SceneCreate temporarily
    project_id: str = Field(..., description="ID of the parent project")
    chapter_id: str = Field(..., description="ID of the parent chapter")
    # Explicitly define fields matching SceneCreate + ID
    id: str = Field(...)
    title: str = Field(...)
    order: int = Field(...) # Order will always be set when reading
    content: str = Field(...)
    pass

# Wrapper for list response
class SceneList(BaseModel):
    scenes: list[SceneRead] = []