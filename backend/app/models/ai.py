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

# --- Query Models ---

class AIQueryRequest(BaseModel):
    query: str = Field(..., description="The user's question or query text.")

class SourceNodeModel(BaseModel):
     id: str = Field(..., description="The unique ID of the source node/chunk.")
     text: str = Field(..., description="The text content of the source node/chunk.")
     score: Optional[float] = Field(None, description="The similarity score of the node (if applicable).")
     metadata: Optional[dict] = Field(None, description="Metadata associated with the node (e.g., file_path, project_id).")
     # Add other relevant fields from LlamaIndex NodeWithScore if needed

class AIQueryResponse(BaseModel):
    answer: str = Field(..., description="The AI-generated answer.")
    source_nodes: Optional[List[SourceNodeModel]] = Field(None, description="List of source nodes retrieved and used for the answer.")


# --- Scene Generation Models ---

class AISceneGenerationRequest(BaseModel):
    prompt_summary: Optional[str] = Field(None, description="Optional brief summary or prompt to guide the scene generation.")
    # Field to indicate the order number of the preceding scene
    previous_scene_order: Optional[int] = Field(None, ge=0, description="The order number of the scene immediately preceding the one to be generated (0 if it's the first scene).")
    # Add other potential fields later: target_characters, setting, etc.

class AISceneGenerationResponse(BaseModel):
    generated_content: str = Field(..., description="The generated Markdown content for the scene draft.")


# --- Text Editing Models ---

class AIRephraseRequest(BaseModel):
    selected_text: str = Field(..., description="The text selected by the user for rephrasing.")
    context_before: Optional[str] = Field(None, description="Optional text immediately preceding the selection for better context.")
    context_after: Optional[str] = Field(None, description="Optional text immediately following the selection for better context.")
    # Add other potential fields: desired_tone, target_audience, etc.

class AIRephraseResponse(BaseModel):
    suggestions: List[str] = Field(..., description="A list of alternative phrasings for the selected text.")


# --- Chapter Splitting Models ---

class AIChapterSplitRequest(BaseModel):
    # We might load the chapter content on the backend based on chapter_id,
    # so the request body might be empty or contain optional parameters later.
    # For now, let's keep it simple.
    # Example optional parameter:
    # hint: Optional[str] = Field(None, description="Optional hint for the AI on how to split (e.g., 'split by location changes').")
    pass # No specific request body needed initially

class ProposedScene(BaseModel):
    """Represents a single scene proposed by the AI splitter."""
    suggested_title: str = Field(..., description="A title suggested by the AI for the new scene.")
    content: str = Field(..., description="The Markdown content chunk identified by the AI for this scene.")
    # We might add suggested_order later if the AI determines it.

# --- NEW: Pydantic model for the Tool's arguments ---
class ProposedSceneList(BaseModel):
    """Data model for the list of proposed scenes, used as Tool arguments."""
    proposed_scenes: List[ProposedScene] = Field(..., description="The list of scenes identified in the chapter.")
# --- END NEW ---

class AIChapterSplitResponse(BaseModel):
    proposed_scenes: List[ProposedScene] = Field(..., description="A list of proposed scenes derived from the chapter content.")


# Add other models for editing requests/responses later (Summarize, Expand, etc.)
# class AISummarizeRequest(...)
# class AISummarizeResponse(...)
# class AIExpandRequest(...)
# class AIExpandResponse(...)