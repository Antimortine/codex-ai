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
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Optional, Set # Import Set

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted # Import base error

from app.core.config import settings # Import settings directly

logger = logging.getLogger(__name__)

# --- Define a retry predicate function ---
def _is_retryable_google_api_error(exception):
    """Return True if the exception is a Google API 429 error."""
    if isinstance(exception, GoogleAPICallError):
        if hasattr(exception, 'status_code') and exception.status_code == 429: logger.warning("Google API rate limit hit (429 status code). Retrying rephrase..."); return True
        if isinstance(exception, ResourceExhausted): logger.warning("Google API ResourceExhausted error encountered. Retrying rephrase..."); return True
        if hasattr(exception, 'message') and '429' in str(exception.message): logger.warning("Google API rate limit hit (429 in message). Retrying rephrase..."); return True
    logger.debug(f"Non-retryable error encountered during rephrase: {type(exception)}")
    return False
# --- End retry predicate ---

class Rephraser:
    """Handles RAG rephrasing logic."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        if not index: raise ValueError("Rephraser requires a valid VectorStoreIndex instance.")
        if not llm: raise ValueError("Rephraser requires a valid LLM instance.")
        self.index = index
        self.llm = llm
        logger.info("Rephraser initialized.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
        retry=retry_if_exception(_is_retryable_google_api_error),
        reraise=True
    )
    async def _execute_llm_complete(self, prompt: str):
        """Helper function to isolate the LLM call for retry logic."""
        logger.info(f"Calling LLM for rephrase suggestions (Temperature: {settings.LLM_TEMPERATURE})...") # Log temp
        logger.debug(f"--- Rephrase Prompt Start ---\n{prompt}\n--- Rephrase Prompt End ---")
        # --- MODIFIED: Explicitly pass temperature ---
        return await self.llm.acomplete(prompt, temperature=settings.LLM_TEMPERATURE)
        # --- END MODIFIED ---

    async def rephrase(
        self,
        project_id: str,
        selected_text: str,
        context_before: Optional[str],
        context_after: Optional[str],
        explicit_plan: Optional[str], # Now optional
        explicit_synopsis: Optional[str], # Now optional
        paths_to_filter: Optional[Set[str]] = None
        ) -> List[str]:
        logger.info(f"Rephraser: Starting rephrase for project '{project_id}'. Text: '{selected_text[:50]}...'")

        if not selected_text.strip():
             logger.warning("Rephraser: Received empty selected_text. Returning empty suggestions.")
             return []

        final_paths_to_filter_obj = {Path(p).resolve() for p in (paths_to_filter or set())}
        logger.debug(f"Rephraser: Paths to filter (resolved): {final_paths_to_filter_obj}")
        retrieved_nodes: List[NodeWithScore] = []
        nodes_for_prompt: List[NodeWithScore] = []

        try:
            # 1. Construct Retrieval Query & Retrieve Context (Unchanged logic)
            retrieval_context = f"{context_before or ''} {selected_text} {context_after or ''}".strip()
            retrieval_query = (
                f"Find context relevant to rephrasing the specific text: '{selected_text}'. "
                f"The surrounding passage is: '{retrieval_context}'."
            )
            logger.debug(f"Constructed retrieval query for rephrase: '{retrieval_query}'")
            logger.debug(f"Creating retriever for rephrase with top_k={settings.RAG_GENERATION_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K,
                filters=MetadataFilters(filters=[ExactMatchFilter(key="project_id", value=project_id)]),
            )
            retrieved_nodes = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for rephrase context.")
            if retrieved_nodes:
                log_nodes = [(n.node_id, n.metadata.get('file_path'), n.score) for n in retrieved_nodes]
                logger.debug(f"Rephraser: Nodes retrieved BEFORE filtering: {log_nodes}")
            else:
                logger.debug("Rephraser: No nodes retrieved.")

            # --- Deduplication and Filtering (Unchanged logic) ---
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
                logger.debug(f"Rephraser: Starting node filtering against {len(final_paths_to_filter_obj)} filter paths.")
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
                logger.debug(f"Rephraser: Nodes remaining AFTER filtering (for prompt): {log_nodes_after}")
            else:
                logger.debug("Rephraser: No nodes remaining after filtering.")

            # --- Format RAG context (Unchanged logic) ---
            rag_context_list = []
            if nodes_for_prompt:
                 for node_with_score in nodes_for_prompt:
                      node = node_with_score.node
                      doc_type = node.metadata.get('document_type', 'Unknown')
                      doc_title = node.metadata.get('document_title', 'Unknown Source')
                      char_name = node.metadata.get('character_name')
                      char_info = f" (Character: {char_name})" if char_name and doc_type != 'Character' else ""
                      source_label = f"Source ({doc_type}: \"{doc_title}\"{char_info})"
                      node_content = node.get_content(); max_node_len = 500
                      truncated_content = node_content[:max_node_len] + ('...' if len(node_content) > max_node_len else '')
                      rag_context_list.append(f"{source_label}\n\n{truncated_content}")
            rag_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No specific context was retrieved via search."
            logger.debug(f"Rephraser: Final rag_context_str for prompt:\n---\n{rag_context_str}\n---")


            # 2. Build Rephrase Prompt
            logger.debug("Building rephrase prompt...")
            system_prompt = (
                "You are an expert writing assistant. Your task is to rephrase the user's selected text, providing several alternative phrasings. "
                "Use the surrounding text and the broader project context provided (Plan, Synopsis, Retrieved Snippets) to ensure the suggestions fit naturally and maintain consistency with the overall narrative style and tone."
            )

            user_message_content = (
                f"Please provide {settings.RAG_REPHRASE_SUGGESTION_COUNT} alternative ways to phrase the 'Text to Rephrase' below, considering the context.\n\n"
            )

            # --- MODIFIED: Conditionally add project context ---
            if explicit_plan:
                user_message_content += f"**Project Plan:**\n```markdown\n{explicit_plan}\n```\n\n"
            if explicit_synopsis:
                user_message_content += f"**Project Synopsis:**\n```markdown\n{explicit_synopsis}\n```\n\n"
            # --- END MODIFIED ---

            user_message_content += (
                f"**Additional Retrieved Context:**\n```markdown\n{rag_context_str}\n```\n\n"
            )
            if context_before or context_after:
                 user_message_content += "**Surrounding Text:**\n```\n"
                 if context_before: user_message_content += f"{context_before}\n"
                 user_message_content += f"[[[--- TEXT TO REPHRASE ---]]]\n{selected_text}\n[[[--- END TEXT TO REPHRASE ---]]]\n"
                 if context_after: user_message_content += f"{context_after}\n"
                 user_message_content += "```\n\n"
            else:
                 user_message_content += f"**Text to Rephrase:**\n```\n{selected_text}\n```\n\n"
            user_message_content += (
                f"**Instructions:**\n"
                f"- Provide exactly {settings.RAG_REPHRASE_SUGGESTION_COUNT} distinct suggestions.\n"
                f"- Each suggestion should be a direct replacement for the 'Text to Rephrase'.\n"
                f"- Maintain the original meaning and approximate length.\n"
                f"- Match the tone and style suggested by the surrounding text and context.\n"
                f"- Output the suggestions as a simple numbered list (e.g., '1. Suggestion one\\n2. Suggestion two').\n"
                f"- Just output the numbered list of suggestions."
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"


            # 3. Call LLM via retry helper
            llm_response = await self._execute_llm_complete(full_prompt)
            generated_text = llm_response.text.strip() if llm_response else ""

            if not generated_text:
                 logger.warning("LLM returned an empty response for rephrase.")
                 return ["Error: The AI failed to generate suggestions. Please try again."]

            # 4. Parse the Numbered List Response (Unchanged)
            logger.debug(f"Raw LLM response for parsing:\n{generated_text}")
            suggestions = re.findall(r"^\s*\d+\.\s*(.*)", generated_text, re.MULTILINE)
            if not suggestions:
                logger.warning(f"Could not parse numbered list from LLM response. Response was:\n{generated_text}")
                # Fallback parsing: split by lines, remove empty, take first N
                suggestions = [line.strip() for line in generated_text.splitlines() if line.strip()]
                if not suggestions: return [f"Error: Could not parse suggestions. Raw response: {generated_text}"]
                logger.warning(f"Fallback parsing used (split by newline), got {len(suggestions)} potential suggestions.")

            suggestions = [s.strip() for s in suggestions if s.strip()][:settings.RAG_REPHRASE_SUGGESTION_COUNT]

            logger.info(f"Successfully parsed {len(suggestions)} rephrase suggestions for project '{project_id}'.")
            return suggestions

        # --- Exception Handling (Unchanged) ---
        except GoogleAPICallError as e:
             if _is_retryable_google_api_error(e):
                  logger.error(f"Rate limit error persisted after retries for rephrase: {e}", exc_info=False)
                  return [f"Error: Rate limit exceeded after multiple retries. Please wait and try again."]
             else:
                  logger.error(f"Non-retryable GoogleAPICallError during rephrase for project '{project_id}': {e}", exc_info=True)
                  return [f"Error: An unexpected error occurred while communicating with the AI service. Details: {e}"]
        except Exception as e:
             logger.error(f"Error during rephrase for project '{project_id}': {e}", exc_info=True)
             return [f"Error: An unexpected internal error occurred while rephrasing."]