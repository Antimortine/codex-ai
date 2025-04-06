# backend___app___rag___rephraser.py.txt

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

from app.core.config import settings

logger = logging.getLogger(__name__)

# Use settings for configuration
REPHRASE_SIMILARITY_TOP_K = settings.RAG_GENERATION_SIMILARITY_TOP_K # Reuse generation K for context retrieval
REPHRASE_SUGGESTION_COUNT = settings.RAG_REPHRASE_SUGGESTION_COUNT # Number of suggestions

class Rephraser:
    """Handles RAG rephrasing logic."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        """
        Initializes the Rephraser.

        Args:
            index: The loaded VectorStoreIndex instance.
            llm: The configured LLM instance.
        """
        if not index:
            raise ValueError("Rephraser requires a valid VectorStoreIndex instance.")
        if not llm:
             raise ValueError("Rephraser requires a valid LLM instance.")
        self.index = index
        self.llm = llm
        logger.info("Rephraser initialized.")

    async def rephrase(self, project_id: str, selected_text: str, context_before: Optional[str], context_after: Optional[str]) -> List[str]:
        """
        Rephrases the selected text using RAG context.

        Args:
            project_id: The ID of the project for context retrieval.
            selected_text: The text snippet to rephrase.
            context_before: Optional text immediately preceding the selection.
            context_after: Optional text immediately following the selection.

        Returns:
            A list of rephrased suggestions (strings).
            Returns ["Error: ..."] on failure.
        """
        logger.info(f"Rephraser: Starting rephrase for project '{project_id}'. Text: '{selected_text[:50]}...'")

        try:
            # 1. Construct Retrieval Query based on the text to be rephrased
            retrieval_query = f"Context relevant to the following text: {selected_text}"
            logger.debug(f"Constructed retrieval query for rephrase: '{retrieval_query}'")

            # 2. Retrieve Context
            logger.debug(f"Creating retriever for rephrase with top_k={REPHRASE_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=REPHRASE_SIMILARITY_TOP_K,
                filters=MetadataFilters(
                    filters=[ExactMatchFilter(key="project_id", value=project_id)]
                ),
            )
            retrieved_nodes: List[NodeWithScore] = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for rephrase context.")

            # Include character name in RAG context string if available
            rag_context_list = []
            if retrieved_nodes:
                 for node in retrieved_nodes:
                      char_name = node.metadata.get('character_name')
                      char_info = f" [Character: {char_name}]" if char_name else ""
                      rag_context_list.append(f"Source: {node.metadata.get('file_path', 'N/A')}{char_info}\n\n{node.get_content()}")
            rag_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No additional context retrieved via search."

            # 3. Build Rephrase Prompt
            logger.debug("Building rephrase prompt...")
            system_prompt = (
                "You are an expert writing assistant. Your task is to rephrase the user's selected text, providing several alternative phrasings. "
                "Use the surrounding text and the broader project context provided to ensure the suggestions fit naturally and maintain consistency."
            )

            user_message_content = (
                f"Please provide {REPHRASE_SUGGESTION_COUNT} alternative ways to phrase the following selected text, considering the context.\n\n"
                f"**Broader Project Context:**\n```markdown\n{rag_context_str}\n```\n\n"
                f"**Text to Rephrase:**\n```\n{selected_text}\n```\n\n"
            )
            if context_before:
                user_message_content += f"**Text Immediately Before Selection:**\n```\n{context_before}\n```\n\n"
            if context_after:
                user_message_content += f"**Text Immediately After Selection:**\n```\n{context_after}\n```\n\n"

            user_message_content += (
                f"**Instructions:**\n"
                f"- Provide exactly {REPHRASE_SUGGESTION_COUNT} distinct suggestions.\n"
                f"- Present the suggestions as a numbered list, starting with '1.'.\n"
                f"- Each suggestion should be a plausible replacement for the original selected text.\n"
                f"- Do NOT add explanations, commentary, or apologies before or after the numbered list.\n"
                f"- Just output the numbered list of suggestions."
            )

            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"
            logger.info("Calling LLM for rephrase suggestions...")
            llm_response = await self.llm.acomplete(full_prompt)

            generated_text = llm_response.text.strip() if llm_response else ""

            if not generated_text:
                 logger.warning("LLM returned an empty response for rephrase.")
                 return ["Error: The AI failed to generate suggestions. Please try again."]

            # 5. Parse the Numbered List Response
            logger.debug(f"Raw LLM response for parsing:\n{generated_text}")
            suggestions = re.findall(r"^\s*\d+\.\s*(.*)", generated_text, re.MULTILINE)

            if not suggestions:
                logger.warning(f"Could not parse numbered list from LLM response. Response was:\n{generated_text}")
                return [f"Error: Could not parse suggestions. Raw response: {generated_text}"]

            suggestions = [s.strip() for s in suggestions]

            logger.info(f"Successfully parsed {len(suggestions)} rephrase suggestions for project '{project_id}'.")
            return suggestions

        except Exception as e:
            logger.error(f"Error during rephrase for project '{project_id}': {e}", exc_info=True)
            return [f"Error: An unexpected error occurred while rephrasing. Please check logs."]