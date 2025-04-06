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

class SourceNodeModel(BaseModel): # For returning sources later
     id: str
     text: str
     score: Optional[float] = None
     metadata: Optional[dict] = None
     # Add other relevant fields from LlamaIndex NodeWithScore if needed

class AIQueryResponse(BaseModel):# pylint: disable=too-few-public-methods
    answer: str = Field(..., description="The AI-generated answer.")
    # Optionally include source nodes used for the answer
    source_nodes: Optional[List[SourceNodeModel]] = Field(None, description="List of source nodes retrieved and used for the answer.")

# Add other models for generation/editing requests/responses later
# class AISceneGenerationRequest(...)
# class AISceneGenerationResponse(...)