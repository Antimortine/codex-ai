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
# Removed unused imports: HTTPException, status, file_service
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Tuple, Optional, Dict # Keep Dict for type hint clarity

from app.core.config import settings
# Removed file_service import

logger = logging.getLogger(__name__)

# PREVIOUS_SCENE_COUNT is now only used by AIService to decide how many scenes to load

class SceneGenerator:
    """Handles RAG scene generation logic, given explicit and retrieved context."""

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
        logger.info("SceneGenerator initialized.")

    async def generate_scene(
        self,
        project_id: str,
        chapter_id: str,
        prompt_summary: Optional[str],
        previous_scene_order: Optional[int], # Still useful for the retrieval query
        explicit_plan: str,
        explicit_synopsis: str,
        explicit_previous_scenes: List[Tuple[int, str]] # Now receives loaded scenes
        ) -> str:
        """
        Generates a scene draft using provided explicit context (plan, synopsis, previous N scenes)
        and RAG context for the given project and chapter.

        Args:
            project_id: The ID of the project.
            chapter_id: The ID of the chapter for the new scene.
            prompt_summary: An optional user-provided summary to guide generation.
            previous_scene_order: The order number of the scene immediately preceding.
            explicit_plan: The loaded content of the project plan.
            explicit_synopsis: The loaded content of the project synopsis.
            explicit_previous_scenes: A list of (order, content) tuples for preceding scenes.

        Returns:
            The generated scene content as a Markdown string or an error message.
        """
        logger.info(f"SceneGenerator: Generating scene for project '{project_id}', chapter '{chapter_id}'. Previous order: {previous_scene_order}. Summary: '{prompt_summary}'")

        try:
            # --- 1. Retrieve RAG Context --- (Explicit context is now passed in)
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


            # --- 2. Build Generation Prompt ---
            logger.debug("Building enhanced generation prompt with provided explicit context...")
            system_prompt = (
                "You are an expert writing assistant helping a user draft the next scene in their creative writing project. "
                "Generate a coherent and engaging scene draft in Markdown format. "
                "Pay close attention to the provided Project Plan, Synopsis, and the content of the Immediately Previous Scene(s) to ensure consistency and logical progression. "
                "Also consider the Additional Context retrieved via search."
            )

            # Construct Previous Scenes part of the prompt using the passed data
            previous_scenes_prompt_part = ""
            if explicit_previous_scenes:
                 for order, content in explicit_previous_scenes: # Assumes already sorted chronologically
                      label = f"Immediately Previous Scene (Order: {order})" if order == previous_scene_order else f"Previous Scene (Order: {order})"
                      previous_scenes_prompt_part += f"**{label}:**\n```markdown\n{content}\n```\n\n"
            else:
                 previous_scenes_prompt_part = "**Previous Scene(s):** N/A (Generating the first scene)\n\n"

            # --- MODIFIED: Construct main instruction based on prompt_summary ---
            main_instruction = ""
            if prompt_summary:
                main_instruction = f"Please write a draft for the next scene, focusing on the following guidance: '{prompt_summary}'. It should follow the previous scene(s) provided below.\n\n"
            else:
                main_instruction = "Please write a draft for the next scene, ensuring it follows the previous scene(s) provided below.\n\n"
            # --- END MODIFICATION ---

            user_message_content = (
                # Use the dynamic main_instruction
                f"{main_instruction}"
                # Use the passed explicit context strings
                f"**Project Plan:**\n```markdown\n{explicit_plan}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{explicit_synopsis}\n```\n\n"
                f"{previous_scenes_prompt_part}"
                f"**Additional Retrieved Context:**\n```markdown\n{rag_context_str}\n```\n\n"
                f"**New Scene Details:**\n"
                f"- Belongs to: Chapter ID '{chapter_id}'\n"
                f"- Should logically follow the provided previous scene(s).\n"
            )
            # --- REMOVED redundant User Guidance/Focus line ---
            # if prompt_summary:
            #     user_message_content += f"- User Guidance/Focus for New Scene: {prompt_summary}\n\n"
            # else:
            #     user_message_content += "- User Guidance/Focus for New Scene: (None provided - focus on natural progression from the previous scene(s) and overall context)\n\n"
            # --- END REMOVAL ---

            user_message_content += (
                "\n**Instructions:**\n" # Added newline for spacing
                "- Generate the new scene content in pure Markdown format.\n"
                "- Start directly with the scene content (e.g., a heading like '## Scene Title' or directly with narrative).\n"
                "- Ensure the new scene flows logically from the previous scene(s).\n"
                "- Maintain consistency with characters, plot points, and world details mentioned in the Plan, Synopsis, and other context.\n"
                "- Do NOT add explanations or commentary outside the new scene's Markdown content."
            )

            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"

            # Log the full prompt for debugging
            logger.debug(f"SceneGenerator: Full prompt being sent to LLM (length: {len(full_prompt)}):\n--- PROMPT START ---\n{full_prompt}\n--- PROMPT END ---")

            logger.info("Calling LLM for enhanced scene generation...")
            llm_response = await self.llm.acomplete(full_prompt)

            generated_text = llm_response.text if llm_response else ""

            if not generated_text.strip():
                 logger.warning("LLM returned an empty response for scene generation.")
                 return "Error: The AI failed to generate a scene draft. Please try again."

            logger.info(f"Enhanced scene generation successful for project '{project_id}', chapter '{chapter_id}'.")
            return generated_text.strip()

        except Exception as e:
            logger.error(f"Error during scene generation processing for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            return f"Error: An unexpected error occurred during scene generation. Please check logs."