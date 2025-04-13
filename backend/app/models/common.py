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
import uuid

# We can use UUIDs for project/chapter/scene IDs for global uniqueness
# Alternatively, simple integer IDs or slugs could be used. Let's start with UUIDs.

def generate_uuid():
    return str(uuid.uuid4())

class IDModel(BaseModel):
    id: str = Field(default_factory=generate_uuid)

class Message(BaseModel):
    """ A simple message response model """
    message: str

# Create MessageResponse as an alias for Message class for backward compatibility
class MessageResponse(Message):
    """ Alias for Message for backward compatibility """
    pass

# Add other common fields or base models if needed later