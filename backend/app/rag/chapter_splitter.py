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
import re # Import regex for parsing
from pathlib import Path
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import NodeWithScore
from llama_index.core.llms import LLM
from fastapi import HTTPException, status

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted # Import base error

from typing import List, Optional, Set # Import Set

from app.models.ai import ProposedScene
from app.core.config import settings # Import settings
from app.services.file_service import file_service

logger = logging.getLogger(__name__)

# --- Define a retry predicate function ---
def _is_retryable_google_api_error(exception):
    """Return True if the exception is a Google API 429 error."""
    if isinstance(exception, GoogleAPICallError):
        if hasattr(exception, 'status_code') and exception.status_code == 429: logger.warning("Google API rate limit hit (429 status code). Retrying chapter split..."); return True
        if isinstance(exception, ResourceExhausted): logger.warning("Google API ResourceExhausted error encountered. Retrying chapter split..."); return True
        if hasattr(exception, 'message') and '429' in str(exception.message): logger.warning("Google API rate limit hit (429 in message). Retrying chapter split..."); return True
    logger.debug(f"Non-retryable error encountered during chapter split: {type(exception)}")
    return False
# --- End retry predicate ---


class ChapterSplitter:
    """Handles the logic for splitting chapter text into proposed scenes using a single LLM call and parsing."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        if not index: raise ValueError("ChapterSplitter requires a valid VectorStoreIndex instance.")
        if not llm: raise ValueError("ChapterSplitter requires a valid LLM instance.")
        self.index = index # Store index
        self.llm = llm
        logger.info("ChapterSplitter initialized.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
        retry=retry_if_exception(_is_retryable_google_api_error),
        reraise=True
    )
    async def _execute_llm_complete(self, prompt: str):
        """Helper function to isolate the LLM call for retry logic."""
        # --- MODIFIED: Add prompt size logging ---
        char_count = len(prompt)
        est_tokens = char_count // 4
        logger.info(f"Calling LLM acomple for chapter splitting (Temperature: {settings.LLM_TEMPERATURE}, Chars: {char_count}, Est. Tokens: {est_tokens})...")
        logger.debug(f"--- Chapter Split Prompt Start (Chars: {char_count}, Est. Tokens: {est_tokens}) ---\n{prompt}\n--- Chapter Split Prompt End ---")
        # --- END MODIFIED ---
        response = await self.llm.acomplete(prompt, temperature=settings.LLM_TEMPERATURE)
        return response

    async def split(
        self,
        project_id: str,
        chapter_id: str,
        chapter_content: str,
        explicit_plan: Optional[str],
        explicit_synopsis: Optional[str],
        explicit_chapter_plan: Optional[str],
        explicit_chapter_synopsis: Optional[str],
        paths_to_filter: Optional[Set[str]] = None
        ) -> List[ProposedScene]:
        """
        Splits chapter content into proposed scenes using a single LLM call and parsing.

        Returns:
            A list of ProposedScene objects or raises HTTPException on failure.
        """
        logger.info(f"ChapterSplitter: Starting split via Single Call for chapter '{chapter_id}' in project '{project_id}'.")

        if not chapter_content.strip():
            logger.warning("Chapter content is empty, cannot split.")
            return []

        chapter_title = f"Chapter {chapter_id}" # Default
        try:
            project_meta = file_service.read_project_metadata(project_id)
            chapter_info = project_meta.get('chapters', {}).get(chapter_id)
            if chapter_info and chapter_info.get('title'):
                chapter_title = chapter_info['title']
        except Exception as e:
            logger.warning(f"Could not retrieve chapter title for {chapter_id}: {e}")

        final_paths_to_filter_obj = {Path(p).resolve() for p in (paths_to_filter or set())}
        logger.debug(f"ChapterSplitter: Paths to filter (resolved): {final_paths_to_filter_obj}")
        retrieved_nodes: List[NodeWithScore] = []
        nodes_for_prompt: List[NodeWithScore] = []

        try:
            # Retrieve RAG Context (Unchanged logic)
            logger.debug("Retrieving context for chapter splitting...")
            retrieval_query = f"Find context relevant to splitting the following chapter content into scenes: {chapter_content[:1000]}..."
            logger.debug(f"Constructed retrieval query for chapter split: '{retrieval_query}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K,
                filters=MetadataFilters(filters=[ExactMatchFilter(key="project_id", value=project_id)]),
            )
            retrieved_nodes = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for chapter split context.")
            if retrieved_nodes:
                log_nodes = [(n.node_id, n.metadata.get('file_path'), n.score) for n in retrieved_nodes]
                logger.debug(f"ChapterSplitter: Nodes retrieved BEFORE filtering: {log_nodes}")
            else:
                logger.debug("ChapterSplitter: No nodes retrieved.")

            # Deduplication and Filtering (Unchanged logic)
            unique_retrieved_nodes_map = {}
            if retrieved_nodes:
                for node_with_score in retrieved_nodes:
                    node = node_with_score.node
                    unique_key = (node.get_content(), node.metadata.get('file_path'))
                    if unique_key not in unique_retrieved_nodes_map or node_with_score.score > unique_retrieved_nodes_map[unique_key].score:
                        unique_retrieved_nodes_map[unique_key] = node_with_score
            unique_retrieved_nodes = list(unique_retrieved_nodes_map.values())
            if len(unique_retrieved_nodes) < len(retrieved_nodes):
                logger.debug(f"Deduplicated {len(retrieved_nodes) - len(unique_retrieved_nodes)} nodes based on content and file path.")

            if unique_retrieved_nodes:
                logger.debug(f"ChapterSplitter: Starting node filtering against {len(final_paths_to_filter_obj)} filter paths.")
                for node_with_score in unique_retrieved_nodes:
                    node = node_with_score.node
                    node_path_str = node.metadata.get('file_path')
                    if not node_path_str:
                        logger.warning(f"Node {node.node_id} missing 'file_path' metadata. Including in prompt.")
                        nodes_for_prompt.append(node_with_score)
                        continue
                    try:
                        node_path_obj = Path(node_path_str).resolve()
                        is_filtered = node_path_obj in final_paths_to_filter_obj
                        logger.debug(f"  Comparing Node Path: {node_path_obj} | In Filter Set: {is_filtered}")
                        if not is_filtered:
                            nodes_for_prompt.append(node_with_score)
                    except Exception as e:
                        logger.error(f"Error resolving or comparing path '{node_path_str}' for node {node.node_id}. Including node. Error: {e}")
                        nodes_for_prompt.append(node_with_score)

                if len(nodes_for_prompt) < len(unique_retrieved_nodes):
                    logger.debug(f"Filtered {len(unique_retrieved_nodes) - len(nodes_for_prompt)} unique retrieved nodes based on paths_to_filter.")
                else:
                    logger.debug("No unique nodes were filtered based on paths_to_filter.")
            if nodes_for_prompt:
                log_nodes_after = [(n.node_id, n.metadata.get('file_path'), n.score) for n in nodes_for_prompt]
                logger.debug(f"ChapterSplitter: Nodes remaining AFTER filtering (for prompt): {log_nodes_after}")
            else:
                logger.debug("ChapterSplitter: No nodes remaining after filtering.")

            # Format RAG context (with truncation)
            rag_context_list = []
            if nodes_for_prompt:
                 for node_with_score in nodes_for_prompt:
                      node = node_with_score.node
                      doc_type = node.metadata.get('document_type', 'Unknown')
                      doc_title = node.metadata.get('document_title', 'Unknown Source')
                      char_name = node.metadata.get('character_name')
                      char_info = f" (Character: {char_name})" if char_name and doc_type != 'Character' else ""
                      source_label = f"Source ({doc_type}: \"{doc_title}\"{char_info})"
                      node_content = node.get_content()
                      # --- MODIFIED: Use MAX_CONTEXT_LENGTH ---
                      max_node_len = settings.MAX_CONTEXT_LENGTH
                      truncated_content = node_content[:max_node_len] + ('...' if len(node_content) > max_node_len else '')
                      # --- END MODIFIED ---
                      rag_context_list.append(f"{source_label}\n\n{truncated_content}")
            rag_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No additional relevant context snippets were retrieved via search."
            logger.debug(f"ChapterSplitter: Final rag_context_str for prompt:\n---\n{rag_context_str}\n---")


            # --- Build Prompt with Strict Formatting ---
            logger.debug("Building strict format prompt for chapter splitting...")
            system_prompt = (
                "You are an AI assistant specialized in analyzing and structuring narrative text. "
                "Your task is to split the provided chapter content into distinct scenes based on logical breaks "
                "(time, location, POV shifts, topic changes, dialogue starts/ends). "
                "For each scene, provide a concise title and the full Markdown content."
            )

            scene_start_delim = "<<<SCENE_START>>>"; scene_end_delim = "<<<SCENE_END>>>"; title_prefix = "TITLE:"; content_prefix = "CONTENT:"

            user_message_content = (
                f"Analyze the chapter content provided below (between <<<CHAPTER_START>>> and <<<CHAPTER_END>>>) and split it into distinct scenes. "
                f"The chapter ID is '{chapter_id}' and the chapter title is '{chapter_title}'.\n\n"
                "Use the provided Project Plan, Project Synopsis, Chapter Plan, Chapter Synopsis, and Additional Context for context on the overall story and potential scene breaks.\n\n"
            )

            # Conditionally add context sections (with truncation for project level)
            if explicit_plan:
                # --- MODIFIED: Use MAX_CONTEXT_LENGTH ---
                truncated_plan = explicit_plan[:settings.MAX_CONTEXT_LENGTH] + ('...' if len(explicit_plan) > settings.MAX_CONTEXT_LENGTH else '')
                user_message_content += f"**Project Plan:**\n```markdown\n{truncated_plan}\n```\n\n"
                # --- END MODIFIED ---
            if explicit_synopsis:
                # --- MODIFIED: Use MAX_CONTEXT_LENGTH ---
                truncated_synopsis = explicit_synopsis[:settings.MAX_CONTEXT_LENGTH] + ('...' if len(explicit_synopsis) > settings.MAX_CONTEXT_LENGTH else '')
                user_message_content += f"**Project Synopsis:**\n```markdown\n{truncated_synopsis}\n```\n\n"
                # --- END MODIFIED ---
            # Chapter context - NO TRUNCATION
            if explicit_chapter_plan:
                user_message_content += f"**Chapter Plan (for Chapter '{chapter_title}'):**\n```markdown\n{explicit_chapter_plan}\n```\n\n"
            if explicit_chapter_synopsis:
                user_message_content += f"**Chapter Synopsis (for Chapter '{chapter_title}'):**\n```markdown\n{explicit_chapter_synopsis}\n```\n\n"

            user_message_content += (
                f"**Additional Retrieved Context:**\n```markdown\n{rag_context_str}\n```\n\n"
                f"<<<CHAPTER_START>>>\n{chapter_content}\n<<<CHAPTER_END>>>\n\n"
                f"**Output Format Requirement:** Your response MUST consist ONLY of scene blocks. Each scene block MUST start exactly with '{scene_start_delim}' on its own line, followed by a line starting exactly with '{title_prefix} ' and the scene title, followed by a line starting exactly with '{content_prefix}', followed by the full Markdown content of the scene (which can span multiple lines), and finally end exactly with '{scene_end_delim}' on its own line. Ensure the 'content' segments cover the original chapter without overlap or gaps. The title MUST be in the same language as the main chapter content."
                f"\nExample:\n{scene_start_delim}\n{title_prefix} The Arrival\n{content_prefix}\nThe character arrived.\n{scene_end_delim}\n{scene_start_delim}\n{title_prefix} The Conversation\n{content_prefix}\nThey talked for hours.\n{scene_end_delim}"
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"

            # --- Call LLM ---
            llm_response = await self._execute_llm_complete(full_prompt)
            generated_text = llm_response.text.strip() if llm_response else ""

            if not generated_text:
                 logger.warning("LLM returned an empty response for chapter splitting.")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: The AI failed to propose scene splits.")

            # --- Parse the Response (Unchanged logic) ---
            logger.debug("Parsing LLM response for scene splits...")
            proposed_scenes = []
            scene_pattern = re.compile( rf"^{re.escape(scene_start_delim)}\s*?\n" rf"^{re.escape(title_prefix)}\s*(.*?)\s*?\n" rf"^{re.escape(content_prefix)}\s*?\n?" rf"(.*?)" rf"^{re.escape(scene_end_delim)}\s*?$", re.DOTALL | re.MULTILINE )
            matches = scene_pattern.finditer(generated_text); found_scenes = False
            for match in matches:
                found_scenes = True; title = match.group(1).strip(); content = match.group(2).strip()
                if title and content: proposed_scenes.append(ProposedScene(suggested_title=title, content=content)); logger.debug(f"Parsed scene: Title='{title[:50]}...', Content Length={len(content)}")
                else: logger.warning(f"Skipping partially parsed scene block: Title='{title}', Content Present={bool(content)}. Block text: {match.group(0)[:200]}...")
            if not found_scenes: logger.warning(f"Could not parse any scene blocks using delimiters from LLM response. Response start:\n{generated_text[:500]}..."); return []
            concatenated_content = "".join(scene.content for scene in proposed_scenes)
            if len(concatenated_content.strip()) < len(chapter_content.strip()) * 0.8: logger.warning(f"Concatenated split content length ({len(concatenated_content)}) significantly differs from original ({len(chapter_content)}). Potential content loss.")
            logger.info(f"Successfully parsed {len(proposed_scenes)} proposed scenes.")
            return proposed_scenes

        # --- Exception Handling (Unchanged) ---
        except GoogleAPICallError as e:
             if _is_retryable_google_api_error(e):
                  logger.error(f"Rate limit error persisted after retries for chapter split: {e}", exc_info=False)
                  raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Error: Rate limit exceeded after multiple retries. Please wait and try again.") from e
             else:
                  logger.error(f"Non-retryable GoogleAPICallError during chapter split for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
                  raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: An unexpected error occurred while communicating with the AI service. Details: {e}") from e
        except Exception as e:
            logger.error(f"Error during chapter splitting processing for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            if isinstance(e, HTTPException):
                 if not e.detail.startswith("Error: "): e.detail = f"Error: {e.detail}"
                 raise e
            else:
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: An unexpected error occurred during chapter splitting. Please check logs.") from e