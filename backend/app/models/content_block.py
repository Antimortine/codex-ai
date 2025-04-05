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

# Base model for reading content
class ContentBlockRead(BaseModel):
    project_id: str = Field(..., description="ID of the parent project")
    content: str = Field(..., description="Markdown content")

# Model for updating content
class ContentBlockUpdate(BaseModel):
    content: str = Field(..., description="New Markdown content")