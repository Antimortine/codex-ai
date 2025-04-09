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
# Removed file_service import and related unused imports
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Tuple, Optional, Dict # Keep Dict for type hint clarity

# --- ADDED: Import tenacity and ClientError for retry logic ---
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.genai.errors import ClientError
# --- END ADDED ---

from app.core.config import settings
# Removed file_service import

logger = logging.getLogger(__name__)

# PREVIOUS_SCENE_COUNT is now only used by AIService to decide how many scenes to load

# --- ADDED: Retry predicate function ---
def _is_retryable_google_api_error(exception):
    """Return True if the exception is a Google API 429 error."""
    if isinstance(exception, ClientError):
        status_code = None
        try:
            # Attempt to extract status code robustly
            if hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
                status_code = exception.response.status_code
            elif hasattr(exception, 'status_code'): # Sometimes it's directly on the exception
                 status_code = exception.status_code
            elif isinstance(exception.args, (list, tuple)) and len(exception.args) > 0:
                # Check if first arg is int status code
                if isinstance(exception.args[0], int):
                    status_code = int(exception.args[0])
                # Check if first arg is string containing status code (less reliable)
                elif isinstance(exception.args[0], str) and '429' in exception.args[0]:
                    logger.warning("Google API rate limit hit (ClientError 429 - string check). Retrying scene generation...")
                    return True
        except (ValueError, TypeError, IndexError, AttributeError):
            pass # Ignore errors during status code extraction

        if status_code == 429:
             logger.warning("Google API rate limit hit (ClientError 429). Retrying scene generation...")
             return True
    logger.debug(f"Non-retryable error encountered during scene generation: {type(exception)}")
    return False
# --- END ADDED ---


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

    # --- ADDED: Retry decorator and helper method ---
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
        retry=retry_if_exception(_is_retryable_google_api_error),
        reraise=True # Re-raise the exception if retries fail
    )
    async def _execute_llm_complete(self, prompt: str):
        """Helper function to isolate the LLM call for retry logic."""
        logger.info("Calling LLM for scene generation...")
        return await self.llm.acomplete(prompt)
    # --- END ADDED ---

    async def generate_scene(
        self,
        project_id: str,
        chapter_id: str,
        prompt_summary: Optional[str],
        previous_scene_order: Optional[int], # Still useful for the retrieval query
        # --- MODIFIED: Accept explicit context as arguments ---
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
            previous_scene_order: The order number of the scene immediately preceding (used for retrieval query).
            explicit_plan: The loaded content of the project plan.
            explicit_synopsis: The loaded content of the project synopsis.
            explicit_previous_scenes: A list of (order, content) tuples for preceding scenes.

        Returns:
            The generated scene content as a Markdown string or an error message.
        """
        logger.info(f"SceneGenerator: Generating scene for project '{project_id}', chapter '{chapter_id}'. Previous order: {previous_scene_order}. Summary: '{prompt_summary}'")
        retrieved_nodes: List[NodeWithScore] = [] # Initialize here

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
            retrieved_nodes = await retriever.aretrieve(retrieval_query) # Assign to variable
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
                 actual_previous_order = max(order for order, _ in explicit_previous_scenes) if explicit_previous_scenes else None
                 for order, content in explicit_previous_scenes:
                      label = f"Immediately Previous Scene (Order: {order})" if order == actual_previous_order else f"Previous Scene (Order: {order})"
                      previous_scenes_prompt_part += f"**{label}:**\n```markdown\n{content}\n```\n\n"
            else:
                 previous_scenes_prompt_part = "**Previous Scene(s):** N/A (Generating the first scene)\n\n"

            # Construct main instruction based on prompt_summary
            main_instruction = ""
            if prompt_summary:
                main_instruction = f"Please write a draft for the next scene, focusing on the following guidance: '{prompt_summary}'. It should follow the previous scene(s) provided below.\n\n"
            else:
                main_instruction = "Please write a draft for the next scene, ensuring it follows the previous scene(s) provided below.\n\n"

            user_message_content = (
                f"{main_instruction}"
                f"**Project Plan:**\n```markdown\n{explicit_plan}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{explicit_synopsis}\n```\n\n"
                f"{previous_scenes_prompt_part}"
                f"**Additional Retrieved Context:**\n```markdown\n{rag_context_str}\n```\n\n"
                f"**New Scene Details:**\n"
                f"- Belongs to: Chapter ID '{chapter_id}'\n"
                f"- Should logically follow the provided previous scene(s).\n"
            )

            user_message_content += (
                "\n**Instructions:**\n"
                "- Generate the new scene content in pure Markdown format.\n"
                "- Start directly with the scene content (e.g., a heading like '## Scene Title' or directly with narrative).\n"
                "- Ensure the new scene flows logically from the previous scene(s).\n"
                "- Maintain consistency with characters, plot points, and world details mentioned in the Plan, Synopsis, and other context.\n"
                "- Do NOT add explanations or commentary outside the new scene's Markdown content."
            )

            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"

            # --- 3. Call LLM via Retry Helper ---
            logger.debug(f"SceneGenerator: Calling _execute_llm_complete...")
            llm_response = await self._execute_llm_complete(full_prompt)
            # --- END MODIFIED ---

            generated_text = llm_response.text if llm_response else ""

            if not generated_text.strip():
                 logger.warning("LLM returned an empty response for scene generation.")
                 # --- MODIFIED: Add "Error: " prefix ---
                 return "Error: The AI failed to generate a scene draft. Please try again."
                 # --- END MODIFIED ---

            logger.info(f"Enhanced scene generation successful for project '{project_id}', chapter '{chapter_id}'.")
            return generated_text.strip()

        # --- ADDED: Specific handling for ClientError after retries ---
        except ClientError as e:
             if _is_retryable_google_api_error(e): # Check if it's the 429 error that persisted
                  logger.error(f"Rate limit error persisted after retries for scene generation: {e}", exc_info=False)
                  # --- MODIFIED: Add "Error: " prefix ---
                  return f"Error: Rate limit exceeded after multiple retries. Please wait and try again."
                  # --- END MODIFIED ---
             else:
                  # Handle other non-retryable ClientErrors
                  logger.error(f"Non-retryable ClientError during scene generation for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
                  # --- MODIFIED: Add "Error: " prefix ---
                  return f"Error: An unexpected error occurred while communicating with the AI service. Details: {e}"
                  # --- END MODIFIED ---
        # --- END ADDED ---
        except Exception as e:
            logger.error(f"Error during scene generation processing for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            # --- MODIFIED: Add "Error: " prefix ---
            return f"Error: An unexpected error occurred during scene generation. Please check logs."
            # --- END MODIFIED ---