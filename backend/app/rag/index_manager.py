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
from pathlib import Path
import os
import torch
from typing import Optional, Dict, Any, List # Import List

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings as LlamaSettings,
    load_index_from_storage,
)
from llama_index.core.vector_stores import ExactMatchFilter, MetadataFilters
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.google_genai import GoogleGenAI
import chromadb
from app.core.config import settings, BASE_PROJECT_DIR # Import settings
from app.services.file_service import file_service


logger = logging.getLogger(__name__)

# --- Configuration ---
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_COLLECTION_NAME = "codex_ai_documents"
LLM_MODEL_NAME = "models/gemini-1.5-pro-latest"
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-mpnet-base-v2"

class IndexManager:
    """
    Manages the RAG index for project content using LlamaIndex, ChromaDB, Google Gemini LLM, and HuggingFace Embeddings.
    Focuses on index initialization and modification (add/update/delete).
    Injects relevant metadata (project_id, file_path, document_type, document_title, chapter_id, chapter_title) into nodes.
    """

    def __init__(self):
        """
        Initializes the IndexManager. Sets up LlamaIndex components (LLM, Embeddings, Vector Store)
        and loads or creates the VectorStoreIndex.
        """
        logger.info("Initializing IndexManager...")
        self.index: Optional[VectorStoreIndex] = None
        self.llm: Optional[GoogleGenAI] = None # Specific type hint
        self.embed_model: Optional[HuggingFaceEmbedding] = None
        self.storage_context: Optional[StorageContext] = None
        self.vector_store: Optional[ChromaVectorStore] = None
        self.chroma_collection: Optional[chromadb.Collection] = None

        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY not found in settings. Cannot initialize AI components.")
            raise ValueError("GOOGLE_API_KEY is not configured.")

        try:
            # 1. Configure LlamaIndex Settings globally
            logger.debug(f"Configuring LLM: {LLM_MODEL_NAME} with temperature: {settings.LLM_TEMPERATURE}")
            try:
                 LlamaSettings.llm = GoogleGenAI(
                     model=LLM_MODEL_NAME,
                     api_key=settings.GOOGLE_API_KEY,
                     temperature=settings.LLM_TEMPERATURE
                 )
            except TypeError:
                 logger.warning("Initialization with 'model' failed for GoogleGenAI, trying 'model_name'.")
                 LlamaSettings.llm = GoogleGenAI(
                     model_name=LLM_MODEL_NAME,
                     api_key=settings.GOOGLE_API_KEY,
                     temperature=settings.LLM_TEMPERATURE
                 )
            self.llm = LlamaSettings.llm

            logger.debug(f"Configuring Embedding Model: {EMBEDDING_MODEL_NAME}")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device '{device}' for HuggingFace embeddings.")
            LlamaSettings.embed_model = HuggingFaceEmbedding(model_name=EMBEDDING_MODEL_NAME, device=device)
            self.embed_model = LlamaSettings.embed_model

            # 2. Initialize ChromaDB Client and Vector Store
            logger.debug(f"Initializing ChromaDB client with persistence directory: {CHROMA_PERSIST_DIR}")
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            db = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            logger.debug(f"Getting or creating ChromaDB collection: {CHROMA_COLLECTION_NAME}")
            self.chroma_collection = db.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
            logger.debug("Initializing ChromaVectorStore...")
            self.vector_store = ChromaVectorStore(chroma_collection=self.chroma_collection)

            # 3. Initialize Storage Context
            logger.debug("Initializing StorageContext...")
            self.storage_context = StorageContext.from_defaults(vector_store=self.vector_store)

            # 4. Load or Create the Index
            try:
                logger.info(f"Attempting to load index from storage: {CHROMA_PERSIST_DIR}")
                self.index = load_index_from_storage(self.storage_context)
                logger.info("Successfully loaded existing index.")
            except Exception as e:
                if isinstance(e, ValueError) and ("No existing" in str(e) and "storage" in str(e)):
                     logger.warning(f"Failed to load index from storage (Index not found or empty): {e}. Creating new index.")
                else:
                     logger.warning(f"Failed to load index from storage (might be first run or other issue): {e}. Creating new index.")
                self.index = VectorStoreIndex.from_documents([], storage_context=self.storage_context)
                logger.info("Created new empty index.")

            if not self.index: # Final check
                 raise RuntimeError("Index could not be loaded or created.")

            logger.info("IndexManager initialized successfully.")

        except Exception as e:
            logger.error(f"Fatal error during IndexManager initialization: {e}", exc_info=True)
            self.index = None # Ensure index is None on failure
            raise RuntimeError(f"Failed to initialize IndexManager: {e}") from e

    def _extract_project_id(self, file_path: Path) -> str | None:
        """
        Extracts the project_id from the file path relative to BASE_PROJECT_DIR.
        Returns the project_id string or None if the path is not structured as expected.
        """
        try:
            abs_file_path = file_path.resolve(); abs_base_dir = BASE_PROJECT_DIR.resolve()
            if abs_base_dir not in abs_file_path.parents: return None
            relative_path = abs_file_path.relative_to(abs_base_dir)
            if not relative_path.parts: return None
            return relative_path.parts[0]
        except Exception as e: logger.error(f"Error extracting project_id from path {file_path}: {e}", exc_info=True); return None

    def _get_document_details(self, file_path: Path, project_id: str) -> Dict[str, Any]:
        """
        Determines the document type and title based on its path and project metadata.
        For scenes, it also attempts to add chapter_id and chapter_title.
        For chapter plan/synopsis, it adds chapter_id and chapter_title.
        For notes, it gets the title from project metadata.
        Returns a dictionary containing metadata keys.
        """
        default_title = file_path.name
        details = {'document_type': 'Unknown', 'document_title': default_title}
        fs = file_service # Use the imported file_service instance

        # ADDED: Skip special ".folder" placeholder notes
        if file_path.stem == '.folder':
            logger.debug(f"Skipping '.folder' placeholder note: {file_path}")
            details = {'document_type': 'SkipIndexing', 'document_title': '.folder'}
            return details

        try:
            relative_path_parts = file_path.relative_to(BASE_PROJECT_DIR / project_id).parts
            # Project-level files
            if file_path.name == "plan.md" and len(relative_path_parts) == 1: details = {'document_type': 'Plan', 'document_title': 'Project Plan'}
            elif file_path.name == "synopsis.md" and len(relative_path_parts) == 1: details = {'document_type': 'Synopsis', 'document_title': 'Project Synopsis'}
            elif file_path.name == "world.md" and len(relative_path_parts) == 1: details = {'document_type': 'World', 'document_title': 'World Info'}
            # Character files
            elif len(relative_path_parts) > 1 and relative_path_parts[0] == 'characters' and file_path.suffix == '.md':
                character_id = file_path.stem
                project_meta = fs.read_project_metadata(project_id=project_id) # Use keyword
                char_name = project_meta.get('characters', {}).get(character_id, {}).get('name')
                details = {'document_type': 'Character', 'document_title': char_name or character_id}
            # --- ADDED: Note files ---
            elif len(relative_path_parts) > 1 and relative_path_parts[0] == 'notes' and file_path.suffix == '.md':
                note_id = file_path.stem # Note ID is the filename stem (UUID)
                # ADDED: Skip technical notes
                if note_id.startswith('.'):
                    logger.debug(f"Skipping technical note with ID starting with '.': {note_id}")
                    details = {'document_type': 'SkipIndexing', 'document_title': note_id}
                    return details
                
                project_meta = fs.read_project_metadata(project_id=project_id) # Use keyword
                note_title = project_meta.get('notes', {}).get(note_id, {}).get('title')
                details = {'document_type': 'Note', 'document_title': note_title or note_id} # Fallback to ID
            # --- END ADDED ---
            # Chapter-level files (Scenes, Plan, Synopsis)
            elif len(relative_path_parts) > 1 and relative_path_parts[0] == 'chapters':
                chapter_id = relative_path_parts[1]
                chapter_title = chapter_id # Default chapter title to ID
                # Get Chapter Title from project metadata
                try:
                    project_meta = fs.read_project_metadata(project_id=project_id) # Use keyword
                    chapter_meta_in_proj = project_meta.get('chapters', {}).get(chapter_id, {})
                    title_from_proj_meta = chapter_meta_in_proj.get('title')
                    if title_from_proj_meta:
                        chapter_title = title_from_proj_meta
                        logger.debug(f"Found chapter title '{chapter_title}' in project metadata for chapter {chapter_id}.")
                    else:
                        logger.warning(f"Chapter title not found or empty in project metadata for chapter {chapter_id}. Using ID '{chapter_id}' as chapter title.")
                except Exception as e:
                    logger.warning(f"Could not read project metadata to get chapter title for {chapter_id}: {e}. Using ID '{chapter_id}' as chapter title.")

                if file_path.name == "plan.md" and len(relative_path_parts) == 3:
                    details = {
                        'document_type': 'ChapterPlan',
                        'document_title': f"Plan for Chapter '{chapter_title}'",
                        'chapter_id': chapter_id,
                        'chapter_title': chapter_title
                    }
                elif file_path.name == "synopsis.md" and len(relative_path_parts) == 3:
                    details = {
                        'document_type': 'ChapterSynopsis',
                        'document_title': f"Synopsis for Chapter '{chapter_title}'",
                        'chapter_id': chapter_id,
                        'chapter_title': chapter_title
                    }
                elif len(relative_path_parts) > 2 and relative_path_parts[2].endswith('.md'): # Check if it's likely a scene file
                    scene_id = file_path.stem
                    scene_title = scene_id # Default to ID
                    try:
                        chapter_meta = fs.read_chapter_metadata(project_id=project_id, chapter_id=chapter_id) # Use keywords
                        scene_meta = chapter_meta.get('scenes', {}).get(scene_id, {})
                        title_from_meta = scene_meta.get('title')
                        if title_from_meta:
                            scene_title = title_from_meta
                            logger.debug(f"Found scene title '{scene_title}' in chapter metadata for scene {scene_id}.")
                        else:
                            logger.warning(f"Scene title not found or empty in chapter metadata for scene {scene_id}. Using ID '{scene_id}' as title.")
                    except Exception as e:
                        logger.warning(f"Could not read chapter metadata for {chapter_id} to get scene title for {scene_id}: {e}. Using ID '{scene_id}' as title.")

                    details = {
                        'document_type': 'Scene',
                        'document_title': scene_title,
                        'chapter_id': chapter_id,
                        'chapter_title': chapter_title
                    }
            # Note: Removed redundant 'notes' check here as it's handled above now.
        except Exception as e: logger.error(f"Error determining document details for {file_path}: {e}", exc_info=True)
        return details

    def index_file(self, file_path: Path, preloaded_metadata: Optional[Dict[str, Any]] = None):
        """
        Loads, parses, embeds, adds metadata (project_id, file_path, document_type, document_title, chapter_id, chapter_title),
        and inserts/updates a single file's content into the index.
        If the document already exists (based on file_path), it's deleted first.
        Empty files are skipped.

        Args:
            file_path: Path to the file to index
            preloaded_metadata: Optional dictionary containing pre-loaded metadata to use instead of reading from filesystem
                               This helps avoid race conditions when metadata has just been updated
        """
        if not self.index: logger.error("Index is not initialized. Cannot index file."); return
        if not isinstance(file_path, Path): logger.error(f"IndexManager.index_file called with invalid type for file_path: {type(file_path)}"); return
        if not file_path.is_file(): logger.warning(f"IndexManager.index_file called with non-existent file: {file_path}"); return

        try:
            if file_path.stat().st_size == 0:
                logger.info(f"Skipping indexing for empty file: {file_path}")
                self.delete_doc(file_path) # Attempt to remove any stale nodes
                return
        except OSError as e: logger.error(f"Could not check file size for {file_path}: {e}"); return

        logger.info(f"IndexManager: Received request to index/update file: {file_path}")
        project_id = self._extract_project_id(file_path)
        if not project_id: logger.error(f"Could not determine project_id for file {file_path}. Skipping indexing."); return
        
        # ADDED: Check if the file is a special file that should be skipped (like .folder notes)
        if file_path.stem == '.folder' or file_path.stem.startswith('.'):
            logger.info(f"Skipping indexing for technical file: {file_path}")
            self.delete_doc(file_path)  # Remove any existing nodes for this path
            return
            
        # Get document details and check if it should be skipped
        doc_details = self._get_document_details(file_path, project_id)
        if doc_details.get('document_type') == 'SkipIndexing':
            logger.info(f"Skipping indexing for file marked as SkipIndexing: {file_path}")
            self.delete_doc(file_path)  # Remove any existing nodes for this path
            return
            
        logger.info(f"Determined project_id '{project_id}' for file {file_path}")

        try:
            # --- Delete existing nodes first ---
            self.delete_doc(file_path)
            # --- End Deletion ---

            logger.debug(f"Loading document content from: {file_path}")
            def file_metadata_func(file_name: str) -> Dict[str, Any]:
                 current_path = Path(file_name)
                 current_project_id = self._extract_project_id(current_path)

                 if preloaded_metadata and str(current_path) == str(file_path):
                     logger.debug(f"Using preloaded metadata for {file_name}: {preloaded_metadata}")
                     meta = {
                         "file_path": file_name,
                         "project_id": current_project_id or "UNKNOWN",
                     }
                     meta.update(preloaded_metadata)
                     return meta

                 current_details = self._get_document_details(current_path, current_project_id) if current_project_id else {}
                 meta = {
                     "file_path": file_name,
                     "project_id": current_project_id or "UNKNOWN",
                     "document_type": current_details.get('document_type', 'Unknown'),
                     "document_title": current_details.get('document_title', current_path.name)
                 }
                 # Add specific metadata based on type
                 if meta["document_type"] == "Character":
                     meta["character_name"] = meta["document_title"]
                 if meta["document_type"] in ["Scene", "ChapterPlan", "ChapterSynopsis"]:
                     meta["chapter_id"] = current_details.get('chapter_id', 'UNKNOWN')
                     meta["chapter_title"] = current_details.get('chapter_title', 'UNKNOWN')
                 # --- ADDED: Note specific metadata (optional, could add note_id if needed) ---
                 # if meta["document_type"] == "Note":
                 #     meta["note_title"] = meta["document_title"] # Already have title
                 # --- END ADDED ---

                 logger.debug(f"Generated metadata for {file_name}: {meta}")
                 return meta

            reader = SimpleDirectoryReader(input_files=[file_path], file_metadata=file_metadata_func)
            documents = reader.load_data()
            if not documents: logger.warning(f"No documents loaded from file: {file_path}. Skipping insertion."); return

            logger.debug(f"Inserting new nodes for file: {file_path} (metadata added via file_metadata_func)")

            # --- MODIFIED: Handle preloaded metadata for Notes as well ---
            if preloaded_metadata and preloaded_metadata.get('document_type') in ['Scene', 'Note', 'Character']: # Add Note/Character
                doc_type = preloaded_metadata.get('document_type')
                logger.info(f"Using enhanced insertion for {doc_type} document with title: {preloaded_metadata.get('document_title')}")
                for doc in documents:
                    logger.debug(f"Document metadata before insertion: {doc.metadata}")
                    # Ensure the preloaded title overrides any potentially stale one from file_metadata_func
                    if 'document_title' in preloaded_metadata:
                        doc.metadata['document_title'] = preloaded_metadata['document_title']
                    # Add other relevant preloaded fields if necessary
                    if doc_type == 'Scene' and 'chapter_title' in preloaded_metadata:
                         doc.metadata['chapter_title'] = preloaded_metadata['chapter_title']
                    logger.debug(f"Final document metadata for insertion: {doc.metadata}")
            # --- END MODIFIED ---

            self.index.insert_nodes(documents)
            logger.info(f"Successfully indexed/updated file: {file_path} with project_id '{project_id}'")

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}", exc_info=True)


    def delete_doc(self, file_path: Path):
        """
        Deletes nodes associated with a specific file path from the index.
        Attempts both direct ChromaDB deletion and LlamaIndex ref_doc deletion.
        """
        if not isinstance(file_path, Path): logger.error(f"IndexManager.delete_doc called with invalid type for file_path: {type(file_path)}"); return
        logger.info(f"IndexManager: Received request to delete document associated with file path: {file_path}")

        # --- MODIFIED: Attempt both deletion methods ---
        # Attempt 1: Direct ChromaDB deletion using file_path metadata
        if self.chroma_collection:
            try:
                logger.debug(f"Attempting direct ChromaDB deletion for file_path: {str(file_path)}")
                delete_result = self.chroma_collection.delete(where={"file_path": str(file_path)})
                logger.info(f"Direct ChromaDB deletion attempt for file_path='{str(file_path)}' completed.")
            except Exception as chroma_delete_err:
                logger.warning(f"Direct ChromaDB deletion failed for {file_path}: {chroma_delete_err}")
        else:
            logger.warning("Chroma collection not available for direct deletion.")

        # Attempt 2: LlamaIndex deletion using ref_doc_id
        if self.index:
             doc_id = str(file_path) # LlamaIndex uses file path string as ref_doc_id
             try:
                 logger.debug(f"Attempting LlamaIndex deletion for ref_doc_id: {doc_id}")
                 self.index.delete_ref_doc(ref_doc_id=doc_id, delete_from_docstore=True)
                 logger.info(f"LlamaIndex deletion attempt for ref_doc_id: {doc_id} completed (might not find nodes if direct delete worked).")
             except Exception as e:
                 # This might be expected if direct deletion worked, or could be another issue
                 logger.warning(f"LlamaIndex delete_ref_doc failed for {doc_id}: {e}")
        else:
             logger.error("Index is not initialized. Cannot delete doc via LlamaIndex.")
        # --- END MODIFIED ---


    def delete_project_docs(self, project_id: str):
        """
        Deletes all nodes associated with a specific project_id from the index
        by directly interacting with the ChromaDB collection.
        """
        if not self.chroma_collection:
            logger.error("Chroma collection not initialized. Cannot delete project docs.")
            return

        logger.info(f"Attempting to delete all indexed documents for project_id: {project_id} directly from ChromaDB.")
        try:
            self.chroma_collection.delete(where={"project_id": project_id})
            logger.info(f"Successfully deleted documents for project {project_id} from ChromaDB collection '{self.chroma_collection.name}'.")
        except Exception as e:
            logger.error(f"Error during direct ChromaDB deletion for project {project_id}: {e}", exc_info=True)


# --- Instantiate Singleton ---
try:
    index_manager = IndexManager()
except Exception as e:
    logger.critical(f"Failed to create IndexManager instance on startup: {e}", exc_info=True)
    index_manager = None