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
from unittest.mock import MagicMock, AsyncMock, patch, ANY
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM, CompletionResponse
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.schema import NodeWithScore, TextNode

# Import the class we are testing
from app.rag.scene_generator import SceneGenerator
from app.core.config import settings # For RAG_GENERATION_SIMILARITY_TOP_K

# --- Fixtures are now defined in tests/rag/conftest.py ---
# Removed mock_llm, mock_retriever, mock_index definitions


# --- Test SceneGenerator ---

@pytest.mark.asyncio
# Patch the VectorIndexRetriever where it's used inside SceneGenerator.generate_scene
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_success_with_context(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,             # Injected from conftest.py
    mock_index: MagicMock            # Injected from conftest.py
):
    """Test successful scene generation with plan, synopsis, previous scenes, and RAG context."""
    # Arrange
    project_id = "proj-sg-1"
    chapter_id = "ch-sg-1"
    prompt_summary = "Character enters the tavern."
    previous_scene_order = 1
    plan = "Plan: Go to tavern."
    synopsis = "Synopsis: Hero needs info."
    prev_scene_content = "## Scene 1\nHero walks down the street."
    explicit_previous_scenes = [(1, prev_scene_content)]
    mock_node1 = NodeWithScore(node=TextNode(id_='n1', text="Tavern description.", metadata={'file_path': 'world.md', 'project_id': project_id}), score=0.85)
    retrieved_nodes = [mock_node1]
    expected_generated_text = "## Scene 2\nHe pushed open the heavy tavern door."

    # Configure mocks
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text=expected_generated_text)

    # Instantiate and Act
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_text = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order,
        plan, synopsis, explicit_previous_scenes
    )

    # Assert
    assert generated_text == expected_generated_text

    # Verify retriever instantiation and call
    mock_retriever_class.assert_called_once_with(
        index=mock_index,
        similarity_top_k=settings.RAG_GENERATION_SIMILARITY_TOP_K,
        filters=ANY # Check filters more specifically if needed
    )
    expected_retrieval_query = f"Context relevant for writing a new scene after scene order {previous_scene_order} in chapter {chapter_id}. Scene focus: {prompt_summary}"
    mock_retriever_instance.aretrieve.assert_awaited_once_with(expected_retrieval_query)

    # Verify LLM call (check prompt contains key elements)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert prompt_summary in prompt_arg
    assert plan in prompt_arg
    assert synopsis in prompt_arg
    assert prev_scene_content in prompt_arg
    assert "Immediately Previous Scene (Order: 1)" in prompt_arg
    assert "Tavern description." in prompt_arg # RAG context
    assert "Source: world.md" in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_success_first_scene(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,             # Injected from conftest.py
    mock_index: MagicMock            # Injected from conftest.py
):
    """Test successful generation for the first scene (no previous scenes)."""
    # Arrange
    project_id = "proj-sg-2"
    chapter_id = "ch-sg-2"
    prompt_summary = "The story begins."
    previous_scene_order = 0 # Indicate first scene
    plan = "Plan: Introduction."
    synopsis = "Synopsis: A new beginning."
    explicit_previous_scenes = [] # Empty list
    retrieved_nodes = [] # No relevant RAG context found
    expected_generated_text = "## Chapter Start\nThe sun rose."

    # Configure mocks
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text=expected_generated_text)

    # Instantiate and Act
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_text = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order,
        plan, synopsis, explicit_previous_scenes
    )

    # Assert
    assert generated_text == expected_generated_text

    # Verify retriever call
    expected_retrieval_query = f"Context relevant for writing a new scene after scene order {previous_scene_order} in chapter {chapter_id}. Scene focus: {prompt_summary}"
    mock_retriever_instance.aretrieve.assert_awaited_once_with(expected_retrieval_query)

    # Verify LLM call (check prompt indicates first scene and no RAG context)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert prompt_summary in prompt_arg
    assert plan in prompt_arg
    assert synopsis in prompt_arg
    assert "Previous Scene(s):** N/A (Generating the first scene)" in prompt_arg
    assert "No additional context retrieved via search." in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_success_no_rag_nodes(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,             # Injected from conftest.py
    mock_index: MagicMock            # Injected from conftest.py
):
    """Test successful generation when retriever finds no relevant nodes."""
    # Arrange
    project_id = "proj-sg-3"
    chapter_id = "ch-sg-3"
    prompt_summary = None # No specific summary
    previous_scene_order = 2
    plan = "Plan"
    synopsis = "Synopsis"
    prev_scene_content = "## Scene 2\nSomething happened."
    explicit_previous_scenes = [(2, prev_scene_content)]
    retrieved_nodes = [] # No RAG nodes
    expected_generated_text = "## Scene 3\nFollowing the previous events..."

    # Configure mocks
    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text=expected_generated_text)

    # Instantiate and Act
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_text = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order,
        plan, synopsis, explicit_previous_scenes
    )

    # Assert
    assert generated_text == expected_generated_text

    # Verify retriever call
    expected_retrieval_query = f"Context relevant for writing a new scene after scene order {previous_scene_order} in chapter {chapter_id}." # No summary part
    mock_retriever_instance.aretrieve.assert_awaited_once_with(expected_retrieval_query)

    # Verify LLM call (check prompt includes explicit context and indication of no retrieved nodes)
    mock_llm.acomplete.assert_awaited_once()
    prompt_arg = mock_llm.acomplete.call_args[0][0]
    assert plan in prompt_arg
    assert synopsis in prompt_arg
    assert prev_scene_content in prompt_arg
    assert "No additional context retrieved via search." in prompt_arg

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_retriever_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,             # Injected from conftest.py
    mock_index: MagicMock            # Injected from conftest.py
):
    """Test generation when the retriever fails."""
    # Arrange
    project_id = "proj-sg-4"
    chapter_id = "ch-sg-4"
    prompt_summary = "Summary"
    previous_scene_order = 1
    plan = "Plan"
    synopsis = "Synopsis"
    explicit_previous_scenes = [(1, "Previous")]

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(side_effect=RuntimeError("Retriever failed"))

    # Instantiate and Act
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_text = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order,
        plan, synopsis, explicit_previous_scenes
    )

    # Assert
    assert "Error: An unexpected error occurred during scene generation." in generated_text
    mock_retriever_instance.aretrieve.assert_awaited_once() # Retriever was called
    mock_llm.acomplete.assert_not_awaited() # LLM should not be called

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_llm_error(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,             # Injected from conftest.py
    mock_index: MagicMock            # Injected from conftest.py
):
    """Test generation when the LLM call fails."""
    # Arrange
    project_id = "proj-sg-5"
    chapter_id = "ch-sg-5"
    prompt_summary = "Summary"
    previous_scene_order = 1
    plan = "Plan"
    synopsis = "Synopsis"
    explicit_previous_scenes = [(1, "Previous")]
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete = AsyncMock(side_effect=RuntimeError("LLM failed"))

    # Instantiate and Act
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_text = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order,
        plan, synopsis, explicit_previous_scenes
    )

    # Assert
    assert "Error: An unexpected error occurred during scene generation." in generated_text
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once() # LLM was called

@pytest.mark.asyncio
@patch('app.rag.scene_generator.VectorIndexRetriever', autospec=True)
async def test_generate_scene_llm_empty_response(
    mock_retriever_class: MagicMock,
    mock_llm: MagicMock,             # Injected from conftest.py
    mock_index: MagicMock            # Injected from conftest.py
):
    """Test generation when the LLM returns an empty response."""
    # Arrange
    project_id = "proj-sg-6"
    chapter_id = "ch-sg-6"
    prompt_summary = "Summary"
    previous_scene_order = 1
    plan = "Plan"
    synopsis = "Synopsis"
    explicit_previous_scenes = [(1, "Previous")]
    retrieved_nodes = []

    mock_retriever_instance = mock_retriever_class.return_value
    mock_retriever_instance.aretrieve = AsyncMock(return_value=retrieved_nodes)
    mock_llm.acomplete.return_value = CompletionResponse(text="") # Empty response

    # Instantiate and Act
    generator = SceneGenerator(index=mock_index, llm=mock_llm)
    generated_text = await generator.generate_scene(
        project_id, chapter_id, prompt_summary, previous_scene_order,
        plan, synopsis, explicit_previous_scenes
    )

    # Assert
    assert "Error: The AI failed to generate a scene draft." in generated_text
    mock_retriever_instance.aretrieve.assert_awaited_once()
    mock_llm.acomplete.assert_awaited_once()