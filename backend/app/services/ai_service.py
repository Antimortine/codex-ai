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
from fastapi import HTTPException, status
from app.rag.engine import rag_engine
from app.models.ai import ( AISceneGenerationRequest, AISceneGenerationResponse, AIRephraseRequest, AIRephraseResponse, AIChapterSplitRequest, AIChapterSplitResponse, ProposedScene )
from llama_index.core.base.response.schema import NodeWithScore
from typing import List, Tuple, Optional, Dict, Set, TypedDict # Import TypedDict
import re
from pathlib import Path
from app.services.file_service import file_service
from app.core.config import settings

logger = logging.getLogger(__name__)
PREVIOUS_SCENE_COUNT = settings.RAG_GENERATION_PREVIOUS_SCENE_COUNT

# Type hint for context dictionary
class LoadedContext(TypedDict, total=False):
    project_plan: Optional[str]
    project_synopsis: Optional[str]
    chapter_plan: Optional[str]
    chapter_synopsis: Optional[str]
    filter_paths: Set[str]
    # This field is optional and added in _load_context() when a chapter_id is provided
    chapter_title: Optional[str] # Include chapter title if loaded


class AIService:
    def __init__(self):
        self.rag_engine = rag_engine; self.file_service = file_service
        if self.rag_engine is None: logger.critical("RagEngine instance is None during AIService init!")
        logger.info("AIService initialized.")

    # Context Loading Helper (already implemented in previous step)
    def _load_context(self, project_id: str, chapter_id: Optional[str] = None) -> LoadedContext:
        """
        Loads project-level and optionally chapter-level plan/synopsis.
        Returns a dictionary with loaded content (or None if not found/error)
        and a set of absolute paths for successfully loaded files.
        """
        # Initialize all fields with default values to ensure backward compatibility with tests
        context: LoadedContext = {
            'project_plan': None,
            'project_synopsis': None,
            'chapter_plan': None,
            'chapter_synopsis': None,
            'filter_paths': set(),
            'chapter_title': None,  # Always initialize with None even if chapter_id is not provided
        }
        logger.debug(f"AIService: Loading context for project '{project_id}'" + (f", chapter '{chapter_id}'" if chapter_id else ""))

        # Load Project Plan
        try:
            plan_path = self.file_service._get_content_block_path(project_id, "plan.md")
            context['project_plan'] = self.file_service.read_content_block_file(project_id, "plan.md")
            context['filter_paths'].add(str(plan_path.resolve()))
            logger.debug(f"  - Loaded project plan (path: {plan_path})")
        except HTTPException as e:
            if e.status_code != 404: logger.error(f"  - Error loading project plan: {e.detail}")
            else: logger.debug("  - Project plan file not found.")
        except Exception as e:
            logger.error(f"  - Unexpected error loading project plan: {e}", exc_info=True)

        # Load Project Synopsis
        try:
            synopsis_path = self.file_service._get_content_block_path(project_id, "synopsis.md")
            context['project_synopsis'] = self.file_service.read_content_block_file(project_id, "synopsis.md")
            context['filter_paths'].add(str(synopsis_path.resolve()))
            logger.debug(f"  - Loaded project synopsis (path: {synopsis_path})")
        except HTTPException as e:
            if e.status_code != 404: logger.error(f"  - Error loading project synopsis: {e.detail}")
            else: logger.debug("  - Project synopsis file not found.")
        except Exception as e:
            logger.error(f"  - Unexpected error loading project synopsis: {e}", exc_info=True)

        # Load Chapter Context if chapter_id is provided
        if chapter_id:
            # Get Chapter Title (best effort)
            try:
                project_meta = self.file_service.read_project_metadata(project_id)
                chapter_meta_in_proj = project_meta.get('chapters', {}).get(chapter_id, {})
                context['chapter_title'] = chapter_meta_in_proj.get('title', chapter_id) # Fallback to ID
            except Exception as e:
                logger.warning(f"  - Could not get chapter title for {chapter_id}: {e}")
                context['chapter_title'] = chapter_id # Fallback

            # Load Chapter Plan
            try:
                chap_plan_path = self.file_service._get_chapter_plan_path(project_id, chapter_id)
                context['chapter_plan'] = self.file_service.read_chapter_plan_file(project_id, chapter_id)
                if context['chapter_plan'] is not None:
                    context['filter_paths'].add(str(chap_plan_path.resolve()))
                    logger.debug(f"  - Loaded chapter plan for {chapter_id} (path: {chap_plan_path})")
                else:
                    logger.debug(f"  - Chapter plan file not found for {chapter_id}.")
            except Exception as e:
                 logger.error(f"  - Error loading chapter plan for {chapter_id}: {e}", exc_info=True)

            # Load Chapter Synopsis
            try:
                chap_syn_path = self.file_service._get_chapter_synopsis_path(project_id, chapter_id)
                context['chapter_synopsis'] = self.file_service.read_chapter_synopsis_file(project_id, chapter_id)
                if context['chapter_synopsis'] is not None:
                    context['filter_paths'].add(str(chap_syn_path.resolve()))
                    logger.debug(f"  - Loaded chapter synopsis for {chapter_id} (path: {chap_syn_path})")
                else:
                    logger.debug(f"  - Chapter synopsis file not found for {chapter_id}.")
            except Exception as e:
                 logger.error(f"  - Error loading chapter synopsis for {chapter_id}: {e}", exc_info=True)

        logger.debug(f"AIService: Context loading complete. Filter paths: {context['filter_paths']}")
        return context

    async def query_project(self, project_id: str, query_text: str) -> Tuple[str, List[NodeWithScore], Optional[List[Dict[str, str]]]]:
        logger.info(f"AIService: Processing general AI query for project {project_id}. Query: '{query_text}'")
        if self.rag_engine is None: raise HTTPException(status_code=503, detail="AI Engine not ready.")

        # Initialization
        direct_sources_data = [] # List to hold direct entity content
        direct_chapter_context = None # Dictionary for chapter plan/synopsis
        directly_included_paths = set() # Set of paths to filter from RAG retrieval

        # --- REFACTORED: Use helper for project context ---
        project_context = self._load_context(project_id)
        explicit_plan = project_context.get('project_plan')
        explicit_synopsis = project_context.get('project_synopsis')
        paths_to_filter = project_context.get('filter_paths', set())
        # --- END REFACTORED ---

        entity_list = []
        directly_included_paths: Set[str] = paths_to_filter.copy() # Start with paths from project context
        direct_chapter_context: Optional[Dict[str, Optional[str]]] = None # For chapter plan/synopsis if matched

        logger.debug("AIService (Query): Compiling full entity list...")
        try:
            # Add project-level blocks that were successfully loaded
            # --- MODIFIED: Check for None before adding ---
            if explicit_plan is not None:
                try: entity_list.append({ 'type': 'Plan', 'name': 'Project Plan', 'id': 'plan', 'file_path': self.file_service._get_content_block_path(project_id, "plan.md") })
                except Exception as e: logger.warning(f"Could not get path for project plan: {e}")
            if explicit_synopsis is not None:
                try: entity_list.append({ 'type': 'Synopsis', 'name': 'Project Synopsis', 'id': 'synopsis', 'file_path': self.file_service._get_content_block_path(project_id, "synopsis.md") })
                except Exception as e: logger.warning(f"Could not get path for project synopsis: {e}")
            # --- END MODIFIED ---
            try: entity_list.append({ 'type': 'World', 'name': 'World Info', 'id': 'world', 'file_path': self.file_service._get_content_block_path(project_id, "world.md") })
            except Exception as e: logger.warning(f"Could not get path for world info: {e}")

            project_metadata = self.file_service.read_project_metadata(project_id)
            for char_id, char_data in project_metadata.get('characters', {}).items():
                char_name = char_data.get('name');
                if char_name:
                    try: entity_list.append({ 'type': 'Character', 'name': char_name, 'id': char_id, 'file_path': self.file_service._get_character_path(project_id, char_id) })
                    except Exception as e: logger.warning(f"Could not get path for character {char_id}: {e}")

            for chapter_id_meta, chapter_data_meta in project_metadata.get('chapters', {}).items():
                chapter_title = chapter_data_meta.get('title')
                if chapter_title:
                    try:
                        entity_list.append({
                            'type': 'Chapter',
                            'name': chapter_title,
                            'id': chapter_id_meta,
                            'plan_path': self.file_service._get_chapter_plan_path(project_id, chapter_id_meta),
                            'synopsis_path': self.file_service._get_chapter_synopsis_path(project_id, chapter_id_meta)
                        })
                    except Exception as e: logger.warning(f"Could not get paths for chapter {chapter_id_meta}: {e}")

                try:
                    chapter_metadata = self.file_service.read_chapter_metadata(project_id, chapter_id_meta)
                    for scene_id, scene_data in chapter_metadata.get('scenes', {}).items():
                        scene_title = scene_data.get('title');
                        if scene_title:
                            try: entity_list.append({ 'type': 'Scene', 'name': scene_title, 'id': scene_id, 'file_path': self.file_service._get_scene_path(project_id, chapter_id_meta, scene_id), 'chapter_id': chapter_id_meta })
                            except Exception as e: logger.warning(f"Could not get path for scene {scene_id}: {e}")
                except Exception as e: logger.error(f"AIService (Query): Error reading chapter metadata for {chapter_id_meta}: {e}", exc_info=True)

            notes_dir = self.file_service._get_project_path(project_id) / "notes"
            if self.file_service.path_exists(notes_dir) and notes_dir.is_dir():
                for note_path in notes_dir.glob('*.md'):
                    if note_path.is_file():
                        try: entity_list.append({ 'type': 'Note', 'name': note_path.stem, 'id': str(note_path), 'file_path': note_path })
                        except Exception as e: logger.warning(f"Could not process note path {note_path}: {e}")
        except Exception as e: logger.error(f"AIService (Query): Unexpected error compiling entity list for {project_id}: {e}", exc_info=True)

        logger.debug(f"AIService (Query): Compiled entity list with {len(entity_list)} items.")
        if entity_list:
            normalized_query = query_text.lower().strip()
            def normalize_name(name): return name.lower().strip()
            logger.debug(f"AIService (Query): Searching for entity names in normalized query: '{normalized_query}'")
            for entity in entity_list:
                # Skip project plan/synopsis as they are always loaded explicitly (if available)
                if entity['type'] in ['Plan', 'Synopsis']: continue

                normalized_entity_name = normalize_name(entity['name'])
                
                # More flexible matching for Notes and other entities
                is_match = False
                
                # First try exact word boundary matching for best precision
                pattern = rf"\b{re.escape(normalized_entity_name)}\b"
                if re.search(pattern, normalized_query):
                    is_match = True
                    logger.debug(f"AIService (Query): Found exact word match for '{entity['name']}'")
                # For Notes specifically, also try a more flexible match if the note title is significant
                elif entity['type'] == 'Note' and len(normalized_entity_name) > 3 and normalized_entity_name in normalized_query:
                    is_match = True
                    logger.info(f"AIService (Query): Found flexible match for Note '{entity['name']}' - TYPE: {entity['type']}")
                
                if is_match:
                    logger.info(f"AIService (Query): Found direct match: Type='{entity['type']}', Name='{entity['name']}'")
                    try:
                        if entity['type'] == 'Chapter':
                            chapter_id_match = entity['id']
                            logger.debug(f"AIService (Query): Loading direct context for matched Chapter '{entity['name']}' (ID: {chapter_id_match})...")
                            # Use _load_context to get chapter plan/synopsis
                            matched_chapter_context = self._load_context(project_id, chapter_id_match)
                            # Store the loaded context to pass to the engine
                            direct_chapter_context = {
                                'chapter_plan': matched_chapter_context.get('chapter_plan'),
                                'chapter_synopsis': matched_chapter_context.get('chapter_synopsis'),
                                'chapter_title': matched_chapter_context.get('chapter_title', entity['name'])
                            }
                            # Add successfully loaded chapter file paths to filter set
                            directly_included_paths.update(matched_chapter_context.get('filter_paths', set()))
                            logger.info(f"AIService (Query): Loaded direct chapter context for '{entity['name']}'. Plan: {bool(direct_chapter_context['chapter_plan'])}, Synopsis: {bool(direct_chapter_context['chapter_synopsis'])}")
                        else: # Handle other entity types (World, Character, Scene, Note)
                            file_path_to_load = entity.get('file_path')
                            if not file_path_to_load or not isinstance(file_path_to_load, Path):
                                logger.error(f"AIService (Query): Invalid or missing file_path for entity '{entity['name']}': {file_path_to_load}"); continue

                            content = ""
                            if entity['type'] == 'World': 
                                content = self.file_service.read_content_block_file(project_id, file_path_to_load.name)
                                logger.info(f"AIService (Query): Successfully read World content block: {file_path_to_load.name}")
                            elif entity['type'] in ['Character', 'Scene', 'Note']: 
                                try:
                                    logger.info(f"AIService (Query): Attempting to read {entity['type']} file: {file_path_to_load}")
                                    content = self.file_service.read_text_file(file_path_to_load)
                                    logger.info(f"AIService (Query): Successfully read {entity['type']} file, content length: {len(content)}")
                                    if entity['type'] == 'Note':
                                        logger.info(f"AIService (Query): NOTE CONTENT FIRST 100 CHARS: {content[:100]}")
                                except Exception as read_error:
                                    logger.error(f"AIService (Query): Error reading {entity['type']} file {file_path_to_load}: {read_error}")
                                    raise
                            else: 
                                logger.warning(f"AIService (Query): Unknown entity type '{entity['type']}' encountered for direct loading."); 
                                continue

                            # Add to direct sources data
                            source_item = { 'type': entity['type'], 'name': entity['name'], 'content': content, 'file_path': str(file_path_to_load) }
                            direct_sources_data.append(source_item)
                            directly_included_paths.add(str(file_path_to_load.resolve())) # Add resolved path
                            
                            # Log more details for debugging
                            if entity['type'] == 'Note':
                                logger.info(f"AIService (Query): Added Note to direct_sources_data: {entity['name']} with path {file_path_to_load}")
                                logger.info(f"AIService (Query): Current direct_sources_data count: {len(direct_sources_data)}")
                            
                            logger.info(f"AIService (Query): Successfully loaded direct content for '{entity['name']}' (Length: {len(content)})")
                    except Exception as e: logger.error(f"AIService (Query): Error loading direct content for '{entity['name']}': {e}", exc_info=True)

        if not direct_sources_data and not direct_chapter_context: logger.info("AIService (Query): No direct entity matches found in query.")
        else: logger.info(f"AIService (Query): Found and loaded {len(direct_sources_data)} direct sources and chapter context: {bool(direct_chapter_context)}.")

        logger.debug(f"AIService (Query): Final paths to filter from RAG: {directly_included_paths}")
        logger.debug("AIService (Query): Delegating query to RagEngine...")
        answer, source_nodes, direct_sources_info_list = await self.rag_engine.query(
            project_id=project_id,
            query_text=query_text,
            explicit_plan=explicit_plan, # Pass potentially None
            explicit_synopsis=explicit_synopsis, # Pass potentially None
            direct_sources_data=direct_sources_data,
            direct_chapter_context=direct_chapter_context, # Pass chapter context
            paths_to_filter=directly_included_paths
        )
        return answer, source_nodes, direct_sources_info_list

    async def generate_scene_draft(self, project_id: str, chapter_id: str, request_data: AISceneGenerationRequest) -> Dict[str, str]:
        logger.info(f"AIService: Processing scene generation request for project {project_id}, chapter {chapter_id}, previous order: {request_data.previous_scene_order}")
        if self.rag_engine is None: raise HTTPException(status_code=503, detail="AI Engine not ready.")

        # --- REFACTORED: Use helper for project AND chapter context ---
        loaded_context = self._load_context(project_id, chapter_id)
        explicit_plan = loaded_context.get('project_plan')
        explicit_synopsis = loaded_context.get('project_synopsis')
        explicit_chapter_plan = loaded_context.get('chapter_plan')
        explicit_chapter_synopsis = loaded_context.get('chapter_synopsis')
        paths_to_filter = loaded_context.get('filter_paths', set())
        # --- END REFACTORED ---

        explicit_previous_scenes: List[Tuple[int, str]] = []
        # Load previous scenes and add their paths to the filter set
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
                            paths_to_filter.add(str(scene_path.resolve())) # Add path to filter
                            loaded_count += 1
                        except HTTPException as scene_load_err: logger.warning(f"AIService (Gen): Scene file not found/error for order {target_order} (ID: {scene_id_to_load}): {scene_load_err.detail}")
            except Exception as general_err: logger.error(f"AIService (Gen): Unexpected error loading previous scenes: {general_err}", exc_info=True)
            explicit_previous_scenes.reverse()

        logger.debug(f"AIService (Gen): Context prepared - Proj Plan: {bool(explicit_plan)}, Proj Syn: {bool(explicit_synopsis)}, Chap Plan: {bool(explicit_chapter_plan)}, Chap Syn: {bool(explicit_chapter_synopsis)}, Prev Scenes: {len(explicit_previous_scenes)}")
        logger.debug(f"AIService (Gen): Paths to filter from RAG: {paths_to_filter}")
        try:
            generated_draft_dict = await self.rag_engine.generate_scene(
                project_id=project_id, chapter_id=chapter_id, prompt_summary=request_data.prompt_summary,
                previous_scene_order=request_data.previous_scene_order,
                explicit_plan=explicit_plan,
                explicit_synopsis=explicit_synopsis,
                explicit_chapter_plan=explicit_chapter_plan,
                explicit_chapter_synopsis=explicit_chapter_synopsis,
                explicit_previous_scenes=explicit_previous_scenes,
                paths_to_filter=paths_to_filter
            )
            if not isinstance(generated_draft_dict, dict) or "title" not in generated_draft_dict or "content" not in generated_draft_dict: raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"AI scene generation returned an unexpected format: {generated_draft_dict}")
            if isinstance(generated_draft_dict["content"], str) and generated_draft_dict["content"].strip().startswith("Error:"): raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=generated_draft_dict['content'])
            return generated_draft_dict
        except HTTPException as http_exc: logger.error(f"HTTP Exception during scene generation delegation: {http_exc.detail}", exc_info=True); raise http_exc
        except Exception as e: logger.error(f"Unexpected error during scene generation delegation: {e}", exc_info=True); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during AI scene generation.")

    async def rephrase_text(self, project_id: str, request_data: AIRephraseRequest) -> List[str]:
        logger.info(f"AIService: Processing rephrase request for project {project_id}. Text: '{request_data.text_to_rephrase[:50]}...'")
        if self.rag_engine is None: raise HTTPException(status_code=503, detail="AI Engine not ready.")

        # --- REFACTORED: Use helper for project context ---
        loaded_context = self._load_context(project_id) # No chapter_id needed
        explicit_plan = loaded_context.get('project_plan')
        explicit_synopsis = loaded_context.get('project_synopsis')
        paths_to_filter = loaded_context.get('filter_paths', set())
        # --- END REFACTORED ---

        logger.debug(f"AIService (Rephrase): Paths to filter from RAG: {paths_to_filter}")
        try:
            suggestions = await self.rag_engine.rephrase(
                project_id=project_id, selected_text=request_data.text_to_rephrase,
                context_before=request_data.context_before, context_after=request_data.context_after,
                explicit_plan=explicit_plan, # Pass potentially None
                explicit_synopsis=explicit_synopsis, # Pass potentially None
                paths_to_filter=paths_to_filter
            )
            if suggestions and isinstance(suggestions[0], str) and suggestions[0].startswith("Error:"): raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=suggestions[0])
            return suggestions
        except HTTPException as http_exc: logger.error(f"HTTP Exception during rephrase delegation: {http_exc.detail}", exc_info=True); raise http_exc
        except Exception as e: logger.error(f"Unexpected error during rephrase delegation: {e}", exc_info=True); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during AI rephrasing.")

    async def split_chapter_into_scenes(self, project_id: str, chapter_id: str, request_data: AIChapterSplitRequest) -> List[ProposedScene]:
        logger.info(f"AIService: Processing chapter split request for project {project_id}, chapter {chapter_id}")
        if self.rag_engine is None: raise HTTPException(status_code=503, detail="AI Engine not ready.")
        chapter_content = request_data.chapter_content
        if not chapter_content or not chapter_content.strip(): logger.warning(f"AIService (Split): Received empty chapter content for chapter {chapter_id}. Returning empty split."); return []
        logger.debug(f"AIService (Split): Received chapter content (Length: {len(chapter_content)})")

        # --- REFACTORED: Use helper for project AND chapter context ---
        loaded_context = self._load_context(project_id, chapter_id)
        explicit_plan = loaded_context.get('project_plan')
        explicit_synopsis = loaded_context.get('project_synopsis')
        explicit_chapter_plan = loaded_context.get('chapter_plan')
        explicit_chapter_synopsis = loaded_context.get('chapter_synopsis')
        paths_to_filter = loaded_context.get('filter_paths', set())
        # --- END REFACTORED ---

        logger.debug(f"AIService (Split): Paths to filter from RAG: {paths_to_filter}")
        try:
            logger.debug("AIService (Split): Delegating to ChapterSplitter...")
            proposed_scenes = await self.rag_engine.split_chapter(
                project_id=project_id, chapter_id=chapter_id, chapter_content=chapter_content,
                explicit_plan=explicit_plan, # Pass potentially None
                explicit_synopsis=explicit_synopsis, # Pass potentially None
                explicit_chapter_plan=explicit_chapter_plan, # Pass potentially None
                explicit_chapter_synopsis=explicit_chapter_synopsis, # Pass potentially None
                paths_to_filter=paths_to_filter
            )
            return proposed_scenes
        except HTTPException as http_exc: logger.error(f"HTTP Exception during chapter split delegation: {http_exc.detail}", exc_info=True); raise http_exc
        except Exception as e: logger.error(f"Unexpected error during chapter split delegation: {e}", exc_info=True); raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during AI chapter splitting.")

    # (rebuild_project_index remains unchanged)
    async def rebuild_project_index(self, project_id: str) -> Tuple[int, int]:
        """
        Deletes and rebuilds the vector index for a specific project.
        Returns a tuple of (deleted_count, indexed_count).
        """
        logger.info(f"AIService: Received request to rebuild index for project {project_id}")
        if self.rag_engine is None:
            logger.error("AIService: Cannot rebuild index, RagEngine not ready.")
            raise HTTPException(status_code=503, detail="AI Engine not ready.")

        try:
            # 1. Get all markdown file paths for the project
            logger.info(f"AIService: Finding all markdown files for project {project_id}...")
            markdown_paths = self.file_service.get_all_markdown_paths(project_id)
            if not markdown_paths:
                logger.warning(f"AIService: No markdown files found for project {project_id}. Index rebuild might not be necessary or project is empty.")
                # Continue to ensure deletion happens if index exists but files were removed manually
                # Return 0 indexed if no files found, but still perform deletion
                indexed_count = 0
            else:
                indexed_count = len(markdown_paths)

            # 2. Delegate to RagEngine to perform deletion and re-indexing
            logger.info(f"AIService: Delegating index rebuild for {len(markdown_paths)} files to RagEngine...")
            # Assuming RagEngine.rebuild_index is synchronous for now
            # If it becomes async, use 'await' here.
            result = self.rag_engine.rebuild_index(project_id, markdown_paths)
            logger.info(f"AIService: Index rebuild delegation complete for project {project_id}.")
            
            # For now, assume deleted count equals indexed count
            # In a more advanced implementation, the RagEngine could return actual counts
            deleted_count = indexed_count
            
            return deleted_count, indexed_count

        except Exception as e:
            logger.error(f"AIService: Unexpected error during index rebuild for project {project_id}: {e}", exc_info=True)
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to rebuild index for project {project_id} due to an internal error.")


# --- Instantiate Singleton ---
try: ai_service = AIService()
except Exception as e: logger.critical(f"Failed to create AIService instance on startup: {e}", exc_info=True); ai_service = None

# --- Dependency Injection Function ---
def get_ai_service() -> AIService:
    """FastAPI dependency function to inject the AI service instance."""
    if ai_service is None:
        raise HTTPException(status_code=503, detail="AI Service is not available")
    return ai_service