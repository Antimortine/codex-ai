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

from llama_index.core import (
    VectorStoreIndex,
    SimpleDirectoryReader,
    StorageContext,
    Settings as LlamaSettings, # Rename to avoid conflict with Pydantic settings
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.chroma import ChromaVectorStore
from llama_index.embeddings.google import GeminiEmbedding
from llama_index.llms.gemini import Gemini
import chromadb
from app.core.config import settings # To get API keys etc.

logger = logging.getLogger(__name__)

# --- Configuration ---
# Ensure this path is in your .gitignore
CHROMA_PERSIST_DIR = "./chroma_db"
# Use a specific collection name within ChromaDB
CHROMA_COLLECTION_NAME = "codex_ai_documents"
# LLM and Embedding Model Names
LLM_MODEL_NAME = "models/gemini-1.5-pro-latest"
EMBEDDING_MODEL_NAME = "models/text-embedding-004" # Correct model for GeminiEmbedding

class IndexManager:
    """
    Manages the RAG index for project content using LlamaIndex, ChromaDB, and Google AI.
    """

    def __init__(self):
        """
        Initializes the IndexManager. Sets up LlamaIndex components (LLM, Embeddings, Vector Store)
        and loads or creates the VectorStoreIndex.
        """
        logger.info("Initializing IndexManager (Stage 3 - Real Implementation)...")

        if not settings.GOOGLE_API_KEY:
            logger.error("GOOGLE_API_KEY not found in settings. Cannot initialize AI components.")
            raise ValueError("GOOGLE_API_KEY is not configured.")

        try:
            # 1. Configure LlamaIndex Settings globally
            logger.debug(f"Configuring LLM: {LLM_MODEL_NAME}")
            LlamaSettings.llm = Gemini(model_name=LLM_MODEL_NAME, api_key=settings.GOOGLE_API_KEY)

            logger.debug(f"Configuring Embedding Model: {EMBEDDING_MODEL_NAME}")
            # Use GeminiEmbedding for text-embedding-004
            LlamaSettings.embed_model = GeminiEmbedding(model_name=EMBEDDING_MODEL_NAME, api_key=settings.GOOGLE_API_KEY) # CORRECTED CLASS NAME

            # Optional: Configure Node Parser (can use defaults)
            # LlamaSettings.node_parser = SentenceSplitter(chunk_size=512, chunk_overlap=20)

            # 2. Initialize ChromaDB Client and Vector Store
            logger.debug(f"Initializing ChromaDB client with persistence directory: {CHROMA_PERSIST_DIR}")
            # Ensure the directory exists
            os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
            db = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)

            logger.debug(f"Getting or creating ChromaDB collection: {CHROMA_COLLECTION_NAME}")
            chroma_collection = db.get_or_create_collection(CHROMA_COLLECTION_NAME)

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
            except Exception as e: # Broad exception capture as specific error type might vary
                logger.warning(f"Failed to load index from storage (might be first run): {e}. Creating new index.")
                # If loading fails (e.g., directory is empty or index is corrupted/incompatible),
                # create an empty index attached to the storage context.
                # We don't need to provide documents here; they will be added via index_file.
                self.index = VectorStoreIndex.from_documents(
                    [], storage_context=storage_context
                )
                logger.info("Created new empty index.")

            logger.info("IndexManager initialized successfully.")

        except Exception as e:
            logger.error(f"Fatal error during IndexManager initialization: {e}", exc_info=True)
            # Depending on the application's needs, you might want to exit or handle this differently.
            raise RuntimeError(f"Failed to initialize IndexManager: {e}") from e

    def index_file(self, file_path: Path):
        """
        Loads, parses, embeds, and inserts/updates a single file's content into the index.
        If the document already exists (based on file_path), it's deleted first.
        """
        if not isinstance(file_path, Path):
             logger.error(f"IndexManager.index_file called with invalid type for file_path: {type(file_path)}")
             return
        if not file_path.is_file():
            logger.warning(f"IndexManager.index_file called with non-existent file: {file_path}")
            return

        logger.info(f"IndexManager: Received request to index/update file: {file_path}")
        doc_id = str(file_path) # Use the file path string as the unique document ID

        try:
            # 1. Attempt to delete existing document nodes first to ensure update
            logger.debug(f"Attempting to delete existing nodes for doc_id: {doc_id}")
            try:
                # delete_from_docstore=True ensures associated text is removed if stored separately
                self.index.delete_ref_doc(ref_doc_id=doc_id, delete_from_docstore=True)
                logger.info(f"Successfully deleted existing nodes for doc_id: {doc_id} (if they existed).")
            except Exception as delete_error:
                 # This might happen if the doc didn't exist, which is fine for an update/insert flow.
                 # Log as warning or debug. Specific error types could be caught if needed.
                 logger.warning(f"Could not delete nodes for doc_id {doc_id} (may not have existed): {delete_error}")


            # 2. Load the new document content
            logger.debug(f"Loading document content from: {file_path}")
            # SimpleDirectoryReader automatically adds 'file_path' metadata
            reader = SimpleDirectoryReader(input_files=[file_path])
            documents = reader.load_data()

            if not documents:
                logger.warning(f"No documents loaded from file: {file_path}. Skipping insertion.")
                return

            # Ensure the ref_doc_id is set correctly if needed (usually automatic)
            # for doc in documents:
            #     doc.id_ = doc_id # Explicitly set if SimpleDirectoryReader doesn't

            # 3. Insert the new document nodes
            logger.debug(f"Inserting new nodes for doc_id: {doc_id}")
            # insert_nodes handles parsing, embedding, and storage via the index's components
            # LlamaIndex v0.10+ uses index.insert() for Document objects
            # If documents is a list of Document objects:
            for doc in documents:
                self.index.insert(doc) # Use insert for individual documents
            # If using older LlamaIndex or if insert_nodes is preferred for Node objects:
            # nodes = LlamaSettings.node_parser.get_nodes_from_documents(documents)
            # self.index.insert_nodes(nodes)

            # Note: ChromaDB persistence is handled automatically by the VectorStore setup

            logger.info(f"Successfully indexed/updated file: {file_path}")

        except Exception as e:
            logger.error(f"Error indexing file {file_path}: {e}", exc_info=True)
            # Depending on requirements, you might want to raise this error
            # raise

    def delete_doc(self, file_path: Path):
        """
        Deletes nodes associated with a specific file path from the index.
        """
        if not isinstance(file_path, Path):
             logger.error(f"IndexManager.delete_doc called with invalid type for file_path: {type(file_path)}")
             return

        logger.info(f"IndexManager: Received request to delete document associated with file path: {file_path}")
        doc_id = str(file_path) # Use the file path string as the document ID

        try:
            logger.debug(f"Attempting to delete nodes for doc_id: {doc_id}")
            # delete_from_docstore=True ensures associated text is removed if stored separately
            self.index.delete_ref_doc(ref_doc_id=doc_id, delete_from_docstore=True)
            # Note: ChromaDB persistence is handled automatically

            logger.info(f"Successfully deleted nodes for file {file_path} from index (if they existed).")
        except Exception as e:
            # Log error, but don't necessarily crash if deletion fails (e.g., doc already gone)
            logger.error(f"Error deleting document for file {file_path} (doc_id: {doc_id}): {e}", exc_info=True)
            # raise # Optionally re-raise if deletion failure is critical

    # --- Stage 3 Query/Retrieval Methods (Placeholder) ---
    # def query(self, query_text: str, project_id: str):
    #     logger.info(f"[STAGE 3 PLACEHOLDER] Received query for project {project_id}: {query_text}")
    #     # query_engine = self.index.as_query_engine()
    #     # response = query_engine.query(query_text)
    #     # return str(response)
    #     return "Query functionality not implemented yet."


# --- Singleton Instance ---
# Create a single instance of the IndexManager to be used throughout the application.
# This will trigger the __init__ process on application startup.
try:
    index_manager = IndexManager()
except Exception as e:
    logger.critical(f"Failed to create IndexManager instance on startup: {e}", exc_info=True)
    # Handle critical failure: maybe exit, or provide a dummy manager
    # For now, let it raise to prevent the app starting in a broken state
    raise