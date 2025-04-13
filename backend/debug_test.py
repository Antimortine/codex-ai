#!/usr/bin/env python
"""
Direct debugging script to test the AI service endpoint without pytest.
This will help us see detailed error messages that might be suppressed in pytest.
"""
import sys
import traceback
import asyncio
from unittest.mock import MagicMock, AsyncMock
from fastapi import FastAPI
from fastapi.testclient import TestClient

try:
    # Import the app
    from app.main import app
    from app.api.v1.endpoints.ai import router, get_ai_service
    from app.models.ai import AIQueryRequest, AIQueryResponse
    from app.models.project import ProjectRead
    from app.services.ai_service import AIService

    # Create a test client
    client = TestClient(app)

    # Main debug function
    def debug_test():
        print("=" * 80)
        print("Starting debug test")
        print("=" * 80)
        
        # Create a simple FastAPI app for isolated testing
        test_app = FastAPI()
        test_app.include_router(router)
        test_client = TestClient(test_app)
        
        try:
            # Create mocks
            mock_ai_service = MagicMock(spec=AIService)
            mock_ai_service.query_project = AsyncMock(return_value=("Test answer", [], None))
            
            # Store original function
            original_get_ai_service = get_ai_service
            
            # Replace the dependency
            async def mock_get_ai_service():
                print("Mock get_ai_service called")
                return mock_ai_service
                
            # Patch the global router's dependencies
            for route in router.routes:
                if hasattr(route, "dependencies"):
                    for i, dependency in enumerate(route.dependencies):
                        if getattr(dependency, "dependency", None) == get_ai_service:
                            print(f"Found dependency on route {route.path}, replacing...")
                            route.dependencies[i].dependency = mock_get_ai_service
            
            # Test with the actual app
            print("Making test request to /api/v1/ai/query/test-project")
            response = client.post(
                "/api/v1/ai/query/test-project",
                json={"query": "Test query"}
            )
            
            # Print response details
            print(f"Response status: {response.status_code}")
            print(f"Response headers: {response.headers}")
            print(f"Response body: {response.content.decode()}")
            
            # Reset the dependency
            for route in router.routes:
                if hasattr(route, "dependencies"):
                    for i, dependency in enumerate(route.dependencies):
                        if getattr(dependency, "dependency", None) == mock_get_ai_service:
                            print(f"Restoring original dependency...")
                            route.dependencies[i].dependency = original_get_ai_service
            
        except Exception as e:
            print(f"Error during test: {e}")
            traceback.print_exc()
        
        print("=" * 80)
        print("Debug test completed")
        print("=" * 80)

except ImportError as e:
    print(f"Import error: {e}")
    traceback.print_exc()
    sys.exit(1)

if __name__ == "__main__":
    debug_test()
