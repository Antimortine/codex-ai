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
import re
from fastapi import HTTPException, status
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from pydantic import ValidationError
from typing import List, Tuple, Optional, Dict, Any

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.genai.errors import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

# Retry predicate function (remains the same)
def _is_retryable_google_api_error(exception):
    # ... (implementation unchanged) ...
    if isinstance(exception, ClientError):
        status_code = None
        try:
            if hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
                status_code = exception.response.status_code
            elif hasattr(exception, 'status_code'):
                 status_code = exception.status_code
            elif isinstance(exception.args, (list, tuple)) and len(exception.args) > 0:
                if isinstance(exception.args[0], int):
                    status_code = int(exception.args[0])
                elif isinstance(exception.args[0], str) and '429' in exception.args[0]:
                    logger.warning("Google API rate limit hit (ClientError 429 - string check). Retrying scene generation...")
                    return True
        except (ValueError, TypeError, IndexError, AttributeError):
            pass
        if status_code == 429:
             logger.warning("Google API rate limit hit (ClientError 429). Retrying scene generation...")
             return True
    logger.debug(f"Non-retryable error encountered during scene generation: {type(exception)}")
    return False

class SceneGenerator:
    """Handles RAG scene generation logic using a single LLM call and parsing."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        if not index: raise ValueError("SceneGenerator requires a valid VectorStoreIndex instance.")
        if not llm: raise ValueError("SceneGenerator requires a valid LLM instance.")
        self.index = index
        self.llm = llm
        logger.info("SceneGenerator initialized.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
        retry=retry_if_exception(_is_retryable_google_api_error),
        reraise=True
    )
    async def _execute_llm_complete(self, prompt: str):
        """Helper function to isolate the LLM call for retry logic."""
        logger.info("Calling LLM acomple for scene generation...")
        response = await self.llm.acomplete(prompt)
        return response

    async def generate_scene(
        self,
        project_id: str,
        chapter_id: str,
        prompt_summary: Optional[str],
        previous_scene_order: Optional[int],
        explicit_plan: str,
        explicit_synopsis: str,
        explicit_previous_scenes: List[Tuple[int, str]]
        ) -> Dict[str, str]:
        """
        Generates a scene draft (title and content) using a single LLM call
        based on provided explicit context and RAG context. Parses the result.

        Returns:
            A dictionary containing 'title' and 'content' of the generated scene,
            or raises an HTTPException on failure.
        """
        logger.info(f"SceneGenerator: Generating scene via Single Call for project '{project_id}', chapter '{chapter_id}'.")
        retrieved_nodes: List[NodeWithScore] = []

        try:
            # --- 1. Retrieve RAG Context ---
            # (Context retrieval and truncation logic remains the same)
            retrieval_query = f"Context relevant for writing a new scene after scene order {previous_scene_order} in chapter {chapter_id}."
            if prompt_summary:
                retrieval_query += f" Scene focus: {prompt_summary}"
            logger.debug(f"Constructed retrieval query: '{retrieval_query}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K,
                filters=MetadataFilters(filters=[ExactMatchFilter(key="project_id", value=project_id)]),
            )
            retrieved_nodes = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for RAG context.")
            rag_context_list = []
            if retrieved_nodes:
                 for node in retrieved_nodes:
                      char_name = node.metadata.get('character_name')
                      char_info = f" [Character: {char_name}]" if char_name else ""
                      node_content = node.get_content()
                      max_node_len = 500
                      truncated_content = node_content[:max_node_len] + ('...' if len(node_content) > max_node_len else '')
                      rag_context_list.append(f"Source: {node.metadata.get('file_path', 'N/A')}{char_info}\n\n{truncated_content}")
            rag_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No additional context retrieved via search."

            # --- 2. Build Generation Prompt with Strict Formatting ---
            # (Prompt building remains the same)
            logger.debug("Building strict format generation prompt...")
            system_prompt = (
                "You are an expert writing assistant helping a user draft the next scene in their creative writing project. "
                "Generate a coherent and engaging scene draft in Markdown format. "
                "Pay close attention to the provided Project Plan, Synopsis, and the content of the Immediately Previous Scene(s) to ensure consistency and logical progression. "
                "Also consider the Additional Context retrieved via search."
            )
            previous_scenes_prompt_part = ""
            if explicit_previous_scenes:
                 actual_previous_order = max(order for order, _ in explicit_previous_scenes) if explicit_previous_scenes else None
                 for order, content in explicit_previous_scenes:
                      label = f"Immediately Previous Scene (Order: {order})" if order == actual_previous_order else f"Previous Scene (Order: {order})"
                      max_prev_len = 1000
                      truncated_prev_content = content[:max_prev_len] + ('...' if len(content) > max_prev_len else '')
                      previous_scenes_prompt_part += f"**{label}:**\n```markdown\n{truncated_prev_content}\n```\n\n"
            else:
                 previous_scenes_prompt_part = "**Previous Scene(s):** N/A (Generating the first scene)\n\n"
            main_instruction = f"Guidance for new scene: '{prompt_summary}'.\n\n" if prompt_summary else "Generate the next logical scene based on the context.\n\n"
            max_plan_synopsis_len = 1000
            truncated_plan = (explicit_plan or '')[:max_plan_synopsis_len] + ('...' if len(explicit_plan or '') > max_plan_synopsis_len else '')
            truncated_synopsis = (explicit_synopsis or '')[:max_plan_synopsis_len] + ('...' if len(explicit_synopsis or '') > max_plan_synopsis_len else '')
            user_message_content = (
                f"{main_instruction}"
                f"**Project Plan:**\n```markdown\n{truncated_plan}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{truncated_synopsis}\n```\n\n"
                f"{previous_scenes_prompt_part}"
                f"**Additional Retrieved Context:**\n```markdown\n{rag_context_str}\n```\n\n"
                f"**New Scene Details:**\n"
                f"- Belongs to: Chapter ID '{chapter_id}'\n"
                f"- Should logically follow the provided previous scene(s).\n\n"
                f"**Output Format Requirement:** Your response MUST include a concise scene title formatted as an H2 Markdown heading (e.g., `## The Confrontation`) followed by the Markdown content of the scene itself. Start the response with the H2 heading."
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"


            # --- 3. Call LLM via Retry Helper ---
            logger.debug(f"SceneGenerator: Prompt length: {len(full_prompt)}")
            logger.debug(f"SceneGenerator: Calling _execute_llm_complete...")
            llm_response = await self._execute_llm_complete(full_prompt)
            generated_text = llm_response.text.strip() if llm_response else ""

            if not generated_text:
                 logger.warning("LLM returned an empty response for scene generation.")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: The AI failed to generate a scene draft. Please try again.")

            # --- 4. Parse the Response (More Robustly) ---
            logger.debug("Parsing LLM response for title and content...")
            title = "Untitled Scene"
            content = generated_text # Default to full text if parsing fails

            title_match = re.search(r"^\s*##\s+(.+?)\s*$", generated_text, re.MULTILINE)

            if title_match:
                parsed_title = title_match.group(1).strip()
                content_start_index = title_match.end()
                newline_after_title = generated_text.find('\n', content_start_index)

                # --- MODIFIED: Check if content exists after newline ---
                if newline_after_title != -1:
                    parsed_content = generated_text[newline_after_title:].strip()
                    if parsed_content: # Only assign if there's actual content after newline
                        title = parsed_title
                        content = parsed_content
                        logger.info(f"Successfully parsed title and content via regex: '{title}'")
                    else:
                        # Found title, but content after newline is empty/whitespace
                        logger.warning(f"LLM response had H2 heading '## {parsed_title}' but no substantial content followed. Using default title and full text.")
                        # Fallback: Keep default title and original generated_text as content
                        title = "Untitled Scene"
                        content = generated_text
                else:
                    # Found title, but no newline at all after it
                    logger.warning(f"LLM response had H2 heading '## {parsed_title}' but no newline/content followed. Using default title and full text.")
                    # Fallback: Keep default title and original generated_text as content
                    title = "Untitled Scene"
                    content = generated_text
                # --- END MODIFIED ---
            else:
                logger.warning(f"LLM response did not contain an H2 heading '## Title'. Using default title. Full response start:\n{generated_text[:200]}...")
                # Fallback already handled by initial assignment: title = "Untitled Scene", content = generated_text

            generated_draft = {"title": title, "content": content}

            logger.info(f"Scene generation processed. Title: '{generated_draft['title']}'")
            return generated_draft

        # Exception handling remains the same...
        except ClientError as e:
             if _is_retryable_google_api_error(e):
                  logger.error(f"Rate limit error persisted after retries for scene generation: {e}", exc_info=False)
                  raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Error: Rate limit exceeded after multiple retries. Please wait and try again.") from e
             else:
                  logger.error(f"Non-retryable ClientError during scene generation for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
                  raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: An unexpected error occurred while communicating with the AI service. Details: {e}") from e
        except Exception as e:
            logger.error(f"Error during scene generation processing for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            if isinstance(e, HTTPException):
                 if not e.detail.startswith("Error: "): e.detail = f"Error: {e.detail}"
                 raise e
            else:
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: An unexpected error occurred during scene generation. Please check logs.") from e