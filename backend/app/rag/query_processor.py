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
# --- REMOVED: RetrieverQueryEngine import ---
# from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import Response, NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Handles RAG querying logic, including explicit context."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        """
        Initializes the QueryProcessor.

        Args:
            index: The loaded VectorStoreIndex instance.
            llm: The configured LLM instance.
        """
        if not index:
            raise ValueError("QueryProcessor requires a valid VectorStoreIndex instance.")
        if not llm:
             raise ValueError("QueryProcessor requires a valid LLM instance.")
        self.index = index
        self.llm = llm
        logger.info("QueryProcessor initialized.")

    # --- MODIFIED: Added explicit_plan and explicit_synopsis arguments ---
    async def query(self, project_id: str, query_text: str, explicit_plan: str, explicit_synopsis: str) -> Tuple[str, List[NodeWithScore]]:
        """
        Performs a RAG query against the index, filtered by project_id,
        and incorporates explicit plan/synopsis context into the LLM prompt.

        Args:
            project_id: The ID of the project to scope the query to.
            query_text: The user's query.
            explicit_plan: The content of the project's plan.md.
            explicit_synopsis: The content of the project's synopsis.md.

        Returns:
            A tuple containing:
            - The response string from the LLM.
            - A list of LlamaIndex NodeWithScore objects representing the retrieved source nodes.
            Returns ("Error message", []) on failure.
        """
        logger.info(f"QueryProcessor: Received query for project '{project_id}': '{query_text}'")

        try:
            # 1. Create a retriever with metadata filtering
            logger.debug(f"Creating retriever with top_k={settings.RAG_QUERY_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_QUERY_SIMILARITY_TOP_K,
                filters=MetadataFilters(
                    filters=[ExactMatchFilter(key="project_id", value=project_id)]
                ),
            )
            logger.debug(f"Retriever created successfully.")

            # 2. Retrieve relevant nodes based on the query
            logger.info(f"Retrieving nodes for query: '{query_text}'")
            retrieved_nodes: List[NodeWithScore] = await retriever.aretrieve(query_text)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for query context.")

            if retrieved_nodes:
                 logger.debug(f"Retrieved {len(retrieved_nodes)} source nodes:")
                 for i, node in enumerate(retrieved_nodes):
                      char_name = node.metadata.get('character_name')
                      char_info = f" (Character: {char_name})" if char_name else ""
                      logger.debug(f"  Node {i+1}: Score={node.score:.4f}, ID={node.node_id}, Path={node.metadata.get('file_path', 'N/A')}{char_info}")
            else:
                 logger.debug("No source nodes retrieved.")

            # 3. Build the prompt for the LLM, including explicit context
            logger.debug("Building query prompt with explicit and retrieved context...")
            system_prompt = (
                "You are an AI assistant answering questions about a creative writing project. "
                "Use the provided Project Plan, Project Synopsis, and Retrieved Context Snippets to answer the user's query accurately and concisely. "
                "If the context doesn't contain the answer, say that you cannot answer based on the provided information."
            )

            # Format retrieved nodes for the prompt
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
            # logger.debug(f"QueryProcessor: Full prompt being sent to LLM (length: {len(full_prompt)}):\n--- PROMPT START ---\n{full_prompt}\n--- PROMPT END ---")

            # 4. Call the LLM directly with the constructed prompt
            logger.info(f"Calling LLM with combined context for query: '{query_text}'")
            llm_response = await self.llm.acomplete(full_prompt)
            answer = llm_response.text.strip() if llm_response else ""
            logger.info("LLM call complete.")

            if not answer:
                 logger.warning("LLM query returned an empty response string.")
                 answer = "(The AI did not provide an answer based on the context.)"

            logger.info(f"Query successful. Returning answer and {len(retrieved_nodes)} source nodes.")
            # Return the LLM's answer and the nodes that were retrieved (used to build the prompt)
            return answer, retrieved_nodes

        except Exception as e:
            logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
            error_message = f"Sorry, an error occurred while processing your query for project '{project_id}'. Please check the backend logs for details."
            # Return error message and empty list of nodes
            return error_message, []