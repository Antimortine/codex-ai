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
from typing import Optional, Dict, Any

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings as LlamaSettings,
    load_index_from_storage,
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.google_genai import GoogleGenAI
import chromadb
from app.core.config import settings, BASE_PROJECT_DIR
# --- MODIFIED: Import file_service instance directly ---
from app.services.file_service import file_service
# --- END MODIFIED ---


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
    Injects relevant metadata (project_id, file_path, document_type, document_title) into nodes.
    """

    def __init__(self):
        """
        Initializes the IndexManager. Sets up LlamaIndex components (LLM, Embeddings, Vector Store)
        and loads or creates the VectorStoreIndex.
        """
        logger.info("Initializing IndexManager...")
        self.index: Optional[VectorStoreIndex] = None
        self.llm: Optional[LLM] = None
        self.embed_model: Optional[HuggingFaceEmbedding] = None
        self.storage_context: Optional[StorageContext] = None
        self.vector_store: Optional[ChromaVectorStore] = None

        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY not found in settings. Cannot initialize AI components.")
            raise ValueError("GOOGLE_API_KEY is not configured.")

        try:
            # 1. Configure LlamaIndex Settings globally
            logger.debug(f"Configuring LLM: {LLM_MODEL_NAME}")
            try:
                 LlamaSettings.llm = GoogleGenAI(model=LLM_MODEL_NAME, api_key=settings.GOOGLE_API_KEY)
            except TypeError:
                 logger.warning("Initialization with 'model' failed for GoogleGenAI, trying 'model_name'.")
                 LlamaSettings.llm = GoogleGenAI(model_name=LLM_MODEL_NAME, api_key=settings.GOOGLE_API_KEY)
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
            chroma_collection = db.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
            logger.debug("Initializing ChromaVectorStore...")
            self.vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

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
        Returns a dictionary containing 'document_type' and 'document_title'.
        """
        # Default title is now full filename for Unknown, stem for Note
        default_title = file_path.name
        details = {'document_type': 'Unknown', 'document_title': default_title}
        fs = file_service

        try:
            relative_path_parts = file_path.relative_to(BASE_PROJECT_DIR / project_id).parts
            if file_path.name == "plan.md" and len(relative_path_parts) == 1: details = {'document_type': 'Plan', 'document_title': 'Project Plan'}
            elif file_path.name == "synopsis.md" and len(relative_path_parts) == 1: details = {'document_type': 'Synopsis', 'document_title': 'Project Synopsis'}
            elif file_path.name == "world.md" and len(relative_path_parts) == 1: details = {'document_type': 'World', 'document_title': 'World Info'}
            elif len(relative_path_parts) > 1 and relative_path_parts[0] == 'characters' and file_path.suffix == '.md':
                character_id = file_path.stem; project_meta = fs.read_project_metadata(project_id)
                char_name = project_meta.get('characters', {}).get(character_id, {}).get('name')
                details = {'document_type': 'Character', 'document_title': char_name or character_id}
            elif len(relative_path_parts) > 2 and relative_path_parts[0] == 'chapters' and relative_path_parts[2].endswith('.md'):
                chapter_id = relative_path_parts[1]; scene_id = file_path.stem
                # --- REVISED: Scene title logic ---
                scene_title = scene_id # Default to ID
                try:
                    chapter_meta = fs.read_chapter_metadata(project_id, chapter_id)
                    scene_meta = chapter_meta.get('scenes', {}).get(scene_id, {})
                    title_from_meta = scene_meta.get('title') # Get title, could be None or empty string
                    if title_from_meta: # Check if title is truthy (not None, not empty string)
                        scene_title = title_from_meta
                        logger.debug(f"Found scene title '{scene_title}' in metadata for scene {scene_id}.")
                    else:
                        logger.warning(f"Scene title not found or empty in metadata for scene {scene_id} in chapter {chapter_id}. Using ID '{scene_id}' as title.")
                except Exception as e:
                    logger.warning(f"Could not read chapter metadata for {chapter_id} to get scene title for {scene_id}: {e}. Using ID '{scene_id}' as title.")
                details = {'document_type': 'Scene', 'document_title': scene_title}
                # --- END REVISED ---
            elif len(relative_path_parts) > 1 and relative_path_parts[0] == 'notes' and file_path.suffix == '.md':
                details = {'document_type': 'Note', 'document_title': file_path.stem} # Use stem for Note title
        except Exception as e: logger.error(f"Error determining document details for {file_path}: {e}", exc_info=True)
        # logger.debug(f"Determined details for {file_path}: {details}") # Moved logging to file_metadata_func
        return details

    def index_file(self, file_path: Path):
        """
        Loads, parses, embeds, adds metadata (project_id, file_path, document_type, document_title),
        and inserts/updates a single file's content into the index.
        If the document already exists (based on file_path), it's deleted first.
        Empty files are skipped.
        """
        if not self.index: logger.error("Index is not initialized. Cannot index file."); return
        if not isinstance(file_path, Path): logger.error(f"IndexManager.index_file called with invalid type for file_path: {type(file_path)}"); return
        if not file_path.is_file(): logger.warning(f"IndexManager.index_file called with non-existent file: {file_path}"); return

        try:
            if file_path.stat().st_size == 0:
                logger.info(f"Skipping indexing for empty file: {file_path}")
                doc_id_for_empty = str(file_path)
                try: logger.debug(f"Attempting to delete nodes for now-empty file: {doc_id_for_empty}"); self.index.delete_ref_doc(ref_doc_id=doc_id_for_empty, delete_from_docstore=True); logger.info(f"Successfully deleted existing nodes for now-empty file: {doc_id_for_empty} (if they existed).")
                except Exception as delete_error: logger.warning(f"Could not delete nodes for now-empty file {doc_id_for_empty} (may not have existed): {delete_error}")
                return
        except OSError as e: logger.error(f"Could not check file size for {file_path}: {e}"); return

        logger.info(f"IndexManager: Received request to index/update file: {file_path}")
        doc_id = str(file_path)
        project_id = self._extract_project_id(file_path)
        if not project_id: logger.error(f"Could not determine project_id for file {file_path}. Skipping indexing."); return
        logger.info(f"Determined project_id '{project_id}' for file {file_path}")

        try:
            logger.debug(f"Attempting to delete existing nodes for doc_id: {doc_id}")
            try: self.index.delete_ref_doc(ref_doc_id=doc_id, delete_from_docstore=True); logger.info(f"Successfully deleted existing nodes for doc_id: {doc_id} (if they existed).")
            except Exception as delete_error: logger.warning(f"Could not delete nodes for doc_id {doc_id} (may not have existed): {delete_error}")

            logger.debug(f"Loading document content from: {file_path}")
            # --- file_metadata_func remains the same, relying on corrected _get_document_details ---
            def file_metadata_func(file_name: str) -> Dict[str, Any]:
                 current_path = Path(file_name)
                 current_project_id = self._extract_project_id(current_path)
                 # Call the instance method to get details
                 current_details = self._get_document_details(current_path, current_project_id) if current_project_id else {}
                 meta = {
                     "file_path": file_name,
                     "project_id": current_project_id or "UNKNOWN",
                     "document_type": current_details.get('document_type', 'Unknown'),
                     "document_title": current_details.get('document_title', current_path.name) # Use full name as fallback
                 }
                 # Add character_name specifically if it's a character doc
                 if meta["document_type"] == "Character":
                     meta["character_name"] = meta["document_title"]
                 # --- ADDED: Log the generated metadata ---
                 logger.debug(f"Generated metadata for {file_name}: {meta}")
                 # --- END ADDED ---
                 return meta
            # --- END ---

            reader = SimpleDirectoryReader(input_files=[file_path], file_metadata=file_metadata_func)
            documents = reader.load_data()
            if not documents: logger.warning(f"No documents loaded from file: {file_path}. Skipping insertion."); return

            logger.debug(f"Inserting new nodes for doc_id: {doc_id} (metadata added via file_metadata_func)")
            self.index.insert_nodes(documents)
            logger.info(f"Successfully indexed/updated file: {file_path} with project_id '{project_id}'")

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}", exc_info=True)


    def delete_doc(self, file_path: Path):
        """
        Deletes nodes associated with a specific file path from the index.
        Uses the file path string as the ref_doc_id.
        """
        if not self.index: logger.error("Index is not initialized. Cannot delete doc."); return
        if not isinstance(file_path, Path): logger.error(f"IndexManager.delete_doc called with invalid type for file_path: {type(file_path)}"); return
        logger.info(f"IndexManager: Received request to delete document associated with file path: {file_path}")
        doc_id = str(file_path)
        try:
            logger.debug(f"Attempting to delete nodes for ref_doc_id: {doc_id}")
            self.index.delete_ref_doc(ref_doc_id=doc_id, delete_from_docstore=True)
            logger.info(f"Successfully deleted nodes for file {file_path} from index (if they existed).")
        except Exception as e: logger.error(f"Error deleting document from index for file {file_path} (ref_doc_id: {doc_id}): {e}", exc_info=True)


# --- ADDED: Instantiate Singleton ---
try:
    index_manager = IndexManager()
except Exception as e:
    logger.critical(f"Failed to create IndexManager instance on startup: {e}", exc_info=True)
    # Make it None so dependent modules can check
    index_manager = None
    # Optionally re-raise or handle differently depending on desired app behavior on init failure
    # raise RuntimeError(f"Failed to initialize IndexManager: {e}") from e
# --- END ADDED ---

# --- REMOVED Placeholder and Initializer Function ---
# index_manager: Optional[IndexManager] = None
# def initialize_index_manager(): ...
# --- END REMOVED ---