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
# --- Import the engine instance ---
# This import statement will trigger the execution of engine.py,
# including the creation of the rag_engine singleton.
from app.rag.engine import rag_engine
# Import AI models later when needed
# from app.models.ai import AIQueryRequest, AIQueryResponse

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
        logger.info("AIService initialized.") # Log AIService initialization

    async def query_project(self, project_id: str, query_text: str) -> str: # -> AIQueryResponse later
        """
        Handles the business logic for querying a project's context.
        """
        logger.info(f"AIService: Processing query for project {project_id}")
        # Delegate the core RAG work to the engine
        response = await self.rag_engine.query(project_id, query_text)
        # Process/format the response if needed
        # For now, just return the string
        return response # Return AIQueryResponse(...) later

    # --- Add other methods later for generation, editing etc. ---
    # async def generate_scene_draft(...)
    # async def suggest_edits(...)

# --- Create a singleton instance of AIService ---
# This instantiation also ensures the module is loaded and the import happens.
try:
    ai_service = AIService()
except Exception as e:
     logger.critical(f"Failed to create AIService instance on startup: {e}", exc_info=True)
     # Decide how to handle this - maybe the app shouldn't start?
     raise # Re-raise to prevent app startup if service fails