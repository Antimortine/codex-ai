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
import re # For parsing numbered lists
from fastapi import HTTPException, status # For file not found errors
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.core.base.response.schema import Response, NodeWithScore
from typing import List, Tuple, Optional, Dict

from app.rag.index_manager import index_manager
from app.core.config import settings # Import settings
from app.services.file_service import file_service # Import FileService

logger = logging.getLogger(__name__)

# Use settings for configuration
REPHRASE_SIMILARITY_TOP_K = settings.RAG_GENERATION_SIMILARITY_TOP_K # Reuse generation K for context retrieval during edits for now
REPHRASE_SUGGESTION_COUNT = settings.RAG_REPHRASE_SUGGESTION_COUNT # Number of suggestions
PREVIOUS_SCENE_COUNT = settings.RAG_GENERATION_PREVIOUS_SCENE_COUNT # Number of previous scenes to load

class RagEngine:
    """
    Handles RAG querying and potentially generation logic, using the
    index and components initialized by IndexManager.
    """
    def __init__(self):
        """Initializes the RagEngine, ensuring the IndexManager's components are ready."""
        # ... (init remains unchanged) ...
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
        # ... (query method remains unchanged, maybe add character name logging) ...
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


    async def generate_scene(self, project_id: str, chapter_id: str, prompt_summary: Optional[str], previous_scene_order: Optional[int]) -> str:
        """
        Generates a scene draft using explicit context (plan, synopsis, previous N scenes)
        and RAG context for the given project and chapter.

        Args:
            project_id: The ID of the project.
            chapter_id: The ID of the chapter for the new scene.
            prompt_summary: An optional user-provided summary to guide generation.
            previous_scene_order: The order number of the scene immediately preceding
                                  the one to be generated (0 if first scene).

        Returns:
            The generated scene content as a Markdown string or an error message.
        """
        logger.info(f"RagEngine: Starting enhanced scene generation for project '{project_id}', chapter '{chapter_id}'. Previous order: {previous_scene_order}. Prev Scene Count: {PREVIOUS_SCENE_COUNT}. Summary: '{prompt_summary}'")

        if not self.index or not self.llm:
             logger.error("RagEngine cannot generate scene: Index or LLM is not available.")
             return "Error: RAG components are not properly initialized."

        explicit_context = {}
        previous_scenes_content: List[Tuple[int, str]] = [] # Store as (order, content) tuples

        try:
            # --- 1. Load Explicit Context ---
            logger.debug("Loading explicit context: Plan, Synopsis, Previous Scene(s)...")

            # Load Plan
            try:
                 explicit_context['plan'] = file_service.read_content_block_file(project_id, "plan.md")
                 logger.debug("Loaded plan.md")
            except HTTPException as e:
                 if e.status_code == 404: logger.warning("plan.md not found."); explicit_context['plan'] = "Not Available"
                 else: raise

            # Load Synopsis
            try:
                 explicit_context['synopsis'] = file_service.read_content_block_file(project_id, "synopsis.md")
                 logger.debug("Loaded synopsis.md")
            except HTTPException as e:
                 if e.status_code == 404: logger.warning("synopsis.md not found."); explicit_context['synopsis'] = "Not Available"
                 else: raise

            # Load Previous Scene(s) Content
            if previous_scene_order is not None and previous_scene_order > 0 and PREVIOUS_SCENE_COUNT > 0:
                logger.debug(f"Attempting to load up to {PREVIOUS_SCENE_COUNT} previous scene(s) ending at order {previous_scene_order} for chapter {chapter_id}")
                try:
                    # Read chapter metadata once to map order to ID
                    chapter_metadata = file_service.read_chapter_metadata(project_id, chapter_id)
                    scenes_by_order: Dict[int, str] = { # {order: scene_id}
                         data.get('order'): scene_id
                         for scene_id, data in chapter_metadata.get('scenes', {}).items() if data.get('order') is not None
                    }

                    # Loop backwards from previous_scene_order
                    loaded_count = 0
                    for target_order in range(previous_scene_order, 0, -1):
                        if loaded_count >= PREVIOUS_SCENE_COUNT:
                            break # Stop if we've loaded enough scenes

                        scene_id_to_load = scenes_by_order.get(target_order)
                        if scene_id_to_load:
                            try:
                                scene_path = file_service._get_scene_path(project_id, chapter_id, scene_id_to_load)
                                content = file_service.read_text_file(scene_path)
                                previous_scenes_content.append((target_order, content))
                                loaded_count += 1
                                logger.debug(f"Loaded previous scene content (Order: {target_order}, ID: {scene_id_to_load})")
                            except HTTPException as scene_load_err:
                                if scene_load_err.status_code == 404:
                                    logger.warning(f"Scene file not found for order {target_order} (ID: {scene_id_to_load}), skipping.")
                                else:
                                    logger.error(f"Error loading scene file for order {target_order} (ID: {scene_id_to_load}): {scene_load_err.detail}")
                                    # Optionally append an error placeholder to previous_scenes_content
                        else:
                             logger.debug(f"No scene found with order {target_order} in metadata.")

                    # Reverse the list so it's in chronological order [oldest_loaded ... most_recent_loaded]
                    previous_scenes_content.reverse()

                except HTTPException as e:
                    if e.status_code == 404:
                         logger.warning(f"Chapter metadata not found for {chapter_id} while loading previous scenes: {e.detail}")
                    else: raise # Re-raise other file errors
                except Exception as general_err:
                     logger.error(f"Unexpected error loading previous scenes: {general_err}", exc_info=True)

            # --- 2. Retrieve RAG Context ---
            # Retrieval query can still be guided by the summary
            retrieval_query = f"Context relevant for writing a new scene after scene order {previous_scene_order} in chapter {chapter_id}."
            if prompt_summary:
                retrieval_query += f" Scene focus: {prompt_summary}"
            logger.debug(f"Constructed retrieval query: '{retrieval_query}'")

            logger.debug(f"Creating retriever for generation with top_k={settings.RAG_GENERATION_SIMILARITY_TOP_K} and filter for project_id='{project_id}'")
            retriever = VectorIndexRetriever(
                index=self.index,
                similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K,
                filters=MetadataFilters(
                    filters=[ExactMatchFilter(key="project_id", value=project_id)]
                ),
            )
            retrieved_nodes: List[NodeWithScore] = await retriever.aretrieve(retrieval_query)
            logger.info(f"Retrieved {len(retrieved_nodes)} nodes for RAG context.")

            # Include character name in RAG context string if available
            rag_context_list = []
            if retrieved_nodes:
                 for node in retrieved_nodes:
                      char_name = node.metadata.get('character_name')
                      char_info = f" [Character: {char_name}]" if char_name else ""
                      rag_context_list.append(f"Source: {node.metadata.get('file_path', 'N/A')}{char_info}\n\n{node.get_content()}")
            rag_context_str = "\n\n---\n\n".join(rag_context_list) if rag_context_list else "No additional context retrieved via search."


            # --- 3. Build Generation Prompt ---
            logger.debug("Building enhanced generation prompt...")
            system_prompt = (
                "You are an expert writing assistant helping a user draft the next scene in their creative writing project. "
                "Generate a coherent and engaging scene draft in Markdown format. "
                "Pay close attention to the provided Project Plan, Synopsis, and the content of the Immediately Previous Scene(s) to ensure consistency and logical progression. "
                "Also consider the Additional Context retrieved via search."
            )

            # Construct Previous Scenes part of the prompt
            previous_scenes_prompt_part = ""
            if previous_scenes_content:
                 for order, content in previous_scenes_content:
                      # Label the most recent one differently if desired
                      label = f"Immediately Previous Scene (Order: {order})" if order == previous_scene_order else f"Previous Scene (Order: {order})"
                      previous_scenes_prompt_part += f"**{label}:**\n```markdown\n{content}\n```\n\n"
            else:
                 previous_scenes_prompt_part = "**Previous Scene(s):** N/A (Generating the first scene)\n\n"


            user_message_content = (
                f"Please write a draft for the scene that follows the previous scene(s) provided below.\n\n"
                f"**Project Plan:**\n```markdown\n{explicit_context.get('plan', 'Not Available')}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{explicit_context.get('synopsis', 'Not Available')}\n```\n\n"
                # Add the constructed previous scenes block
                f"{previous_scenes_prompt_part}"
                f"**Additional Retrieved Context:**\n```markdown\n{rag_context_str}\n```\n\n"
                f"**New Scene Details:**\n"
                f"- Belongs to: Chapter ID '{chapter_id}'\n"
                f"- Should logically follow the provided previous scene(s).\n"
            )
            if prompt_summary:
                user_message_content += f"- User Guidance/Focus for New Scene: {prompt_summary}\n\n"
            else:
                user_message_content += "- User Guidance/Focus for New Scene: (None provided - focus on natural progression from the previous scene(s) and overall context)\n\n"

            user_message_content += (
                "**Instructions:**\n"
                "- Generate the new scene content in pure Markdown format.\n"
                "- Start directly with the scene content (e.g., a heading like '## Scene Title' or directly with narrative).\n"
                "- Ensure the new scene flows logically from the previous scene(s).\n"
                "- Maintain consistency with characters, plot points, and world details mentioned in the Plan, Synopsis, and other context.\n"
                "- Do NOT add explanations or commentary outside the new scene's Markdown content."
            )

            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"
            # Optional: Log the full prompt if needed for debugging (can be very long)
            # logger.debug(f"Full Generation Prompt:\n{full_prompt}")
            logger.info("Calling LLM for enhanced scene generation...")
            llm_response = await self.llm.acomplete(full_prompt)

            generated_text = llm_response.text if llm_response else ""

            if not generated_text.strip():
                 logger.warning("LLM returned an empty response for scene generation.")
                 return "Error: The AI failed to generate a scene draft. Please try again."

            logger.info(f"Enhanced scene generation successful for project '{project_id}', chapter '{chapter_id}'.")
            return generated_text.strip()

        except HTTPException as http_exc:
            logger.error(f"HTTP Exception during explicit context loading for scene generation: {http_exc.detail}", exc_info=True)
            return f"Error: Could not load necessary project context ({http_exc.detail})."
        except Exception as e:
            logger.error(f"Error during scene generation for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            error_message = f"Sorry, an error occurred while generating the scene draft. Please check logs."
            return error_message


    async def rephrase(self, project_id: str, selected_text: str, context_before: Optional[str], context_after: Optional[str]) -> List[str]:
        """Rephrases the selected text using RAG context."""
        # ... (rephrase method remains unchanged) ...
        logger.info(f"RagEngine: Starting rephrase for project '{project_id}'. Text: '{selected_text[:50]}...'")

        if not self.index or not self.llm:
            logger.error("RagEngine cannot rephrase: Index or LLM is not available.")
            return ["Error: RAG components are not properly initialized."]

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
            # Use regex to find lines starting with number, dot, optional space
            suggestions = re.findall(r"^\s*\d+\.\s*(.*)", generated_text, re.MULTILINE)

            if not suggestions:
                logger.warning(f"Could not parse numbered list from LLM response. Response was:\n{generated_text}")
                # Return the raw response as a single suggestion if parsing fails, better than nothing
                return [f"Error: Could not parse suggestions. Raw response: {generated_text}"]

            # Clean up potential leading/trailing whitespace from parsed suggestions
            suggestions = [s.strip() for s in suggestions]

            logger.info(f"Successfully parsed {len(suggestions)} rephrase suggestions for project '{project_id}'.")
            return suggestions

        except Exception as e:
            logger.error(f"Error during rephrase for project '{project_id}': {e}", exc_info=True)
            return [f"Error: An unexpected error occurred while rephrasing. Please check logs."]


# --- Singleton Instance ---
# No change needed here
try:
     rag_engine = RagEngine()
except Exception as e:
     logger.critical(f"Failed to create RagEngine instance on startup: {e}", exc_info=True)
     raise