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

from fastapi import APIRouter, HTTPException, status, Body, Path, Depends
import logging
from typing import List

from app.services.ai_service import ai_service
# Import all needed AI models
from app.models.ai import (
    AIQueryRequest,
    AIQueryResponse,
    SourceNodeModel,
    AISceneGenerationRequest,
    AISceneGenerationResponse,
    AIRephraseRequest,
    AIRephraseResponse,
    AIChapterSplitRequest,   # Import new request model
    AIChapterSplitResponse   # Import new response model
)
# Import dependencies for checking project/chapter existence
from app.api.v1.endpoints.content_blocks import get_project_dependency # Checks project exists
from app.api.v1.endpoints.scenes import get_chapter_dependency # Checks project & chapter exist

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
    project_id: str = Depends(get_project_dependency) # Use project dependency
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

    # --- MODIFIED EXCEPTION HANDLING ---
    except HTTPException as http_exc:
        # Re-raise HTTPExceptions directly (like 404 from dependency or 5xx from service)
        logger.warning(f"HTTPException during AI query for project {project_id}: {http_exc.status_code} - {http_exc.detail}")
        raise http_exc
    except Exception as e:
        # Catch any other unexpected exceptions
        logger.error(f"Unexpected error processing AI query for project {project_id}: {e}", exc_info=True)
        # Raise a generic 500 error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process AI query for project {project_id} due to an internal error."
        )
    # --- END MODIFIED EXCEPTION HANDLING ---


@router.post(
    "/generate/scene/{project_id}/{chapter_id}",
    response_model=AISceneGenerationResponse,
    status_code=status.HTTP_200_OK, # Use 200 OK for successful generation
    summary="Generate Scene Draft (RAG)",
    description="Generates a draft for a new scene within the specified chapter, using project context and an optional prompt."
)
async def generate_scene_draft(
    request_data: AISceneGenerationRequest = Body(...),
    ids: tuple[str, str] = Depends(get_chapter_dependency) # Ensures project & chapter exist
):
    """
    Generates a scene draft using AI based on project context.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the parent chapter (in path).
    - **request_data**: Contains optional guidance for generation (e.g., prompt_summary).
    """
    project_id, chapter_id = ids
    logger.info(f"Received AI scene generation request for project {project_id}, chapter {chapter_id}. Summary: '{request_data.prompt_summary}'")

    try:
        generated_content = await ai_service.generate_scene_draft(
            project_id=project_id,
            chapter_id=chapter_id,
            request_data=request_data
        )

        # Check if the service returned an error message (simple check for now)
        # AIService now raises HTTPException for errors, so this check might be redundant
        # but kept for defense.
        if isinstance(generated_content, str) and generated_content.startswith("Error:"):
             logger.error(f"Scene generation failed for project {project_id}, chapter {chapter_id}: {generated_content}")
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail=f"Failed to generate scene draft: {generated_content}"
             )

        logger.info(f"Successfully generated scene draft for project {project_id}, chapter {chapter_id}.")
        return AISceneGenerationResponse(generated_content=generated_content)

    # --- MODIFIED EXCEPTION HANDLING ---
    except HTTPException as http_exc:
         # Re-raise HTTPException (e.g., 404 from dependency or 5xx from service)
         logger.warning(f"HTTPException during scene generation for project {project_id}, chapter {chapter_id}: {http_exc.status_code} - {http_exc.detail}")
         raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error processing AI scene generation for project {project_id}, chapter {chapter_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process AI scene generation for project {project_id}, chapter {chapter_id} due to an internal error."
        )
    # --- END MODIFIED EXCEPTION HANDLING ---


@router.post(
    "/edit/rephrase/{project_id}",
    response_model=AIRephraseResponse,
    status_code=status.HTTP_200_OK,
    summary="Rephrase Selected Text (RAG)",
    description="Provides alternative phrasings for the selected text, using project context."
)
async def rephrase_text_endpoint(
    request_data: AIRephraseRequest = Body(...),
    project_id: str = Depends(get_project_dependency) # Ensures project exists
):
    """
    Rephrases the provided text using AI based on project context.

    - **project_id**: The UUID of the project context to use (in path).
    - **request_data**: Contains the text to rephrase (`selected_text`) and optional surrounding context (`context_before`, `context_after`).
    """
    logger.info(f"Received AI rephrase request for project {project_id}. Text: '{request_data.selected_text[:50]}...'")

    try:
        suggestions = await ai_service.rephrase_text(
            project_id=project_id,
            request_data=request_data
        )

        # Check if the service returned an error message
        # AIService now raises HTTPException for errors, so this check might be redundant
        if suggestions and isinstance(suggestions[0], str) and suggestions[0].startswith("Error:"):
             logger.error(f"Rephrasing failed for project {project_id}: {suggestions[0]}")
             raise HTTPException(
                 status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                 detail=f"Failed to rephrase text: {suggestions[0]}"
             )

        logger.info(f"Successfully generated {len(suggestions)} rephrase suggestions for project {project_id}.")
        return AIRephraseResponse(suggestions=suggestions)

    # --- MODIFIED EXCEPTION HANDLING ---
    except HTTPException as http_exc:
         # Re-raise HTTPException (e.g., 404 from dependency or 5xx from service)
         logger.warning(f"HTTPException during rephrase for project {project_id}: {http_exc.status_code} - {http_exc.detail}")
         raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error processing AI rephrase request for project {project_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process AI rephrase request for project {project_id} due to an internal error."
        )
    # --- END MODIFIED EXCEPTION HANDLING ---


# --- NEW: Chapter Splitting Endpoint ---
@router.post(
    "/split/chapter/{project_id}/{chapter_id}",
    response_model=AIChapterSplitResponse,
    status_code=status.HTTP_200_OK,
    summary="Split Chapter into Scenes (AI)",
    description="Uses AI to analyze chapter content and propose a split into distinct scenes with suggested titles."
)
async def split_chapter_into_scenes(
    request_data: AIChapterSplitRequest = Body(...), # Body might be empty for now
    ids: tuple[str, str] = Depends(get_chapter_dependency) # Ensures project & chapter exist
):
    """
    Analyzes a chapter's content and proposes a split into scenes.

    - **project_id**: The UUID of the parent project (in path).
    - **chapter_id**: The UUID of the chapter to split (in path).
    - **request_data**: Optional parameters to guide splitting (currently empty).
    """
    project_id, chapter_id = ids
    logger.info(f"Received AI chapter split request for project {project_id}, chapter {chapter_id}.")

    try:
        # Call the new service method (to be implemented)
        proposed_scenes = await ai_service.split_chapter_into_scenes(
            project_id=project_id,
            chapter_id=chapter_id,
            request_data=request_data
        )

        # AIService method should raise HTTPException on failure or return the list
        logger.info(f"Successfully proposed {len(proposed_scenes)} scenes for chapter {chapter_id}.")
        return AIChapterSplitResponse(proposed_scenes=proposed_scenes)

    except HTTPException as http_exc:
         logger.warning(f"HTTPException during chapter split for project {project_id}, chapter {chapter_id}: {http_exc.status_code} - {http_exc.detail}")
         raise http_exc
    except Exception as e:
        logger.error(f"Unexpected error processing AI chapter split for project {project_id}, chapter {chapter_id}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process AI chapter split for project {project_id}, chapter {chapter_id} due to an internal error."
        )
# --- END NEW ENDPOINT ---


# --- Add other AI editing endpoints later ---
# @router.post("/edit/summarize/{project_id}", ...)
# async def summarize_text_endpoint(...)