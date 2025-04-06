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
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters # For filtering

# Import the singleton index_manager instance to access the initialized index, llm, etc.
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

    async def query(self, project_id: str, query_text: str) -> str:
        """
        Performs a RAG query against the index, filtered by project_id.

        Args:
            project_id: The ID of the project to scope the query to.
            query_text: The user's query.

        Returns:
            The response string from the LLM.
            (Will later return a structured response, potentially including source nodes).
        """
        logger.info(f"RagEngine: Received query for project '{project_id}': '{query_text}'")

        if not self.index or not self.llm:
             logger.error("RagEngine cannot query: Index or LLM is not available.")
             return "Error: RAG components are not properly initialized."

        try:
            # --- RAG Query Logic Implementation ---

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
            response = await query_engine.aquery(query_text) # Use async query
            logger.info("RAG query execution complete.")

            # Log retrieved source nodes for debugging (optional)
            if hasattr(response, 'source_nodes') and response.source_nodes:
                 logger.debug(f"Retrieved {len(response.source_nodes)} source nodes:")
                 for i, node in enumerate(response.source_nodes):
                      logger.debug(f"  Node {i+1}: Score={node.score:.4f}, ID={node.node_id}, Path={node.metadata.get('file_path', 'N/A')}")
                      # logger.debug(f"    Text: {node.text[:100]}...") # Uncomment to log text snippets
            else:
                 logger.debug("No source nodes retrieved or available in response.")


            # 4. Extract and return the answer string
            # The default __str__ representation of the Response object usually contains the answer.
            answer = str(response)
            if not answer:
                 logger.warning("LLM query returned an empty response string.")
                 answer = "(No response generated)"

            logger.info(f"Query successful. Returning answer (length: {len(answer)}).")
            return answer

        except Exception as e:
            logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
            # Return a user-friendly error message
            return f"Sorry, an error occurred while processing your query for project '{project_id}'. Please check the backend logs for details."


# --- Singleton Instance ---
try:
     rag_engine = RagEngine()
except Exception as e:
     logger.critical(f"Failed to create RagEngine instance on startup: {e}", exc_info=True)
     raise