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
from fastapi import HTTPException, status # Import HTTPException
from app.rag.engine import rag_engine
# Import all needed AI models
from app.models.ai import (
    AISceneGenerationRequest, AISceneGenerationResponse,
    AIRephraseRequest, AIRephraseResponse,
    AIChapterSplitRequest, AIChapterSplitResponse, ProposedScene # Added chapter split models
)
from llama_index.core.base.response.schema import NodeWithScore
from typing import List, Tuple, Optional, Dict # Import Optional, Dict
import re # Import re for query matching normalization

# Import FileService to load explicit context
from app.services.file_service import file_service
from app.core.config import settings # Import settings for PREVIOUS_SCENE_COUNT

# --- Import the new ChapterSplitter ---
from app.rag.chapter_splitter import ChapterSplitter

logger = logging.getLogger(__name__)

PREVIOUS_SCENE_COUNT = settings.RAG_GENERATION_PREVIOUS_SCENE_COUNT

class AIService:
    """
    Service layer for handling AI-related operations like querying,
    generation, editing, and chapter splitting. Loads explicit context
    before delegating to the appropriate RAG processor.
    """
    def __init__(self):
        # (Initialization unchanged)
        if rag_engine is None:
             logger.critical("RagEngine instance is None! AIService cannot function.")
             raise RuntimeError("Failed to initialize AIService due to missing RagEngine.")
        self.rag_engine = rag_engine
        self.file_service = file_service
        if not hasattr(rag_engine, 'llm') or not rag_engine.llm:
             logger.critical("RagEngine's LLM is not initialized! AIService cannot initialize ChapterSplitter.")
             raise RuntimeError("AIService cannot initialize ChapterSplitter without a valid LLM.")
        if not hasattr(rag_engine, 'index') or not rag_engine.index:
             logger.critical("RagEngine's index is not initialized! AIService cannot initialize ChapterSplitter.")
             raise RuntimeError("AIService cannot initialize ChapterSplitter without a valid index.")
        try:
            self.chapter_splitter = ChapterSplitter(index=rag_engine.index, llm=rag_engine.llm)
            logger.info("ChapterSplitter initialized within AIService.")
        except Exception as e:
            logger.critical(f"Failed to initialize ChapterSplitter within AIService: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize ChapterSplitter: {e}") from e
        logger.info("AIService initialized.")

    async def query_project(self, project_id: str, query_text: str) -> Tuple[str, List[NodeWithScore], Optional[List[Dict[str, str]]]]: # Return list of dicts
        """
        Handles the business logic for querying a project's context.
        Loads explicit Plan/Synopsis, identifies if the query mentions known entities
        (Plan, Synopsis, World, Character, Scene, Note), loads content directly for ALL matches,
        and delegates to RagEngine.
        Returns: Tuple of (answer_string, list_of_retrieved_nodes, optional_list_of_direct_source_info_dicts)
        """
        logger.info(f"AIService: Processing query for project {project_id}: '{query_text}'")

        explicit_plan = "Not Available"
        explicit_synopsis = "Not Available"
        direct_sources_data: List[Dict] = [] # List to hold {'type':..., 'name':..., 'content':...}
        entity_list = [] # List to hold known entities

        logger.debug(f"AIService: Loading explicit context for query (Plan, Synopsis)...")

        # --- 1. Load Plan & Synopsis (Standard Context) & Add to Entity List ---
        # (Logic unchanged)
        try:
            explicit_plan = self.file_service.read_content_block_file(project_id, "plan.md")
            logger.debug(f"AIService (Query): Loaded plan.md (Length: {len(explicit_plan)})")
            entity_list.append({ 'type': 'Plan', 'name': 'Project Plan', 'id': 'plan', 'file_path': self.file_service._get_content_block_path(project_id, "plan.md") })
        except Exception as e: logger.error(f"AIService (Query): Error loading plan.md: {e}", exc_info=True); explicit_plan = "Error loading plan." if not isinstance(e, HTTPException) or e.status_code != 404 else ""
        try:
            explicit_synopsis = self.file_service.read_content_block_file(project_id, "synopsis.md")
            logger.debug(f"AIService (Query): Loaded synopsis.md (Length: {len(explicit_synopsis)})")
            entity_list.append({ 'type': 'Synopsis', 'name': 'Project Synopsis', 'id': 'synopsis', 'file_path': self.file_service._get_content_block_path(project_id, "synopsis.md") })
        except Exception as e: logger.error(f"AIService (Query): Error loading synopsis.md: {e}", exc_info=True); explicit_synopsis = "Error loading synopsis." if not isinstance(e, HTTPException) or e.status_code != 404 else ""

        # --- 2. Compile Full Entity List (World, Characters, Scenes, Notes) ---
        # (Logic unchanged)
        logger.debug("AIService (Query): Compiling full entity list...")
        try:
            entity_list.append({ 'type': 'World', 'name': 'World Info', 'id': 'world', 'file_path': self.file_service._get_content_block_path(project_id, "world.md") })
            project_metadata = self.file_service.read_project_metadata(project_id)
            for char_id, char_data in project_metadata.get('characters', {}).items():
                char_name = char_data.get('name')
                if char_name: entity_list.append({ 'type': 'Character', 'name': char_name, 'id': char_id, 'file_path': self.file_service._get_character_path(project_id, char_id) })
            for chapter_id in project_metadata.get('chapters', {}).keys():
                try:
                    chapter_metadata = self.file_service.read_chapter_metadata(project_id, chapter_id)
                    for scene_id, scene_data in chapter_metadata.get('scenes', {}).items():
                        scene_title = scene_data.get('title')
                        if scene_title: entity_list.append({ 'type': 'Scene', 'name': scene_title, 'id': scene_id, 'file_path': self.file_service._get_scene_path(project_id, chapter_id, scene_id) })
                except Exception as e: logger.error(f"AIService (Query): Error reading chapter metadata for {chapter_id}: {e}", exc_info=True)
            notes_dir = self.file_service._get_project_path(project_id) / "notes"
            if self.file_service.path_exists(notes_dir) and notes_dir.is_dir():
                logger.debug(f"AIService (Query): Scanning notes directory: {notes_dir}")
                for note_path in notes_dir.glob('*.md'):
                    if note_path.is_file():
                        note_name = note_path.stem
                        entity_list.append({ 'type': 'Note', 'name': note_name, 'id': str(note_path), 'file_path': note_path })
            else: logger.debug(f"AIService (Query): Notes directory not found or not a directory: {notes_dir}")
        except Exception as e: logger.error(f"AIService (Query): Unexpected error compiling entity list for {project_id}: {e}", exc_info=True)
        logger.debug(f"AIService (Query): Compiled entity list with {len(entity_list)} items.")


        # --- 3. Query Matching & Direct Content Fetching (MODIFIED to find ALL matches) ---
        # (Logic unchanged)
        matched_entities_found: List[Dict] = []
        if entity_list:
            normalized_query = query_text.lower().strip()
            def normalize_name(name): return name.lower().strip()
            logger.debug(f"AIService (Query): Searching for entity names in normalized query: '{normalized_query}'")
            for entity in entity_list:
                normalized_entity_name = normalize_name(entity['name'])
                pattern = rf"\b{re.escape(normalized_entity_name)}\b"
                if re.search(pattern, normalized_query):
                    logger.info(f"AIService (Query): Found direct match: Type='{entity['type']}', Name='{entity['name']}'")
                    try:
                        logger.info(f"AIService (Query): Attempting to load direct content for matched entity: {entity['name']}")
                        file_path_to_load = entity['file_path']
                        content = ""
                        if entity['type'] in ['Plan', 'Synopsis', 'World']: content = self.file_service.read_content_block_file(project_id, file_path_to_load.name)
                        else: content = self.file_service.read_text_file(file_path_to_load)
                        direct_sources_data.append({ 'type': entity['type'], 'name': entity['name'], 'content': content })
                        logger.info(f"AIService (Query): Successfully loaded direct content for '{entity['name']}' (Length: {len(content)})")
                    except Exception as e: logger.error(f"AIService (Query): Error loading direct content for '{entity['name']}': {e}", exc_info=True) # Log error but continue
        if not direct_sources_data: logger.info("AIService (Query): No direct entity matches found in query.")
        else: logger.info(f"AIService (Query): Found and loaded {len(direct_sources_data)} direct sources.")


        # --- 4. Call RAG Engine ---
        logger.debug("AIService (Query): Delegating query to RagEngine...")
        # --- MODIFIED: Pass direct_sources_data list correctly ---
        answer, source_nodes, direct_sources_info_list = await self.rag_engine.query(
            project_id=project_id,
            query_text=query_text,
            explicit_plan=explicit_plan,
            explicit_synopsis=explicit_synopsis,
            direct_sources_data=direct_sources_data # Pass the list of dicts
        )
        # --- END MODIFIED ---
        return answer, source_nodes, direct_sources_info_list


    # --- generate_scene_draft, rephrase_text, split_chapter_into_scenes remain unchanged ---
    # ... (rest of the methods) ...
    async def generate_scene_draft(self, project_id: str, chapter_id: str, request_data: AISceneGenerationRequest) -> Dict[str, str]: # Return Dict
        # (Logic unchanged)
        logger.info(f"AIService: Processing scene generation request for project {project_id}, chapter {chapter_id}, previous order: {request_data.previous_scene_order}")
        explicit_plan = "Not Available"
        explicit_synopsis = "Not Available"
        explicit_previous_scenes: List[Tuple[int, str]] = []
        logger.debug("AIService: Loading explicit context for generation...")
        try:
            explicit_plan = self.file_service.read_content_block_file(project_id, "plan.md")
        except Exception as e: logger.error(f"AIService (Gen): Error loading plan.md: {e}", exc_info=True); explicit_plan = "Error loading plan." if not isinstance(e, HTTPException) or e.status_code != 404 else ""
        try:
            explicit_synopsis = self.file_service.read_content_block_file(project_id, "synopsis.md")
        except Exception as e: logger.error(f"AIService (Gen): Error loading synopsis.md: {e}", exc_info=True); explicit_synopsis = "Error loading synopsis." if not isinstance(e, HTTPException) or e.status_code != 404 else ""
        previous_scene_order = request_data.previous_scene_order
        if previous_scene_order is not None and previous_scene_order > 0 and PREVIOUS_SCENE_COUNT > 0:
            try:
                chapter_metadata = self.file_service.read_chapter_metadata(project_id, chapter_id)
                scenes_by_order: Dict[int, str] = { data.get('order'): scene_id for scene_id, data in chapter_metadata.get('scenes', {}).items() if data.get('order') is not None and isinstance(data.get('order'), int) }
                loaded_count = 0
                for target_order in range(previous_scene_order, 0, -1):
                    if loaded_count >= PREVIOUS_SCENE_COUNT: break
                    scene_id_to_load = scenes_by_order.get(target_order)
                    if scene_id_to_load:
                        try:
                            scene_path = self.file_service._get_scene_path(project_id, chapter_id, scene_id_to_load)
                            content = self.file_service.read_text_file(scene_path)
                            explicit_previous_scenes.append((target_order, content))
                            loaded_count += 1
                        except HTTPException as scene_load_err: logger.warning(f"AIService (Gen): Scene file not found/error for order {target_order} (ID: {scene_id_to_load}): {scene_load_err.detail}")
            except Exception as general_err: logger.error(f"AIService (Gen): Unexpected error loading previous scenes: {general_err}", exc_info=True)
            explicit_previous_scenes.reverse()
        logger.debug(f"AIService (Gen): Context prepared - Plan: {len(explicit_plan)} chars, Synopsis: {len(explicit_synopsis)} chars, Prev Scenes: {len(explicit_previous_scenes)}")
        try:
            generated_draft_dict = await self.rag_engine.generate_scene(project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary, previous_scene_order=request_data.previous_scene_order, explicit_plan=explicit_plan, explicit_synopsis=explicit_synopsis, explicit_previous_scenes=explicit_previous_scenes)
            if not isinstance(generated_draft_dict, dict) or "title" not in generated_draft_dict or "content" not in generated_draft_dict:
                 error_detail = f"AI scene generation returned an unexpected format: {generated_draft_dict}"
                 logger.error(error_detail)
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=error_detail)
            if isinstance(generated_draft_dict["content"], str) and generated_draft_dict["content"].strip().startswith("Error:"):
                 logger.error(f"Scene generation failed: {generated_draft_dict['content']}")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=generated_draft_dict['content'])
            return generated_draft_dict
        except HTTPException as http_exc: logger.error(f"HTTP Exception during scene generation delegation: {http_exc.detail}", exc_info=True); raise http_exc
        except Exception as e: logger.error(f"Unexpected error during scene generation delegation: {e}", exc_info=True); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during AI scene generation.")

    async def rephrase_text(self, project_id: str, request_data: AIRephraseRequest) -> List[str]:
        # (Logic unchanged)
        logger.info(f"AIService: Processing rephrase request for project {project_id}. Text: '{request_data.selected_text[:50]}...'")
        try:
            suggestions = await self.rag_engine.rephrase(project_id=project_id, selected_text=request_data.selected_text, context_before=request_data.context_before, context_after=request_data.context_after)
            if suggestions and isinstance(suggestions[0], str) and suggestions[0].startswith("Error:"):
                logger.error(f"Rephrasing failed: {suggestions[0]}")
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=suggestions[0])
            return suggestions
        except HTTPException as http_exc: logger.error(f"HTTP Exception during rephrase delegation: {http_exc.detail}", exc_info=True); raise http_exc
        except Exception as e: logger.error(f"Unexpected error during rephrase delegation: {e}", exc_info=True); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during AI rephrasing.")

    async def split_chapter_into_scenes(self, project_id: str, chapter_id: str, request_data: AIChapterSplitRequest) -> List[ProposedScene]:
        # (Logic unchanged)
        logger.info(f"AIService: Processing chapter split request for project {project_id}, chapter {chapter_id}")
        chapter_content = request_data.chapter_content
        if not chapter_content or not chapter_content.strip(): logger.warning(f"AIService (Split): Received empty chapter content for chapter {chapter_id}. Returning empty split."); return []
        logger.debug(f"AIService (Split): Received chapter content (Length: {len(chapter_content)})")
        explicit_plan = "Not Available"; explicit_synopsis = "Not Available"
        logger.debug("AIService (Split): Loading context (Plan, Synopsis)...")
        try: explicit_plan = self.file_service.read_content_block_file(project_id, "plan.md")
        except Exception as e: logger.error(f"AIService (Split): Error loading plan.md: {e}", exc_info=True); explicit_plan = "Error loading plan." if not isinstance(e, HTTPException) or e.status_code != 404 else ""
        try: explicit_synopsis = self.file_service.read_content_block_file(project_id, "synopsis.md")
        except Exception as e: logger.error(f"AIService (Split): Error loading synopsis.md: {e}", exc_info=True); explicit_synopsis = "Error loading synopsis." if not isinstance(e, HTTPException) or e.status_code != 404 else ""
        try:
            logger.debug("AIService (Split): Delegating to ChapterSplitter...")
            proposed_scenes = await self.chapter_splitter.split(project_id=project_id, chapter_id=chapter_id, chapter_content=chapter_content, explicit_plan=explicit_plan, explicit_synopsis=explicit_synopsis)
            return proposed_scenes
        except HTTPException as http_exc: logger.error(f"HTTP Exception during chapter split delegation: {http_exc.detail}", exc_info=True); raise http_exc
        except Exception as e: logger.error(f"Unexpected error during chapter split delegation: {e}", exc_info=True); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during AI chapter splitting.")


# --- Create a singleton instance ---
# (Unchanged)
try:
    ai_service = AIService()
except Exception as e:
     logger.critical(f"Failed to create AIService instance on startup: {e}", exc_info=True)
     raise RuntimeError(f"Failed to initialize AIService: {e}") from e