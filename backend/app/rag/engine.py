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
from typing import List, Tuple, Optional, Dict, Set # Import Set

from app.rag.query_processor import QueryProcessor
from app.rag.scene_generator import SceneGenerator
from app.rag.rephraser import Rephraser
from app.rag.chapter_splitter import ChapterSplitter
from app.rag.index_manager import index_manager
from llama_index.core.base.response.schema import NodeWithScore

logger = logging.getLogger(__name__)

class RagEngine:
    def __init__(self):
        if index_manager is None or not index_manager.index or not index_manager.llm: raise RuntimeError("RagEngine requires an initialized IndexManager.")
        self.index = index_manager.index; self.llm = index_manager.llm
        try: self.query_processor = QueryProcessor(self.index, self.llm); self.scene_generator = SceneGenerator(self.index, self.llm); self.rephraser = Rephraser(self.index, self.llm); self.chapter_splitter = ChapterSplitter(self.index, self.llm); logger.info("RagEngine Facade initialized with task processors.")
        except Exception as e: logger.critical(f"Failed to initialize RAG task processors: {e}", exc_info=True); raise

    async def query(self, project_id: str, query_text: str, explicit_plan: str, explicit_synopsis: str, direct_sources_data: Optional[List[Dict]] = None, paths_to_filter: Optional[Set[str]] = None) -> Tuple[str, List[NodeWithScore], Optional[List[Dict[str, str]]]]:
        logger.debug(f"RagEngine Facade: Delegating query for project '{project_id}' to QueryProcessor.")
        return await self.query_processor.query(project_id=project_id, query_text=query_text, explicit_plan=explicit_plan, explicit_synopsis=explicit_synopsis, direct_sources_data=direct_sources_data, paths_to_filter=paths_to_filter)

    # --- MODIFIED: Added paths_to_filter ---
    async def generate_scene(self, project_id: str, chapter_id: str, prompt_summary: Optional[str], previous_scene_order: Optional[int], explicit_plan: str, explicit_synopsis: str, explicit_previous_scenes: List[Tuple[int, str]], paths_to_filter: Optional[Set[str]] = None) -> Dict[str, str]:
        logger.debug(f"RagEngine Facade: Delegating generate_scene for project '{project_id}', chapter '{chapter_id}' to SceneGenerator.")
        return await self.scene_generator.generate_scene(
            project_id=project_id, chapter_id=chapter_id, prompt_summary=prompt_summary,
            previous_scene_order=previous_scene_order, explicit_plan=explicit_plan,
            explicit_synopsis=explicit_synopsis, explicit_previous_scenes=explicit_previous_scenes,
            paths_to_filter=paths_to_filter # Pass through
        )
    # --- END MODIFIED ---

    # --- MODIFIED: Added explicit_plan, explicit_synopsis, paths_to_filter ---
    async def rephrase(self, project_id: str, selected_text: str, context_before: Optional[str], context_after: Optional[str],
                     explicit_plan: str, explicit_synopsis: str, # Added Plan/Synopsis
                     paths_to_filter: Optional[Set[str]] = None # Added filter
                     ) -> List[str]:
        logger.debug(f"RagEngine Facade: Delegating rephrase for project '{project_id}' to Rephraser.")
        return await self.rephraser.rephrase(
            project_id=project_id, selected_text=selected_text, context_before=context_before,
            context_after=context_after, explicit_plan=explicit_plan, explicit_synopsis=explicit_synopsis, # Pass through
            paths_to_filter=paths_to_filter # Pass through
        )
    # --- END MODIFIED ---

    # --- MODIFIED: Added paths_to_filter ---
    async def split_chapter(self, project_id: str, chapter_id: str, chapter_content: str, explicit_plan: str, explicit_synopsis: str, paths_to_filter: Optional[Set[str]] = None) -> List:
        logger.debug(f"RagEngine Facade: Delegating split_chapter for project '{project_id}', chapter '{chapter_id}' to ChapterSplitter.")
        return await self.chapter_splitter.split(
            project_id=project_id, chapter_id=chapter_id, chapter_content=chapter_content,
            explicit_plan=explicit_plan, explicit_synopsis=explicit_synopsis,
            paths_to_filter=paths_to_filter # Pass through
        )
    # --- END MODIFIED ---


# --- Instantiate Singleton ---
try: rag_engine = RagEngine()
except Exception as e: logger.critical(f"Failed to create RagEngine facade instance on startup: {e}", exc_info=True); rag_engine = None