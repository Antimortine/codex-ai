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
import re # Import re
from pathlib import Path
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import Response, NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Tuple, Optional, Dict, Set # Import Set

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Define a retry predicate function ---
def _is_retryable_google_api_error(exception):
    """Return True if the exception is a Google API 429 error."""
    if isinstance(exception, GoogleAPICallError):
        if hasattr(exception, 'status_code') and exception.status_code == 429: logger.warning("Google API rate limit hit (429 status code). Retrying query..."); return True
        if isinstance(exception, ResourceExhausted): logger.warning("Google API ResourceExhausted error encountered. Retrying query..."); return True
        if hasattr(exception, 'message') and '429' in str(exception.message): logger.warning("Google API rate limit hit (429 in message). Retrying query..."); return True
    logger.debug(f"Non-retryable error encountered during query: {type(exception)}")
    return False
# --- End retry predicate ---


class QueryProcessor:
    """Handles RAG querying logic, including explicit context."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        if not index: raise ValueError("QueryProcessor requires a valid VectorStoreIndex instance.")
        if not llm: raise ValueError("QueryProcessor requires a valid LLM instance.")
        self.index = index; self.llm = llm; logger.info("QueryProcessor initialized.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
        retry=retry_if_exception(_is_retryable_google_api_error),
        reraise=True
    )
    async def _execute_llm_complete(self, prompt: str):
        """Helper function to isolate the LLM call for retry logic."""
        logger.info(f"Calling LLM with combined context for query...")
        logger.debug(f"--- Query Prompt Start ---\n{prompt}\n--- Query Prompt End ---") # Log prompt
        return await self.llm.acomplete(prompt)

    async def query(self, project_id: str, query_text: str, explicit_plan: str, explicit_synopsis: str,
                  direct_sources_data: Optional[List[Dict]] = None,
                  paths_to_filter: Optional[Set[str]] = None
                  ) -> Tuple[str, List[NodeWithScore], Optional[List[Dict[str, str]]]]:
        logger.info(f"QueryProcessor: Received query for project '{project_id}': '{query_text}'")
        retrieved_nodes: List[NodeWithScore] = []
        nodes_for_prompt: List[NodeWithScore] = []
        direct_sources_info_list: Optional[List[Dict[str, str]]] = None
        final_paths_to_filter_obj = {Path(p).resolve() for p in (paths_to_filter or set())}
        logger.debug(f"QueryProcessor: Paths to filter (resolved): {final_paths_to_filter_obj}")

        if direct_sources_data:
             direct_sources_info_list = []
             for source in direct_sources_data:
                 direct_sources_info_list.append({
                     "type": source.get("type", "Unknown"),
                     "name": source.get("name", "Unknown")
                 })

        try:
            # 1. Create Retriever & Retrieve Nodes
            logger.debug(f"Creating retriever with top_k={settings.RAG_QUERY_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(index=self.index, similarity_top_k=settings.RAG_QUERY_SIMILARITY_TOP_K, filters=MetadataFilters(filters=[ExactMatchFilter(key="project_id", value=project_id)]))
            logger.info(f"Retrieving nodes for query: '{query_text}'")
            retrieved_nodes = await retriever.aretrieve(query_text)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for query context.")
            if retrieved_nodes:
                log_nodes = [(n.node_id, n.metadata.get('file_path'), n.score) for n in retrieved_nodes]
                logger.debug(f"QueryProcessor: Nodes retrieved BEFORE filtering: {log_nodes}")
            else:
                logger.debug("QueryProcessor: No nodes retrieved.")

            # --- ADDED: Deduplicate retrieved nodes before filtering ---
            unique_retrieved_nodes_map = {}
            if retrieved_nodes:
                for node_with_score in retrieved_nodes:
                    node = node_with_score.node
                    # Use text content and file path as a key for uniqueness
                    unique_key = (node.get_content(), node.metadata.get('file_path'))
                    # Keep the node with the highest score if duplicates found
                    if unique_key not in unique_retrieved_nodes_map or node_with_score.score > unique_retrieved_nodes_map[unique_key].score:
                        unique_retrieved_nodes_map[unique_key] = node_with_score
            unique_retrieved_nodes = list(unique_retrieved_nodes_map.values())
            if len(unique_retrieved_nodes) < len(retrieved_nodes):
                logger.debug(f"Deduplicated {len(retrieved_nodes) - len(unique_retrieved_nodes)} nodes based on content and file path.")
            # --- END ADDED ---

            # --- Filter unique retrieved nodes using Path objects ---
            if unique_retrieved_nodes: # Filter the deduplicated list
                logger.debug(f"QueryProcessor: Starting node filtering against {len(final_paths_to_filter_obj)} filter paths.")
                for node_with_score in unique_retrieved_nodes: # Iterate over unique nodes
                    node = node_with_score.node
                    node_path_str = node.metadata.get('file_path')
                    if not node_path_str:
                        logger.warning(f"Node {node.node_id} missing 'file_path' metadata. Including in prompt.")
                        nodes_for_prompt.append(node_with_score) # Append NodeWithScore
                        continue
                    try:
                        node_path_obj = Path(node_path_str).resolve()
                        is_filtered = node_path_obj in final_paths_to_filter_obj
                        logger.debug(f"  Comparing Node Path: {node_path_obj} | In Filter Set: {is_filtered}")
                        if not is_filtered:
                            nodes_for_prompt.append(node_with_score) # Append NodeWithScore
                    except Exception as e:
                        logger.error(f"Error resolving or comparing path '{node_path_str}' for node {node.node_id}. Including node. Error: {e}")
                        nodes_for_prompt.append(node_with_score) # Append NodeWithScore

                if len(nodes_for_prompt) < len(unique_retrieved_nodes):
                    logger.debug(f"Filtered {len(unique_retrieved_nodes) - len(nodes_for_prompt)} unique retrieved nodes based on paths_to_filter.")
                else:
                    logger.debug("No unique nodes were filtered based on paths_to_filter.")
            if nodes_for_prompt:
                log_nodes_after = [(n.node_id, n.metadata.get('file_path'), n.score) for n in nodes_for_prompt]
                logger.debug(f"QueryProcessor: Nodes remaining AFTER filtering (for prompt): {log_nodes_after}")
            else:
                logger.debug("QueryProcessor: No nodes remaining after filtering.")

            # 2. Build Prompt
            logger.debug("Building query prompt with explicit, direct, and retrieved context...")
            system_prompt = (
                "You are an AI assistant answering questions about a creative writing project. "
                "Use the provided Project Plan, Project Synopsis, Directly Requested Content section(s) (if provided), and Retrieved Context Snippets to answer the user's query accurately and concisely. "
                "Prioritize the Directly Requested Content if it seems most relevant to the query. "
                "If the context doesn't contain the answer, say that you cannot answer based on the provided information."
            )
            user_message_content = (
                f"**User Query:**\n{query_text}\n\n"
                f"**Project Plan:**\n```markdown\n{explicit_plan or 'Not Available'}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{explicit_synopsis or 'Not Available'}\n```\n\n"
            )
            if direct_sources_data:
                 user_message_content += "**Directly Requested Content:**\n"
                 for i, source_data in enumerate(direct_sources_data):
                      source_type = source_data.get('type', 'Unknown'); source_name = source_data.get('name', f'Source {i+1}'); source_content = source_data.get('content', ''); truncated_direct_content = source_content
                      user_message_content += (f"--- Start Directly Requested {source_type}: \"{source_name}\" ---\n" f"```markdown\n{truncated_direct_content}\n```\n" f"--- End Directly Requested {source_type}: \"{source_name}\" ---\n\n")

            # --- Use filtered nodes_for_prompt and corrected formatting ---
            rag_context_list = []
            if nodes_for_prompt: # Use filtered nodes
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
            retrieved_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No additional relevant context snippets were retrieved via search."
            logger.debug(f"QueryProcessor: Final rag_context_str for prompt:\n---\n{retrieved_context_str}\n---")

            user_message_content += (
                 f"**Retrieved Context Snippets:**\n```markdown\n{retrieved_context_str}\n```\n\n"
                 f"**Instruction:** Based *only* on the provided Plan, Synopsis, Directly Requested Content (if any), and Retrieved Context, answer the User Query."
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"

            # 3. Call LLM via retry helper (Unchanged)
            llm_response = await self._execute_llm_complete(full_prompt)
            answer = llm_response.text.strip() if llm_response else ""
            logger.info("LLM call complete.")
            if not answer: logger.warning("LLM query returned an empty response string."); answer = "(The AI did not provide an answer based on the context.)"

            # --- Return the filtered nodes_for_prompt ---
            logger.info(f"Query successful. Returning answer, {len(nodes_for_prompt)} filtered source nodes, and direct source info list (if any).")
            return answer, nodes_for_prompt, direct_sources_info_list

        # --- Exception Handling ---
        except GoogleAPICallError as e:
             if _is_retryable_google_api_error(e):
                 logger.error(f"Rate limit error persisted after retries for query: {e}", exc_info=False)
                 error_message = f"Error: Rate limit exceeded for query after multiple retries. Please wait and try again."
                 # Return filtered nodes even on error
                 return error_message, nodes_for_prompt, None
             else:
                 logger.error(f"Non-retryable GoogleAPICallError during query for project '{project_id}': {e}", exc_info=True)
                 error_message = f"Error: Sorry, an error occurred while communicating with the AI service for project '{project_id}'. Details: {e}"
                 return error_message, [], None
        except Exception as e:
             logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
             error_message = f"Error: Sorry, an internal error occurred processing the query. Please check logs."
             return error_message, [], None