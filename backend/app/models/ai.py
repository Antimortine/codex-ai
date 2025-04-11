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
from typing import Optional, List, Dict # Import Dict
from .common import IDModel, generate_uuid # Import generate_uuid

# --- Query Models ---
class AIQueryRequest(BaseModel):
    query: str = Field(..., description="The user's question or query text.")

class SourceNodeModel(BaseModel):
     id: str = Field(..., description="The unique ID of the source node/chunk.")
     text: str = Field(..., description="The text content of the source node/chunk.")
     score: Optional[float] = Field(None, description="The similarity score of the node (if applicable).")
     metadata: Optional[dict] = Field(None, description="Metadata associated with the node (e.g., file_path, project_id).")

class AIQueryResponse(BaseModel):
    answer: str = Field(..., description="The AI-generated answer.")
    source_nodes: Optional[List[SourceNodeModel]] = Field(None, description="List of source nodes retrieved via vector search.")
    direct_sources: Optional[List[Dict[str, str]]] = Field(None, description="List of primary sources directly loaded based on query match (e.g., [{'type': 'Scene', 'name': 'Scene Title'}, {'type': 'Character', 'name': 'Char Name'}]).")

# --- Scene Generation Models ---
class AISceneGenerationRequest(BaseModel):
    prompt_summary: Optional[str] = Field(None, description="Optional brief summary or prompt to guide the scene generation.")
    previous_scene_order: Optional[int] = Field(None, ge=0, description="The order number of the scene immediately preceding the one to be generated (0 if it's the first scene).")

class SaveGeneratedSceneToolSchema(BaseModel):
    title: str = Field(..., description="The concise title generated for the scene draft.")
    content: str = Field(..., description="The full Markdown content generated for the scene draft.")

class AISceneGenerationResponse(BaseModel):
    title: str = Field(..., description="The AI-generated title for the scene draft.")
    content: str = Field(..., description="The AI-generated Markdown content for the scene draft.")


# --- Text Editing Models ---
class AIRephraseRequest(BaseModel):
    selected_text: str = Field(..., description="The text selected by the user for rephrasing.")
    context_before: Optional[str] = Field(None, description="Optional text immediately preceding the selection for better context.")
    context_after: Optional[str] = Field(None, description="Optional text immediately following the selection for better context.")

class AIRephraseResponse(BaseModel):
    suggestions: List[str] = Field(..., description="A list of alternative phrasings for the selected text.")

# --- Chapter Splitting Models ---
class AIChapterSplitRequest(BaseModel):
    chapter_content: str = Field(..., description="The full Markdown content of the chapter to be split.")

class ProposedScene(BaseModel):
    suggested_title: str = Field(..., description="Suggested scene title.")
    content: str = Field(..., description="Markdown content for the scene.")

class ProposedSceneList(BaseModel):
    proposed_scenes: List[ProposedScene] = Field(..., description="List of proposed scenes.")

class AIChapterSplitResponse(BaseModel):
    proposed_scenes: List[ProposedScene] = Field(..., description="A list of proposed scenes derived from the chapter content.")

# --- Chat History Models ---
class ChatHistoryEntry(BaseModel):
    id: int # Keep simple integer ID within a session's history list
    query: str
    response: Optional[AIQueryResponse] = None
    error: Optional[str] = None

class ChatHistoryWrite(BaseModel):
    # This now represents the history for a *single* session being updated
    history: List[ChatHistoryEntry] = Field(..., description="The complete list of chat history entries for a specific session.")

class ChatHistoryRead(ChatHistoryWrite):
    # Response when reading a single session's history
    pass

# --- ADDED: Chat Session Models ---
class ChatSessionBase(BaseModel):
    name: str = Field(..., min_length=1, description="User-defined name for the chat session.")

class ChatSessionCreate(ChatSessionBase):
    # Name is provided by the user
    pass

class ChatSessionUpdate(BaseModel):
    # Only allow updating the name for now
    name: Optional[str] = Field(None, min_length=1, description="New name for the chat session.")

class ChatSessionRead(IDModel, ChatSessionBase):
    # Inherits id from IDModel and name from ChatSessionBase
    project_id: str = Field(..., description="ID of the parent project")
    # Add other fields like last_modified if needed later
    pass

class ChatSessionList(BaseModel):
    sessions: List[ChatSessionRead] = Field([], description="List of available chat sessions for the project.")
# --- END ADDED ---