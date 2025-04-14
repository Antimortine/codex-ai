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
from fastapi import APIRouter, Depends, HTTPException, status, Body
from app.services.ai_service import AIService, get_ai_service
from app.models.ai import (
    AIQueryRequest, AIQueryResponse, AISceneGenerationRequest, AISceneGenerationResponse,
    AIRephraseRequest, AIRephraseResponse, AIChapterSplitRequest, AIChapterSplitResponse,
    RebuildIndexResponse
)
from app.models.common import MessageResponse

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/query/{project_id}", response_model=AIQueryResponse)
async def query_project(
    project_id: str,
    request: AIQueryRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Query the project context using RAG.
    Provides an answer based on the project's indexed content and explicit context.
    """
    try:
        logger.info(f"Received query for project {project_id}: '{request.query}'")
        answer, sources, direct_sources = await ai_service.query_project(project_id, request.query)
        
        # Enhanced logging for direct sources debugging
        if direct_sources:
            logger.info(f"API query_project received direct_sources: {direct_sources}")
        else:
            logger.info("API query_project received None or empty direct_sources")
            # Ensure we at least send an empty array instead of null
            direct_sources = []
            
        logger.info(f"Successfully generated query response for project {project_id}")
        
        # Convert NodeWithScore objects to the format expected by SourceNodeModel
        formatted_sources = []
        for node in sources:
            formatted_sources.append({
                "id": node.node.id_,
                "text": node.node.text,
                "score": node.score,
                "metadata": node.node.metadata
            })
        
        # Log what we're returning to the client
        logger.info(f"API returning to client: answer length={len(answer) if answer else 0}, sources={len(formatted_sources)}, direct_sources={len(direct_sources) if direct_sources else 0}")
        if direct_sources:
            logger.info(f"API direct_sources being returned: {direct_sources}")
            
        return AIQueryResponse(answer=answer, source_nodes=formatted_sources, direct_sources=direct_sources)
    except FileNotFoundError as e:
        logger.warning(f"Project not found during query: {project_id}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
    except Exception as e:
        logger.exception(f"Error querying project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to query project: {str(e)}")

@router.post("/generate/scene/{project_id}/{chapter_id}", response_model=AISceneGenerationResponse)
async def generate_scene(
    project_id: str,
    chapter_id: str,
    request_data: AISceneGenerationRequest = Body(...), # Expects request body matching the model
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Generate a new scene draft for a chapter using AI, considering context.
    """
    try:
        logger.info(f"Received scene generation request for project {project_id}, chapter {chapter_id}. Summary: '{request_data.prompt_summary}', Prev Scenes: {request_data.previous_scene_order}")
        # Pass the validated request data object to the service
        result = await ai_service.generate_scene_draft(project_id, chapter_id, request_data)
        logger.info(f"Successfully generated scene draft for project {project_id}, chapter {chapter_id}")
        return AISceneGenerationResponse(**result)
    except FileNotFoundError as e:
        logger.warning(f"Project or chapter not found during scene generation: {project_id}/{chapter_id}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' or Chapter '{chapter_id}' not found.")
    except ValueError as e:
         logger.warning(f"Value error during scene generation for {project_id}/{chapter_id}: {e}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error generating scene for project {project_id}, chapter {chapter_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to generate scene: {str(e)}")


@router.post("/edit/rephrase/{project_id}", response_model=AIRephraseResponse)
async def rephrase_selection(
    project_id: str,
    request: AIRephraseRequest,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Provide rephrasing suggestions for the selected text within its context.
    """
    try:
        logger.info(f"Received rephrase request for project {project_id}. Context Path: {request.context_path}")
        suggestions = await ai_service.rephrase_text(
            project_id=project_id,
            text_to_rephrase=request.text_to_rephrase,
            context_before=request.context_before,
            context_after=request.context_after,
            context_path=request.context_path,
            n_suggestions=request.n_suggestions
        )
        logger.info(f"Successfully generated rephrasing suggestions for project {project_id}")
        return AIRephraseResponse(suggestions=suggestions)
    except FileNotFoundError as e:
        logger.warning(f"Project or context file not found during rephrase: {project_id}/{request.context_path}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' or context file not found.")
    except Exception as e:
        logger.exception(f"Error rephrasing text for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to rephrase text: {str(e)}")


@router.post("/split/chapter/{project_id}/{chapter_id}", response_model=AIChapterSplitResponse)
async def split_chapter(
    project_id: str,
    chapter_id: str,
    request_data: AIChapterSplitRequest = Body(...),
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Split provided chapter content into proposed scenes using AI.
    """
    try:
        logger.info(f"Received chapter split request for project {project_id}, chapter {chapter_id}")
        if not request_data.chapter_content:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="chapter_content cannot be empty.")

        proposed_scenes = await ai_service.split_chapter_into_scenes(
            project_id=project_id,
            chapter_id=chapter_id,
            request_data=request_data
        )
        logger.info(f"Successfully proposed scene splits for project {project_id}, chapter {chapter_id}")
        return AIChapterSplitResponse(proposed_scenes=proposed_scenes)
    except FileNotFoundError as e:
        logger.warning(f"Project or chapter not found during chapter split: {project_id}/{chapter_id}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' or Chapter '{chapter_id}' not found.")
    except ValueError as e:
         logger.warning(f"Value error during chapter split for {project_id}/{chapter_id}: {e}")
         raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.exception(f"Error splitting chapter for project {project_id}, chapter {chapter_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to split chapter: {str(e)}")


@router.post("/rebuild_index/{project_id}", response_model=RebuildIndexResponse)
async def rebuild_index(
    project_id: str,
    ai_service: AIService = Depends(get_ai_service)
):
    """
    Force a rebuild of the vector index for a specific project.
    Deletes existing project index data and re-indexes all content.
    """
    try:
        logger.info(f"Received request to rebuild index for project {project_id}")
        deleted_count, indexed_count = await ai_service.rebuild_project_index(project_id)
        logger.info(f"Successfully rebuilt index for project {project_id}. Deleted: {deleted_count}, Indexed: {indexed_count}")
        return RebuildIndexResponse(
            success=True,
            message=f"Successfully rebuilt index for project {project_id}.",
            documents_deleted=deleted_count,
            documents_indexed=indexed_count
        )
    except FileNotFoundError as e:
        logger.warning(f"Project not found during index rebuild: {project_id}. Error: {e}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project '{project_id}' not found.")
    except Exception as e:
        logger.exception(f"Error rebuilding index for project {project_id}: {e}", exc_info=True)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to rebuild index: {str(e)}")