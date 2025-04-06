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

class RagEngine:
    """
    Handles RAG querying and potentially generation logic, using the
    index and components initialized by IndexManager.
    """
    def __init__(self):
        """
        Initializes the RagEngine, ensuring the IndexManager's components are ready.
        """
        # Access the globally initialized index, LLM, and embed_model from IndexManager
        # This relies on IndexManager being initialized successfully before RagEngine.
        if not hasattr(index_manager, 'index') or not index_manager.index:
             logger.critical("IndexManager's index is not initialized! RagEngine cannot function.")
             raise RuntimeError("RagEngine cannot initialize without a valid index from IndexManager.")
        if not hasattr(index_manager, 'llm') or not index_manager.llm:
             logger.critical("IndexManager's LLM is not initialized! RagEngine cannot function.")
             raise RuntimeError("RagEngine cannot initialize without a valid LLM from IndexManager.")
        # Embed model might not be strictly needed for querying if retriever handles it,
        # but good to have access if needed for query transformations etc.
        if not hasattr(index_manager, 'embed_model') or not index_manager.embed_model:
             logger.warning("IndexManager's embed_model is not initialized! RagEngine might face issues.")
             # Decide if this is critical - for basic retrieval, maybe not.

        self.index = index_manager.index
        self.llm = index_manager.llm
        self.embed_model = index_manager.embed_model # Store reference if needed
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

        try:
            # --- RAG Query Logic (Stage 3 Implementation) ---

            # 1. Create a retriever with metadata filtering
            # We specify the metadata key ('project_id') and the value to match
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=3, # Retrieve top 3 most similar nodes (configurable)
                filters=MetadataFilters(
                    filters=[ExactMatchFilter(key="project_id", value=project_id)]
                ),
                # embed_model=self.embed_model # Usually not needed here, index has it
            )
            logger.debug(f"Created retriever for project_id '{project_id}'")

            # 2. Create a query engine using the filtered retriever
            # This combines the retriever (finds context) and the LLM (generates answer)
            query_engine = RetrieverQueryEngine.from_args(
                retriever=retriever,
                llm=self.llm,
                # node_postprocessors=... # Optional: Add re-ranking etc. later
                # response_synthesizer=... # Optional: Customize how response is built
            )
            logger.debug("Created query engine with filtered retriever")

            # 3. Execute the query
            logger.info(f"Executing query against engine: '{query_text}'")
            response = await query_engine.aquery(query_text) # Use async query
            logger.info("Query execution complete.")
            logger.debug(f"Raw response object: {response}") # Log the full response object

            # 4. Extract and return the answer string
            # TODO: Later, return a structured response including source_nodes: response.source_nodes
            answer = str(response) # Default string representation often contains the answer
            logger.info(f"Query successful. Answer length: {len(answer)}")
            return answer

        except Exception as e:
            logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
            # Return a user-friendly error message or re-raise a specific exception
            return f"Error processing query for project '{project_id}'. Please check logs."


# --- Singleton Instance ---
# Create a single instance of the RagEngine to be used across the application.
try:
     rag_engine = RagEngine()
except Exception as e:
     # Log critical failure during startup
     logger.critical(f"Failed to create RagEngine instance on startup: {e}", exc_info=True)
     # Re-raise the exception to potentially halt application startup if the engine is essential
     raise