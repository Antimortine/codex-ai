"""
Tests for the AIService implementation, focusing on direct method testing.
"""
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException
from app.services.ai_service import AIService
from app.models.ai import AISceneGenerationRequest, AIChapterSplitRequest
from llama_index.core.base.response.schema import NodeWithScore

# Constants for testing
TEST_PROJECT_ID = "test-project-123"
TEST_CHAPTER_ID = "test-chapter-456"


@pytest.mark.asyncio
async def test_query_project_service_error():
    """
    Test direct AIService.query_project method error handling.
    This replaces the API-level test that was skipped due to FastAPI testing limitations.
    """
    # Create a service instance
    ai_service = AIService()
    
    # Mock the rag_engine to raise an exception
    mock_rag_engine = AsyncMock()
    mock_rag_engine.query.side_effect = Exception("RAG engine error")
    ai_service.rag_engine = mock_rag_engine
    
    # Mock the file_service for context loading
    mock_file_service = MagicMock()
    mock_file_service.read_content_block_file.return_value = "Mocked content"
    mock_file_service._get_content_block_path.return_value = MagicMock()
    ai_service.file_service = mock_file_service
    
    # Test that the exception is properly raised and transformed
    with pytest.raises(Exception) as exc_info:
        await ai_service.query_project(
            project_id=TEST_PROJECT_ID,
            query_text="Test query"
        )
    
    # Verify the exception details
    assert "RAG engine error" in str(exc_info.value)
    
    # Verify that the rag_engine's query method was called with appropriate parameters
    mock_rag_engine.query.assert_called_once()


@pytest.mark.asyncio
async def test_query_project_formatting_error():
    """
    Test direct AIService.query_project method error handling during response formatting.
    This replaces the API-level test that was skipped due to FastAPI testing limitations.
    """
    # Create a service instance
    ai_service = AIService()
    
    # Mock the rag_engine to return a response that will cause formatting errors
    mock_response = MagicMock()
    mock_response.response = "Mocked response"
    
    # This will cause an error during processing of source nodes
    mock_response.source_nodes = [
        object()  # Not a proper NodeWithScore object, will cause formatting error
    ]
    
    mock_rag_engine = AsyncMock()
    mock_rag_engine.query.return_value = mock_response
    ai_service.rag_engine = mock_rag_engine
    
    # Mock the file_service for context loading
    mock_file_service = MagicMock()
    mock_file_service.read_content_block_file.return_value = "Mocked content"
    mock_file_service._get_content_block_path.return_value = MagicMock()
    ai_service.file_service = mock_file_service
    
    # Test that the formatting exception is properly raised
    with pytest.raises(Exception) as exc_info:
        await ai_service.query_project(
            project_id=TEST_PROJECT_ID,
            query_text="Test query"
        )
    
    # The exact error message will depend on implementation details,
    # but we can verify that the function attempted to process the response
    assert mock_rag_engine.query.called


@pytest.mark.asyncio
async def test_generate_scene_draft_service_error():
    """
    Test scene generation error handling at the service level.
    This replaces the API-level test that was skipped due to FastAPI testing limitations.
    """
    # Create a service instance
    ai_service = AIService()
    
    # Make the RAG engine raise an exception for any method called
    mock_rag_engine = MagicMock()
    # Set all async methods to raise exceptions
    for method_name in ['generate', 'generate_scene', 'generate_text', 'complete_text']:
        if hasattr(mock_rag_engine, method_name):
            getattr(mock_rag_engine, method_name).side_effect = Exception("Mock error")
    ai_service.rag_engine = mock_rag_engine
    
    # Mock the file_service for context loading
    mock_file_service = MagicMock()
    mock_file_service.read_content_block_file.return_value = "Mocked content"
    mock_file_service._get_content_block_path.return_value = MagicMock()
    mock_file_service.read_project_metadata.return_value = {"chapters": {TEST_CHAPTER_ID: {"title": "Test Chapter"}}}
    ai_service.file_service = mock_file_service
    
    # Create a request object
    request_data = AISceneGenerationRequest(
        prompt="Test prompt",
        previous_scene_order=1,
        next_scene_order=2
    )
    
    # Test an error occurs - could be various types of exceptions depending on implementation
    try:
        await ai_service.generate_scene_draft(
            project_id=TEST_PROJECT_ID,
            chapter_id=TEST_CHAPTER_ID,
            request_data=request_data
        )
        pytest.fail("Expected an exception but none was raised")
    except Exception as e:
        # Success - an exception was raised
        # It could be HTTPException, ValueError, or the original exception
        # The key is that the service doesn't let errors pass silently
        assert str(e)  # Just verify the exception has a message


@pytest.mark.asyncio
async def test_split_chapter_service_error():
    """
    Test chapter splitting error handling at the service level.
    This replaces the API-level test that was skipped due to FastAPI testing limitations.
    """
    # Create a service instance
    ai_service = AIService()
    
    # Make the RAG engine raise an exception for any method called
    mock_rag_engine = MagicMock()
    # Set split methods to raise exceptions
    for method_name in ['split_text', 'split_content', 'split_chapter']:
        if hasattr(mock_rag_engine, method_name):
            getattr(mock_rag_engine, method_name).side_effect = Exception("Mock splitting error")
    ai_service.rag_engine = mock_rag_engine
    
    # Mock the file_service for context loading
    mock_file_service = MagicMock()
    mock_file_service.read_content_block_file.return_value = "Mocked content"
    mock_file_service._get_content_block_path.return_value = MagicMock()
    mock_file_service.read_project_metadata.return_value = {"chapters": {TEST_CHAPTER_ID: {"title": "Test Chapter"}}}
    ai_service.file_service = mock_file_service
    
    # Create a request object
    request_data = AIChapterSplitRequest(
        chapter_content="Test chapter content to split"
    )
    
    # Test an error occurs - could be various types of exceptions depending on implementation
    try:
        await ai_service.split_chapter_into_scenes(
            project_id=TEST_PROJECT_ID,
            chapter_id=TEST_CHAPTER_ID,
            request_data=request_data
        )
        pytest.fail("Expected an exception but none was raised")
    except Exception as e:
        # Success - an exception was raised
        # The key is that the service doesn't let errors pass silently
        assert str(e)  # Just verify the exception has a message


@pytest.mark.asyncio
async def test_rebuild_index_error_validation():
    """
    Test API-level validation for rebuild index endpoint when errors occur.
    This is a simplified test that validates error handling at the endpoint level.
    """
    from fastapi import status
    from fastapi.testclient import TestClient
    from app.main import app
    from unittest.mock import patch

    client = TestClient(app)
    
    # Patch the AIService.rebuild_project_index method globally
    with patch('app.services.ai_service.AIService.rebuild_project_index', 
               side_effect=Exception("Simulated rebuild error")):
        
        # Make a direct request to the API endpoint
        response = client.post(f"/api/v1/ai/rebuild_index/{TEST_PROJECT_ID}")
        
        # Verify the API properly converts the error to a 500 status code
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to rebuild index" in response.json()["detail"]
