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

from fastapi import HTTPException, status
from app.models.character import CharacterCreate, CharacterUpdate, CharacterRead, CharacterList
from app.services.file_service import file_service
from app.services.project_service import project_service
from app.models.common import generate_uuid
# No direct index_manager import needed here anymore
import logging

logger = logging.getLogger(__name__)

class CharacterService:

    # --- REMOVED internal _read_project_meta and _write_project_meta ---

    def create(self, project_id: str, character_in: CharacterCreate) -> CharacterRead:
        """Creates a new character for a project."""
        project_service.get_by_id(project_id)

        character_id = generate_uuid()
        character_path = file_service._get_character_path(project_id, character_id)

        if file_service.path_exists(character_path):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Character ID collision")

        # Create the character markdown file with description and trigger indexing
        # Pass trigger_index=True
        file_service.write_text_file(character_path, character_in.description, trigger_index=True)

        # Update project metadata using file_service
        project_metadata = file_service.read_project_metadata(project_id)
        if 'characters' not in project_metadata: project_metadata['characters'] = {}

        project_metadata['characters'][character_id] = {
            "name": character_in.name
        }
        file_service.write_project_metadata(project_id, project_metadata) # JSON, no index trigger

        return CharacterRead(
            id=character_id,
            project_id=project_id,
            name=character_in.name,
            description=character_in.description
        )

    def get_by_id(self, project_id: str, character_id: str) -> CharacterRead:
        """Gets character details and description by ID."""
        project_service.get_by_id(project_id)

        project_metadata = file_service.read_project_metadata(project_id)
        char_data = project_metadata.get('characters', {}).get(character_id)

        if not char_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character {character_id} not found in project {project_id}")

        character_path = file_service._get_character_path(project_id, character_id)
        try:
            description = file_service.read_text_file(character_path)
        except HTTPException as e:
            if e.status_code == 404:
                 logger.warning(f"Character metadata exists for {character_id} but file is missing.")
                 raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character {character_id} data missing") from e
            raise e

        return CharacterRead(
            id=character_id,
            project_id=project_id,
            name=char_data.get("name", f"Character {character_id}"),
            description=description
        )

    def get_all_for_project(self, project_id: str) -> CharacterList:
        """Lists all characters for a specific project."""
        project_service.get_by_id(project_id)

        project_metadata = file_service.read_project_metadata(project_id)
        chars_meta = project_metadata.get('characters', {})

        characters = []
        for char_id, data in chars_meta.items():
             # Basic check if file exists before adding? Optional, adds overhead. Let's skip for now.
             character_path_check = file_service._get_character_path(project_id, char_id)
             if file_service.path_exists(character_path_check):
                 characters.append(CharacterRead(
                     id=char_id,
                     project_id=project_id,
                     name=data.get("name", f"Character {char_id}"),
                     description="" # Don't include description in list view
                 ))
             else:
                 logger.warning(f"Skipping character {char_id} in list view: description file missing.")


        characters.sort(key=lambda c: c.name)
        return CharacterList(characters=characters)

    def update(self, project_id: str, character_id: str, character_in: CharacterUpdate) -> CharacterRead:
        """Updates character name or description."""
        existing_character = self.get_by_id(project_id, character_id) # checks existence

        project_metadata = file_service.read_project_metadata(project_id)
        char_data = project_metadata.get('characters', {}).get(character_id)

        if not char_data:
             logger.error(f"Character metadata inconsistency during update for {character_id}")
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character metadata inconsistency during update")

        meta_updated = False
        if character_in.name is not None and character_in.name != char_data.get("name"):
            char_data["name"] = character_in.name
            existing_character.name = character_in.name
            meta_updated = True

        if meta_updated:
            file_service.write_project_metadata(project_id, project_metadata) # JSON, no index trigger

        description_updated = False
        if character_in.description is not None and character_in.description != existing_character.description:
            character_path = file_service._get_character_path(project_id, character_id)
            # Write MD file and trigger indexing
            # Pass trigger_index=True
            file_service.write_text_file(character_path, character_in.description, trigger_index=True)
            existing_character.description = character_in.description
            description_updated = True
            # No need for separate index call here anymore

        return existing_character

    def delete(self, project_id: str, character_id: str):
        """Deletes a character."""
        # Check existence using metadata first for efficiency
        project_metadata = file_service.read_project_metadata(project_id)
        if character_id not in project_metadata.get('characters', {}):
             character_path_check = file_service._get_character_path(project_id, character_id)
             if not file_service.path_exists(character_path_check):
                  raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
             else:
                  logger.warning(f"Character {character_id} found on filesystem but not in metadata.")

        character_path = file_service._get_character_path(project_id, character_id)

        # FileService delete_file handles index deletion now
        file_service.delete_file(character_path)

        # Update project metadata (re-read to be safe in case of concurrent ops?)
        project_metadata = file_service.read_project_metadata(project_id)
        if character_id in project_metadata.get('characters', {}):
            del project_metadata['characters'][character_id]
            file_service.write_project_metadata(project_id, project_metadata) # JSON, no index
            logger.info(f"Character {character_id} removed from project metadata.")
        else:
            logger.warning(f"Character {character_id} was already missing from project metadata during delete.")


# Create a single instance
character_service = CharacterService()