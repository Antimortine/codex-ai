# Mock AI Service for use in tests
from unittest.mock import MagicMock, AsyncMock
from typing import Dict, Set, List, Optional, Tuple, Any

# Create a mock AI service class with appropriate async method mocks
class MockAIService:
    def __init__(self):
        # Create async mock methods for all public AI service methods
        self.query_project = AsyncMock()
        self.generate_scene_draft = AsyncMock()
        self.rephrase_text = AsyncMock()
        self.split_chapter_into_scenes = AsyncMock()
        self.rebuild_project_index = AsyncMock()
        
        # Some sane default return values
        self.query_project.return_value = ("Mock answer", [], None)
        self.generate_scene_draft.return_value = {"title": "Mock Scene", "content": "Mock content"}
        self.rephrase_text.return_value = ["Mock rephrased text"]
        self.split_chapter_into_scenes.return_value = []
        self.rebuild_project_index.return_value = True
        
    # Add utility method to configure mock return values
    def configure_query_return(self, answer: str, nodes=None, sources=None):
        self.query_project.return_value = (answer, nodes or [], sources)
        
    def configure_generate_scene_return(self, title: str, content: str):
        self.generate_scene_draft.return_value = {"title": title, "content": content}
        
    def configure_rephrase_return(self, suggestions: List[str]):
        self.rephrase_text.return_value = suggestions
        
    def configure_split_return(self, scenes: List[Dict[str, str]]):
        self.split_chapter_into_scenes.return_value = scenes
        
    def configure_rebuild_return(self, success: bool):
        self.rebuild_project_index.return_value = success
        
    # Add utility method to raise exceptions
    def configure_query_error(self, status_code: int, detail: str):
        from fastapi import HTTPException
        self.query_project.side_effect = HTTPException(status_code=status_code, detail=detail)
        
    def configure_generate_scene_error(self, status_code: int, detail: str):
        from fastapi import HTTPException
        self.generate_scene_draft.side_effect = HTTPException(status_code=status_code, detail=detail)
        
    # ... similar methods for other operations

# Create a singleton instance for use in tests
mock_ai_service = MockAIService()
