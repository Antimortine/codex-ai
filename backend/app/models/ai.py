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
    # Add other potential fields later: target_characters, setting, etc.

class AISceneGenerationResponse(BaseModel):
    generated_content: str = Field(..., description="The generated Markdown content for the scene draft.")

# Add other models for editing requests/responses later
# class AIEditRequest(...)
# class AIEditResponse(...)