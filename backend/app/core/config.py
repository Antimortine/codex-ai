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

from pydantic_settings import BaseSettings
import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv() # Loads variables from .env file

# --- Define BASE_PROJECT_DIR here ---
BASE_PROJECT_DIR: Path = Path(os.getenv("BASE_PROJECT_DIR", "user_projects"))

class Settings(BaseSettings):
    PROJECT_NAME: str = "Codex AI"
    API_V1_STR: str = "/api/v1"
    GOOGLE_API_KEY: str = os.getenv("GOOGLE_API_KEY")

    # --- RAG Configuration ---
    RAG_QUERY_SIMILARITY_TOP_K: int = int(os.getenv("RAG_QUERY_SIMILARITY_TOP_K", 3))
    RAG_GENERATION_SIMILARITY_TOP_K: int = int(os.getenv("RAG_GENERATION_SIMILARITY_TOP_K", 5))
    RAG_REPHRASE_SUGGESTION_COUNT: int = int(os.getenv("RAG_REPHRASE_SUGGESTION_COUNT", 3))
    # New: Number of preceding scenes to load for generation context
    RAG_GENERATION_PREVIOUS_SCENE_COUNT: int = int(os.getenv("RAG_GENERATION_PREVIOUS_SCENE_COUNT", 1))


settings = Settings()

# --- Ensure the base directory exists on startup ---
try:
    BASE_PROJECT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ensured base project directory exists: {BASE_PROJECT_DIR.resolve()}")
except OSError as e:
    print(f"ERROR: Could not create base project directory {BASE_PROJECT_DIR}: {e}")