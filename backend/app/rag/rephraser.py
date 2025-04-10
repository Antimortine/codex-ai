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
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Optional

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.genai.errors import ClientError

from app.core.config import settings # Import settings directly

logger = logging.getLogger(__name__)

# --- REMOVED Local Constants ---
# REPHRASE_SIMILARITY_TOP_K = settings.RAG_GENERATION_SIMILARITY_TOP_K # Use settings.RAG_GENERATION_SIMILARITY_TOP_K directly
# REPHRASE_SUGGESTION_COUNT = settings.RAG_REPHRASE_SUGGESTION_COUNT # Use settings.RAG_REPHRASE_SUGGESTION_COUNT directly
# --- END REMOVED ---

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
             logger.warning("Google API rate limit hit (ClientError 429). Retrying rephrase...")
             return True
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
        logger.info("Calling LLM for rephrase suggestions...")
        return await self.llm.acomplete(prompt)

    async def rephrase(self, project_id: str, selected_text: str, context_before: Optional[str], context_after: Optional[str]) -> List[str]:
        logger.info(f"Rephraser: Starting rephrase for project '{project_id}'. Text: '{selected_text[:50]}...'")

        if not selected_text.strip():
             logger.warning("Rephraser: Received empty selected_text. Returning empty suggestions.")
             return []

        try:
            # 1. Construct Retrieval Query & Retrieve Context
            retrieval_context = f"{context_before or ''} {selected_text} {context_after or ''}".strip()
            retrieval_query = f"Context relevant to the following passage: {retrieval_context}"
            logger.debug(f"Constructed retrieval query for rephrase: '{retrieval_query}'")
            # --- MODIFIED: Use settings directly ---
            logger.debug(f"Creating retriever for rephrase with top_k={settings.RAG_GENERATION_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K, # Use setting directly
                filters=MetadataFilters(filters=[ExactMatchFilter(key="project_id", value=project_id)]),
            )
            # --- END MODIFIED ---
            retrieved_nodes: List[NodeWithScore] = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for rephrase context.")
            rag_context_list = []
            if retrieved_nodes:
                 for node in retrieved_nodes:
                      char_name = node.metadata.get('character_name')
                      char_info = f" [Character: {char_name}]" if char_name else ""
                      rag_context_list.append(f"Source: {node.metadata.get('file_path', 'N/A')}{char_info}\n\n{node.get_content()}")
            rag_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No specific context was retrieved via search."


            # 2. Build Rephrase Prompt
            logger.debug("Building rephrase prompt...")
            system_prompt = (
                "You are an expert writing assistant. Your task is to rephrase the user's selected text, providing several alternative phrasings. "
                "Use the surrounding text and the broader project context provided to ensure the suggestions fit naturally and maintain consistency with the overall narrative style and tone."
            )
            # --- MODIFIED: Use settings directly ---
            user_message_content = (
                f"Please provide {settings.RAG_REPHRASE_SUGGESTION_COUNT} alternative ways to phrase the 'Text to Rephrase' below, considering the context.\n\n" # Use setting directly
                f"**Broader Project Context:**\n```markdown\n{rag_context_str}\n```\n\n"
            )
            # --- END MODIFIED ---
            if context_before or context_after:
                 user_message_content += "**Surrounding Text:**\n```\n"
                 if context_before: user_message_content += f"{context_before}\n"
                 user_message_content += f"[[[--- TEXT TO REPHRASE ---]]]\n{selected_text}\n[[[--- END TEXT TO REPHRASE ---]]]\n"
                 if context_after: user_message_content += f"{context_after}\n"
                 user_message_content += "```\n\n"
            else:
                 user_message_content += f"**Text to Rephrase:**\n```\n{selected_text}\n```\n\n"
            # --- MODIFIED: Use settings directly ---
            user_message_content += (
                f"**Instructions:**\n"
                f"- Provide exactly {settings.RAG_REPHRASE_SUGGESTION_COUNT} distinct suggestions.\n" # Use setting directly
                f"- Each suggestion should be a direct replacement for the 'Text to Rephrase'.\n"
                f"- Maintain the original meaning and approximate length.\n"
                f"- Match the tone and style suggested by the surrounding text and context.\n"
                f"- Output the suggestions as a simple numbered list (e.g., '1. Suggestion one\n2. Suggestion two').\n"
                f"- Just output the numbered list of suggestions."
            )
            # --- END MODIFIED ---
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"


            # 3. Call LLM via retry helper
            llm_response = await self._execute_llm_complete(full_prompt)
            generated_text = llm_response.text.strip() if llm_response else ""

            if not generated_text:
                 logger.warning("LLM returned an empty response for rephrase.")
                 return ["Error: The AI failed to generate suggestions. Please try again."]

            # 4. Parse the Numbered List Response
            logger.debug(f"Raw LLM response for parsing:\n{generated_text}")
            suggestions = re.findall(r"^\s*\d+\.\s*(.*)", generated_text, re.MULTILINE)
            if not suggestions:
                logger.warning(f"Could not parse numbered list from LLM response. Response was:\n{generated_text}")
                suggestions = [line.strip() for line in generated_text.splitlines() if line.strip()]
                if not suggestions: return [f"Error: Could not parse suggestions. Raw response: {generated_text}"]
                logger.warning(f"Fallback parsing used (split by newline), got {len(suggestions)} potential suggestions.")

            # --- MODIFIED: Use settings directly ---
            suggestions = [s.strip() for s in suggestions if s.strip()][:settings.RAG_REPHRASE_SUGGESTION_COUNT] # Use setting directly
            # --- END MODIFIED ---

            logger.info(f"Successfully parsed {len(suggestions)} rephrase suggestions for project '{project_id}'.")
            return suggestions

        # Exception Handling (remains the same)
        except ClientError as e:
             if _is_retryable_google_api_error(e):
                  logger.error(f"Rate limit error persisted after retries for rephrase: {e}", exc_info=False)
                  return [f"Error: Rate limit exceeded after multiple retries. Please wait and try again."]
             else:
                  logger.error(f"Non-retryable ClientError during rephrase for project '{project_id}': {e}", exc_info=True)
                  return [f"Error: An unexpected error occurred while communicating with the AI service. Details: {e}"]
        except Exception as e:
             logger.error(f"Error during rephrase for project '{project_id}': {e}", exc_info=True)
             return [f"Error: An unexpected internal error occurred while rephrasing."]