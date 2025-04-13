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
from typing import Optional, List
from .common import IDModel

# Base properties for a note
class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the note")

# Properties required when creating a note
class NoteCreate(NoteBase):
    content: str = Field("", description="Optional Markdown content of the note upon creation")

# Properties required when updating a note (all optional)
class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="New title for the note")
    content: Optional[str] = Field(None, description="New Markdown content for the note")

# Properties returned when reading a full note (including content)
class NoteRead(IDModel, NoteBase):
    project_id: str = Field(..., description="ID of the parent project")
    content: str = Field(..., description="Markdown content of the note")
    last_modified: Optional[float] = Field(None, description="Unix timestamp of the last modification time of the note file")
    # Inherits id, title

# Properties returned when listing notes (excluding content)
class NoteReadBasic(IDModel, NoteBase):
    project_id: str = Field(..., description="ID of the parent project")
    last_modified: Optional[float] = Field(None, description="Unix timestamp of the last modification time of the note file")
    # Inherits id, title

# Wrapper for list response
class NoteList(BaseModel):
    notes: List[NoteReadBasic] = Field([], description="List of notes for the project")