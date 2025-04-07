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

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings as LlamaSettings,
    load_index_from_storage,
)
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
# --- MODIFIED: Import 'GoogleGenAI' class ---
# from llama_index.llms.google_genai import Gemini # Incorrect
from llama_index.llms.google_genai import GoogleGenAI # Try this class name
# --- END MODIFIED ---
import chromadb
from app.core.config import settings, BASE_PROJECT_DIR
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
    """

    def __init__(self):
        """
        Initializes the IndexManager. Sets up LlamaIndex components (LLM, Embeddings, Vector Store)
        and loads or creates the VectorStoreIndex.
        """
        logger.info("Initializing IndexManager...")

        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY not found in settings. Cannot initialize AI components.")
            raise ValueError("GOOGLE_API_KEY is not configured.")

        try:
            # 1. Configure LlamaIndex Settings globally
            logger.debug(f"Configuring LLM: {LLM_MODEL_NAME}")
            # --- MODIFIED: Use GoogleGenAI class ---
            # Check parameters for GoogleGenAI - it might use 'model' or 'model_name'
            try:
                 LlamaSettings.llm = GoogleGenAI(model=LLM_MODEL_NAME, api_key=settings.GOOGLE_API_KEY)
            except TypeError:
                 logger.warning("Initialization with 'model' failed for GoogleGenAI, trying 'model_name'.")
                 LlamaSettings.llm = GoogleGenAI(model_name=LLM_MODEL_NAME, api_key=settings.GOOGLE_API_KEY)
            # --- END MODIFIED ---
            self.llm = LlamaSettings.llm

            # Configure HuggingFace Embedding Model
            logger.debug(f"Configuring Embedding Model: {EMBEDDING_MODEL_NAME}")
            device = "cuda" if torch.cuda.is_available() else "cpu"
            logger.info(f"Using device '{device}' for HuggingFace embeddings.")
            LlamaSettings.embed_model = HuggingFaceEmbedding(
                model_name=EMBEDDING_MODEL_NAME,
                device=device
            )
            self.embed_model = LlamaSettings.embed_model

            # 2. Initialize ChromaDB Client and Vector Store
            logger.debug(f"Initializing ChromaDB client with persistence directory: {CHROMA_PERSIST_DIR}")
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            db = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            logger.debug(f"Getting or creating ChromaDB collection: {CHROMA_COLLECTION_NAME}")
            chroma_collection = db.get_or_create_collection(name=CHROMA_COLLECTION_NAME)
            logger.debug("Initializing ChromaVectorStore...")
            vector_store = ChromaVectorStore(chroma_collection=chroma_collection)

            # 3. Initialize Storage Context
            logger.debug("Initializing StorageContext...")
            storage_context = StorageContext.from_defaults(vector_store=vector_store)

            # 4. Load or Create the Index
            try:
                logger.info(f"Attempting to load index from storage: {CHROMA_PERSIST_DIR}")
                self.index = load_index_from_storage(storage_context)
                logger.info("Successfully loaded existing index.")
            except Exception as e:
                if isinstance(e, ValueError) and ("No existing" in str(e) and "storage" in str(e)):
                     logger.warning(f"Failed to load index from storage (Index not found or empty): {e}. Creating new index.")
                else:
                     logger.warning(f"Failed to load index from storage (might be first run or other issue): {e}. Creating new index.")
                self.index = VectorStoreIndex.from_documents(
                    [], storage_context=storage_context
                )
                logger.info("Created new empty index.")

            logger.info("IndexManager initialized successfully.")

        except Exception as e:
            logger.error(f"Fatal error during IndexManager initialization: {e}", exc_info=True)
            raise RuntimeError(f"Failed to initialize IndexManager: {e}") from e

    # ... (rest of the IndexManager class: _extract_project_id, index_file, delete_doc) ...
    def _extract_project_id(self, file_path: Path) -> str | None:
        """
        Extracts the project_id from the file path relative to BASE_PROJECT_DIR.
        Returns the project_id string or None if the path is not structured as expected.
        """
        try:
            abs_file_path = file_path.resolve()
            abs_base_dir = BASE_PROJECT_DIR.resolve()

            if abs_base_dir not in abs_file_path.parents:
                 logger.warning(f"File path {abs_file_path} is not within BASE_PROJECT_DIR {abs_base_dir}. Cannot extract project_id.")
                 return None

            relative_path = abs_file_path.relative_to(abs_base_dir)
            if not relative_path.parts:
                 logger.warning(f"File path {abs_file_path} is the base directory itself. Cannot extract project_id.")
                 return None

            project_id = relative_path.parts[0]
            return project_id

        except ValueError:
             logger.error(f"Could not make path relative: {file_path} to {BASE_PROJECT_DIR}")
             return None
        except Exception as e:
            logger.error(f"Error extracting project_id from path {file_path}: {e}", exc_info=True)
            return None


    def index_file(self, file_path: Path):
        """
        Loads, parses, embeds, adds metadata (project_id, file_path, character_name),
        and inserts/updates a single file's content into the index.
        If the document already exists (based on file_path), it's deleted first.
        Empty files are skipped.
        """
        if not isinstance(file_path, Path):
             logger.error(f"IndexManager.index_file called with invalid type for file_path: {type(file_path)}")
             return
        if not file_path.is_file():
            logger.warning(f"IndexManager.index_file called with non-existent file: {file_path}")
            return

        try:
            if file_path.stat().st_size == 0:
                logger.info(f"Skipping indexing for empty file: {file_path}")
                doc_id_for_empty = str(file_path)
                try:
                    logger.debug(f"Attempting to delete nodes for now-empty file: {doc_id_for_empty}")
                    self.index.delete_ref_doc(ref_doc_id=doc_id_for_empty, delete_from_docstore=True)
                    logger.info(f"Successfully deleted existing nodes for now-empty file: {doc_id_for_empty} (if they existed).")
                except Exception as delete_error:
                    logger.warning(f"Could not delete nodes for now-empty file {doc_id_for_empty} (may not have existed): {delete_error}")
                return
        except OSError as e:
             logger.error(f"Could not check file size for {file_path}: {e}")
             return

        logger.info(f"IndexManager: Received request to index/update file: {file_path}")
        doc_id = str(file_path)

        project_id = self._extract_project_id(file_path)
        if not project_id:
             logger.error(f"Could not determine project_id for file {file_path}. Skipping indexing.")
             return
        logger.info(f"Determined project_id '{project_id}' for file {file_path}")

        character_name_to_inject = None
        try:
            if file_path.parent == file_service._get_characters_dir(project_id):
                 character_id = file_path.stem
                 logger.debug(f"Detected character file for ID: {character_id}. Attempting to read metadata.")
                 project_metadata = file_service.read_project_metadata(project_id)
                 character_data = project_metadata.get('characters', {}).get(character_id)
                 if character_data and 'name' in character_data:
                     character_name_to_inject = character_data['name']
                     logger.info(f"Found character name '{character_name_to_inject}' for ID {character_id}. Will inject into metadata.")
                 else:
                     logger.warning(f"Character name not found in metadata for ID {character_id} in project {project_id}.")
        except Exception as meta_error:
            logger.error(f"Error reading project metadata or finding character name for {file_path}: {meta_error}", exc_info=True)

        try:
            logger.debug(f"Attempting to delete existing nodes for doc_id: {doc_id}")
            try:
                self.index.delete_ref_doc(ref_doc_id=doc_id, delete_from_docstore=True)
                logger.info(f"Successfully deleted existing nodes for doc_id: {doc_id} (if they existed).")
            except Exception as delete_error:
                 logger.warning(f"Could not delete nodes for doc_id {doc_id} (may not have existed): {delete_error}")

            logger.debug(f"Loading document content from: {file_path}")
            def file_metadata_func(file_name: str):
                 p_id = self._extract_project_id(Path(file_name))
                 meta = {"file_path": file_name}
                 if p_id:
                      meta["project_id"] = p_id
                 if character_name_to_inject and Path(file_name).parent == file_service._get_characters_dir(p_id):
                      meta['character_name'] = character_name_to_inject
                 return meta

            reader = SimpleDirectoryReader(
                input_files=[file_path],
                file_metadata=file_metadata_func
            )
            documents = reader.load_data()

            if not documents:
                logger.warning(f"No documents loaded from file: {file_path}. Skipping insertion.")
                return

            for doc in documents:
                doc.id_ = doc_id
                doc.metadata = doc.metadata or {}
                if 'file_path' not in doc.metadata: doc.metadata['file_path'] = str(file_path)
                if 'project_id' not in doc.metadata: doc.metadata['project_id'] = project_id
                if character_name_to_inject and 'character_name' not in doc.metadata and file_path.parent == file_service._get_characters_dir(project_id):
                     doc.metadata['character_name'] = character_name_to_inject
                logger.debug(f"Final metadata for doc_id {doc.id_}: {doc.metadata}")

            logger.debug(f"Inserting new nodes for doc_id: {doc_id} with project_id '{project_id}'")
            self.index.insert_nodes(documents)

            logger.info(f"Successfully indexed/updated file: {file_path} with project_id '{project_id}'")

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}", exc_info=True)


    def delete_doc(self, file_path: Path):
        """
        Deletes nodes associated with a specific file path from the index.
        Uses the file path string as the ref_doc_id.
        """
        if not isinstance(file_path, Path):
             logger.error(f"IndexManager.delete_doc called with invalid type for file_path: {type(file_path)}")
             return

        logger.info(f"IndexManager: Received request to delete document associated with file path: {file_path}")
        doc_id = str(file_path)

        try:
            logger.debug(f"Attempting to delete nodes for ref_doc_id: {doc_id}")
            self.index.delete_ref_doc(ref_doc_id=doc_id, delete_from_docstore=True)
            logger.info(f"Successfully deleted nodes for file {file_path} from index (if they existed).")
        except Exception as e:
            logger.error(f"Error deleting document from index for file {file_path} (ref_doc_id: {doc_id}): {e}", exc_info=True)


# --- Singleton Instance ---
try:
    index_manager = IndexManager()
except Exception as e:
    logger.critical(f"Failed to create IndexManager instance on startup: {e}", exc_info=True)
    raise RuntimeError(f"Failed to initialize IndexManager: {e}") from e