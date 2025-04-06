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


# Add other models for editing requests/responses later (Summarize, Expand, etc.)
# class AISummarizeRequest(...)
# class AISummarizeResponse(...)
# class AIExpandRequest(...)
# class AIExpandResponse(...)