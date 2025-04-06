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
from typing import List, Tuple

from app.rag.index_manager import index_manager

logger = logging.getLogger(__name__)

# --- Configuration for Retrieval/Querying ---
SIMILARITY_TOP_K = 3 # How many relevant chunks to retrieve

class RagEngine:
    """
    Handles RAG querying and potentially generation logic, using the
    index and components initialized by IndexManager.
    """
    def __init__(self):
        """
        Initializes the RagEngine, ensuring the IndexManager's components are ready.
        """
        if not hasattr(index_manager, 'index') or not index_manager.index:
             logger.critical("IndexManager's index is not initialized! RagEngine cannot function.")
             raise RuntimeError("RagEngine cannot initialize without a valid index from IndexManager.")
        if not hasattr(index_manager, 'llm') or not index_manager.llm:
             logger.critical("IndexManager's LLM is not initialized! RagEngine cannot function.")
             raise RuntimeError("RagEngine cannot initialize without a valid LLM from IndexManager.")
        if not hasattr(index_manager, 'embed_model') or not index_manager.embed_model:
             logger.warning("IndexManager's embed_model is not initialized! RagEngine might face issues.")

        self.index = index_manager.index
        self.llm = index_manager.llm
        self.embed_model = index_manager.embed_model
        logger.info("RagEngine initialized, using components from IndexManager.")

    # --- Update return type annotation ---
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
        logger.info(f"RagEngine: Received query for project '{project_id}': '{query_text}'")

        if not self.index or not self.llm:
             logger.error("RagEngine cannot query: Index or LLM is not available.")
             # --- Return tuple on error ---
             return "Error: RAG components are not properly initialized.", []

        try:
            # 1. Create a retriever with metadata filtering
            logger.debug(f"Creating retriever with top_k={SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=SIMILARITY_TOP_K,
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
                # verbose=True, # Optional: Add verbose logging from LlamaIndex
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

            # Log retrieved source nodes
            if source_nodes:
                 logger.debug(f"Retrieved {len(source_nodes)} source nodes:")
                 for i, node in enumerate(source_nodes):
                      logger.debug(f"  Node {i+1}: Score={node.score:.4f}, ID={node.node_id}, Path={node.metadata.get('file_path', 'N/A')}")
            else:
                 logger.debug("No source nodes retrieved or available in response.")

            logger.info(f"Query successful. Returning answer and {len(source_nodes)} source nodes.")
            # --- Return tuple ---
            return answer, source_nodes

        except Exception as e:
            logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
            # --- Return tuple on error ---
            error_message = f"Sorry, an error occurred while processing your query for project '{project_id}'. Please check the backend logs for details."
            return error_message, []


# --- Singleton Instance ---
try:
     rag_engine = RagEngine()
except Exception as e:
     logger.critical(f"Failed to create RagEngine instance on startup: {e}", exc_info=True)
     raise