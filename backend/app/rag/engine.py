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
from typing import List, Tuple, Optional

# Import the individual processors
from app.rag.query_processor import QueryProcessor
from app.rag.scene_generator import SceneGenerator
from app.rag.rephraser import Rephraser

# Import the manager that holds the components (index, llm)
from app.rag.index_manager import index_manager
from llama_index.core.base.response.schema import NodeWithScore # Keep for type hints

logger = logging.getLogger(__name__)

class RagEngine:
    """
    Facade for RAG operations. Initializes and delegates tasks to
    specific processors (QueryProcessor, SceneGenerator, Rephraser).
    """
    def __init__(self):
        """
        Initializes the RagEngine by creating instances of the task processors,
        passing them the shared index and LLM components from IndexManager.
        """
        # Ensure IndexManager components are ready (already checked by processors, but good practice)
        if not hasattr(index_manager, 'index') or not index_manager.index:
             logger.critical("IndexManager's index is not initialized! RagEngine Facade cannot function.")
             raise RuntimeError("RagEngine cannot initialize without a valid index from IndexManager.")
        if not hasattr(index_manager, 'llm') or not index_manager.llm:
             logger.critical("IndexManager's LLM is not initialized! RagEngine Facade cannot function.")
             raise RuntimeError("RagEngine cannot initialize without a valid LLM from IndexManager.")

        self.index = index_manager.index
        self.llm = index_manager.llm

        # Instantiate processors
        try:
             self.query_processor = QueryProcessor(self.index, self.llm)
             self.scene_generator = SceneGenerator(self.index, self.llm)
             self.rephraser = Rephraser(self.index, self.llm)
             logger.info("RagEngine Facade initialized with task processors.")
        except Exception as e:
             logger.critical(f"Failed to initialize RAG task processors: {e}", exc_info=True)
             raise

    async def query(self, project_id: str, query_text: str) -> Tuple[str, List[NodeWithScore]]:
        """Delegates RAG querying to QueryProcessor."""
        logger.debug(f"RagEngine Facade: Delegating query for project '{project_id}' to QueryProcessor.")
        return await self.query_processor.query(project_id, query_text)

    async def generate_scene(self, project_id: str, chapter_id: str, prompt_summary: Optional[str], previous_scene_order: Optional[int]) -> str:
        """Delegates scene generation to SceneGenerator."""
        logger.debug(f"RagEngine Facade: Delegating generate_scene for project '{project_id}', chapter '{chapter_id}' to SceneGenerator.")
        return await self.scene_generator.generate_scene(project_id, chapter_id, prompt_summary, previous_scene_order)

    async def rephrase(self, project_id: str, selected_text: str, context_before: Optional[str], context_after: Optional[str]) -> List[str]:
        """Delegates rephrasing to Rephraser."""
        logger.debug(f"RagEngine Facade: Delegating rephrase for project '{project_id}' to Rephraser.")
        return await self.rephraser.rephrase(project_id, selected_text, context_before, context_after)

# --- Singleton Instance ---
# Create an instance of the facade
try:
     rag_engine = RagEngine()
except Exception as e:
     logger.critical(f"Failed to create RagEngine facade instance on startup: {e}", exc_info=True)
     raise