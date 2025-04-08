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
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from pydantic import ValidationError # Import for validation errors

from typing import List, Optional

# Import the response model structure we expect to return and the tool argument model
from app.models.ai import ProposedScene, ProposedSceneList

logger = logging.getLogger(__name__)

class ChapterSplitter:
    """Handles the logic for splitting chapter text into proposed scenes using an LLM."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        """
        Initializes the ChapterSplitter.

        Args:
            index: The loaded VectorStoreIndex instance (may not be needed initially).
            llm: The configured LLM instance.
        """
        if not llm:
             raise ValueError("ChapterSplitter requires a valid LLM instance.")
        # self.index = index # Keep if RAG context might be useful later
        self.llm = llm
        logger.info("ChapterSplitter initialized.")

    async def split(
        self,
        project_id: str,
        chapter_id: str,
        chapter_content: str,
        explicit_plan: str,
        explicit_synopsis: str,
        # Add optional hint from request_data if needed later
        ) -> List[ProposedScene]:
        """
        Uses the LLM with Function Calling/Tools to split the chapter content into scenes.

        Args:
            project_id: The ID of the project.
            chapter_id: The ID of the chapter being split.
            chapter_content: The full Markdown content of the chapter.
            explicit_plan: The loaded content of the project plan.
            explicit_synopsis: The loaded content of the project synopsis.

        Returns:
            A list of ProposedScene objects.
            Raises exceptions on LLM or parsing failure.
        """
        logger.info(f"ChapterSplitter: Starting split for chapter '{chapter_id}' in project '{project_id}'.")

        if not chapter_content.strip():
            logger.warning("Chapter content is empty, cannot split.")
            return []

        # --- Define the Tool ---
        def save_proposed_scenes(scenes: ProposedSceneList):
            """
            Receives the list of proposed scenes identified by the AI from the chapter content.
            Use this function to structure the output. Each scene should have a suggested_title and the corresponding content chunk.
            """
            return scenes

        scene_list_tool = FunctionTool.from_defaults(
            fn=save_proposed_scenes,
            name="save_proposed_scenes",
            description="Saves the list of proposed scenes extracted from the chapter text, including a suggested title and the content for each scene.",
            fn_schema=ProposedSceneList # Use the Pydantic model defining the list argument
        )

        # --- Construct the Prompt ---
        system_prompt = (
            "You are an AI assistant specialized in analyzing and structuring narrative text for creative writing projects. "
            "Your task is to read the provided chapter content, identify logical scene breaks, "
            "suggest a concise title for each scene, and return the list of scenes using the available tool."
        )

        user_message = (
            f"Please analyze the following chapter content (from chapter ID '{chapter_id}') and split it into distinct scenes. "
            "Identify scene breaks based on significant shifts in time, location, point-of-view character, topic, or the start/end of major dialogue exchanges. "
            "For each scene identified, provide a concise suggested title (less than 50 characters) and the full Markdown content belonging to that scene.\n\n"
            "Use the provided Project Plan and Synopsis for context on the overall story.\n\n"
            f"**Project Plan:**\n```markdown\n{explicit_plan or 'Not Available'}\n```\n\n"
            f"**Project Synopsis:**\n```markdown\n{explicit_synopsis or 'Not Available'}\n```\n\n"
            f"**Full Chapter Content to Split:**\n```markdown\n{chapter_content}\n```\n\n"
            "**Instruction:** Call the 'save_proposed_scenes' function with the complete list of proposed scenes (each having 'suggested_title' and 'content'). Ensure the 'content' field for each scene contains the exact, unmodified Markdown text for that segment. Make sure the content chunks cover the entire original chapter content without overlap or gaps."
        )

        # --- Call LLM with Tool ---
        logger.info("Calling LLM with tool for chapter splitting...")
        try:
            chat_response = await self.llm.chat(
                messages=[
                    ChatMessage(role=MessageRole.SYSTEM, content=system_prompt),
                    ChatMessage(role=MessageRole.USER, content=user_message),
                ],
                tools=[scene_list_tool],
                # Force the model to use the tool - this increases reliability
                tool_choice={"type": "function", "function": {"name": "save_proposed_scenes"}}
            )

            logger.debug(f"LLM chat response received: {chat_response}")

            # --- Process Tool Result ---
            ai_message = chat_response.message
            # --- MODIFIED: Extract tool_calls from additional_kwargs ---
            tool_calls = ai_message.additional_kwargs.get("tool_calls", [])
            # --- END MODIFIED ---

            if not tool_calls:
                logger.error(f"LLM did not call the expected tool 'save_proposed_scenes'. Response content: {ai_message.content}")
                raise ValueError("LLM failed to call the required tool to save proposed scenes.")

            # --- MODIFIED: Handle potential non-list or non-dict tool_calls if necessary ---
            # Ensure tool_calls is a list and contains dict-like objects before proceeding
            if not isinstance(tool_calls, list) or not tool_calls:
                 logger.error(f"Expected 'tool_calls' in additional_kwargs to be a non-empty list, but got: {tool_calls}")
                 raise ValueError("LLM response format for tool calls is unexpected.")
            # --- END MODIFIED ---

            # Assuming the first tool call is the one we want and it's dict-like
            # LlamaIndex might return actual ToolCall objects or dicts depending on version/wrapper
            # Let's access attributes using .get() for safety if it's a dict, or direct access if object
            tool_call_data = tool_calls[0]

            # --- MODIFIED: Access tool_name and tool_arguments safely ---
            tool_name = getattr(tool_call_data, 'tool_name', tool_call_data.get('name') if isinstance(tool_call_data, dict) else None) # Adjust based on actual object type if needed
            tool_arguments = getattr(tool_call_data, 'tool_arguments', tool_call_data.get('arguments') if isinstance(tool_call_data, dict) else None) # Adjust based on actual object type if needed

            if tool_name != "save_proposed_scenes":
                 logger.error(f"LLM called unexpected tool: {tool_name}")
                 raise ValueError(f"LLM called unexpected tool: {tool_name}")

            if tool_arguments is None:
                 logger.error("Extracted tool arguments are None.")
                 raise ValueError("Could not extract arguments from the tool call.")
            # --- END MODIFIED ---

            logger.debug(f"Extracted tool arguments: {tool_arguments}")

            # Validate and extract the list using the Pydantic model
            try:
                # Ensure tool_arguments is a dict before validation
                if not isinstance(tool_arguments, dict):
                     raise TypeError(f"Expected tool_arguments to be a dict, got {type(tool_arguments)}")
                validated_args = ProposedSceneList.model_validate(tool_arguments)
                proposed_scenes_list = validated_args.proposed_scenes
            except (ValidationError, TypeError) as e: # Catch TypeError too
                 logger.error(f"LLM tool arguments failed Pydantic validation or type check: {e}. Arguments: {tool_arguments}")
                 raise ValueError(f"LLM returned data in an unexpected format: {e}") from e

            if not proposed_scenes_list:
                 logger.warning("LLM tool call arguments were valid but contained an empty list of proposed scenes.")
                 return []

            # --- Basic Content Validation (Optional but Recommended) ---
            concatenated_content = "".join(scene.content for scene in proposed_scenes_list)
            if len(concatenated_content.strip()) < len(chapter_content.strip()) * 0.8: # Allow some minor LLM trimming/whitespace changes
                 logger.warning(f"Concatenated content length ({len(concatenated_content)}) significantly differs from original ({len(chapter_content)}). Potential content loss during split.")

            logger.info(f"Successfully extracted and validated {len(proposed_scenes_list)} proposed scenes from LLM tool call.")
            return proposed_scenes_list

        except Exception as e:
            logger.error(f"Error during chapter splitting LLM call or parsing for chapter '{chapter_id}': {e}", exc_info=True)
            # Re-raise or wrap in a specific exception type if needed
            raise RuntimeError(f"Failed to split chapter due to LLM or processing error: {e}") from e