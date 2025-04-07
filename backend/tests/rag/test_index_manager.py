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
from unittest.mock import MagicMock, patch, ANY, call
from pathlib import Path
import sys
import os

# Ensure the backend directory is in the path for imports
backend_dir = Path(__file__).parent.parent.parent / 'backend'
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import the class we are testing *after* path adjustment
import app.rag.index_manager
from app.rag.index_manager import IndexManager, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
from app.core.config import BASE_PROJECT_DIR, settings
from app.services.file_service import file_service # Needed for metadata reading

# --- Mocks Setup ---
# Create persistent mock objects that will be configured by patches
mock_chroma_collection = MagicMock(name="MockChromaCollectionInstance")
mock_chroma_client = MagicMock(name="MockChromaClient")
mock_chroma_client.get_or_create_collection.return_value = mock_chroma_collection

mock_vector_store = MagicMock(name="MockVectorStore")
mock_storage_context = MagicMock(name="MockStorageContext")
mock_vector_index = MagicMock(name="MockVectorStoreIndex")
mock_simple_directory_reader_instance = MagicMock(name="MockSimpleDirectoryReaderInstance")
mock_huggingface_embedding = MagicMock(name="MockHuggingFaceEmbedding")
mock_google_genai = MagicMock(name="MockGoogleGenAI")
mock_llama_settings_llm = MagicMock(name="MockLlamaSettingsLLM")
mock_llama_settings_embed = MagicMock(name="MockLlamaSettingsEmbed")
mock_internal_file_service = MagicMock(spec=file_service, name="MockInternalFileService")

# --- Fixtures ---

@pytest.fixture(scope="function", autouse=True)
def reset_mocks():
    """Reset mocks before each test function."""
    mock_chroma_client.reset_mock()
    mock_chroma_client.get_or_create_collection.reset_mock(return_value=mock_chroma_collection)
    mock_chroma_collection.reset_mock()
    mock_vector_store.reset_mock()
    mock_storage_context.reset_mock()
    mock_vector_index.reset_mock()
    mock_vector_index.delete_ref_doc.reset_mock()
    mock_vector_index.insert_nodes.reset_mock()
    mock_simple_directory_reader_instance.reset_mock()
    mock_simple_directory_reader_instance.load_data.reset_mock()
    mock_huggingface_embedding.reset_mock()
    mock_google_genai.reset_mock()
    mock_llama_settings_llm.reset_mock()
    mock_llama_settings_embed.reset_mock()
    mock_internal_file_service.reset_mock()
    mock_internal_file_service.read_project_metadata.reset_mock()
    mock_internal_file_service._get_characters_dir.reset_mock()


# Use function scope for the fixture applying patches to avoid test interference
@pytest.fixture(scope="function")
def patched_index_manager_instance(request): # request is a pytest fixture
    """
    Provides a freshly initialized IndexManager instance for each test,
    with dependencies patched correctly. Allows local patches via request marker.
    """
    # Check if the test function using this fixture has marked a local patch for load_index
    load_index_patch_config = request.node.get_closest_marker("patch_load_index")
    load_index_mock = MagicMock(return_value=mock_vector_index) # Default behavior
    if load_index_patch_config:
        load_index_mock.side_effect = load_index_patch_config.args[0] # Use side_effect from marker

    # Patch targets *within* the app.rag.index_manager module namespace
    with patch('app.rag.index_manager.chromadb.PersistentClient', return_value=mock_chroma_client) as mock_p_client_cls, \
         patch('app.rag.index_manager.ChromaVectorStore', return_value=mock_vector_store) as mock_c_vs_cls, \
         patch('app.rag.index_manager.StorageContext.from_defaults', return_value=mock_storage_context) as mock_sc_from_defaults, \
         patch('app.rag.index_manager.VectorStoreIndex.from_documents', return_value=mock_vector_index) as mock_vs_from_docs, \
         patch('app.rag.index_manager.load_index_from_storage', load_index_mock) as mock_load_index, \
         patch('app.rag.index_manager.SimpleDirectoryReader', return_value=mock_simple_directory_reader_instance) as mock_sdr_cls, \
         patch('app.rag.index_manager.HuggingFaceEmbedding', return_value=mock_huggingface_embedding) as mock_hf_cls, \
         patch('app.rag.index_manager.GoogleGenAI', return_value=mock_google_genai) as mock_gg_cls, \
         patch('app.rag.index_manager.torch.cuda.is_available', return_value=False) as mock_cuda, \
         patch('app.rag.index_manager.LlamaSettings', llm=mock_llama_settings_llm, embed_model=mock_llama_settings_embed) as mock_llama_settings, \
         patch('app.rag.index_manager.file_service', mock_internal_file_service):

        # Store references to the patch objects if needed for assertions on the class itself
        mocks_dict = {
            "p_client_cls": mock_p_client_cls,
            "c_vs_cls": mock_c_vs_cls,
            "sc_from_defaults": mock_sc_from_defaults,
            "vs_from_docs": mock_vs_from_docs,
            "load_index": mock_load_index, # This is the mock configured by the fixture/marker
            "sdr_cls": mock_sdr_cls,
            "hf_cls": mock_hf_cls,
            "gg_cls": mock_gg_cls,
            "cuda": mock_cuda,
            "llama_settings": mock_llama_settings
        }

        # Ensure GOOGLE_API_KEY is set for initialization to pass
        original_key = settings.GOOGLE_API_KEY
        settings.GOOGLE_API_KEY = "fake-test-key"
        manager = None
        try:
            # Instantiate the manager *within* the patch context
            manager = IndexManager()
            # Assign the mock index to the instance for easier access in tests
            manager.index = mock_vector_index
            # Yield the manager instance along with the patch objects if needed
            yield manager, mocks_dict # Yield manager and mocks
        finally:
            settings.GOOGLE_API_KEY = original_key # Restore original key

# --- Test IndexManager ---

def test_index_manager_initialization_load_existing(patched_index_manager_instance):
    """Test initialization when index is loaded from storage."""
    manager, mocks = patched_index_manager_instance # Unpack fixture result

    # Assertions check the globally defined mocks that were configured by the patches
    mocks["p_client_cls"].assert_called_once_with(path=CHROMA_PERSIST_DIR)
    mock_chroma_client.get_or_create_collection.assert_called_once_with(name=CHROMA_COLLECTION_NAME)

    # *** CORRECTED ASSERTION ***
    # Assert that ChromaVectorStore was called with the object *returned* by get_or_create_collection
    mocks["c_vs_cls"].assert_called_once_with(chroma_collection=mock_chroma_client.get_or_create_collection.return_value)

    mocks["sc_from_defaults"].assert_called_once_with(vector_store=mock_vector_store)
    mocks["load_index"].assert_called_once_with(mock_storage_context) # Check the mock from the fixture
    mocks["vs_from_docs"].assert_not_called() # Should not create new if loaded

    assert manager.index == mock_vector_index


# Mark the test to modify the load_index patch behavior via the fixture
@pytest.mark.patch_load_index(ValueError("No existing index found"))
def test_index_manager_initialization_create_new(patched_index_manager_instance):
     """Test initialization when loading fails and a new index is created."""
     manager, mocks = patched_index_manager_instance # Fixture now handles the init with the marker

     # Assert calls made during the fixture's initialization run for *this test*
     mocks["p_client_cls"].assert_called_once_with(path=CHROMA_PERSIST_DIR)
     mock_chroma_client.get_or_create_collection.assert_called_once_with(name=CHROMA_COLLECTION_NAME)
     mocks["c_vs_cls"].assert_called_once_with(chroma_collection=mock_chroma_client.get_or_create_collection.return_value)
     mocks["sc_from_defaults"].assert_called_once_with(vector_store=mock_vector_store)
     # Assert that the load_index mock (configured by the marker) was called
     mocks["load_index"].assert_called_once_with(mock_storage_context)
     # Assert that from_documents was called because load failed
     mocks["vs_from_docs"].assert_called_once_with([], storage_context=mock_storage_context)
     assert manager.index == mock_vector_index


def test_extract_project_id_success(patched_index_manager_instance):
    """Test successful extraction of project_id."""
    manager, _ = patched_index_manager_instance
    project_id = "proj_123"
    file_path = BASE_PROJECT_DIR / project_id / "chapters" / "ch1" / "scene1.md"
    extracted_id = manager._extract_project_id(file_path)
    assert extracted_id == project_id

def test_extract_project_id_outside_base(patched_index_manager_instance):
    """Test extraction when file is outside BASE_PROJECT_DIR."""
    manager, _ = patched_index_manager_instance
    file_path = Path("/tmp/some_other_file.md")
    extracted_id = manager._extract_project_id(file_path)
    assert extracted_id is None

def test_extract_project_id_base_dir(patched_index_manager_instance):
    """Test extraction when file path is the base directory itself."""
    manager, _ = patched_index_manager_instance
    extracted_id = manager._extract_project_id(BASE_PROJECT_DIR)
    assert extracted_id is None

# --- index_file Tests ---

@patch('pathlib.Path.is_file')
@patch('pathlib.Path.stat')
def test_index_file_success_normal_file(
    mock_stat: MagicMock,
    mock_is_file: MagicMock,
    patched_index_manager_instance
):
    """Test indexing a regular markdown file successfully."""
    manager, mocks = patched_index_manager_instance
    # Arrange
    project_id = "proj_index1"
    file_path = BASE_PROJECT_DIR / project_id / "plan.md"
    doc_id = str(file_path)
    mock_is_file.return_value = True
    mock_stat.return_value.st_size = 100 # Non-empty file
    mock_document = MagicMock(name="MockDocumentPlan")
    mock_document.id_ = doc_id
    mock_document.metadata = {}
    mock_simple_directory_reader_instance.load_data.return_value = [mock_document]

    # Act
    manager.index_file(file_path)

    # Assert
    mock_is_file.assert_called_once()
    mock_stat.assert_called_once()
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)
    mocks["sdr_cls"].assert_called_once_with(
        input_files=[file_path],
        file_metadata=ANY
    )
    mock_simple_directory_reader_instance.load_data.assert_called_once()
    assert mock_document.metadata['file_path'] == doc_id
    assert mock_document.metadata['project_id'] == project_id
    manager.index.insert_nodes.assert_called_once_with([mock_document])

@patch('pathlib.Path.is_file')
@patch('pathlib.Path.stat')
def test_index_file_success_character_file(
    mock_stat: MagicMock,
    mock_is_file: MagicMock,
    patched_index_manager_instance
):
    """Test indexing a character file with name injection."""
    manager, mocks = patched_index_manager_instance
    # Arrange
    project_id = "proj_char_index"
    character_id = "char_abc"
    character_name = "Gandalf"
    file_path = BASE_PROJECT_DIR / project_id / "characters" / f"{character_id}.md"
    doc_id = str(file_path)
    mock_is_file.return_value = True
    mock_stat.return_value.st_size = 50
    mock_document = MagicMock(name="MockDocumentChar")
    mock_document.id_ = doc_id
    mock_document.metadata = {}
    mock_simple_directory_reader_instance.load_data.return_value = [mock_document]
    # Mock file_service response for character name
    mock_fs = mock_internal_file_service
    mock_fs.read_project_metadata.return_value = {
        "characters": {character_id: {"name": character_name}}
    }
    mock_fs._get_characters_dir.return_value = file_path.parent

    # Act
    manager.index_file(file_path)

    # Assert
    mock_is_file.assert_called_once()
    mock_stat.assert_called_once()
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)
    mocks["sdr_cls"].assert_called_once()
    mock_simple_directory_reader_instance.load_data.assert_called_once()
    assert mock_document.metadata['file_path'] == doc_id
    assert mock_document.metadata['project_id'] == project_id
    assert mock_document.metadata['character_name'] == character_name
    manager.index.insert_nodes.assert_called_once_with([mock_document])
    mock_fs.read_project_metadata.assert_called_once_with(project_id)

@patch('pathlib.Path.is_file')
@patch('pathlib.Path.stat')
def test_index_file_empty_file(
    mock_stat: MagicMock,
    mock_is_file: MagicMock,
    patched_index_manager_instance
):
    """Test indexing an empty file (should delete old nodes and skip insertion)."""
    manager, mocks = patched_index_manager_instance
    # Arrange
    project_id = "proj_empty"
    file_path = BASE_PROJECT_DIR / project_id / "empty.md"
    doc_id = str(file_path)
    mock_is_file.return_value = True
    mock_stat.return_value.st_size = 0 # Empty file

    # Act
    manager.index_file(file_path)

    # Assert
    mock_is_file.assert_called_once()
    mock_stat.assert_called_once()
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)
    mocks["sdr_cls"].assert_not_called()
    manager.index.insert_nodes.assert_not_called()

@patch('pathlib.Path.is_file')
def test_index_file_not_a_file(mock_is_file: MagicMock, patched_index_manager_instance):
    """Test indexing something that isn't a file."""
    manager, _ = patched_index_manager_instance
    project_id = "proj_dir"
    file_path = BASE_PROJECT_DIR / project_id / "chapters"
    mock_is_file.return_value = False

    manager.index_file(file_path)

    mock_is_file.assert_called_once()
    manager.index.delete_ref_doc.assert_not_called()
    manager.index.insert_nodes.assert_not_called()

@patch('pathlib.Path.is_file')
@patch('pathlib.Path.stat')
def test_index_file_outside_project(
    mock_stat: MagicMock,
    mock_is_file: MagicMock,
    patched_index_manager_instance
):
    """Test indexing a file outside the base project directory."""
    manager, _ = patched_index_manager_instance
    file_path = Path("/tmp/other.md")
    mock_is_file.return_value = True
    mock_stat.return_value.st_size = 10

    manager.index_file(file_path)

    mock_is_file.assert_called_once()
    mock_stat.assert_called_once()
    manager.index.delete_ref_doc.assert_not_called()
    manager.index.insert_nodes.assert_not_called()

# --- delete_doc Tests ---

def test_delete_doc_success(patched_index_manager_instance):
    """Test successful deletion of a document from the index."""
    manager, _ = patched_index_manager_instance
    project_id = "proj_del"
    file_path = BASE_PROJECT_DIR / project_id / "to_delete.md"
    doc_id = str(file_path)

    manager.delete_doc(file_path)

    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)

def test_delete_doc_non_path_input(patched_index_manager_instance):
    """Test delete_doc with invalid input type."""
    manager, _ = patched_index_manager_instance
    manager.delete_doc("not/a/path/object")
    manager.index.delete_ref_doc.assert_not_called()

@patch('pathlib.Path.is_file')
def test_delete_doc_index_error(mock_is_file: MagicMock, patched_index_manager_instance):
    """Test delete_doc when the index deletion raises an error."""
    manager, _ = patched_index_manager_instance
    # Arrange
    project_id = "proj_del_err"
    file_path = BASE_PROJECT_DIR / project_id / "delete_err.md"
    doc_id = str(file_path)
    mock_is_file.return_value = True
    manager.index.delete_ref_doc.side_effect = RuntimeError("Index deletion failed")

    # Act
    manager.delete_doc(file_path)

    # Assert
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)