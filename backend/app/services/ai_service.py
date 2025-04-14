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
                        try: 
                            # Read the note content to extract title, with improved error handling
                            note_title = note_path.stem  # Default to filename if we can't extract title
                            
                            try:
                                # Use the more robust file reading method we updated
                                note_content = self.file_service.read_text_file(note_path)
                                
                                # Try to extract title from the content
                                if note_content and not note_content.startswith('[Error'):
                                    lines = note_content.splitlines()
                                    if lines:
                                        first_line = lines[0].strip()
                                        if first_line:
                                            # Remove any markdown heading markers and whitespace
                                            note_title = first_line.lstrip('#').strip()
                                            
                                            # Remove any BOM characters that might be at the start of the title
                                            # UTF-16 LE BOM appears as ÿþ in latin-1 encoding
                                            if note_title.startswith('ÿþ'):
                                                note_title = note_title[2:]
                                                logger.info(f"AIService (Query): Removed BOM characters from title, new title: '{note_title}'")
                                            # Handle other potential BOM markers
                                            elif note_title.startswith('\ufeff'): # UTF-8 BOM
                                                note_title = note_title[1:]
                                                logger.info(f"AIService (Query): Removed UTF-8 BOM from title, new title: '{note_title}'")
                                            
                                            logger.info(f"AIService (Query): Extracted note title '{note_title}' from file {note_path.name}")
                                            
                                            # If title seems generic, store entire first line for better matching
                                            if note_title.lower() in ["note", "note 1", "notes"]:
                                                logger.info(f"AIService (Query): Note has generic title: '{note_title}'")
                            except Exception as title_error:
                                logger.warning(f"AIService (Query): Could not extract title from note {note_path}, using filename: {title_error}")
                                
                            # See if the note has a title in project metadata (which is the "official" title)
                            metadata_title = None
                            try:
                                # Check project metadata for title
                                project_metadata = self.file_service.read_project_metadata(project_id=project_id)
                                note_id = note_path.stem  # The note ID is the filename without extension
                                if 'notes' in project_metadata and note_id in project_metadata['notes']:
                                    metadata_title = project_metadata['notes'][note_id].get('title')
                                    logger.info(f"AIService (Query): Found metadata title '{metadata_title}' for note {note_path.name}")
                            except Exception as meta_err:
                                logger.warning(f"AIService (Query): Could not retrieve metadata title for note {note_path}: {meta_err}")
                            
                            # Add note to entity list with extracted or default title
                            entity_list.append({ 
                                'type': 'Note', 
                                'name': note_title, 
                                'id': str(note_path), 
                                'file_path': note_path,
                                'metadata_title': metadata_title  # Store metadata title if available
                            })
                            
                            logger.info(f"AIService (Query): Added note entity: '{note_title}' from {note_path.name}")
                        except Exception as e: logger.warning(f"Could not process note path {note_path}: {e}")
        except Exception as e: logger.error(f"AIService (Query): Unexpected error compiling entity list for {project_id}: {e}", exc_info=True)

        logger.debug(f"AIService (Query): Compiled entity list with {len(entity_list)} items.")
        if entity_list:
            # Improved Unicode normalization for multilingual support, especially for Cyrillic
            import unicodedata
            import re
            
            def normalize_name(name):
                if not name: return ""
                # Convert to Unicode NFC form (fully composed) and lowercase
                normalized = unicodedata.normalize('NFC', name.lower().strip())
                return normalized
                
            # Function to split query into words and clean them
            def extract_query_words(query_text):
                if not query_text: return []
                # Normalize and split by common delimiters
                normalized = normalize_name(query_text)
                # Use regex to split on word boundaries (works for Latin and Cyrillic)
                words = re.findall(r'\b\w+\b', normalized, re.UNICODE)
                # Filter out very short words and common stop words
                return [w for w in words if len(w) > 2 and w not in ['and', 'the', 'for', 'из', 'для', 'и']]
                
            # Extract meaningful words from the query for better matching
            query_words = extract_query_words(query_text)
            normalized_query = normalize_name(query_text)
            logger.debug(f"AIService (Query): Searching for entity names in normalized query: '{normalized_query}'")
            logger.debug(f"AIService (Query): Extracted query words: {query_words}")
            
            # Special handling for Russian queries with "технической информации" section
            # Find sections like "ключевые слова (проигнорируй ... техническая информация): keyword1, keyword2, ..."
            tech_info_match = re.search(r'ключевые слова\s*(?:\(.*?\))?\s*:\s*(.+)', normalized_query, re.IGNORECASE)
            if not tech_info_match:
                # Fallback to older pattern if the first one doesn't match
                tech_info_match = re.search(r'\(?проигнорируй.*?техническ.*?информ[^)]*\)?:(.+)', normalized_query, re.IGNORECASE)
            
            # We'll put all comma-separated items from this section into a list for direct matching
            entity_keywords_to_match = []
            
            if tech_info_match:
                tech_info = tech_info_match.group(1).strip()
                logger.info(f"AIService (Query): Found technical info section for entity extraction: '{tech_info}'")
                
                # Split by commas and clean each item
                raw_keywords = [k.strip() for k in tech_info.split(',')]
                logger.info(f"AIService (Query): Raw comma-separated keywords: {raw_keywords}")
                
                # Save these keywords for exact matching
                for keyword in raw_keywords:
                    # Clean up quotes and extra whitespace
                    clean_keyword = keyword.strip().strip('"').strip()
                    if clean_keyword and len(clean_keyword) > 2:  # Avoid empty or very short keywords
                        entity_keywords_to_match.append(clean_keyword)
                        logger.info(f"AIService (Query): Added keyword for exact matching: '{clean_keyword}'")
                
                # No special cases - we want pure exact matching to work for all notes
                
                logger.info(f"AIService (Query): Final entity keywords to match: {entity_keywords_to_match}")
            
            for entity in entity_list:
                # Skip project plan/synopsis as they are always loaded explicitly (if available)
                if entity['type'] in ['Plan', 'Synopsis']: continue
                
                # Skip technical/system notes (just in case they weren't filtered earlier)
                if entity['type'] == 'Note' and (entity['name'].startswith('.') or entity['name'] == '.folder'):
                    logger.debug(f"AIService (Query): Skipping technical note '{entity['name']}'")
                    continue

                normalized_entity_name = normalize_name(entity['name'])
                entity_words = re.findall(r'\b\w+\b', normalized_entity_name, re.UNICODE)
                
                # MODIFIED: Instead of skipping entities in technical keywords,
                # check if this entity matches any of our extracted entity keywords to match
                entity_match_found = False
                
                # Check if entity name is in our list of entities to match from technical section
                for keyword in entity_keywords_to_match:
                    normalized_keyword = normalize_name(keyword)
                    # Check for various matching methods
                    if (normalized_keyword == normalized_entity_name or
                        normalized_keyword in normalized_entity_name or
                        normalized_entity_name in normalized_keyword):
                        entity_match_found = True
                        logger.info(f"AIService (Query): Entity '{entity['name']}' MATCHED keyword '{keyword}'")
                        break
                
                if entity_match_found:
                    # This is an entity we want to include in direct sources
                    logger.info(f"AIService (Query): Including entity '{entity['name']}' as it matches a keyword to match")
                    # Continue to matching code below
                    pass
                # We've removed the reference to ignored_keywords since it no longer exists
                
                # More flexible matching for Notes and other entities
                is_match = False
                
                # First try exact word boundary matching for best precision
                pattern = rf"\b{re.escape(normalized_entity_name)}\b"
                if re.search(pattern, normalized_query):
                    is_match = True
                    logger.debug(f"AIService (Query): Found exact word match for '{entity['name']}'")
                # For Notes specifically
                # Specific handling for different entity types
                elif entity['type'] == 'Scene' or entity['type'] == 'Character':
                    # Enhanced Scene and Character matching - handle both "log Zero" and "Zero log"
                    original_name = entity['name']
                    # Get normalized clean name
                    clean_name = original_name
                    normalized_clean_name = normalize_name(clean_name)
                    
                    logger.info(f"AIService (Query): Checking {entity['type']} '{original_name}' with normalized name: '{normalized_clean_name}'")
                    
                    # For scenes like "Внутренний лог Zero" we need more flexible matching
                    # Check if all the significant words from the scene title are in the query
                    # But not just any partial matches that could cause false positives
                    scene_words = [w for w in re.findall(r'\b\w+\b', normalized_clean_name, re.UNICODE) if len(w) > 2]
                    if scene_words:
                        # Count how many significant words from the scene title appear in the query
                        matching_words = [word for word in scene_words if word in normalized_query]
                        # For longer titles, require at least 2 words to match
                        min_matches_needed = 2 if len(scene_words) > 2 else 1
                        
                        if len(matching_words) >= min_matches_needed:
                            is_match = True
                            logger.info(f"AIService (Query): Found multiple word matches for {entity['type']} '{original_name}': {matching_words}")
                        # Direct mention with name in quotes
                        elif re.search(f'"{re.escape(normalized_clean_name)}"', normalized_query):
                            is_match = True
                            logger.info(f"AIService (Query): Found quoted name '{original_name}' in query")
                
                elif entity['type'] == 'Note':
                    # IMPORTANT FIX: Use metadata_title for matching when available since it's the actual note title
                    # The entity['name'] is often just the UUID of the note, not its title
                    original_name = entity.get('metadata_title') if entity.get('metadata_title') else entity['name']
                    
                    # Clean name from potential BOM markers for comparison
                    clean_name = original_name
                    if clean_name.startswith('\u00ff\u00fe'): # UTF-16 LE BOM in latin-1
                        clean_name = clean_name[2:]
                        logger.info(f"AIService (Query): Removed BOM characters from note name for matching: '{clean_name}'")
                    
                    logger.info(f"AIService (Query): Using '{clean_name}' for note matching (metadata_title={entity.get('metadata_title')}, entity name={entity['name']})")
                    
                    # SIMPLIFIED MATCHING STRATEGY
                    logger.info(f"AIService (Query): ===== START NOTE MATCHING for '{clean_name}' =====")
                    
                    # Log entity being processed for debugging
                    logger.info(f"AIService (Query): Processing note '{clean_name}' for matching")
                    
                    # 1. Direct keyword match from the comma-separated list (MOST IMPORTANT MATCHING METHOD)
                    # This should be the primary matching method when technical keywords section exists
                    if not is_match:
                        for keyword in entity_keywords_to_match:
                            # Log what we're checking for clarity
                            logger.info(f"AIService (Query): Checking if note title '{clean_name}' exactly matches keyword '{keyword}'")
                            
                            if clean_name == keyword.strip():
                                is_match = True
                                logger.info(f"AIService (Query): EXACT MATCH - Note title '{clean_name}' exactly matches keyword '{keyword}'")
                                break
                                
                            # Also try with quotes removed (in case query has "\u0414\u0443\u0445 \u0438 \u0434\u0435\u0442\u0430\u043b\u0438\u0437\u0430\u0446\u0438\u044f")
                            clean_keyword = keyword.strip().strip('"').strip()
                            logger.info(f"AIService (Query): Also checking cleaned version: '{clean_keyword}'")
                            
                            if clean_name == clean_keyword:
                                is_match = True
                                logger.info(f"AIService (Query): EXACT MATCH after quote removal - Note '{clean_name}' matches '{clean_keyword}'")
                                break
                    
                    # 2. Case-insensitive match
                    if not is_match:
                        clean_name_lower = clean_name.lower()
                        # Check each keyword in lowercase
                        for keyword in entity_keywords_to_match:
                            keyword_lower = keyword.lower()
                            if clean_name_lower == keyword_lower:
                                is_match = True
                                logger.info(f"AIService (Query): CASE-INSENSITIVE MATCH - '{clean_name_lower}' == '{keyword_lower}'")
                                break
                            # For multi-word notes, check for fuzzy matches
                            elif ' ' in clean_name:
                                # Is there significant overlap in the words?
                                clean_words = set(clean_name_lower.split())
                                keyword_words = set(keyword_lower.split())
                                # Calculate how many words overlap
                                overlap = clean_words.intersection(keyword_words)
                                # Calculate percent of overlap
                                overlap_percent = len(overlap) / max(len(clean_words), len(keyword_words))
                                logger.info(f"AIService (Query): Overlap between '{clean_name}' and '{keyword}': {len(overlap)}/{max(len(clean_words), len(keyword_words))} words ({overlap_percent:.2%})")
                                # If significant overlap, consider it a match
                                if overlap_percent > 0.5:
                                    is_match = True
                                    logger.info(f"AIService (Query): WORD OVERLAP MATCH - Note '{clean_name}' words match keyword '{keyword}'")
                                    break
                    
                    # Log final result for this note
                    logger.info(f"AIService (Query): Is '{clean_name}' matched? {is_match}")
                    logger.info(f"AIService (Query): ===== END NOTE MATCHING for '{clean_name}' =====\n")
                    
                    if is_match:
                        logger.info(f"AIService (Query): Found match for Note '{entity['name']}' - TYPE: {entity['type']}")
                
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

                            # Add to direct sources data - use metadata title when available for better UI display
                            display_name = entity.get('metadata_title') if entity.get('metadata_title') else entity['name']
                            source_item = { 'type': entity['type'], 'name': display_name, 'content': content, 'file_path': str(file_path_to_load) }
                            direct_sources_data.append(source_item)
                            directly_included_paths.add(str(file_path_to_load.resolve())) # Add resolved path
                            
                            # Log more details for debugging
                            if entity['type'] == 'Note':
                                logger.info(f"AIService (Query): Added Note to direct_sources_data: {entity['name']} with path {file_path_to_load}")
                                logger.info(f"AIService (Query): Current direct_sources_data count: {len(direct_sources_data)}")
                                logger.info(f"AIService (Query): Direct source data note content first 100 chars: {content[:100] if content else '(empty)'}")
                            
                            logger.info(f"AIService (Query): Successfully loaded direct content for '{entity['name']}' (Length: {len(content)})")
                    except Exception as e: logger.error(f"AIService (Query): Error loading direct content for '{entity['name']}': {e}", exc_info=True)

        # Enhanced logging for direct sources debugging
        logger.info(f"AIService (Query): Final processing - query_text: '{query_text}'")
        logger.info(f"AIService (Query): Direct sources data count: {len(direct_sources_data)}")
        
        if direct_sources_data:
            for i, item in enumerate(direct_sources_data):
                logger.info(f"AIService (Query): Direct source {i+1} type={item.get('type')}, name={item.get('name')}")
                content_len = len(item.get('content', ''))
                logger.info(f"AIService (Query): Content length: {content_len}, first 100 chars: {item.get('content', '')[:100]}")

        # Log original summary
        if not direct_sources_data and not direct_chapter_context: 
            logger.info("AIService (Query): No direct entity matches found in query.")
        else: 
            logger.info(f"AIService (Query): Found and loaded {len(direct_sources_data)} direct sources and chapter context: {bool(direct_chapter_context)}.")

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
        
        # Log the results returned from RAG engine
        logger.info(f"AIService (Query): RagEngine returned: answer length={len(answer) if answer else 0}")
        logger.info(f"AIService (Query): source_nodes count={len(source_nodes) if source_nodes else 0}")
        
        # Debug the direct_sources_info_list
        if direct_sources_info_list:
            logger.info(f"AIService (Query): direct_sources_info_list returned: {direct_sources_info_list}")
        else:
            logger.info("AIService (Query): direct_sources_info_list is None or empty")
            
        # Force direct_sources_info_list to contain something if we had direct sources
        if direct_sources_data and (direct_sources_info_list is None or len(direct_sources_info_list) == 0):
            logger.info("AIService (Query): Creating direct_sources_info_list from direct_sources_data because RagEngine returned None")
            direct_sources_info_list = []
            for source in direct_sources_data:
                direct_sources_info_list.append({
                    "type": source.get("type", "Unknown"),
                    "name": source.get("name", "Unknown")
                })
            logger.info(f"AIService (Query): Created direct_sources_info_list: {direct_sources_info_list}")
            
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