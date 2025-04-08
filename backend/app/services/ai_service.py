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
from fastapi import HTTPException, status # Import HTTPException
from app.rag.engine import rag_engine
# Import all needed AI models
from app.models.ai import (
    AISceneGenerationRequest, AISceneGenerationResponse,
    AIRephraseRequest, AIRephraseResponse,
    AIChapterSplitRequest, AIChapterSplitResponse, ProposedScene # Added chapter split models
)
from llama_index.core.base.response.schema import NodeWithScore
from typing import List, Tuple, Optional, Dict # Import Optional, Dict

# Import FileService to load explicit context
from app.services.file_service import file_service
# Import ChapterService to get chapter content
from app.services.chapter_service import chapter_service
from app.core.config import settings # Import settings for PREVIOUS_SCENE_COUNT

# --- Import the new ChapterSplitter ---
from app.rag.chapter_splitter import ChapterSplitter

logger = logging.getLogger(__name__)

PREVIOUS_SCENE_COUNT = settings.RAG_GENERATION_PREVIOUS_SCENE_COUNT

class AIService:
    """
    Service layer for handling AI-related operations like querying,
    generation, editing, and chapter splitting. Loads explicit context
    before delegating to the appropriate RAG processor.
    """
    def __init__(self):
        # Store reference to the singleton engine instance
        if rag_engine is None:
             logger.critical("RagEngine instance is None! AIService cannot function.")
             raise RuntimeError("Failed to initialize AIService due to missing RagEngine.")
        self.rag_engine = rag_engine
        # Store reference to file service
        self.file_service = file_service

        # --- Instantiate ChapterSplitter ---
        # It needs the LLM from the engine/index_manager
        if not hasattr(rag_engine, 'llm') or not rag_engine.llm:
             logger.critical("RagEngine's LLM is not initialized! AIService cannot initialize ChapterSplitter.")
             raise RuntimeError("AIService cannot initialize ChapterSplitter without a valid LLM.")
        # Pass index too, although splitter might not use it initially
        if not hasattr(rag_engine, 'index') or not rag_engine.index:
             logger.critical("RagEngine's index is not initialized! AIService cannot initialize ChapterSplitter.")
             raise RuntimeError("AIService cannot initialize ChapterSplitter without a valid index.")
        try:
            self.chapter_splitter = ChapterSplitter(index=rag_engine.index, llm=rag_engine.llm)
            logger.info("ChapterSplitter initialized within AIService.")
        except Exception as e:
            logger.critical(f"Failed to initialize ChapterSplitter within AIService: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize ChapterSplitter: {e}") from e
        # ---------------------------------

        logger.info("AIService initialized.")

    async def query_project(self, project_id: str, query_text: str) -> Tuple[str, List[NodeWithScore]]:
        """
        Handles the business logic for querying a project's context.
        Loads explicit Plan/Synopsis and delegates to RagEngine.
        """
        logger.info(f"AIService: Processing query for project {project_id}")

        # --- MODIFIED: Load Plan and Synopsis independently ---
        explicit_plan = "Not Available"
        explicit_synopsis = "Not Available"
        logger.debug(f"AIService: Loading explicit context for query (Plan, Synopsis)...")

        # Load Plan
        try:
            explicit_plan = self.file_service.read_content_block_file(project_id, "plan.md")
            logger.debug(f"AIService (Query): Loaded plan.md (Length: {len(explicit_plan)})")
        except HTTPException as e:
            if e.status_code == 404:
                logger.warning("AIService (Query): plan.md not found.")
                explicit_plan = "" # Use empty string if not found
            else:
                logger.error(f"AIService (Query): HTTP error loading plan.md for project {project_id}: {e.detail}", exc_info=True)
                explicit_plan = "Error loading plan." # Indicate error but continue
        except Exception as e:
            logger.error(f"AIService (Query): Unexpected error loading plan.md for project {project_id}: {e}", exc_info=True)
            explicit_plan = "Error loading plan." # Indicate error but continue

        # Load Synopsis
        try:
            explicit_synopsis = self.file_service.read_content_block_file(project_id, "synopsis.md")
            logger.debug(f"AIService (Query): Loaded synopsis.md (Length: {len(explicit_synopsis)})")
        except HTTPException as e:
            if e.status_code == 404:
                logger.warning("AIService (Query): synopsis.md not found.")
                explicit_synopsis = "" # Use empty string if not found
            else:
                logger.error(f"AIService (Query): HTTP error loading synopsis.md for project {project_id}: {e.detail}", exc_info=True)
                explicit_synopsis = "Error loading synopsis." # Indicate error but continue
        except Exception as e:
            logger.error(f"AIService (Query): Unexpected error loading synopsis.md for project {project_id}: {e}", exc_info=True)
            explicit_synopsis = "Error loading synopsis." # Indicate error but continue
        # --- END MODIFIED ---

        # Pass potentially modified context to rag_engine.query
        answer, source_nodes = await self.rag_engine.query(
            project_id=project_id,
            query_text=query_text,
            explicit_plan=explicit_plan,
            explicit_synopsis=explicit_synopsis
        )
        return answer, source_nodes

    async def generate_scene_draft(self, project_id: str, chapter_id: str, request_data: AISceneGenerationRequest) -> str:
        """
        Handles the business logic for generating a scene draft.
        Loads explicit context (plan, synopsis, previous scenes) and delegates
        to the SceneGenerator via RagEngine.
        """
        logger.info(f"AIService: Processing scene generation request for project {project_id}, chapter {chapter_id}, previous order: {request_data.previous_scene_order}")

        # --- MODIFIED: Load context independently (similar pattern to query) ---
        explicit_plan = "Not Available"
        explicit_synopsis = "Not Available"
        explicit_previous_scenes: List[Tuple[int, str]] = []

        logger.debug("AIService: Loading explicit context for generation...")

        # Load Plan
        try:
            explicit_plan = self.file_service.read_content_block_file(project_id, "plan.md")
            logger.debug(f"AIService (Gen): Loaded plan.md (Length: {len(explicit_plan)})")
        except HTTPException as e:
            if e.status_code == 404:
                logger.warning("AIService (Gen): plan.md not found.")
                explicit_plan = ""
            else:
                logger.error(f"AIService (Gen): HTTP error loading plan.md: {e.detail}", exc_info=True)
                explicit_plan = "Error loading plan."
        except Exception as e:
            logger.error(f"AIService (Gen): Unexpected error loading plan.md: {e}", exc_info=True)
            explicit_plan = "Error loading plan."

        # Load Synopsis
        try:
            explicit_synopsis = self.file_service.read_content_block_file(project_id, "synopsis.md")
            logger.debug(f"AIService (Gen): Loaded synopsis.md (Length: {len(explicit_synopsis)})")
        except HTTPException as e:
            if e.status_code == 404:
                logger.warning("AIService (Gen): synopsis.md not found.")
                explicit_synopsis = ""
            else:
                logger.error(f"AIService (Gen): HTTP error loading synopsis.md: {e.detail}", exc_info=True)
                explicit_synopsis = "Error loading synopsis."
        except Exception as e:
            logger.error(f"AIService (Gen): Unexpected error loading synopsis.md: {e}", exc_info=True)
            explicit_synopsis = "Error loading synopsis."

        # Load Previous Scene(s) - Keep existing try/except structure for this part
        previous_scene_order = request_data.previous_scene_order
        if previous_scene_order is not None and previous_scene_order > 0 and PREVIOUS_SCENE_COUNT > 0:
            logger.debug(f"AIService (Gen): Attempting to load up to {PREVIOUS_SCENE_COUNT} previous scene(s) ending at order {previous_scene_order}")
            try:
                chapter_metadata = self.file_service.read_chapter_metadata(project_id, chapter_id)
                scenes_by_order: Dict[int, str] = {
                     data.get('order'): scene_id
                     for scene_id, data in chapter_metadata.get('scenes', {}).items()
                     if data.get('order') is not None and isinstance(data.get('order'), int)
                }

                loaded_count = 0
                for target_order in range(previous_scene_order, 0, -1):
                    if loaded_count >= PREVIOUS_SCENE_COUNT: break
                    scene_id_to_load = scenes_by_order.get(target_order)
                    if scene_id_to_load:
                        try:
                            scene_path = self.file_service._get_scene_path(project_id, chapter_id, scene_id_to_load)
                            content = self.file_service.read_text_file(scene_path)
                            explicit_previous_scenes.append((target_order, content))
                            loaded_count += 1
                            logger.debug(f"AIService (Gen): Loaded previous scene (Order: {target_order}, ID: {scene_id_to_load}, Length: {len(content)})")
                        except HTTPException as scene_load_err:
                            if scene_load_err.status_code == 404: logger.warning(f"AIService (Gen): Scene file not found for order {target_order} (ID: {scene_id_to_load}), skipping.")
                            else: logger.error(f"AIService (Gen): Error loading scene file order {target_order}: {scene_load_err.detail}")
                    else: logger.debug(f"AIService (Gen): No scene found with order {target_order} in metadata.")

                explicit_previous_scenes.reverse() # Ensure chronological order

            except HTTPException as e:
                # Log chapter metadata errors but don't stop the whole process
                if e.status_code == 404: logger.warning(f"AIService (Gen): Chapter metadata not found for {chapter_id} while loading previous scenes: {e.detail}")
                else: logger.error(f"AIService (Gen): HTTP error loading chapter metadata for previous scenes: {e.detail}", exc_info=True)
            except Exception as general_err:
                 logger.error(f"AIService (Gen): Unexpected error loading previous scenes: {general_err}", exc_info=True)
        # --- END MODIFIED ---

        # Debug Logging Before Delegation
        logger.debug("AIService (Gen): Context prepared for SceneGenerator:")
        logger.debug(f"  - Explicit Plan: '{explicit_plan[:50]}...'") # Log start of content
        logger.debug(f"  - Explicit Synopsis: '{explicit_synopsis[:50]}...'")
        logger.debug(f"  - Explicit Previous Scenes Count: {len(explicit_previous_scenes)}")
        # for order, content in explicit_previous_scenes: # Keep this if needed
        #      logger.debug(f"    - Scene Order {order} Length: {len(content)}")

        # Delegate to RagEngine
        try:
            generated_content = await self.rag_engine.generate_scene(
                project_id=project_id,
                chapter_id=chapter_id,
                prompt_summary=request_data.prompt_summary,
                previous_scene_order=request_data.previous_scene_order,
                explicit_plan=explicit_plan,
                explicit_synopsis=explicit_synopsis,
                explicit_previous_scenes=explicit_previous_scenes
            )

            # Check for error string from engine
            if isinstance(generated_content, str) and generated_content.startswith("Error:"):
                 logger.error(f"Scene generation failed: {generated_content}")
                 raise HTTPException(
                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                     detail=generated_content
                 )

            return generated_content

        except HTTPException as http_exc:
             logger.error(f"HTTP Exception during scene generation delegation: {http_exc.detail}", exc_info=True)
             raise http_exc # Re-raise HTTP exceptions from engine/processors
        except Exception as e:
             logger.error(f"Unexpected error during scene generation delegation: {e}", exc_info=True)
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="An unexpected error occurred during AI scene generation."
             )


    async def rephrase_text(self, project_id: str, request_data: AIRephraseRequest) -> List[str]:
        """
        Handles the business logic for rephrasing selected text.
        Delegates to RagEngine.
        """
        logger.info(f"AIService: Processing rephrase request for project {project_id}. Text: '{request_data.selected_text[:50]}...'")
        try:
            suggestions = await self.rag_engine.rephrase(
                project_id=project_id,
                selected_text=request_data.selected_text,
                context_before=request_data.context_before,
                context_after=request_data.context_after
            )

            # Check for error message from engine
            if suggestions and isinstance(suggestions[0], str) and suggestions[0].startswith("Error:"):
                logger.error(f"Rephrasing failed: {suggestions[0]}")
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=suggestions[0]
                )

            return suggestions
        except HTTPException as http_exc:
             logger.error(f"HTTP Exception during rephrase delegation: {http_exc.detail}", exc_info=True)
             raise http_exc
        except Exception as e:
             logger.error(f"Unexpected error during rephrase delegation: {e}", exc_info=True)
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="An unexpected error occurred during AI rephrasing."
             )

    # --- NEW: Chapter Splitting Method ---
    async def split_chapter_into_scenes(
        self,
        project_id: str,
        chapter_id: str,
        request_data: AIChapterSplitRequest # Currently empty, might add hints later
        ) -> List[ProposedScene]:
        """
        Handles the business logic for splitting a chapter into scenes.
        Loads chapter content, plan, synopsis and delegates to ChapterSplitter.
        """
        logger.info(f"AIService: Processing chapter split request for project {project_id}, chapter {chapter_id}")

        # --- Load Required Context ---
        explicit_plan = "Not Available"
        explicit_synopsis = "Not Available"
        chapter_content = "Not Available"

        logger.debug("AIService (Split): Loading context (Chapter, Plan, Synopsis)...")

        # Load Chapter Content (Crucial for splitting)
        try:
            # Need a way to get the chapter content. Assuming chapter_service has get_by_id
            # that returns an object with a 'content' field, or we need a dedicated method.
            # Let's assume chapter_service.get_by_id returns enough info, including content path implicitly.
            # We need the actual content string. Let's add a hypothetical method to file_service
            # or assume chapter_service can provide it.
            # FOR NOW: Let's assume we need to read *all* scene files for the chapter and concatenate.
            # This is inefficient but demonstrates the need. A better approach would be if chapters
            # were single files or chapter_service could provide the full content.
            # --- TEMPORARY: Concatenate scenes ---
            temp_content_parts = []
            try:
                # Use chapter_service to get scene metadata (title, order)
                chapter_meta = self.file_service.read_chapter_metadata(project_id, chapter_id)
                scenes_in_order = sorted(
                    chapter_meta.get('scenes', {}).items(),
                    key=lambda item: item[1].get('order', float('inf'))
                )
                for scene_id, scene_meta in scenes_in_order:
                    try:
                        scene_path = self.file_service._get_scene_path(project_id, chapter_id, scene_id)
                        scene_content = self.file_service.read_text_file(scene_path)
                        # Add a simple separator or header
                        temp_content_parts.append(f"## {scene_meta.get('title', 'Scene')} (Order: {scene_meta.get('order', '?')})\n\n{scene_content}")
                    except HTTPException as e:
                        if e.status_code == 404:
                            logger.warning(f"AIService (Split): Scene file for {scene_id} not found, skipping for concatenation.")
                        else: raise e # Re-raise other errors
                if not temp_content_parts:
                     logger.warning(f"AIService (Split): No scene content found for chapter {chapter_id}.")
                     chapter_content = "" # Treat as empty if no scenes found/readable
                else:
                     chapter_content = "\n\n---\n\n".join(temp_content_parts) # Join with separator
                logger.debug(f"AIService (Split): Loaded chapter content by concatenating scenes (Length: {len(chapter_content)})")

            except HTTPException as e:
                 logger.error(f"AIService (Split): Failed to load chapter metadata or scene files for splitting: {e.detail}", exc_info=True)
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load chapter content for splitting.")
            # --- END TEMPORARY ---

        except Exception as e:
            logger.error(f"AIService (Split): Unexpected error loading chapter content for project {project_id}, chapter {chapter_id}: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to load chapter content for splitting.")


        # Load Plan
        try:
            explicit_plan = self.file_service.read_content_block_file(project_id, "plan.md")
            logger.debug(f"AIService (Split): Loaded plan.md (Length: {len(explicit_plan)})")
        except HTTPException as e:
            if e.status_code == 404: logger.warning("AIService (Split): plan.md not found.")
            else: logger.error(f"AIService (Split): HTTP error loading plan.md: {e.detail}", exc_info=True)
            explicit_plan = "" # Use empty string on error/not found
        except Exception as e:
            logger.error(f"AIService (Split): Unexpected error loading plan.md: {e}", exc_info=True)
            explicit_plan = "Error loading plan."

        # Load Synopsis
        try:
            explicit_synopsis = self.file_service.read_content_block_file(project_id, "synopsis.md")
            logger.debug(f"AIService (Split): Loaded synopsis.md (Length: {len(explicit_synopsis)})")
        except HTTPException as e:
            if e.status_code == 404: logger.warning("AIService (Split): synopsis.md not found.")
            else: logger.error(f"AIService (Split): HTTP error loading synopsis.md: {e.detail}", exc_info=True)
            explicit_synopsis = "" # Use empty string on error/not found
        except Exception as e:
            logger.error(f"AIService (Split): Unexpected error loading synopsis.md: {e}", exc_info=True)
            explicit_synopsis = "Error loading synopsis."

        # --- Delegate to ChapterSplitter ---
        try:
            if not chapter_content.strip():
                 logger.warning(f"AIService (Split): Chapter content for {chapter_id} is empty. Returning empty split.")
                 return []

            logger.debug("AIService (Split): Delegating to ChapterSplitter...")
            proposed_scenes = await self.chapter_splitter.split(
                project_id=project_id,
                chapter_id=chapter_id,
                chapter_content=chapter_content,
                explicit_plan=explicit_plan,
                explicit_synopsis=explicit_synopsis
                # Pass request_data.hint here if implemented
            )
            return proposed_scenes

        except HTTPException as http_exc:
             logger.error(f"HTTP Exception during chapter split delegation: {http_exc.detail}", exc_info=True)
             raise http_exc # Re-raise HTTP exceptions from splitter
        except Exception as e:
             logger.error(f"Unexpected error during chapter split delegation: {e}", exc_info=True)
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="An unexpected error occurred during AI chapter splitting."
             )
    # --- END NEW METHOD ---


    # --- Add other methods later ---

# --- Create a singleton instance ---
# Keep singleton creation as is, tests will use manual instantiation
try:
    ai_service = AIService()
except Exception as e:
     logger.critical(f"Failed to create AIService instance on startup: {e}", exc_info=True)
     # Make sure this error propagates during startup
     raise RuntimeError(f"Failed to initialize AIService: {e}") from e