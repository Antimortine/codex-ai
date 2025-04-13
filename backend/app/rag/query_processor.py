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

from app.core.config import settings # Import settings

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
        # --- MODIFIED: Add prompt size logging ---
        char_count = len(prompt)
        est_tokens = char_count // 4
        logger.info(f"Calling LLM with combined context for query (Temperature: {settings.LLM_TEMPERATURE}, Chars: {char_count}, Est. Tokens: {est_tokens})...")
        logger.debug(f"--- Query Prompt Start (Chars: {char_count}, Est. Tokens: {est_tokens}) ---\n{prompt}\n--- Query Prompt End ---")
        # --- END MODIFIED ---
        return await self.llm.acomplete(prompt, temperature=settings.LLM_TEMPERATURE)

    async def query(self,
                  project_id: str,
                  query_text: str,
                  explicit_plan: Optional[str],
                  explicit_synopsis: Optional[str],
                  direct_sources_data: Optional[List[Dict]] = None,
                  direct_chapter_context: Optional[Dict[str, Optional[str]]] = None,
                  paths_to_filter: Optional[Set[str]] = None
                  ) -> Tuple[str, List[NodeWithScore], Optional[List[Dict[str, str]]]]:
        # ENHANCED: More robust direct sources data handling
        if direct_sources_data is None:
            direct_sources_data = []
            logger.info("QueryProcessor.query: direct_sources_data was None, initialized to empty list")
        
        # Add diagnostics for direct sources data
        if direct_sources_data:
            logger.info(f"QueryProcessor.query: Received {len(direct_sources_data)} direct sources items")
            for i, item in enumerate(direct_sources_data):
                item_type = item.get('type', 'Unknown')
                item_name = item.get('name', f'Item {i+1}')
                content_length = len(item.get('content', ''))
                logger.info(f"QueryProcessor.query: Direct source {i+1}: Type={item_type}, Name={item_name}, Content length={content_length}")
                
                # Verify content exists and is reasonable
                if content_length == 0:
                    logger.warning(f"QueryProcessor.query: Direct source {item_type} '{item_name}' has empty content!")
                elif content_length < 10:
                    logger.warning(f"QueryProcessor.query: Direct source {item_type} '{item_name}' has very short content: '{item.get('content')}'")                
        else:
            logger.info("QueryProcessor.query: Empty direct_sources_data list received")
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
        if direct_chapter_context:
            if not direct_sources_info_list: direct_sources_info_list = []
            chapter_title = direct_chapter_context.get('chapter_title', 'Unknown Chapter')
            if direct_chapter_context.get('chapter_plan'):
                direct_sources_info_list.append({'type': 'ChapterPlan', 'name': f"Plan for Chapter '{chapter_title}'"})
            if direct_chapter_context.get('chapter_synopsis'):
                direct_sources_info_list.append({'type': 'ChapterSynopsis', 'name': f"Synopsis for Chapter '{chapter_title}'"})

        try:
            # 1. Retrieve Nodes (Unchanged)
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

            # Deduplication and Filtering (Unchanged)
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
                logger.debug(f"QueryProcessor: Starting node filtering against {len(final_paths_to_filter_obj)} filter paths.")
                for node_with_score in unique_retrieved_nodes:
                    node = node_with_score.node
                    node_path_str = node.metadata.get('file_path')
                    if not node_path_str:
                        logger.warning(f"Node {node.node_id} missing 'file_path' metadata. Including in prompt.")
                        nodes_for_prompt.append(node_with_score)
                        continue
                    try:
                        node_path_obj = Path(node_path_str).resolve()
                        # Check if this node should be filtered out (because it's already in direct sources)
                        is_filtered = False
                        
                        # First, compare as Path objects
                        if node_path_obj in final_paths_to_filter_obj:
                            is_filtered = True
                            logger.debug(f"  Filtering node via Path object match: {node_path_obj}")
                        
                        # For Notes and other document types that may have path inconsistencies,
                        # also check string comparison as fallback
                        if not is_filtered:
                            node_path_str_norm = str(node_path_obj).lower().replace('\\', '/')
                            for filter_path in final_paths_to_filter_obj:
                                filter_path_str = str(filter_path).lower().replace('\\', '/')
                                if node_path_str_norm == filter_path_str:
                                    is_filtered = True
                                    logger.debug(f"  Filtering node via string path match: {node_path_str_norm}")
                                    break
                        
                        # If the node is not filtered, add it to the prompt
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
            user_message_content = f"**User Query:**\n{query_text}\n\n"

            # Conditionally add project context (no truncation here)
            if explicit_plan:
                user_message_content += f"**Project Plan:**\n```markdown\n{explicit_plan}\n```\n\n"
            if explicit_synopsis:
                user_message_content += f"**Project Synopsis:**\n```markdown\n{explicit_synopsis}\n```\n\n"

            # Conditionally add direct chapter context (no truncation here)
            if direct_chapter_context:
                chapter_title = direct_chapter_context.get('chapter_title', 'Unknown Chapter')
                chapter_plan = direct_chapter_context.get('chapter_plan')
                chapter_synopsis = direct_chapter_context.get('chapter_synopsis')
                has_direct_chapter_content = chapter_plan or chapter_synopsis
                if has_direct_chapter_content:
                    user_message_content += f"**Directly Requested Chapter Context (for Chapter '{chapter_title}'):**\n"
                    if chapter_plan:
                        user_message_content += f"--- Start Chapter Plan ---\n```markdown\n{chapter_plan}\n```\n--- End Chapter Plan ---\n\n"
                    if chapter_synopsis:
                        user_message_content += f"--- Start Chapter Synopsis ---\n```markdown\n{chapter_synopsis}\n```\n--- End Chapter Synopsis ---\n\n"

            # FIXED: Add other direct sources (no truncation here)
            # Handle direct sources content more robustly
            if direct_sources_data and len(direct_sources_data) > 0:
                # Log what we're about to process
                logger.info(f"QueryProcessor: Processing {len(direct_sources_data)} direct sources items")
                content_found = False
                
                # First verify we have actual content in at least one item
                for i, source_item in enumerate(direct_sources_data):
                    source_type = source_item.get('type', 'Unknown')
                    source_name = source_item.get('name', f'Item {i+1}')
                    source_content = source_item.get('content', '')
                    content_length = len(source_content)
                    
                    logger.info(f"QueryProcessor: Checking direct source {i+1}: Type={source_type}, Name='{source_name}', Content length={content_length}")
                    
                    if content_length > 0:
                        content_found = True
                        if source_type == 'Note':
                            logger.info(f"QueryProcessor: Found valid Note content for '{source_name}' with length {content_length}")
                
                # Only add the section header if we found content
                if content_found:
                    user_message_content += "**Directly Requested Content:**\n"
                    
                    # Process each direct source
                    for i, source_data in enumerate(direct_sources_data):
                        source_type = source_data.get('type', 'Unknown')
                        source_name = source_data.get('name', f'Source {i+1}')
                        source_content = source_data.get('content', '')
                        
                        # Skip empty content
                        if not source_content:
                            logger.warning(f"QueryProcessor: Skipping empty direct source: {source_type} '{source_name}'")
                            continue
                            
                        logger.info(f"QueryProcessor: Adding direct source to prompt: {source_type} '{source_name}' with content length {len(source_content)}")
                        
                        # No truncation for directly requested content
                        user_message_content += (f"--- Start Directly Requested {source_type}: \"{source_name}\" ---\n" 
                                               f"```markdown\n{source_content}\n```\n" 
                                               f"--- End Directly Requested {source_type}: \"{source_name}\" ---\n\n")
                else:
                    logger.warning("QueryProcessor: No valid content found in any direct sources items!")
            else:
                logger.info("QueryProcessor: No direct sources to add to prompt")

            # Add retrieved RAG context (with truncation)
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
                      max_node_len = settings.MAX_CONTEXT_LENGTH # Use global setting
                      truncated_content = node_content[:max_node_len] + ('...' if len(node_content) > max_node_len else '')
                      # --- END MODIFIED ---
                      rag_context_list.append(f"{source_label}\n\n{truncated_content}")
            retrieved_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No additional relevant context snippets were retrieved via search."
            logger.debug(f"QueryProcessor: Final rag_context_str for prompt:\n---\n{retrieved_context_str}\n---")

            user_message_content += (
                 f"**Retrieved Context Snippets:**\n```markdown\n{retrieved_context_str}\n```\n\n"
                 f"**Instruction:** Based *only* on the provided Plan, Synopsis, Directly Requested Content (if any), and Retrieved Context, answer the User Query."
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"

            # 3. Call LLM via retry helper
            llm_response = await self._execute_llm_complete(full_prompt)
            answer = llm_response.text.strip() if llm_response else ""
            logger.info("LLM call complete.")
            if not answer: logger.warning("LLM query returned an empty response string."); answer = "(The AI did not provide an answer based on the context.)"

            # Return the filtered nodes_for_prompt
            logger.info(f"Query successful. Returning answer, {len(nodes_for_prompt)} filtered source nodes, and direct source info list (if any).")
            return answer, nodes_for_prompt, direct_sources_info_list

        # Exception Handling (Unchanged)
        except GoogleAPICallError as e:
             if _is_retryable_google_api_error(e):
                 logger.error(f"Rate limit error persisted after retries for query: {e}", exc_info=False)
                 error_message = f"Error: Rate limit exceeded for query after multiple retries. Please wait and try again."
                 return error_message, nodes_for_prompt, None
             else:
                 logger.error(f"Non-retryable GoogleAPICallError during query for project '{project_id}': {e}", exc_info=True)
                 error_message = f"Error: Sorry, an error occurred while communicating with the AI service for project '{project_id}'. Details: {e}"
                 return error_message, [], None
        except Exception as e:
             logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
             error_message = f"Error: Sorry, an internal error occurred processing the query. Please check logs."
             return error_message, [], None