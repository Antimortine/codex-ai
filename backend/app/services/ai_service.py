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

import logging
from app.rag.engine import rag_engine
# Import new request/response models
from app.models.ai import (
    AISceneGenerationRequest, AISceneGenerationResponse,
    AIRephraseRequest, AIRephraseResponse
)
from llama_index.core.base.response.schema import NodeWithScore
from typing import List, Tuple

logger = logging.getLogger(__name__)

class AIService:
    """
    Service layer for handling AI-related operations like querying,
    generation, and editing, using the RagEngine.
    """
    def __init__(self):
        # Store reference to the singleton engine instance
        # Ensure rag_engine was successfully imported and instantiated
        if rag_engine is None:
             logger.critical("RagEngine instance is None! AIService cannot function.")
             raise RuntimeError("Failed to initialize AIService due to missing RagEngine.")
        self.rag_engine = rag_engine
        logger.info("AIService initialized.")

    async def query_project(self, project_id: str, query_text: str) -> Tuple[str, List[NodeWithScore]]:
        """
        Handles the business logic for querying a project's context.
        Delegates to RagEngine and returns the result.
        """
        # ... (query_project remains unchanged) ...
        logger.info(f"AIService: Processing query for project {project_id}")
        answer, source_nodes = await self.rag_engine.query(project_id, query_text)
        return answer, source_nodes

    async def generate_scene_draft(self, project_id: str, chapter_id: str, request_data: AISceneGenerationRequest) -> str:
        """
        Handles the business logic for generating a scene draft.
        Delegates to RagEngine.
        """
        logger.info(f"AIService: Processing scene generation request for project {project_id}, chapter {chapter_id}, previous order: {request_data.previous_scene_order}")
        # Pass necessary info to the RagEngine's generation method
        generated_content = await self.rag_engine.generate_scene(
            project_id=project_id,
            chapter_id=chapter_id,
            prompt_summary=request_data.prompt_summary,
            previous_scene_order=request_data.previous_scene_order # Pass the new field
        )
        return generated_content

    async def rephrase_text(self, project_id: str, request_data: AIRephraseRequest) -> List[str]:
        """
        Handles the business logic for rephrasing selected text.
        Delegates to RagEngine.
        """
        # ... (rephrase_text remains unchanged) ...
        logger.info(f"AIService: Processing rephrase request for project {project_id}. Text: '{request_data.selected_text[:50]}...'")
        suggestions = await self.rag_engine.rephrase(
            project_id=project_id,
            selected_text=request_data.selected_text,
            context_before=request_data.context_before,
            context_after=request_data.context_after
        )
        return suggestions


    # --- Add other methods later ---
    # async def summarize_text(...)
    # async def expand_text(...)
    # async def suggest_edits(...)

# --- Create a singleton instance ---
try:
    ai_service = AIService()
except Exception as e:
     logger.critical(f"Failed to create AIService instance on startup: {e}", exc_info=True)
     raise