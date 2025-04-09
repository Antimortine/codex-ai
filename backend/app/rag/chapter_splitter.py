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

import logging
import asyncio
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
from llama_index.core.tools import FunctionTool
from llama_index.core.agent import ReActAgent
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from pydantic import ValidationError, TypeAdapter
from fastapi import HTTPException, status

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.genai.errors import ClientError

from typing import List, Optional

from app.models.ai import ProposedScene, ProposedSceneList

logger = logging.getLogger(__name__)

ProposedSceneListAdapter = TypeAdapter(List[ProposedScene])

# --- Define a retry predicate function ---
def _is_retryable_google_api_error(exception):
    """Return True if the exception is a Google API 429 error."""
    if isinstance(exception, ClientError):
        status_code = None
        try:
            # Attempt to extract status code robustly
            if hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
                status_code = exception.response.status_code
            elif hasattr(exception, 'status_code'): # Sometimes it's directly on the exception
                 status_code = exception.status_code
            elif isinstance(exception.args, (list, tuple)) and len(exception.args) > 0:
                # Check if first arg is int status code
                if isinstance(exception.args[0], int):
                    status_code = int(exception.args[0])
                # Check if first arg is string containing status code (less reliable)
                elif isinstance(exception.args[0], str) and '429' in exception.args[0]:
                    logger.warning("Google API rate limit hit (ClientError 429 - string check). Retrying chapter split...")
                    return True
        except (ValueError, TypeError, IndexError, AttributeError):
            pass # Ignore errors during status code extraction

        if status_code == 429:
             logger.warning("Google API rate limit hit (ClientError 429). Retrying chapter split...")
             return True
    logger.debug(f"Non-retryable error encountered during chapter split: {type(exception)}")
    return False
# --- End retry predicate ---


class ChapterSplitter:
    """Handles the logic for splitting chapter text into proposed scenes using an LLM."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        if not llm: raise ValueError("ChapterSplitter requires a valid LLM instance.")
        self.llm = llm
        logger.info("ChapterSplitter initialized.")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
        retry=retry_if_exception(_is_retryable_google_api_error),
        reraise=True
    )
    async def _execute_agent_chat(self, agent, agent_input):
        """Helper function to isolate the agent call for retry logic."""
        logger.info("Running agent chat for chapter splitting...")
        return await agent.achat(agent_input)

    async def split(
        self,
        project_id: str,
        chapter_id: str,
        chapter_content: str,
        explicit_plan: str,
        explicit_synopsis: str,
        ) -> List[ProposedScene]:
        logger.info(f"ChapterSplitter: Starting split for chapter '{chapter_id}' in project '{project_id}'.")

        if not chapter_content.strip():
            logger.warning("Chapter content is empty, cannot split.")
            return []

        self._tool_result_storage = {"scenes": None}

        def save_proposed_scenes(**kwargs):
            logger.debug(f"Tool 'save_proposed_scenes' called by agent with kwargs: {kwargs}")
            proposed_scenes_data = kwargs.get("proposed_scenes")
            if proposed_scenes_data is None: raise ValueError("Tool did not receive expected 'proposed_scenes' data.")
            try:
                validated_scenes = ProposedSceneListAdapter.validate_python(proposed_scenes_data)
                self._tool_result_storage["scenes"] = validated_scenes
                confirmation_message = f"Successfully validated and stored {len(validated_scenes)} proposed scenes."
                logger.debug(f"Tool returning confirmation: '{confirmation_message}'")
                return confirmation_message
            except ValidationError as e:
                 logger.error(f"Pydantic validation failed inside tool function: {e}. Data: {proposed_scenes_data}")
                 # Provide more specific feedback to the agent
                 error_details = "; ".join([f"{err['loc'][1]}: {err['msg']}" for err in e.errors()]) if isinstance(e.errors(), list) else str(e)
                 # --- MODIFIED: Add "Error: " prefix ---
                 return f"Error: Validation failed for proposed scenes data. Details: {error_details}. Ensure each scene has 'suggested_title' (string) and 'content' (string)."
                 # --- END MODIFIED ---


        scene_list_tool = FunctionTool.from_defaults(
            fn=save_proposed_scenes,
            name="save_proposed_scenes",
            description="Saves the list of proposed scenes (title and content) extracted from chapter text.",
            fn_schema=ProposedSceneList
        )

        # --- Construct the Input for the Agent ---
        # --- MODIFIED: Added language instruction for titles ---
        agent_input = (
            f"Analyze the chapter content provided below (between <<<CHAPTER_START>>> and <<<CHAPTER_END>>>) and split it into distinct scenes. "
            f"The chapter ID is '{chapter_id}'.\n"
            "Identify scene breaks based on significant shifts in time, location, point-of-view character, topic, or the start/end of major dialogue exchanges. "
            "For each scene identified, provide a concise suggested title and the full Markdown content belonging to that scene.\n\n"
            "**IMPORTANT:** The `suggested_title` for each scene MUST be in the **same language** as the main language used in the provided chapter content.\n\n" # <-- ADDED INSTRUCTION
            "Use the provided Project Plan and Synopsis for context on the overall story.\n\n"
            f"**Project Plan:**\n```markdown\n{explicit_plan or 'Not Available'}\n```\n\n"
            f"**Project Synopsis:**\n```markdown\n{explicit_synopsis or 'Not Available'}\n```\n\n"
            f"<<<CHAPTER_START>>>\n{chapter_content}\n<<<CHAPTER_END>>>\n\n"
            "**Instruction:** Call the 'save_proposed_scenes' function with the complete list of proposed scenes. The function expects a single argument named 'proposed_scenes' which is a list of scene objects (each having 'suggested_title' and 'content'). Ensure the 'content' field contains the exact Markdown text for that segment and that the segments cover the original chapter without overlap or gaps."
        )
        # --- END MODIFIED ---


        logger.info("Initializing ReActAgent for chapter splitting...")
        try:
            agent_system_prompt = (
                 "You are an AI assistant specialized in analyzing and structuring narrative text. "
                 "Your goal is to use the available tools to process the user's request accurately. "
                 "Pay close attention to all instructions, especially regarding output format and language requirements." # Added emphasis
            )
            agent = ReActAgent.from_tools(
                tools=[scene_list_tool],
                llm=self.llm,
                verbose=True,
                system_prompt=agent_system_prompt
            )

            agent_response = await self._execute_agent_chat(agent, agent_input)
            logger.debug(f"Agent final response content: {agent_response.response}")

            if self._tool_result_storage["scenes"] is None:
                 logger.error("Agent finished but did not successfully store tool results.")
                 error_detail = "Agent failed to execute the tool correctly or store results."
                 if agent_response.response: error_detail += f" Agent response: {agent_response.response[:200]}..."
                 # Check if the tool function itself returned an error string
                 tool_outputs = [node.raw_output for node in agent_response.source_nodes if hasattr(node, 'raw_output')] if agent_response.source_nodes else [] # Check if source_nodes exists
                 if tool_outputs and isinstance(tool_outputs[0], str) and tool_outputs[0].startswith("Error:"):
                      error_detail = f"Tool execution failed: {tool_outputs[0]}"
                 # --- MODIFIED: Raise HTTPException instead of ValueError ---
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: {error_detail}")
                 # --- END MODIFIED ---

            proposed_scenes_list = self._tool_result_storage["scenes"]

            if not isinstance(proposed_scenes_list, list): raise TypeError(f"Internal error: Stored tool result has unexpected type {type(proposed_scenes_list)}.")
            if not proposed_scenes_list: return []

            concatenated_content = "".join(scene.content for scene in proposed_scenes_list)
            if len(concatenated_content.strip()) < len(chapter_content.strip()) * 0.8:
                 logger.warning(f"Concatenated content length ({len(concatenated_content)}) significantly differs from original ({len(chapter_content)}). Potential content loss during split.")

            logger.info(f"Successfully extracted and validated {len(proposed_scenes_list)} proposed scenes via ReActAgent tool call.")
            return proposed_scenes_list

        except ClientError as e:
             if _is_retryable_google_api_error(e):
                  logger.error(f"Rate limit error persisted after retries for chapter '{chapter_id}': {e}", exc_info=False)
                  # --- MODIFIED: Add "Error: " prefix ---
                  raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Error: Rate limit exceeded after multiple retries: {e}") from e
                  # --- END MODIFIED ---
             else:
                  logger.error(f"Non-retryable ClientError during chapter splitting for chapter '{chapter_id}': {e}", exc_info=True)
                  # --- MODIFIED: Add "Error: " prefix ---
                  raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: Failed to split chapter due to Google API error: {e}") from e
                  # --- END MODIFIED ---
        except Exception as e:
             logger.error(f"Error during chapter splitting via ReActAgent for chapter '{chapter_id}': {e}", exc_info=True)
             # --- MODIFIED: Add "Error: " prefix ---
             # Re-raise other exceptions as HTTP 500, ensuring the prefix
             if isinstance(e, HTTPException): # If it's already an HTTPException, ensure prefix
                 if not e.detail.startswith("Error: "):
                     e.detail = f"Error: {e.detail}"
                 raise e
             else: # Wrap other exceptions
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: Failed to split chapter due to internal processing error: {e}") from e
             # --- END MODIFIED ---
        finally:
             self._tool_result_storage = {"scenes": None}