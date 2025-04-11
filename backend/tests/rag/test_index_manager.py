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
from typing import Dict, Any # Import Dict, Any

# Ensure the backend directory is in the path for imports
backend_dir = Path(__file__).parent.parent.parent / 'backend'
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Import the class we are testing *after* path adjustment
import app.rag.index_manager
from app.rag.index_manager import IndexManager, CHROMA_PERSIST_DIR, CHROMA_COLLECTION_NAME
from app.core.config import BASE_PROJECT_DIR, settings
from app.services.file_service import FileService, file_service as actual_file_service


# --- Mocks Setup ---
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
mock_internal_file_service = MagicMock(spec=FileService, name="MockInternalFileService")


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
    mock_internal_file_service._get_content_block_path.reset_mock()
    mock_internal_file_service._get_chapter_path.reset_mock()
    mock_internal_file_service._get_scene_path.reset_mock()
    mock_internal_file_service.read_chapter_metadata.reset_mock()


@pytest.fixture(scope="function")
def patched_index_manager_instance(request):
    load_index_patch_config = request.node.get_closest_marker("patch_load_index")
    load_index_mock = MagicMock(return_value=mock_vector_index)
    if load_index_patch_config:
        load_index_mock.side_effect = load_index_patch_config.args[0]

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
         patch('app.rag.index_manager.file_service', mock_internal_file_service): # Patch the imported instance

        mocks_dict = { "p_client_cls": mock_p_client_cls, "c_vs_cls": mock_c_vs_cls, "sc_from_defaults": mock_sc_from_defaults, "vs_from_docs": mock_vs_from_docs, "load_index": mock_load_index, "sdr_cls": mock_sdr_cls, "hf_cls": mock_hf_cls, "gg_cls": mock_gg_cls, "cuda": mock_cuda, "llama_settings": mock_llama_settings }
        original_key = settings.GOOGLE_API_KEY
        settings.GOOGLE_API_KEY = "fake-test-key"
        manager = None
        try:
            manager = IndexManager()
            manager.index = mock_vector_index
            yield manager, mocks_dict
        finally:
            settings.GOOGLE_API_KEY = original_key

# --- Test IndexManager ---
def test_index_manager_initialization_load_existing(patched_index_manager_instance):
    manager, mocks = patched_index_manager_instance
    mocks["p_client_cls"].assert_called_once_with(path=CHROMA_PERSIST_DIR)
    mock_chroma_client.get_or_create_collection.assert_called_once_with(name=CHROMA_COLLECTION_NAME)
    mocks["c_vs_cls"].assert_called_once_with(chroma_collection=mock_chroma_client.get_or_create_collection.return_value)
    mocks["sc_from_defaults"].assert_called_once_with(vector_store=mock_vector_store)
    mocks["load_index"].assert_called_once_with(mock_storage_context)
    mocks["vs_from_docs"].assert_not_called()
    assert manager.index == mock_vector_index
    # --- CORRECTED: Only assert against the return value ---
    assert manager.chroma_collection is mock_chroma_client.get_or_create_collection.return_value
    # --- END CORRECTED ---

@pytest.mark.patch_load_index(ValueError("No existing index found"))
def test_index_manager_initialization_create_new(patched_index_manager_instance):
     manager, mocks = patched_index_manager_instance
     mocks["p_client_cls"].assert_called_once_with(path=CHROMA_PERSIST_DIR)
     mock_chroma_client.get_or_create_collection.assert_called_once_with(name=CHROMA_COLLECTION_NAME)
     mocks["c_vs_cls"].assert_called_once_with(chroma_collection=mock_chroma_client.get_or_create_collection.return_value)
     mocks["sc_from_defaults"].assert_called_once_with(vector_store=mock_vector_store)
     mocks["load_index"].assert_called_once_with(mock_storage_context)
     mocks["vs_from_docs"].assert_called_once_with([], storage_context=mock_storage_context)
     assert manager.index == mock_vector_index
     # --- CORRECTED: Only assert against the return value ---
     assert manager.chroma_collection is mock_chroma_client.get_or_create_collection.return_value
     # --- END CORRECTED ---


def test_extract_project_id_success(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_123"
    file_path = BASE_PROJECT_DIR / project_id / "chapters" / "ch1" / "scene1.md"
    extracted_id = manager._extract_project_id(file_path)
    assert extracted_id == project_id

def test_extract_project_id_outside_base(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    file_path = Path("/tmp/some_other_file.md")
    extracted_id = manager._extract_project_id(file_path)
    assert extracted_id is None

def test_extract_project_id_base_dir(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    extracted_id = manager._extract_project_id(BASE_PROJECT_DIR)
    assert extracted_id is None

# --- _get_document_details Tests ---
def test_get_document_details_plan(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details"
    file_path = BASE_PROJECT_DIR / project_id / "plan.md"
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Plan', 'document_title': 'Project Plan'}
    mock_internal_file_service.read_project_metadata.assert_not_called()
    mock_internal_file_service.read_chapter_metadata.assert_not_called()

def test_get_document_details_synopsis(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details"
    file_path = BASE_PROJECT_DIR / project_id / "synopsis.md"
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Synopsis', 'document_title': 'Project Synopsis'}
    mock_internal_file_service.read_project_metadata.assert_not_called()
    mock_internal_file_service.read_chapter_metadata.assert_not_called()

def test_get_document_details_world(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details"
    file_path = BASE_PROJECT_DIR / project_id / "world.md"
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'World', 'document_title': 'World Info'}
    mock_internal_file_service.read_project_metadata.assert_not_called()
    mock_internal_file_service.read_chapter_metadata.assert_not_called()

def test_get_document_details_character_success(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details_char"
    char_id = "char1"
    char_name = "Gandalf"
    file_path = BASE_PROJECT_DIR / project_id / "characters" / f"{char_id}.md"
    mock_internal_file_service.read_project_metadata.return_value = {
        "characters": {char_id: {"name": char_name}}
    }
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Character', 'document_title': char_name}
    mock_internal_file_service.read_project_metadata.assert_called_once_with(project_id)
    mock_internal_file_service.read_chapter_metadata.assert_not_called()

def test_get_document_details_character_metadata_missing_name(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details_char_no_name"
    char_id = "char_no_name"
    file_path = BASE_PROJECT_DIR / project_id / "characters" / f"{char_id}.md"
    mock_internal_file_service.read_project_metadata.return_value = {
        "characters": {char_id: {}} # No name field
    }
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Character', 'document_title': char_id}
    mock_internal_file_service.read_project_metadata.assert_called_once_with(project_id)

def test_get_document_details_character_metadata_missing_char(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details_char_missing"
    char_id = "char_missing"
    file_path = BASE_PROJECT_DIR / project_id / "characters" / f"{char_id}.md"
    mock_internal_file_service.read_project_metadata.return_value = {
        "characters": {"other_char": {"name": "Someone else"}}
    }
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Character', 'document_title': char_id}
    mock_internal_file_service.read_project_metadata.assert_called_once_with(project_id)

def test_get_document_details_character_metadata_read_error(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details_char_err"
    char_id = "char_err"
    file_path = BASE_PROJECT_DIR / project_id / "characters" / f"{char_id}.md"
    mock_internal_file_service.read_project_metadata.side_effect = OSError("Cannot read file")
    details = manager._get_document_details(file_path, project_id)
    # Fallback when project metadata read fails is 'Unknown' type and full filename
    assert details == {'document_type': 'Unknown', 'document_title': f"{char_id}.md"}
    mock_internal_file_service.read_project_metadata.assert_called_once_with(project_id)


def test_get_document_details_scene_success(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details_scene"
    chapter_id = "ch1"
    scene_id = "sc1_good_title"
    scene_title = "The Shire"
    file_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id / f"{scene_id}.md"
    mock_internal_file_service.read_chapter_metadata.return_value = {
        "scenes": {scene_id: {"title": scene_title}}
    }
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Scene', 'document_title': scene_title}
    mock_internal_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)

def test_get_document_details_scene_metadata_missing_title(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details_scene_no_title"
    chapter_id = "ch1"
    scene_id = "sc1_no_title"
    file_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id / f"{scene_id}.md"
    mock_internal_file_service.read_chapter_metadata.return_value = {
        "scenes": {scene_id: {}} # No title field
    }
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Scene', 'document_title': scene_id}
    mock_internal_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)

def test_get_document_details_scene_metadata_missing_scene(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details_scene_missing"
    chapter_id = "ch1"
    scene_id = "sc1_missing"
    file_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id / f"{scene_id}.md"
    mock_internal_file_service.read_chapter_metadata.return_value = {
        "scenes": {"other_scene": {"title": "Another Scene"}}
    }
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Scene', 'document_title': scene_id}
    mock_internal_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)

def test_get_document_details_scene_metadata_read_error(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details_scene_err"
    chapter_id = "ch1"
    scene_id = "sc1_err"
    file_path = BASE_PROJECT_DIR / project_id / "chapters" / chapter_id / f"{scene_id}.md"
    mock_internal_file_service.read_chapter_metadata.side_effect = OSError("Cannot read chapter meta")
    details = manager._get_document_details(file_path, project_id)
    # --- CORRECTED: Fallback is scene_id (stem), type is Scene ---
    assert details == {'document_type': 'Scene', 'document_title': scene_id}
    # --- END CORRECTED ---
    mock_internal_file_service.read_chapter_metadata.assert_called_once_with(project_id, chapter_id)

def test_get_document_details_note(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details"
    note_name = "Magic System Ideas"
    file_path = BASE_PROJECT_DIR / project_id / "notes" / f"{note_name}.md"
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Note', 'document_title': note_name}
    mock_internal_file_service.read_project_metadata.assert_not_called()
    mock_internal_file_service.read_chapter_metadata.assert_not_called()

def test_get_document_details_unknown(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_details"
    file_path = BASE_PROJECT_DIR / project_id / "other_folder" / "some_file.txt"
    details = manager._get_document_details(file_path, project_id)
    assert details == {'document_type': 'Unknown', 'document_title': 'some_file.txt'}
    mock_internal_file_service.read_project_metadata.assert_not_called()
    mock_internal_file_service.read_chapter_metadata.assert_not_called()

# --- index_file Tests ---
@patch('pathlib.Path.is_file')
@patch('pathlib.Path.stat')
def test_index_file_success_normal_file(
    mock_stat: MagicMock,
    mock_is_file: MagicMock,
    patched_index_manager_instance
):
    manager, mocks = patched_index_manager_instance
    project_id = "proj_index1"
    file_path = BASE_PROJECT_DIR / project_id / "plan.md"
    doc_id = str(file_path)
    mock_is_file.return_value = True
    mock_stat.return_value.st_size = 100
    mock_document = MagicMock(name="MockDocumentPlan")
    mock_simple_directory_reader_instance.load_data.return_value = [mock_document]

    # Mocks for file_metadata_func internal calls (assuming plan doesn't need them)
    mock_internal_file_service.read_project_metadata.return_value = {}
    mock_internal_file_service.read_chapter_metadata.return_value = {}

    manager.index_file(file_path)

    mock_is_file.assert_called_once()
    mock_stat.assert_called_once()
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)
    mocks["sdr_cls"].assert_called_once_with(input_files=[file_path], file_metadata=ANY)
    assert callable(mocks["sdr_cls"].call_args.kwargs['file_metadata'])
    mock_simple_directory_reader_instance.load_data.assert_called_once()
    manager.index.insert_nodes.assert_called_once_with([mock_document])

@patch('pathlib.Path.is_file')
@patch('pathlib.Path.stat')
def test_index_file_success_character_file(
    mock_stat: MagicMock,
    mock_is_file: MagicMock,
    patched_index_manager_instance
):
    manager, mocks = patched_index_manager_instance
    project_id = "proj_char_index"
    character_id = "char_abc"
    character_name = "Gandalf"
    file_path = BASE_PROJECT_DIR / project_id / "characters" / f"{character_id}.md"
    doc_id = str(file_path)
    mock_is_file.return_value = True
    mock_stat.return_value.st_size = 50
    mock_document = MagicMock(name="MockDocumentChar")
    mock_simple_directory_reader_instance.load_data.return_value = [mock_document]

    mock_internal_file_service.read_project_metadata.return_value = {
        "characters": {character_id: {"name": character_name}}
    }
    manager.index_file(file_path)

    mock_is_file.assert_called_once()
    mock_stat.assert_called_once()
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)
    mocks["sdr_cls"].assert_called_once_with(input_files=[file_path], file_metadata=ANY)
    assert callable(mocks["sdr_cls"].call_args.kwargs['file_metadata'])
    mock_simple_directory_reader_instance.load_data.assert_called_once()
    manager.index.insert_nodes.assert_called_once_with([mock_document])


@patch('pathlib.Path.is_file')
@patch('pathlib.Path.stat')
def test_index_file_empty_file(mock_stat: MagicMock, mock_is_file: MagicMock, patched_index_manager_instance):
    manager, mocks = patched_index_manager_instance
    project_id = "proj_empty"
    file_path = BASE_PROJECT_DIR / project_id / "empty.md"
    doc_id = str(file_path)
    mock_is_file.return_value = True
    mock_stat.return_value.st_size = 0
    manager.index_file(file_path)
    mock_is_file.assert_called_once()
    mock_stat.assert_called_once()
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)
    mocks["sdr_cls"].assert_not_called()
    manager.index.insert_nodes.assert_not_called()

@patch('pathlib.Path.is_file')
def test_index_file_not_a_file(mock_is_file: MagicMock, patched_index_manager_instance):
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
def test_index_file_outside_project(mock_stat: MagicMock, mock_is_file: MagicMock, patched_index_manager_instance):
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
    manager, _ = patched_index_manager_instance
    project_id = "proj_del"
    file_path = BASE_PROJECT_DIR / project_id / "to_delete.md"
    doc_id = str(file_path)
    manager.delete_doc(file_path)
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)

def test_delete_doc_non_path_input(patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    manager.delete_doc("not/a/path/object")
    manager.index.delete_ref_doc.assert_not_called()

@patch('pathlib.Path.is_file')
def test_delete_doc_index_error(mock_is_file: MagicMock, patched_index_manager_instance):
    manager, _ = patched_index_manager_instance
    project_id = "proj_del_err"
    file_path = BASE_PROJECT_DIR / project_id / "delete_err.md"
    doc_id = str(file_path)
    manager.index.delete_ref_doc.side_effect = RuntimeError("Index deletion failed")
    manager.delete_doc(file_path)
    manager.index.delete_ref_doc.assert_called_once_with(ref_doc_id=doc_id, delete_from_docstore=True)

# --- delete_project_docs Tests ---
def test_delete_project_docs_success(patched_index_manager_instance):
    manager, mocks = patched_index_manager_instance
    project_id = "proj_to_clear"
    manager.chroma_collection = mock_chroma_collection
    manager.delete_project_docs(project_id)
    mock_chroma_collection.delete.assert_called_once_with(where={"project_id": project_id})
    manager.index.delete_ref_doc.assert_not_called()

def test_delete_project_docs_chroma_error(patched_index_manager_instance):
    manager, mocks = patched_index_manager_instance
    project_id = "proj_clear_error"
    manager.chroma_collection = mock_chroma_collection
    mock_chroma_collection.delete.side_effect = Exception("Chroma DB write error")
    manager.delete_project_docs(project_id)
    mock_chroma_collection.delete.assert_called_once_with(where={"project_id": project_id})

def test_delete_project_docs_no_collection(patched_index_manager_instance):
    manager, mocks = patched_index_manager_instance
    project_id = "proj_no_coll"
    manager.chroma_collection = None
    manager.delete_project_docs(project_id)
    mock_chroma_collection.delete.assert_not_called()