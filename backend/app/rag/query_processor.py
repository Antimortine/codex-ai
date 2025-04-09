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
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import Response, NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Tuple

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.genai.errors import ClientError

from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Define a retry predicate function ---
def _is_retryable_google_api_error(exception):
    """Return True if the exception is a Google API 429 error."""
    if isinstance(exception, ClientError):
        status_code = None
        try:
            if hasattr(exception, 'response') and hasattr(exception.response, 'status_code'): status_code = exception.response.status_code
            elif isinstance(exception.args, (list, tuple)) and len(exception.args) > 0 and isinstance(exception.args[0], int): status_code = int(exception.args[0])
            elif isinstance(exception.args, (list, tuple)) and len(exception.args) > 0 and isinstance(exception.args[0], str) and '429' in exception.args[0]: return True
        except (ValueError, TypeError, IndexError, AttributeError): pass
        if status_code == 429:
             # Log is now done within the predicate where tenacity calls it
             # logger.warning("Google API rate limit hit (ClientError 429). Retrying query...")
             return True
    # Log is now done within the predicate where tenacity calls it
    # logger.debug(f"Non-retryable error encountered during query: {type(exception)}")
    return False
# --- End retry predicate ---


class QueryProcessor:
    """Handles RAG querying logic, including explicit context."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
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

    async def query(self, project_id: str, query_text: str, explicit_plan: str, explicit_synopsis: str) -> Tuple[str, List[NodeWithScore]]:
        logger.info(f"QueryProcessor: Received query for project '{project_id}': '{query_text}'")
        retrieved_nodes: List[NodeWithScore] = []

        try:
            # 1. Create Retriever & Retrieve Nodes
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
            # ... (prompt building logic remains the same) ...
            logger.debug("Building query prompt with explicit and retrieved context...")
            system_prompt = (
                "You are an AI assistant answering questions about a creative writing project. "
                "Use the provided Project Plan, Project Synopsis, and Retrieved Context Snippets to answer the user's query accurately and concisely. "
                "If the context doesn't contain the answer, say that you cannot answer based on the provided information."
            )
            retrieved_context_str = "\n\n---\n\n".join(
                [f"Source: {node.metadata.get('file_path', 'N/A')}\n\n{node.get_content()}" for node in retrieved_nodes]
            ) if retrieved_nodes else "No specific context snippets were retrieved via search."
            user_message_content = (
                f"**User Query:**\n{query_text}\n\n"
                f"**Project Plan:**\n```markdown\n{explicit_plan or 'Not Available'}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{explicit_synopsis or 'Not Available'}\n```\n\n"
                f"**Retrieved Context Snippets:**\n```markdown\n{retrieved_context_str}\n```\n\n"
                f"**Instruction:** Based *only* on the provided Plan, Synopsis, and Retrieved Context, answer the User Query."
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"


            # 3. Call LLM via retry helper
            llm_response = await self._execute_llm_complete(full_prompt)
            answer = llm_response.text.strip() if llm_response else ""
            logger.info("LLM call complete.")

            if not answer:
                 logger.warning("LLM query returned an empty response string.")
                 answer = "(The AI did not provide an answer based on the context.)"

            logger.info(f"Query successful. Returning answer and {len(retrieved_nodes)} source nodes.")
            return answer, retrieved_nodes

        # --- CORRECTED Exception Handling ---
        except ClientError as e:
             # Catch ClientError specifically (which tenacity re-raises if it was the cause)
             if _is_retryable_google_api_error(e): # Check if it's the 429 error
                  logger.error(f"Rate limit error persisted after retries for query: {e}", exc_info=False)
                  # --- MODIFIED: Add "Error: " prefix ---
                  error_message = f"Error: Rate limit exceeded for query after multiple retries. Please wait and try again."
                  # --- END MODIFIED ---
                  return error_message, retrieved_nodes # Return nodes retrieved before failure
             else:
                  # Handle other non-retryable ClientErrors
                  logger.error(f"Non-retryable ClientError during query for project '{project_id}': {e}", exc_info=True)
                  # --- MODIFIED: Add "Error: " prefix ---
                  error_message = f"Error: Sorry, an error occurred while communicating with the AI service for project '{project_id}'. Details: {e}"
                  # --- END MODIFIED ---
                  return error_message, [] # Return empty nodes
        except Exception as e:
             # Catch other errors (like retriever errors, prompt errors, etc.)
             logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
             # --- MODIFIED: Add "Error: " prefix ---
             error_message = f"Error: Sorry, an internal error occurred processing the query. Please check logs."
             # --- END MODIFIED ---
             return error_message, []
        # --- END CORRECTED ---