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
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import Response, NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Tuple, Optional, Dict # Import Dict

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.api_core.exceptions import GoogleAPICallError, ServiceUnavailable, ResourceExhausted

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Define a retry predicate function ---
# (Unchanged)
def _is_retryable_google_api_error(exception):
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
        # (Initialization unchanged)
        if not index: raise ValueError("QueryProcessor requires a valid VectorStoreIndex instance.")
        if not llm: raise ValueError("QueryProcessor requires a valid LLM instance.")
        self.index = index
        self.llm = llm
        logger.info("QueryProcessor initialized.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
        retry=retry_if_exception(_is_retryable_google_api_error),
        reraise=True
    )
    async def _execute_llm_complete(self, prompt: str):
        """Helper function to isolate the LLM call for retry logic."""
        logger.info(f"Calling LLM with combined context for query...")
        return await self.llm.acomplete(prompt)

    async def query(self, project_id: str, query_text: str, explicit_plan: str, explicit_synopsis: str,
                  direct_sources_data: Optional[List[Dict]] = None
                  ) -> Tuple[str, List[NodeWithScore], Optional[List[Dict[str, str]]]]:
        logger.info(f"QueryProcessor: Received query for project '{project_id}': '{query_text}'")
        retrieved_nodes: List[NodeWithScore] = []
        direct_sources_info_list: Optional[List[Dict[str, str]]] = None
        # --- MODIFIED: Store file paths of directly loaded sources ---
        direct_source_file_paths = set()
        if direct_sources_data:
             direct_sources_info_list = []
             for source in direct_sources_data:
                 direct_sources_info_list.append({
                     "type": source.get("type", "Unknown"),
                     "name": source.get("name", "Unknown")
                 })
                 # Store the file path associated with this direct source
                 if source.get('file_path'):
                      direct_source_file_paths.add(source['file_path'])
        # --- END MODIFIED ---

        try:
            # 1. Create Retriever & Retrieve Nodes (Unchanged)
            logger.debug(f"Creating retriever with top_k={settings.RAG_QUERY_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_QUERY_SIMILARITY_TOP_K,
                filters=MetadataFilters(filters=[ExactMatchFilter(key="project_id", value=project_id)]),
            )
            logger.info(f"Retrieving nodes for query: '{query_text}'")
            retrieved_nodes = await retriever.aretrieve(query_text)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for query context.")

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
                      source_type = source_data.get('type', 'Unknown')
                      source_name = source_data.get('name', f'Source {i+1}')
                      source_content = source_data.get('content', '')
                      truncated_direct_content = source_content
                      user_message_content += (
                          f"--- Start Directly Requested {source_type}: \"{source_name}\" ---\n"
                          f"```markdown\n{truncated_direct_content}\n```\n"
                          f"--- End Directly Requested {source_type}: \"{source_name}\" ---\n\n"
                      )

            # --- MODIFIED: Filter retrieved nodes before adding to prompt ---
            nodes_for_prompt = []
            if retrieved_nodes:
                nodes_for_prompt = [
                    node for node in retrieved_nodes
                    if node.metadata.get('file_path') not in direct_source_file_paths
                ]
                if len(nodes_for_prompt) < len(retrieved_nodes):
                    logger.debug(f"Filtered {len(retrieved_nodes) - len(nodes_for_prompt)} retrieved nodes to avoid duplicating directly loaded content in prompt.")
            # --- END MODIFIED ---

            retrieved_context_str = "\n\n---\n\n".join(
                # --- MODIFIED: Use document_type and document_title from metadata ---
                [f"Source ({node.metadata.get('document_type', 'Unknown')}: \"{node.metadata.get('document_title', 'Unknown Source')}\")\n\n{node.get_content()}"
                 for node in nodes_for_prompt]
                # --- END MODIFIED ---
            ) if nodes_for_prompt else "No additional relevant context snippets were retrieved via search." # Modified message slightly

            user_message_content += (
                 f"**Retrieved Context Snippets:**\n```markdown\n{retrieved_context_str}\n```\n\n"
                 f"**Instruction:** Based *only* on the provided Plan, Synopsis, Directly Requested Content (if any), and Retrieved Context, answer the User Query."
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"

            # 3. Call LLM via retry helper (Unchanged)
            llm_response = await self._execute_llm_complete(full_prompt)
            answer = llm_response.text.strip() if llm_response else ""
            logger.info("LLM call complete.")

            if not answer:
                 logger.warning("LLM query returned an empty response string.")
                 answer = "(The AI did not provide an answer based on the context.)"

            logger.info(f"Query successful. Returning answer, {len(retrieved_nodes)} source nodes, and direct source info list (if any).")
            # Return the original, unfiltered retrieved_nodes for UI display
            return answer, retrieved_nodes, direct_sources_info_list

        # --- Exception Handling (Unchanged from previous fix) ---
        except GoogleAPICallError as e:
             if _is_retryable_google_api_error(e):
                  logger.error(f"Rate limit error persisted after retries for query: {e}", exc_info=False)
                  error_message = f"Error: Rate limit exceeded for query after multiple retries. Please wait and try again."
                  return error_message, retrieved_nodes, None
             else:
                  logger.error(f"Non-retryable GoogleAPICallError during query for project '{project_id}': {e}", exc_info=True)
                  error_message = f"Error: Sorry, an error occurred while communicating with the AI service for project '{project_id}'. Details: {e}"
                  return error_message, [], None
        except Exception as e:
             logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
             error_message = f"Error: Sorry, an internal error occurred processing the query. Please check logs."
             return error_message, [], None
        # --- END Exception Handling ---