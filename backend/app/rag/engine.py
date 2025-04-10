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
from typing import List, Tuple, Optional, Dict # Added Dict

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
        # (Initialization unchanged)
        if not hasattr(index_manager, 'index') or not index_manager.index:
             logger.critical("IndexManager's index is not initialized! RagEngine Facade cannot function.")
             raise RuntimeError("RagEngine cannot initialize without a valid index from IndexManager.")
        if not hasattr(index_manager, 'llm') or not index_manager.llm:
             logger.critical("IndexManager's LLM is not initialized! RagEngine Facade cannot function.")
             raise RuntimeError("RagEngine cannot initialize without a valid LLM from IndexManager.")
        self.index = index_manager.index
        self.llm = index_manager.llm
        try:
             self.query_processor = QueryProcessor(self.index, self.llm)
             self.scene_generator = SceneGenerator(self.index, self.llm)
             self.rephraser = Rephraser(self.index, self.llm)
             logger.info("RagEngine Facade initialized with task processors.")
        except Exception as e:
             logger.critical(f"Failed to initialize RAG task processors: {e}", exc_info=True)
             raise

    # --- MODIFIED: Accept list of direct sources data, return list of direct source info ---
    async def query(self, project_id: str, query_text: str, explicit_plan: str, explicit_synopsis: str,
                  direct_sources_data: Optional[List[Dict]] = None # Accept list of dicts
                  ) -> Tuple[str, List[NodeWithScore], Optional[List[Dict[str, str]]]]: # Return list of dicts
        """Delegates RAG querying to QueryProcessor, passing explicit and direct context."""
        logger.debug(f"RagEngine Facade: Delegating query for project '{project_id}' to QueryProcessor.")
        # --- MODIFIED: Pass direct_sources_data list correctly ---
        return await self.query_processor.query(
            project_id=project_id,
            query_text=query_text,
            explicit_plan=explicit_plan,
            explicit_synopsis=explicit_synopsis,
            direct_sources_data=direct_sources_data # Pass the list with the correct keyword
        )
        # --- END MODIFIED ---

    async def generate_scene(
        self,
        project_id: str,
        chapter_id: str,
        prompt_summary: Optional[str],
        previous_scene_order: Optional[int],
        explicit_plan: str,
        explicit_synopsis: str,
        explicit_previous_scenes: List[Tuple[int, str]]
        ) -> Dict[str, str]: # Return Dict
        # (Unchanged)
        logger.debug(f"RagEngine Facade: Delegating generate_scene for project '{project_id}', chapter '{chapter_id}' to SceneGenerator.")
        return await self.scene_generator.generate_scene(
            project_id=project_id,
            chapter_id=chapter_id,
            prompt_summary=prompt_summary,
            previous_scene_order=previous_scene_order,
            explicit_plan=explicit_plan,
            explicit_synopsis=explicit_synopsis,
            explicit_previous_scenes=explicit_previous_scenes
        )

    async def rephrase(self, project_id: str, selected_text: str, context_before: Optional[str], context_after: Optional[str]) -> List[str]:
        # (Unchanged)
        logger.debug(f"RagEngine Facade: Delegating rephrase for project '{project_id}' to Rephraser.")
        return await self.rephraser.rephrase(project_id, selected_text, context_before, context_after)

# --- Singleton Instance ---
# (Unchanged)
try:
     rag_engine = RagEngine()
except Exception as e:
     logger.critical(f"Failed to create RagEngine facade instance on startup: {e}", exc_info=True)
     raise RuntimeError(f"Failed to initialize RagEngine: {e}") from e