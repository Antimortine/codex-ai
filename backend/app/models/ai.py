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
    # This field will now be populated
    source_nodes: Optional[List[SourceNodeModel]] = Field(None, description="List of source nodes retrieved and used for the answer.")

# Add other models for generation/editing requests/responses later
# class AISceneGenerationRequest(...)
# class AISceneGenerationResponse(...)