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
from typing import List, Tuple, Optional, Dict, Set
from pathlib import Path # Import Path

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
        # --- ADDED: Store index_manager instance ---
        self.index_manager = index_manager
        # --- END ADDED ---
        try: self.query_processor = QueryProcessor(self.index, self.llm); self.scene_generator = SceneGenerator(self.index, self.llm); self.rephraser = Rephraser(self.index, self.llm); self.chapter_splitter = ChapterSplitter(self.index, self.llm); logger.info("RagEngine Facade initialized with task processors.")
        except Exception as e: logger.critical(f"Failed to initialize RAG task processors: {e}", exc_info=True); raise

    async def query(self, project_id: str, query_text: str, explicit_plan: str, explicit_synopsis: str, direct_sources_data: Optional[List[Dict]] = None, paths_to_filter: Optional[Set[str]] = None) -> Tuple[str, List[NodeWithScore], Optional[List[Dict[str, str]]]]:
        logger.debug(f"RagEngine Facade: Delegating query for project '{project_id}' to QueryProcessor.")
        return await self.query_processor.query(project_id=project_id, query_text=query_text, explicit_plan=explicit_plan, explicit_synopsis=explicit_synopsis, direct_sources_data=direct_sources_data, paths_to_filter=paths_to_filter)

    async def generate_scene(self, project_id: str, chapter_id: str, prompt_summary: Optional[str], previous_scene_order: Optional[int], explicit_plan: str, explicit_synopsis: str, explicit_previous_scenes: List[Tuple[int, str]], paths_to_filter: Optional[Set[str]] = None) -> Dict[str, str]:
        logger.debug(f"RagEngine Facade: Delegating generate_scene for project '{project_id}', chapter '{chapter_id}' to SceneGenerator.")
        return await self.scene_generator.generate_scene(
            project_id=project_id, chapter_id=chapter_id, prompt_summary=prompt_summary,
            previous_scene_order=previous_scene_order, explicit_plan=explicit_plan,
            explicit_synopsis=explicit_synopsis, explicit_previous_scenes=explicit_previous_scenes,
            paths_to_filter=paths_to_filter
        )

    async def rephrase(self, project_id: str, selected_text: str, context_before: Optional[str], context_after: Optional[str],
                     explicit_plan: str, explicit_synopsis: str,
                     paths_to_filter: Optional[Set[str]] = None
                     ) -> List[str]:
        logger.debug(f"RagEngine Facade: Delegating rephrase for project '{project_id}' to Rephraser.")
        return await self.rephraser.rephrase(
            project_id=project_id, selected_text=selected_text, context_before=context_before,
            context_after=context_after, explicit_plan=explicit_plan, explicit_synopsis=explicit_synopsis,
            paths_to_filter=paths_to_filter
        )

    async def split_chapter(self, project_id: str, chapter_id: str, chapter_content: str, explicit_plan: str, explicit_synopsis: str, paths_to_filter: Optional[Set[str]] = None) -> List:
        logger.debug(f"RagEngine Facade: Delegating split_chapter for project '{project_id}', chapter '{chapter_id}' to ChapterSplitter.")
        return await self.chapter_splitter.split(
            project_id=project_id, chapter_id=chapter_id, chapter_content=chapter_content,
            explicit_plan=explicit_plan, explicit_synopsis=explicit_synopsis,
            paths_to_filter=paths_to_filter
        )

    # --- ADDED: Rebuild Index Method ---
    # Note: This is synchronous because index_file and delete_project_docs are currently synchronous.
    # If they become async, this should be async too.
    def rebuild_index(self, project_id: str, file_paths: List[Path]):
        """
        Deletes all existing index entries for a project and re-indexes the provided file paths.
        """
        logger.info(f"RagEngine Facade: Starting index rebuild for project '{project_id}'.")
        if not self.index_manager:
            logger.error("IndexManager not available in RagEngine. Cannot rebuild index.")
            raise RuntimeError("IndexManager not initialized.")

        # 1. Delete existing documents for the project
        try:
            logger.info(f"RagEngine: Deleting existing documents for project {project_id}...")
            self.index_manager.delete_project_docs(project_id)
            logger.info(f"RagEngine: Finished deleting existing documents for project {project_id}.")
        except Exception as e:
            logger.error(f"RagEngine: Error deleting documents for project {project_id} during rebuild: {e}", exc_info=True)
            # Decide whether to continue or raise. Let's continue but log the error.

        # 2. Re-index the provided files
        logger.info(f"RagEngine: Re-indexing {len(file_paths)} files for project {project_id}...")
        indexed_count = 0
        error_count = 0
        for file_path in file_paths:
            try:
                # Assuming index_file is synchronous
                self.index_manager.index_file(file_path)
                indexed_count += 1
            except Exception as e:
                logger.error(f"RagEngine: Error indexing file {file_path} during rebuild: {e}", exc_info=True)
                error_count += 1

        logger.info(f"RagEngine Facade: Finished index rebuild for project '{project_id}'. Indexed: {indexed_count}, Errors: {error_count}.")
    # --- END ADDED ---


# --- Instantiate Singleton ---
try: rag_engine = RagEngine()
except Exception as e: logger.critical(f"Failed to create RagEngine facade instance on startup: {e}", exc_info=True); rag_engine = None