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
# Import new request/response models
from app.models.ai import (
    AISceneGenerationRequest, AISceneGenerationResponse,
    AIRephraseRequest, AIRephraseResponse
)
from llama_index.core.base.response.schema import NodeWithScore
from typing import List, Tuple, Optional, Dict # Import Optional, Dict

# --- MODIFIED: Import FileService to load explicit context ---
from app.services.file_service import file_service
from app.core.config import settings # Import settings for PREVIOUS_SCENE_COUNT

logger = logging.getLogger(__name__)

PREVIOUS_SCENE_COUNT = settings.RAG_GENERATION_PREVIOUS_SCENE_COUNT

class AIService:
    """
    Service layer for handling AI-related operations like querying,
    generation, and editing. Loads explicit context for generation/editing
    before delegating to the RagEngine facade.
    """
    def __init__(self):
        # Store reference to the singleton engine instance
        if rag_engine is None:
             logger.critical("RagEngine instance is None! AIService cannot function.")
             raise RuntimeError("Failed to initialize AIService due to missing RagEngine.")
        self.rag_engine = rag_engine
        # --- MODIFIED: Store reference to file service ---
        self.file_service = file_service
        logger.info("AIService initialized.")

    async def query_project(self, project_id: str, query_text: str) -> Tuple[str, List[NodeWithScore]]:
        """
        Handles the business logic for querying a project's context.
        Delegates to RagEngine.
        """
        logger.info(f"AIService: Processing query for project {project_id}")
        answer, source_nodes = await self.rag_engine.query(project_id, query_text)
        # Note: If query needs explicit context later, load it here too
        return answer, source_nodes

    async def generate_scene_draft(self, project_id: str, chapter_id: str, request_data: AISceneGenerationRequest) -> str:
        """
        Handles the business logic for generating a scene draft.
        Loads explicit context (plan, synopsis, previous scenes) and delegates
        to the SceneGenerator via RagEngine.
        """
        logger.info(f"AIService: Processing scene generation request for project {project_id}, chapter {chapter_id}, previous order: {request_data.previous_scene_order}")

        # --- MODIFIED: Initialize variables for explicit context ---
        explicit_plan = "Not Available"
        explicit_synopsis = "Not Available"
        explicit_previous_scenes: List[Tuple[int, str]] = []

        try:
            # --- MODIFIED: Load Explicit Context using FileService ---
            logger.debug("AIService: Loading explicit context...")
            try:
                 explicit_plan = self.file_service.read_content_block_file(project_id, "plan.md")
                 logger.debug(f"AIService: Loaded plan.md (Length: {len(explicit_plan)})")
            except HTTPException as e:
                 if e.status_code == 404:
                      logger.warning("AIService: plan.md not found.")
                      explicit_plan = "" # Use empty string if not found
                 else: raise # Re-raise other file errors

            try:
                 explicit_synopsis = self.file_service.read_content_block_file(project_id, "synopsis.md")
                 logger.debug(f"AIService: Loaded synopsis.md (Length: {len(explicit_synopsis)})")
            except HTTPException as e:
                 if e.status_code == 404:
                      logger.warning("AIService: synopsis.md not found.")
                      explicit_synopsis = "" # Use empty string if not found
                 else: raise

            # Load Previous Scene(s)
            previous_scene_order = request_data.previous_scene_order
            if previous_scene_order is not None and previous_scene_order > 0 and PREVIOUS_SCENE_COUNT > 0:
                logger.debug(f"AIService: Attempting to load up to {PREVIOUS_SCENE_COUNT} previous scene(s) ending at order {previous_scene_order}")
                try:
                    # Read chapter metadata to find scene IDs by order
                    chapter_metadata = self.file_service.read_chapter_metadata(project_id, chapter_id)
                    scenes_by_order: Dict[int, str] = {
                         data.get('order'): scene_id
                         for scene_id, data in chapter_metadata.get('scenes', {}).items()
                         if data.get('order') is not None and isinstance(data.get('order'), int) # Ensure order is valid int
                    }

                    loaded_count = 0
                    # Iterate downwards from the previous scene's order
                    for target_order in range(previous_scene_order, 0, -1):
                        if loaded_count >= PREVIOUS_SCENE_COUNT:
                            break # Stop if we've loaded enough scenes

                        scene_id_to_load = scenes_by_order.get(target_order)
                        if scene_id_to_load:
                            try:
                                # Construct path and read scene content
                                scene_path = self.file_service._get_scene_path(project_id, chapter_id, scene_id_to_load)
                                content = self.file_service.read_text_file(scene_path)
                                explicit_previous_scenes.append((target_order, content))
                                loaded_count += 1
                                logger.debug(f"AIService: Loaded previous scene (Order: {target_order}, ID: {scene_id_to_load}, Length: {len(content)})")
                            except HTTPException as scene_load_err:
                                # Log errors if a specific scene file is missing, but continue
                                if scene_load_err.status_code == 404:
                                    logger.warning(f"AIService: Scene file not found for order {target_order} (ID: {scene_id_to_load}), skipping.")
                                else:
                                    logger.error(f"AIService: Error loading scene file order {target_order}: {scene_load_err.detail}")
                        else:
                            logger.debug(f"AIService: No scene found with order {target_order} in metadata.")

                    # Ensure the scenes are in chronological order (lowest order first) for the prompt
                    explicit_previous_scenes.reverse()

                except HTTPException as e:
                    # Handle errors reading chapter metadata (e.g., chapter not found)
                    if e.status_code == 404:
                        logger.warning(f"AIService: Chapter metadata not found for {chapter_id} while loading previous scenes: {e.detail}")
                    else: raise # Re-raise other errors
                except Exception as general_err:
                     # Catch unexpected errors during scene loading loop
                     logger.error(f"AIService: Unexpected error loading previous scenes: {general_err}", exc_info=True)
            # --- End Loading Explicit Context ---

            # --- ADD DEBUG LOGGING BEFORE DELEGATION ---
            logger.debug("AIService: Context prepared for SceneGenerator:")
            logger.debug(f"  - Explicit Plan Length: {len(explicit_plan)}")
            logger.debug(f"  - Explicit Synopsis Length: {len(explicit_synopsis)}")
            logger.debug(f"  - Explicit Previous Scenes Count: {len(explicit_previous_scenes)}")
            for order, content in explicit_previous_scenes:
                 logger.debug(f"    - Scene Order {order} Length: {len(content)}")
            # -------------------------------------------

            # --- MODIFIED: Delegate to RagEngine, passing the loaded explicit context ---
            generated_content = await self.rag_engine.generate_scene(
                project_id=project_id,
                chapter_id=chapter_id,
                prompt_summary=request_data.prompt_summary,
                previous_scene_order=request_data.previous_scene_order,
                # Pass the loaded explicit context
                explicit_plan=explicit_plan,
                explicit_synopsis=explicit_synopsis,
                explicit_previous_scenes=explicit_previous_scenes
            )

            # Check if the engine returned an error string
            if isinstance(generated_content, str) and generated_content.startswith("Error:"):
                 logger.error(f"Scene generation failed: {generated_content}")
                 # Raise HTTPException so the API layer returns a proper error response
                 raise HTTPException(
                     status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                     detail=generated_content # Pass the error message from the engine
                 )

            return generated_content

        except HTTPException as http_exc:
             # Catch potential 404s from file loading etc.
             logger.error(f"HTTP Exception during scene generation service: {http_exc.detail}", exc_info=True)
             raise http_exc # Re-raise to API layer
        except Exception as e:
             logger.error(f"Unexpected error in generate_scene_draft service: {e}", exc_info=True)
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail="An unexpected error occurred during scene generation."
             )


    async def rephrase_text(self, project_id: str, request_data: AIRephraseRequest) -> List[str]:
        """
        Handles the business logic for rephrasing selected text.
        Delegates to RagEngine.
        """
        logger.info(f"AIService: Processing rephrase request for project {project_id}. Text: '{request_data.selected_text[:50]}...'")
        # No changes needed here for this refactoring
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


    # --- Add other methods later ---
    # async def summarize_text(...)
    # async def expand_text(...)
    # async def suggest_edits(...)

# --- Create a singleton instance ---
try:
    ai_service = AIService()
except Exception as e:
     logger.critical(f"Failed to create AIService instance on startup: {e}", exc_info=True)
     # Propagate the error to prevent the app from starting incorrectly
     raise RuntimeError(f"Failed to initialize AIService: {e}") from e