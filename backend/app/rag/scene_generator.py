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
from pathlib import Path
from fastapi import HTTPException, status
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from pydantic import ValidationError
from typing import List, Tuple, Optional, Dict, Any, Set # Import Set

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted # Import base error

from app.core.config import settings
from app.services.file_service import file_service # Import file_service to get chapter title


logger = logging.getLogger(__name__)

# Retry predicate function
def _is_retryable_google_api_error(exception):
    """Return True if the exception is a Google API 429 error."""
    if isinstance(exception, GoogleAPICallError):
        if hasattr(exception, 'status_code') and exception.status_code == 429: logger.warning("Google API rate limit hit (429 status code). Retrying scene gen..."); return True
        if isinstance(exception, ResourceExhausted): logger.warning("Google API ResourceExhausted error encountered. Retrying scene gen..."); return True
        if hasattr(exception, 'message') and '429' in str(exception.message): logger.warning("Google API rate limit hit (429 in message). Retrying scene gen..."); return True
    logger.debug(f"Non-retryable error encountered during scene gen: {type(exception)}")
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
        logger.debug(f"--- Scene Gen Prompt Start ---\n{prompt}\n--- Scene Gen Prompt End ---")
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
        explicit_previous_scenes: List[Tuple[int, str]], # Contains (order, content)
        paths_to_filter: Optional[Set[str]] = None
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
        nodes_for_prompt: List[NodeWithScore] = []
        final_paths_to_filter_obj = {Path(p).resolve() for p in (paths_to_filter or set())}
        logger.debug(f"SceneGenerator: Paths to filter (resolved): {final_paths_to_filter_obj}")

        chapter_title = f"Chapter {chapter_id}" # Default
        try:
            project_meta = file_service.read_project_metadata(project_id)
            chapter_info = project_meta.get('chapters', {}).get(chapter_id)
            if chapter_info and chapter_info.get('title'):
                chapter_title = chapter_info['title']
        except Exception as e:
            logger.warning(f"Could not retrieve chapter title for {chapter_id}: {e}")

        try:
            # --- 1. Retrieve RAG Context ---
            # --- REVISED: Retrieval query focuses more on prompt and previous scene ---
            retrieval_query_parts = [
                f"Relevant context for writing the next scene in chapter '{chapter_title}'."
            ]
            if prompt_summary:
                # Make the prompt summary more prominent in the query
                retrieval_query_parts.append(f"The new scene should focus on or involve: {prompt_summary}")
            if explicit_previous_scenes:
                 last_scene_content = explicit_previous_scenes[-1][1]
                 # Use a larger excerpt of the previous scene
                 retrieval_query_parts.append(f"The immediately preceding scene ended with: {last_scene_content[-500:]}") # Last 500 chars
            # Optionally add keywords from plan/synopsis if they seem very relevant
            # retrieval_query_parts.append(f"Keywords from Plan: {explicit_plan[:100]}")
            # retrieval_query_parts.append(f"Keywords from Synopsis: {explicit_synopsis[:100]}")
            retrieval_query = " ".join(retrieval_query_parts)
            # --- END REVISED ---

            logger.debug(f"Constructed retrieval query for scene gen: '{retrieval_query}'")
            retriever = VectorIndexRetriever( index=self.index, similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K, filters=MetadataFilters(filters=[ExactMatchFilter(key="project_id", value=project_id)]), )
            retrieved_nodes = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for RAG context.")
            if retrieved_nodes:
                log_nodes = [(n.node_id, n.metadata.get('file_path'), n.score) for n in retrieved_nodes]
                logger.debug(f"SceneGenerator: Nodes retrieved BEFORE filtering: {log_nodes}")
            else:
                logger.debug("SceneGenerator: No nodes retrieved.")

            # --- Filter retrieved nodes using Path objects ---
            if retrieved_nodes:
                logger.debug(f"SceneGenerator: Starting node filtering against {len(final_paths_to_filter_obj)} filter paths.")
                for node in retrieved_nodes:
                    node_path_str = node.metadata.get('file_path')
                    if not node_path_str:
                        logger.warning(f"Node {node.node_id} missing 'file_path' metadata. Including in prompt.")
                        nodes_for_prompt.append(node)
                        continue
                    try:
                        node_path_obj = Path(node_path_str).resolve()
                        is_filtered = node_path_obj in final_paths_to_filter_obj
                        logger.debug(f"  Comparing Node Path: {node_path_obj} | In Filter Set: {is_filtered}")
                        if not is_filtered:
                            nodes_for_prompt.append(node)
                    except Exception as e:
                        logger.error(f"Error resolving or comparing path '{node_path_str}' for node {node.node_id}. Including node. Error: {e}")
                        nodes_for_prompt.append(node) # Include if error occurs

                if len(nodes_for_prompt) < len(retrieved_nodes):
                    logger.debug(f"Filtered {len(retrieved_nodes) - len(nodes_for_prompt)} retrieved nodes based on paths_to_filter.")
                else:
                    logger.debug("No nodes were filtered based on paths_to_filter.")
            if nodes_for_prompt:
                log_nodes_after = [(n.node_id, n.metadata.get('file_path'), n.score) for n in nodes_for_prompt]
                logger.debug(f"SceneGenerator: Nodes remaining AFTER filtering (for prompt): {log_nodes_after}")
            else:
                logger.debug("SceneGenerator: No nodes remaining after filtering.")

            # --- Format context using type and title (using filtered nodes) ---
            rag_context_list = []
            if nodes_for_prompt: # Use filtered nodes
                 for node_with_score in nodes_for_prompt:
                      node = node_with_score.node
                      doc_type = node.metadata.get('document_type', 'Unknown')
                      doc_title = node.metadata.get('document_title', 'Unknown Source')
                      char_name = node.metadata.get('character_name') # Keep character name if present
                      char_info = f" (Character: {char_name})" if char_name and doc_type != 'Character' else ""
                      source_label = f"Source ({doc_type}: \"{doc_title}\"{char_info})"

                      node_content = node.get_content(); max_node_len = 500 # Keep truncation
                      truncated_content = node_content[:max_node_len] + ('...' if len(node_content) > max_node_len else '')
                      rag_context_list.append(f"{source_label}\n\n{truncated_content}")
            rag_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No additional context retrieved via search."
            logger.debug(f"SceneGenerator: Final rag_context_str for prompt:\n---\n{rag_context_str}\n---")

            # --- 2. Build Generation Prompt ---
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
                      prev_scene_title = f"Scene Order {order}" # Default
                      try:
                          prev_chapter_meta = file_service.read_chapter_metadata(project_id, chapter_id)
                          scene_id = next((sid for sid, data in prev_chapter_meta.get('scenes', {}).items() if data.get('order') == order), None)
                          if scene_id:
                              prev_scene_title = prev_chapter_meta['scenes'][scene_id].get('title', prev_scene_title)
                      except Exception:
                          pass # Ignore errors fetching previous titles for prompt
                      label = f"Immediately Previous Scene (Order: {order}, Title: \"{prev_scene_title}\")" if order == actual_previous_order else f"Previous Scene (Order: {order}, Title: \"{prev_scene_title}\")"
                      max_prev_len = 1000; truncated_prev_content = content[:max_prev_len] + ('...' if len(content) > max_prev_len else '')
                      previous_scenes_prompt_part += f"**{label}:**\n```markdown\n{truncated_prev_content}\n```\n\n"
            else: previous_scenes_prompt_part = "**Previous Scene(s):** N/A (Generating the first scene)\n\n"
            main_instruction = f"Guidance for new scene: '{prompt_summary}'.\n\n" if prompt_summary else "Generate the next logical scene based on the context.\n\n"
            max_plan_synopsis_len = 1000
            truncated_plan = (explicit_plan or '')[:max_plan_synopsis_len] + ('...' if len(explicit_plan or '') > max_plan_synopsis_len else '')
            truncated_synopsis = (explicit_synopsis or '')[:max_plan_synopsis_len] + ('...' if len(explicit_synopsis or '') > max_plan_synopsis_len else '')

            user_message_content = (
                f"{main_instruction}"
                f"**Project Plan:**\n```markdown\n{truncated_plan}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{truncated_synopsis}\n```\n\n"
                f"{previous_scenes_prompt_part}"
                f"**Additional Retrieved Context:**\n```markdown\n{rag_context_str}\n```\n\n" # This now uses titles/types and filtered nodes
                f"**New Scene Details:**\n"
                f"- Belongs to: Chapter '{chapter_title}' (ID: {chapter_id})\n"
                f"- Should logically follow the provided previous scene(s).\n\n"
                f"**Output Format Requirement:** Your response MUST include a concise scene title formatted as an H2 Markdown heading (e.g., `## The Confrontation`) followed by the Markdown content of the scene itself. Start the response with the H2 heading. **IMPORTANT:** The scene title MUST be in the **same language** as the main language used in the provided previous scene(s) or retrieved context."
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"

            # --- 3. Call LLM via Retry Helper (Unchanged) ---
            llm_response = await self._execute_llm_complete(full_prompt)
            generated_text = llm_response.text.strip() if llm_response else ""
            if not generated_text: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: The AI failed to generate a scene draft. Please try again.")

            # --- 4. Parse the Response (Logic remains the same) ---
            logger.debug("Parsing LLM response for title and content...")
            title = "Untitled Scene"; content = generated_text
            title_match = re.search(r"^\s*##\s+(.+?)\s*$", generated_text, re.MULTILINE)
            if title_match:
                parsed_title = title_match.group(1).strip(); content_start_index = title_match.end(); newline_after_title = generated_text.find('\n', content_start_index)
                parsed_content = "" # Initialize
                if newline_after_title != -1: parsed_content = generated_text[newline_after_title:].strip();
                else: parsed_content = generated_text[content_start_index:].strip() # Handle case where content starts immediately after title on same line (less likely)

                if parsed_content: title = parsed_title; content = parsed_content; logger.info(f"Successfully parsed title and content via regex: '{title}'")
                else: logger.warning(f"LLM response had H2 heading '## {parsed_title}' but no substantial content followed."); title = "Untitled Scene"; content = generated_text # Keep original text if parsing fails
            else: logger.warning(f"LLM response did not contain an H2 heading '## Title'. Using default title.")
            generated_draft = {"title": title, "content": content}
            logger.info(f"Scene generation processed. Title: '{generated_draft['title']}'")
            return generated_draft

        # --- Exception handling (Catch GoogleAPICallError) ---
        except GoogleAPICallError as e:
             if _is_retryable_google_api_error(e): raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Error: Rate limit exceeded after multiple retries. Please wait and try again.") from e
             else: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: An unexpected error occurred while communicating with the AI service. Details: {e}") from e
        except Exception as e:
            logger.error(f"Error during scene generation processing for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            if isinstance(e, HTTPException):
                 if not e.detail.startswith("Error: "): e.detail = f"Error: {e.detail}"
                 raise e
            else: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: An unexpected error occurred during scene generation. Please check logs.") from e