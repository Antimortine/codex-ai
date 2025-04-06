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
from typing import List

from app.services.ai_service import ai_service
from app.models.ai import AIQueryRequest, AIQueryResponse, SourceNodeModel
from app.api.v1.endpoints.content_blocks import get_project_dependency
from llama_index.core.base.response.schema import NodeWithScore


logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/query/{project_id}",
    response_model=AIQueryResponse,
    summary="Query Project Context (RAG)",
    description="Sends a query to the AI, using the indexed content of the specified project as context (Retrieval-Augmented Generation)."
)
async def query_project_context(
    query_request: AIQueryRequest = Body(...),
    project_id: str = Depends(get_project_dependency)
):
    """
    Performs a RAG query against the specified project's indexed content.

    - **project_id**: The UUID of the project to query within.
    - **query_request**: Contains the user's query text.
    """
    logger.info(f"Received AI query request for project {project_id}: '{query_request.query}'")
    try:
        # Call the AIService method - it now returns a tuple
        answer_text, raw_source_nodes = await ai_service.query_project(project_id, query_request.query)

        # --- Format Source Nodes ---
        formatted_nodes: List[SourceNodeModel] = []
        if raw_source_nodes:
            logger.debug(f"Formatting {len(raw_source_nodes)} source nodes for API response.")
            for node_with_score in raw_source_nodes:
                # Access attributes from NodeWithScore object
                node = node_with_score.node
                score = node_with_score.score
                formatted_nodes.append(
                    SourceNodeModel(
                        id=node.node_id, # Use node_id which is the same as id_
                        text=node.get_content(), # Use get_content() method
                        score=score,
                        metadata=node.metadata or {} # Ensure metadata is at least an empty dict
                    )
                )
        # -------------------------

        logger.info(f"Successfully processed query for project {project_id}. Returning response with {len(formatted_nodes)} source nodes.")
        # Return the response model, now including formatted source nodes
        return AIQueryResponse(answer=answer_text, source_nodes=formatted_nodes)

    except Exception as e:
        logger.error(f"Error processing AI query for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process AI query for project {project_id}."
        )

# --- Add other AI endpoints later ---
# @router.post("/generate/scene/{project_id}/{chapter_id}", ...)
# async def generate_scene(...)