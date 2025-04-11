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

import pytest
from unittest.mock import MagicMock, AsyncMock

# Import necessary LlamaIndex types for spec
from llama_index.core.llms import LLM
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.indices.vector_store import VectorStoreIndex
# --- ADDED: Import BaseEmbedding ---
from llama_index.core.embeddings import BaseEmbedding
# --- END ADDED ---

# --- Shared Fixtures for RAG Processor Tests ---

@pytest.fixture(scope="function") # Use function scope for isolation between tests
def mock_llm():
    """Fixture for a mock LLM."""
    llm = MagicMock(spec=LLM)
    # Configure the async completion method
    llm.acomplete = AsyncMock()
    return llm

@pytest.fixture(scope="function")
def mock_retriever():
    """Fixture for a mock VectorIndexRetriever."""
    # Note: This fixture might not be directly used if tests patch the class/instantiation
    retriever = MagicMock(spec=VectorIndexRetriever)
    # Configure the async retrieval method
    retriever.aretrieve = AsyncMock()
    return retriever

@pytest.fixture(scope="function")
def mock_index(mock_retriever): # Depends on mock_retriever if needed
    """Fixture for a mock VectorStoreIndex."""
    # This mock might be simple if the main interaction point is the retriever
    index = MagicMock(spec=VectorStoreIndex)
    # Example: If processors called index.as_retriever()
    # index.as_retriever.return_value = mock_retriever

    # --- ADDED: Mock the _embed_model attribute ---
    # Create a simple mock for the embedding model
    mock_embed_model = MagicMock(spec=BaseEmbedding)
    index._embed_model = mock_embed_model
    # --- END ADDED ---

    return index