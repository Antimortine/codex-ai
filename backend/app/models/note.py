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
from typing import Optional, List, Literal # Added Literal
from .common import IDModel

# Base properties for a note
class NoteBase(BaseModel):
    title: str = Field(..., min_length=1, description="Title of the note")

# Properties required when creating a note
class NoteCreate(NoteBase):
    content: str = Field("", description="Optional Markdown content of the note upon creation")
    folder_path: Optional[str] = Field("/", description="Virtual folder path for the note, e.g., '/Ideas/Chapter1' or '/' for root. Defaults to root.")

# Properties required when updating a note (all optional)
class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, description="New title for the note")
    content: Optional[str] = Field(None, description="New Markdown content for the note")
    folder_path: Optional[str] = Field(None, description="New virtual folder path for the note.")

# Properties returned when reading a full note (including content)
class NoteRead(IDModel, NoteBase):
    project_id: str = Field(..., description="ID of the parent project")
    content: str = Field(..., description="Markdown content of the note")
    folder_path: str = Field(..., description="Virtual folder path of the note.")
    last_modified: Optional[float] = Field(None, description="Unix timestamp of the last modification time of the note file")
    # Inherits id, title

# Properties returned when listing notes (excluding content)
class NoteReadBasic(IDModel, NoteBase):
    project_id: str = Field(..., description="ID of the parent project")
    folder_path: str = Field(..., description="Virtual folder path of the note.")
    last_modified: Optional[float] = Field(None, description="Unix timestamp of the last modification time of the note file")
    # Inherits id, title

# Wrapper for list response
class NoteList(BaseModel):
    notes: List[NoteReadBasic] = Field([], description="List of notes for the project")


# --- Models for Tree Structure ---

class NoteTreeNode(BaseModel):
    id: str = Field(..., description="Unique ID for the node (Note ID for notes, generated path for folders)")
    name: str = Field(..., description="Display name of the folder or note title")
    type: Literal['folder', 'note'] = Field(..., description="Type of the node")
    path: str = Field(..., description="Full virtual path of the node")
    children: List['NoteTreeNode'] = Field([], description="Child nodes (for folders)")
    # Optional fields for notes, mirroring NoteReadBasic where applicable
    note_id: Optional[str] = Field(None, description="Original Note ID (if type is 'note')")
    last_modified: Optional[float] = Field(None, description="Unix timestamp (if type is 'note')")

# Allow recursive definition (Pydantic v2)
# NoteTreeNode.model_rebuild() # Pydantic v2 should handle this automatically now

class NoteTree(BaseModel):
    # Represent the tree as a list of top-level nodes (could be folders or notes directly under root)
    tree: List[NoteTreeNode] = Field([], description="Hierarchical structure of notes and virtual folders")


# --- Folder Management Models ---

class FolderRenameRequest(BaseModel):
    old_path: str = Field(..., description="The current virtual path of the folder")
    new_path: str = Field(..., description="The desired new virtual path")

class FolderDeleteRequest(BaseModel):
    path: str = Field(..., description="The virtual path of the folder to delete")
    recursive: bool = Field(False, description="If true, delete folder and all its contents (notes and subfolders). If false, fail if not empty.")