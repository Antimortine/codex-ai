# Copyright 2025 Antimortine (antimortine@gmail.com)
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

from fastapi import APIRouter

from app.api.v1.endpoints import projects
from app.api.v1.endpoints import chapters
from app.api.v1.endpoints import scenes
from app.api.v1.endpoints import characters
from app.api.v1.endpoints import content_blocks
from app.api.v1.endpoints import ai
from app.api.v1.endpoints import chat_history
# --- ADDED: Import notes router ---
from app.api.v1.endpoints import notes
# --- END ADDED ---

api_router = APIRouter()

# --- Project level routes ---
api_router.include_router(
    projects.router,
    prefix="/projects",
    tags=["Projects"]
)

# --- Content Block routes (Plan, Synopsis, World) ---
api_router.include_router(
    content_blocks.router,
    prefix="/projects/{project_id}",
    tags=["Content Blocks (Plan, Synopsis, World)"]
)

# --- Character routes ---
api_router.include_router(
    characters.router,
    prefix="/projects/{project_id}/characters",
    tags=["Characters"]
)

# --- Chapter routes ---
api_router.include_router(
    chapters.router,
    prefix="/projects/{project_id}/chapters",
    tags=["Chapters"]
)

# --- Scene routes ---
api_router.include_router(
    scenes.router,
    prefix="/projects/{project_id}/chapters/{chapter_id}/scenes",
    tags=["Scenes"]
)

# --- AI routes ---
api_router.include_router(
    ai.router,
    prefix="/ai",
    tags=["AI"]
)

# --- Chat History & Session routes ---
# Mount the chat_history router under the project ID prefix
# The endpoints within chat_history.py define the rest of the path
# e.g., /chat_sessions, /chat_history/{session_id}
api_router.include_router(
    chat_history.router,
    prefix="/projects/{project_id}",
    # Tags are defined within the chat_history router itself now
)

# --- ADDED: Notes routes ---
api_router.include_router(
    notes.router,
    prefix="/projects/{project_id}/notes",
    tags=["Notes"]
)
# --- END ADDED ---