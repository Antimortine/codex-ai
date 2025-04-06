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
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import Response, NodeWithScore
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from typing import List, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

class QueryProcessor:
    """Handles RAG querying logic."""

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

    async def query(self, project_id: str, query_text: str) -> Tuple[str, List[NodeWithScore]]:
        """
        Performs a RAG query against the index, filtered by project_id.

        Args:
            project_id: The ID of the project to scope the query to.
            query_text: The user's query.

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

            # 2. Create a query engine using the filtered retriever
            logger.debug("Creating RetrieverQueryEngine...")
            query_engine = RetrieverQueryEngine.from_args(
                retriever=retriever,
                llm=self.llm,
            )
            logger.debug("Query engine created successfully.")

            # 3. Execute the query asynchronously
            logger.info(f"Executing RAG query: '{query_text}'")
            response: Response = await query_engine.aquery(query_text)
            logger.info("RAG query execution complete.")

            # 4. Extract answer and source nodes
            answer = str(response) if response else "(No response generated)"
            source_nodes = response.source_nodes if hasattr(response, 'source_nodes') else []

            if not answer:
                 logger.warning("LLM query returned an empty response string.")
                 answer = "(No response generated)"

            if source_nodes:
                 logger.debug(f"Retrieved {len(source_nodes)} source nodes:")
                 for i, node in enumerate(source_nodes):
                      # Log character name if available in metadata
                      char_name = node.metadata.get('character_name')
                      char_info = f" (Character: {char_name})" if char_name else ""
                      logger.debug(f"  Node {i+1}: Score={node.score:.4f}, ID={node.node_id}, Path={node.metadata.get('file_path', 'N/A')}{char_info}")
            else:
                 logger.debug("No source nodes retrieved or available in response.")

            logger.info(f"Query successful. Returning answer and {len(source_nodes)} source nodes.")
            return answer, source_nodes

        except Exception as e:
            logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
            error_message = f"Sorry, an error occurred while processing your query for project '{project_id}'. Please check the backend logs for details."
            return error_message, []