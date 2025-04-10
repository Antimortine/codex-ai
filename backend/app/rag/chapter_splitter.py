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
import re # Import regex for parsing
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.llms import LLM
# --- REMOVED Agent/Tool Imports ---
# from llama_index.core.tools import FunctionTool
# from llama_index.core.agent import ReActAgent
# from llama_index.core.base.llms.types import ChatMessage, MessageRole
# from pydantic import ValidationError, TypeAdapter
# --- END REMOVED ---
from fastapi import HTTPException, status

from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, RetryError
from google.genai.errors import ClientError

from typing import List, Optional

# --- REMOVED ProposedSceneList Import ---
# from app.models.ai import ProposedScene, ProposedSceneList
# --- ADDED ProposedScene Import ---
from app.models.ai import ProposedScene
# --- END ADDED ---

logger = logging.getLogger(__name__)

# --- REMOVED TypeAdapter ---
# ProposedSceneListAdapter = TypeAdapter(List[ProposedScene])
# --- END REMOVED ---

# --- Define a retry predicate function (remains the same) ---
def _is_retryable_google_api_error(exception):
    """Return True if the exception is a Google API 429 error."""
    if isinstance(exception, ClientError):
        status_code = None
        try:
            if hasattr(exception, 'response') and hasattr(exception.response, 'status_code'):
                status_code = exception.response.status_code
            elif hasattr(exception, 'status_code'):
                 status_code = exception.status_code
            elif isinstance(exception.args, (list, tuple)) and len(exception.args) > 0:
                if isinstance(exception.args[0], int):
                    status_code = int(exception.args[0])
                elif isinstance(exception.args[0], str) and '429' in exception.args[0]:
                    logger.warning("Google API rate limit hit (ClientError 429 - string check). Retrying chapter split...")
                    return True
        except (ValueError, TypeError, IndexError, AttributeError):
            pass
        if status_code == 429:
             logger.warning("Google API rate limit hit (ClientError 429). Retrying chapter split...")
             return True
    logger.debug(f"Non-retryable error encountered during chapter split: {type(exception)}")
    return False
# --- End retry predicate ---


class ChapterSplitter:
    """Handles the logic for splitting chapter text into proposed scenes using a single LLM call and parsing."""

    def __init__(self, index: VectorStoreIndex, llm: LLM):
        # --- REMOVED index from constructor (not needed for splitting) ---
        if not llm: raise ValueError("ChapterSplitter requires a valid LLM instance.")
        self.llm = llm
        # --- END REMOVED ---
        logger.info("ChapterSplitter initialized.")

    # --- Use standard retry helper for llm.acomplete ---
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=5, max=30),
        retry=retry_if_exception(_is_retryable_google_api_error),
        reraise=True
    )
    async def _execute_llm_complete(self, prompt: str):
        """Helper function to isolate the LLM call for retry logic."""
        logger.info("Calling LLM acomple for chapter splitting...")
        response = await self.llm.acomplete(prompt)
        return response
    # --- END MODIFIED ---

    # --- MODIFIED: split method ---
    async def split(
        self,
        project_id: str,
        chapter_id: str,
        chapter_content: str,
        explicit_plan: str,
        explicit_synopsis: str,
        ) -> List[ProposedScene]:
        """
        Splits chapter content into proposed scenes using a single LLM call and parsing.

        Returns:
            A list of ProposedScene objects or raises HTTPException on failure.
        """
        logger.info(f"ChapterSplitter: Starting split via Single Call for chapter '{chapter_id}' in project '{project_id}'.")

        if not chapter_content.strip():
            logger.warning("Chapter content is empty, cannot split.")
            return []

        try:
            # --- 1. Build Prompt with Strict Formatting ---
            logger.debug("Building strict format prompt for chapter splitting...")
            system_prompt = (
                "You are an AI assistant specialized in analyzing and structuring narrative text. "
                "Your task is to split the provided chapter content into distinct scenes based on logical breaks "
                "(time, location, POV shifts, topic changes, dialogue starts/ends). "
                "For each scene, provide a concise title and the full Markdown content."
            )

            # Truncate context if needed (optional, but good practice)
            max_context_len = 1500
            truncated_plan = (explicit_plan or '')[:max_context_len] + ('...' if len(explicit_plan or '') > max_context_len else '')
            truncated_synopsis = (explicit_synopsis or '')[:max_context_len] + ('...' if len(explicit_synopsis or '') > max_context_len else '')

            # Define delimiters
            scene_start_delim = "<<<SCENE_START>>>"
            scene_end_delim = "<<<SCENE_END>>>"
            title_prefix = "TITLE:"
            content_prefix = "CONTENT:"

            user_message_content = (
                f"Analyze the chapter content provided below (between <<<CHAPTER_START>>> and <<<CHAPTER_END>>>) and split it into distinct scenes. "
                f"The chapter ID is '{chapter_id}'.\n\n"
                "Use the provided Project Plan and Synopsis for context on the overall story.\n\n"
                f"**Project Plan:**\n```markdown\n{truncated_plan or 'Not Available'}\n```\n\n"
                f"**Project Synopsis:**\n```markdown\n{truncated_synopsis or 'Not Available'}\n```\n\n"
                f"<<<CHAPTER_START>>>\n{chapter_content}\n<<<CHAPTER_END>>>\n\n"
                f"**Output Format Requirement:** Your response MUST consist ONLY of scene blocks. Each scene block MUST start exactly with '{scene_start_delim}' on its own line, followed by a line starting exactly with '{title_prefix} ' and the scene title, followed by a line starting exactly with '{content_prefix}', followed by the full Markdown content of the scene (which can span multiple lines), and finally end exactly with '{scene_end_delim}' on its own line. Ensure the 'content' segments cover the original chapter without overlap or gaps. The title MUST be in the same language as the main chapter content."
                f"\nExample:\n{scene_start_delim}\n{title_prefix} The Arrival\n{content_prefix}\nThe character arrived.\n{scene_end_delim}\n{scene_start_delim}\n{title_prefix} The Conversation\n{content_prefix}\nThey talked for hours.\n{scene_end_delim}"
            )
            full_prompt = f"{system_prompt}\n\nUser: {user_message_content}\n\nAssistant:"

            # --- 2. Call LLM ---
            logger.debug(f"ChapterSplitter: Prompt length: {len(full_prompt)}")
            logger.debug(f"ChapterSplitter: Calling _execute_llm_complete...")
            llm_response = await self._execute_llm_complete(full_prompt)
            generated_text = llm_response.text.strip() if llm_response else ""

            if not generated_text:
                 logger.warning("LLM returned an empty response for chapter splitting.")
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: The AI failed to propose scene splits.")

            # --- 3. Parse the Response ---
            logger.debug("Parsing LLM response for scene splits...")
            proposed_scenes = []
            # Regex to find scene blocks, capturing title and content
            # DOTALL allows '.' to match newlines within the content
            # MULTILINE allows '^' to match start of lines for delimiters/prefixes
            scene_pattern = re.compile(
                rf"^{re.escape(scene_start_delim)}\s*?\n" # Start delimiter on its own line (optional whitespace)
                rf"^{re.escape(title_prefix)}\s*(.*?)\s*?\n" # Title line, capture title
                rf"^{re.escape(content_prefix)}\s*?\n?" # Content prefix line (optional newline after)
                rf"(.*?)" # Capture content (non-greedy)
                rf"^{re.escape(scene_end_delim)}\s*?$", # End delimiter on its own line
                re.DOTALL | re.MULTILINE
            )

            matches = scene_pattern.finditer(generated_text)
            found_scenes = False
            for match in matches:
                found_scenes = True
                title = match.group(1).strip()
                content = match.group(2).strip()
                if title and content: # Basic validation
                    proposed_scenes.append(ProposedScene(suggested_title=title, content=content))
                    logger.debug(f"Parsed scene: Title='{title[:50]}...', Content Length={len(content)}")
                else:
                    logger.warning(f"Skipping partially parsed scene block: Title='{title}', Content Present={bool(content)}. Block text: {match.group(0)[:200]}...")

            if not found_scenes:
                logger.warning(f"Could not parse any scene blocks using delimiters from LLM response. Response start:\n{generated_text[:500]}...")
                # Optionally, raise an error or return empty list
                # raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error: AI response format for scene splits was invalid.")
                return [] # Return empty list if parsing fails

            # Optional: Content length validation (remains the same)
            concatenated_content = "".join(scene.content for scene in proposed_scenes)
            if len(concatenated_content.strip()) < len(chapter_content.strip()) * 0.8:
                 logger.warning(f"Concatenated split content length ({len(concatenated_content)}) significantly differs from original ({len(chapter_content)}). Potential content loss.")

            logger.info(f"Successfully parsed {len(proposed_scenes)} proposed scenes.")
            return proposed_scenes

        except ClientError as e:
             if _is_retryable_google_api_error(e):
                  logger.error(f"Rate limit error persisted after retries for chapter split: {e}", exc_info=False)
                  raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=f"Error: Rate limit exceeded after multiple retries. Please wait and try again.") from e
             else:
                  logger.error(f"Non-retryable ClientError during chapter split for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
                  raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: An unexpected error occurred while communicating with the AI service. Details: {e}") from e
        except Exception as e:
            logger.error(f"Error during chapter splitting processing for project '{project_id}', chapter '{chapter_id}': {e}", exc_info=True)
            if isinstance(e, HTTPException):
                 if not e.detail.startswith("Error: "): e.detail = f"Error: {e.detail}"
                 raise e
            else:
                 raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error: An unexpected error occurred during chapter splitting. Please check logs.") from e
    # --- END MODIFIED ---