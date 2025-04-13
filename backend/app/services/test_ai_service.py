# Simplified AI service for tests
from typing import Dict, Set, List, Optional, Tuple, Any
from app.models.ai import AISceneGenerationRequest, AIRephraseRequest, AIChapterSplitRequest, ProposedScene

class TestAIService:
    """A simplified version of AIService that doesn't depend on RagEngine or other complex dependencies"""
    
    async def query_project(self, project_id: str, query_text: str) -> Tuple[str, List, Optional[List[Dict[str, str]]]]:
        """Mock implementation of query_project"""
        return f"Test answer for {query_text}", [], None
    
    async def generate_scene_draft(self, project_id: str, chapter_id: str, request: AISceneGenerationRequest) -> Dict[str, str]:
        """Mock implementation of generate_scene_draft"""
        return {
            "title": f"Scene for {chapter_id}",
            "content": f"Content based on prompt: {request.prompt_summary}"
        }
    
    async def rephrase_text(self, project_id: str, request: AIRephraseRequest) -> List[str]:
        """Mock implementation of rephrase_text"""
        return [f"Rephrased: {request.text_to_rephrase}"]
    
    async def split_chapter_into_scenes(self, project_id: str, chapter_id: str, request: AIChapterSplitRequest) -> List[ProposedScene]:
        """Mock implementation of split_chapter_into_scenes"""
        return [
            ProposedScene(suggested_title="Scene 1", content="Content for scene 1"),
            ProposedScene(suggested_title="Scene 2", content="Content for scene 2")
        ]
    
    async def rebuild_project_index(self, project_id: str) -> bool:
        """Mock implementation of rebuild_project_index"""
        return True

# Create an instance for use in tests
test_ai_service = TestAIService()
