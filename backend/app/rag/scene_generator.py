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
import asyncio
from fastapi import HTTPException, status
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Tuple, Optional, Dict

from app.core.config import settings
# Import FileService directly as it's needed for explicit context loading
from app.services.file_service import file_service

logger = logging.getLogger(__name__)

PREVIOUS_SCENE_COUNT = settings.RAG_GENERATION_PREVIOUS_SCENE_COUNT

class SceneGenerator:
    """Handles RAG scene generation logic."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        """
        Initializes the SceneGenerator.

        Args:
            index: The loaded VectorStoreIndex instance.
            llm: The configured LLM instance.
        """
        if not index:
            raise ValueError("SceneGenerator requires a valid VectorStoreIndex instance.")
        if not llm:
             raise ValueError("SceneGenerator requires a valid LLM instance.")
        self.index = index
        self.llm = llm
        # Note: We directly use the file_service singleton here. If dependency
        # injection was more rigorous, we might pass it in.
        self.file_service = file_service
        logger.info("SceneGenerator initialized.")

    async def generate_scene(self, project_id: str, chapter_id: str, prompt_summary: Optional[str], previous_scene_order: Optional[int]) -> str:
        """
        Generates a scene draft using explicit context (plan, synopsis, previous N scenes)
        and RAG context for the given project and chapter.

        Args:
            project_id: The ID of the project.
            chapter_id: The ID of the chapter for the new scene.
            prompt_summary: An optional user-provided summary to guide generation.
            previous_scene_order: The order number of the scene immediately preceding
                                  the one to be generated (0 if first scene).

        Returns:
            The generated scene content as a Markdown string or an error message.
        """
        logger.info(f"SceneGenerator: Starting enhanced scene generation for project '{project_id}', chapter '{chapter_id}'. Previous order: {previous_scene_order}. Prev Scene Count: {PREVIOUS_SCENE_COUNT}. Summary: '{prompt_summary}'")

        explicit_context = {}
        previous_scenes_content: List[Tuple[int, str]] = [] # Store as (order, content) tuples

        try:
            # --- 1. Load Explicit Context ---
            logger.debug("Loading explicit context: Plan, Synopsis, Previous Scene(s)...")

            # Load Plan
            try:
                 explicit_context['plan'] = self.file_service.read_content_block_file(project_id, "plan.md")
                 logger.debug("Loaded plan.md")
            except HTTPException as e:
                 if e.status_code == 404: logger.warning("plan.md not found."); explicit_context['plan'] = "Not Available"
                 else: raise

            # Load Synopsis
            try:
                 explicit_context['synopsis'] = self.file_service.read_content_block_file(project_id, "synopsis.md")
                 logger.debug("Loaded synopsis.md")
            except HTTPException as e:
                 if e.status_code == 404: logger.warning("synopsis.md not found."); explicit_context['synopsis'] = "Not Available"
                 else: raise

            # Load Previous Scene(s) Content
            if previous_scene_order is not None and previous_scene_order > 0 and PREVIOUS_SCENE_COUNT > 0:
                logger.debug(f"Attempting to load up to {PREVIOUS_SCENE_COUNT} previous scene(s) ending at order {previous_scene_order} for chapter {chapter_id}")
                try:
                    # Read chapter metadata once to map order to ID
                    chapter_metadata = self.file_service.read_chapter_metadata(project_id, chapter_id)
                    scenes_by_order: Dict[int, str] = { # {order: scene_id}
                         data.get('order'): scene_id
                         for scene_id, data in chapter_metadata.get('scenes', {}).items() if data.get('order') is not None
                    }

                    # Loop backwards from previous_scene_order
                    loaded_count = 0
                    for target_order in range(previous_scene_order, 0, -1):
                        if loaded_count >= PREVIOUS_SCENE_COUNT:
                            break # Stop if we've loaded enough scenes

                        scene_id_to_load = scenes_by_order.get(target_order)
                        if scene_id_to_load:
                            try:
                                scene_path = self.file_service._get_scene_path(project_id, chapter_id, scene_id_to_load)
                                content = self.file_service.read_text_file(scene_path)
                                previous_scenes_content.append((target_order, content))
                                loaded_count += 1
                                logger.debug(f"Loaded previous scene content (Order: {target_order}, ID: {scene_id_to_load})")
                            except HTTPException as scene_load_err:
                                if scene_load_err.status_code == 404:
                                    logger.warning(f"Scene file not found for order {target_order} (ID: {scene_id_to_load}), skipping.")
                                else:
                                    logger.error(f"Error loading scene file for order {target_order} (ID: {scene_id_to_load}): {scene_load_err.detail}")
                        else:
                             logger.debug(f"No scene found with order {target_order} in metadata.")

                    previous_scenes_content.reverse()

                except HTTPException as e:
                    if e.status_code == 404:
                         logger.warning(f"Chapter metadata not found for {chapter_id} while loading previous scenes: {e.detail}")
                    else: raise
                except Exception as general_err:
                     logger.error(f"Unexpected error loading previous scenes: {general_err}", exc_info=True)

            # --- 2. Retrieve RAG Context ---
            retrieval_query = f"Context relevant for writing a new scene after scene order {previous_scene_order} in chapter {chapter_id}."
            if prompt_summary:
                retrieval_query += f" Scene focus: {prompt_summary}"
            logger.debug(f"Constructed retrieval query: '{retrieval_query}'")

            logger.debug(f"Creating retriever for generation with top_k={settings.RAG_GENERATION_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K,
                filters=MetadataFilters(
                    filters=[ExactMatchFilter(key="project_id", value=project_id)]
                ),
            )
            retrieved_nodes: List[NodeWithScore] = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for RAG context.")

            rag_context_list = []
            if retrieved_nodes:
                 for node in retrieved_nodes:
                      char_name = node.metadata.get('character_name')
                      char_info = f" [Character: {char_name}]" if char_name else ""
                      rag_context_list.append(f"Source: {node.metadata.get('file_path', 'N/A')}{char_info}\n\n{node.get_content()}")
            rag_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No additional context retrieved via search."


            # --- 3. Build Generation Prompt ---
            logger.debug("Building enhanced generation prompt...")
            system_prompt = (
                "You are an expert writing assistant helping a user draft the next scene in their creative writing project. "
                "Generate a coherent and engaging scene draft in Markdown format. "
                "Pay close attention to the provided Project Plan, Synopsis, and the content of the Immediately Previous Scene(s) to ensure consistency and logical progression. "
                "Also consider the Additional Context retrieved via search."
            )

            previous_scenes_prompt_part = ""
            if previous_scenes_content:
                 for order, content in previous_scenes_content:
                      label = f"Immediately Previous Scene (Order: {order})" if order == previous_scene_order else f"Previous Scene (Order: {order})"
                      previous_scenes_prompt_part += f"**{label}:**\n```markdown\n{content}\n```\n\n"
            else:
                 previous_scenes_prompt_part = "**Previous Scene(s):** N/A (Generating the first scene)\n\n"


            user_message_content = (
                f"Please write a draft for the scene that follows the previous scene(s) provided below.\n\n"
                f"**Project Plan:**\n```markdown\n{explicit_context.get('plan', 'Not Available')}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{explicit_context.get('synopsis', 'Not Available')}\n```\n\n"
                f"{previous_scenes_prompt_part}"
                f"**Additional Retrieved Context:**\n```markdown\n{rag_context_str}\n```\n\n"
                f"**New Scene Details:**\n"
                f"- Belongs to: Chapter ID '{chapter_id}'\n"
                f"- Should logically follow the provided previous scene(s).\n"
            )
            if prompt_summary:
                user_message_content += f"- User Guidance/Focus for New Scene: {prompt_summary}\n\n"
            else:
                user_message_content += "- User Guidance/Focus for New Scene: (None provided - focus on natural progression from the previous scene(s) and overall context)\n\n"

            user_message_content += (
                "**Instructions:**\n"
                "- Generate the new scene content in pure Markdown format.\n"
                "- Start directly with the scene content (e.g., a heading like '## Scene Title' or directly with narrative).\n"
                "- Ensure the new scene flows logically from the previous scene(s).\n"
                "- Maintain consistency with characters, plot points, and world details mentioned in the Plan, Synopsis, and other context.\n"
                "- Do NOT add explanations or commentary outside the new scene's Markdown content."
            )

            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"
            logger.info("Calling LLM for enhanced scene generation...")
            llm_response = await self.llm.acomplete(full_prompt)

            generated_text = llm_response.text if llm_response else ""

            if not generated_text.strip():
                 logger.warning("LLM returned an empty response for scene generation.")
                 return "Error: The AI failed to generate a scene draft. Please try again."

            logger.info(f"Enhanced scene generation successful for project '{project_id}', chapter '{chapter_id}'.")
            return generated_text.strip()

        except HTTPException as http_exc:
            logger.error(f"HTTP Exception during explicit context loading for scene generation: {http_exc.detail}", exc_info=True)
            return f"Error: Could not load necessary project context ({http_exc.detail})."
        except Exception as e:
            logger.error(f"Error during scene generation for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            error_message = f"Sorry, an error occurred while generating the scene draft. Please check logs."
            return error_message