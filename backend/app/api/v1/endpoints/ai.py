# Copyright 2025 Antimortine (antimortine@gmail.com)
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

from fastapi import APIRouter, HTTPException, status, Body, Path, Depends
import logging

# Import the service instance - THIS IMPORT IS KEY
from app.services.ai_service import ai_service
# Import request/response models
from app.models.ai import AIQueryRequest, AIQueryResponse
# Import project dependency checker if needed (likely needed for project_id context)
from app.api.v1.endpoints.content_blocks import get_project_dependency

logger = logging.getLogger(__name__)
router = APIRouter()

# --- Placeholder AI Query Endpoint ---
@router.post(
    "/query/{project_id}",
    response_model=AIQueryResponse, # Use the Pydantic model
    summary="Query Project Context (RAG)",
    description="Sends a query to the AI, using the indexed content of the specified project as context (Retrieval-Augmented Generation)."
)
async def query_project_context(
    query_request: AIQueryRequest = Body(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Performs a RAG query against the specified project's indexed content.

    - **project_id**: The UUID of the project to query within.
    - **query_request**: Contains the user's query text.
    """
    logger.info(f"Received AI query request for project {project_id}: '{query_request.query}'")
    try:
        answer_text = await ai_service.query_project(project_id, query_request.query)

        # --- TODO: Enhance response ---
        # In the future, ai_service.query_project might return a richer object
        # including source nodes. We would construct the AIQueryResponse here.
        # For now, just return the answer string.
        # -----------------------------

        logger.info(f"Successfully processed query for project {project_id}.")
        # Return the response model
        return AIQueryResponse(answer=answer_text) # Add source_nodes=... later

    except Exception as e:
        logger.error(f"Error processing AI query for project {project_id}: {e}", exc_info=True)
        # Return a generic error response
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process AI query for project {project_id}."
        )

# --- Add other AI endpoints later (generation, editing) ---
# @router.post("/generate/scene/{project_id}/{chapter_id}", ...)
# async def generate_scene(...)