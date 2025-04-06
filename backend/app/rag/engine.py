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
import asyncio # Needed for async llm call
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import Response, NodeWithScore
from typing import List, Tuple, Optional

from app.rag.index_manager import index_manager
from app.core.config import settings # Import settings

logger = logging.getLogger(__name__)

# --- Configuration moved to config.py ---
# SIMILARITY_TOP_K = settings.RAG_QUERY_SIMILARITY_TOP_K
# GENERATION_SIMILARITY_TOP_K = settings.RAG_GENERATION_SIMILARITY_TOP_K
# REPHRASE_SIMILARITY_TOP_K = settings.RAG_GENERATION_SIMILARITY_TOP_K # Reuse generation K for now

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

    async def query(self, project_id: str, query_text: str) -> Tuple[str, List[NodeWithScore]]:
        """Performs a RAG query against the index, filtered by project_id."""
        # ... (query method remains unchanged) ...
        logger.info(f"RagEngine: Received query for project '{project_id}': '{query_text}'")

        if not self.index or not self.llm:
             logger.error("RagEngine cannot query: Index or LLM is not available.")
             return "Error: RAG components are not properly initialized.", []

        try:
            # 1. Create a retriever with metadata filtering
            logger.debug(f"Creating retriever with top_k={settings.RAG_QUERY_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_QUERY_SIMILARITY_TOP_K, # Use setting
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

            if source_nodes:
                 logger.debug(f"Retrieved {len(source_nodes)} source nodes:")
                 for i, node in enumerate(source_nodes):
                      logger.debug(f"  Node {i+1}: Score={node.score:.4f}, ID={node.node_id}, Path={node.metadata.get('file_path', 'N/A')}")
            else:
                 logger.debug("No source nodes retrieved or available in response.")

            logger.info(f"Query successful. Returning answer and {len(source_nodes)} source nodes.")
            return answer, source_nodes

        except Exception as e:
            logger.error(f"Error during RAG query for project '{project_id}': {e}", exc_info=True)
            error_message = f"Sorry, an error occurred while processing your query for project '{project_id}'. Please check the backend logs for details."
            return error_message, []


    async def generate_scene(self, project_id: str, chapter_id: str, prompt_summary: Optional[str]) -> str:
        """Generates a scene draft using RAG context for the given project and chapter."""
        # ... (generate_scene method remains unchanged) ...
        logger.info(f"RagEngine: Starting scene generation for project '{project_id}', chapter '{chapter_id}'. Summary: '{prompt_summary}'")

        if not self.index or not self.llm:
             logger.error("RagEngine cannot generate scene: Index or LLM is not available.")
             return "Error: RAG components are not properly initialized."

        try:
            # 1. Construct Retrieval Query
            # Combine chapter context and user summary for better retrieval
            retrieval_query = f"Context relevant for writing a new scene in chapter {chapter_id}."
            if prompt_summary:
                retrieval_query += f" Scene summary: {prompt_summary}"
            logger.debug(f"Constructed retrieval query: '{retrieval_query}'")

            # 2. Retrieve Context
            logger.debug(f"Creating retriever for generation with top_k={settings.RAG_GENERATION_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K, # Use generation setting
                filters=MetadataFilters(
                    filters=[ExactMatchFilter(key="project_id", value=project_id)]
                ),
            )
            retrieved_nodes: List[NodeWithScore] = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for generation context.")

            # Format context for the prompt
            context_str = "\n\n---\n\n".join(
                 [f"Source: {node.metadata.get('file_path', 'N/A')}\n\n{node.get_content()}" for node in retrieved_nodes]
            ) if retrieved_nodes else "No specific context was retrieved."

            # 3. Build Generation Prompt
            logger.debug("Building generation prompt...")
            system_prompt = (
                "You are an expert writing assistant helping a user draft a scene for their creative writing project. "
                "Your goal is to generate a coherent and engaging scene draft in Markdown format, "
                "based on the provided project context and user guidance. "
                "Use the context to maintain consistency with the story's plot, characters, and world."
            )

            user_message_content = (
                f"Please write a draft for a new scene.\n\n"
                f"**Project Context:**\n```markdown\n{context_str}\n```\n\n"
                f"**Scene Details:**\n"
                f"- Belongs to: Chapter ID '{chapter_id}'\n"
            )
            if prompt_summary:
                user_message_content += f"- User Guidance/Summary: {prompt_summary}\n\n"
            else:
                user_message_content += "- User Guidance/Summary: (None provided - use the context to generate a plausible next scene for this chapter)\n\n"

            user_message_content += (
                "**Instructions:**\n"
                "- Generate the scene content in pure Markdown format.\n"
                "- Start directly with the scene content (e.g., with a heading like '## Scene Title' or directly with narrative).\n"
                "- Focus on the user's guidance if provided, otherwise infer the scene's direction from the context.\n"
                "- Ensure the scene flows logically from or fits within the provided context.\n"
                "- Do NOT add explanations or commentary outside the scene's Markdown content."
            )

            # Using a chat-like structure can sometimes yield better results with models like Gemini
            # messages = [
            #      {"role": "system", "content": system_prompt},
            #      {"role": "user", "content": user_message_content}
            # ]

            # Formatting as a single string for `acomplete`:
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"
            logger.info("Calling LLM for scene generation...")
            llm_response = await self.llm.acomplete(full_prompt)

            # Extract the generated text (adjust based on actual response structure)
            generated_text = llm_response.text if llm_response else ""

            if not generated_text.strip():
                 logger.warning("LLM returned an empty response for scene generation.")
                 return "Error: The AI failed to generate a scene draft. Please try again."

            logger.info(f"Scene generation successful for project '{project_id}', chapter '{chapter_id}'.")
            # Return the raw generated markdown
            return generated_text.strip()

        except Exception as e:
            logger.error(f"Error during scene generation for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            error_message = f"Sorry, an error occurred while generating the scene draft for project '{project_id}'. Please check the backend logs for details."
            return error_message

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
        logger.info(f"RagEngine: Starting rephrase for project '{project_id}'. Text: '{selected_text[:50]}...'")

        if not self.index or not self.llm:
            logger.error("RagEngine cannot rephrase: Index or LLM is not available.")
            return ["Error: RAG components are not properly initialized."]

        try:
            # --- Placeholder Implementation ---
            # TODO: Implement actual RAG logic for rephrasing:
            # 1. Construct a retrieval query based on selected_text and maybe surrounding context.
            # 2. Retrieve relevant context using VectorIndexRetriever filtered by project_id.
            #    (Use RAG_GENERATION_SIMILARITY_TOP_K or a dedicated setting).
            # 3. Build a detailed prompt for the LLM:
            #    - Include retrieved project context.
            #    - Include context_before and context_after if provided.
            #    - Clearly state the selected_text to be rephrased.
            #    - Instruct the LLM to provide *multiple* alternative phrasings (e.g., 3 options).
            #    - Specify the output format (e.g., a numbered list or JSON list).
            # 4. Call self.llm.acomplete(prompt).
            # 5. Parse the LLM response to extract the list of suggestions. Handle cases where the LLM doesn't follow format.

            logger.warning("rephrase called, but using placeholder implementation.")

            # Simulate LLM call returning a few options
            await asyncio.sleep(0.1) # Simulate async work

            # Simple placeholder suggestions
            suggestions = [
                f"Alternative 1: This is a rephrased version of '{selected_text}'.",
                f"Alternative 2: Consider saying '{selected_text}' this way instead.",
                f"Alternative 3: Another option for '{selected_text}'.",
            ]

            logger.info(f"Rephrase placeholder successful for project '{project_id}'.")
            return suggestions

        except Exception as e:
            logger.error(f"Error during rephrase for project '{project_id}': {e}", exc_info=True)
            return [f"Error: An error occurred while rephrasing. Please check logs."]


# --- Singleton Instance ---
# No change needed here
try:
     rag_engine = RagEngine()
except Exception as e:
     logger.critical(f"Failed to create RagEngine instance on startup: {e}", exc_info=True)
     raise