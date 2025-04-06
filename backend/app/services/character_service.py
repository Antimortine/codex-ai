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
from app.services.project_service import project_service # To check project existence
from app.models.common import generate_uuid
from app.rag.index_manager import index_manager # Import the index manager

class CharacterService:

    # Use the same helper methods as ChapterService for project meta
    def _read_project_meta(self, project_id: str) -> dict:
        """Reads project metadata."""
        metadata_path = file_service._get_project_metadata_path(project_id)
        try:
            return file_service.read_json_file(metadata_path)
        except HTTPException as e:
             if e.status_code == 404:
                 print(f"Warning: Project metadata file not found for existing project {project_id}")
                 # Ensure default structure includes characters key
                 return {"project_name": f"Project {project_id}", "chapters": {}, "characters": {}}
             raise e

    def _write_project_meta(self, project_id: str, metadata: dict):
        """Writes project metadata."""
        metadata_path = file_service._get_project_metadata_path(project_id)
        file_service.write_json_file(metadata_path, metadata)

    def create(self, project_id: str, character_in: CharacterCreate) -> CharacterRead:
        """Creates a new character for a project."""
        # Ensure project exists
        project_service.get_by_id(project_id)

        character_id = generate_uuid()
        character_path = file_service._get_character_path(project_id, character_id)

        if file_service.path_exists(character_path):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Character ID collision")

        # Create the character markdown file with description
        file_service.write_text_file(character_path, character_in.description)

        # --- Index the new character description ---
        try:
            print(f"Indexing new character: {character_path}")
            index_manager.index_file(character_path)
        except Exception as e:
            print(f"ERROR: Failed to index new character {character_id}: {e}")
            # Warn and continue

        # Update project metadata (AFTER file write and indexing attempt)
        project_metadata = self._read_project_meta(project_id)
        if 'characters' not in project_metadata: project_metadata['characters'] = {}

        # Optional: Check for duplicate names? Depends on requirements.
        # ... (duplicate name check logic if needed) ...

        project_metadata['characters'][character_id] = {
            "name": character_in.name
        }
        self._write_project_meta(project_id, project_metadata)

        return CharacterRead(
            id=character_id,
            project_id=project_id,
            name=character_in.name,
            description=character_in.description
        )

    def get_by_id(self, project_id: str, character_id: str) -> CharacterRead:
        """Gets character details and description by ID."""
        # Ensure project exists
        project_service.get_by_id(project_id)

        project_metadata = self._read_project_meta(project_id)
        char_data = project_metadata.get('characters', {}).get(character_id)

        if not char_data:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Character {character_id} not found in project {project_id}")

        # Read description from file
        character_path = file_service._get_character_path(project_id, character_id)
        try:
            description = file_service.read_text_file(character_path)
        except HTTPException as e:
            if e.status_code == 404:
                 print(f"Warning: Character metadata exists for {character_id} but file is missing.")
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
        # Ensure project exists
        project_service.get_by_id(project_id)

        project_metadata = self._read_project_meta(project_id)
        chars_meta = project_metadata.get('characters', {})

        characters = []
        # Read description for list view? Let's keep it consistent with scenes and NOT read file here.
        for char_id, data in chars_meta.items():
             # Only return metadata available info for list view
             characters.append(CharacterRead(
                 id=char_id,
                 project_id=project_id,
                 name=data.get("name", f"Character {char_id}"),
                 description="" # Don't include description in list view
             ))

        # Sort characters by name (optional)
        characters.sort(key=lambda c: c.name)

        return CharacterList(characters=characters)

    def update(self, project_id: str, character_id: str, character_in: CharacterUpdate) -> CharacterRead:
        """Updates character name or description."""
        # Ensure character exists (reads current data)
        existing_character = self.get_by_id(project_id, character_id)

        project_metadata = self._read_project_meta(project_id)
        char_data = project_metadata.get('characters', {}).get(character_id)

        if not char_data:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character metadata inconsistency during update")

        meta_updated = False
        if character_in.name is not None and character_in.name != char_data.get("name"):
            # Optional: Check for duplicate names on update?
            char_data["name"] = character_in.name
            existing_character.name = character_in.name # Update the object we will return
            meta_updated = True

        if meta_updated:
            self._write_project_meta(project_id, project_metadata)

        # Update description if provided and different
        description_updated = False
        if character_in.description is not None and character_in.description != existing_character.description:
            character_path = file_service._get_character_path(project_id, character_id)
            file_service.write_text_file(character_path, character_in.description)
            existing_character.description = character_in.description # Update returned object
            description_updated = True # Flag that description changed

            # --- Trigger Re-indexing ONLY if description changed ---
            try:
                print(f"Description updated for character {character_id}, re-indexing...")
                index_manager.index_file(character_path) # Index the updated description
            except Exception as e:
                print(f"ERROR: Failed to re-index updated character {character_id}: {e}")
                # Warn and continue

        return existing_character

    def delete(self, project_id: str, character_id: str):
        """Deletes a character."""
        # Check existence using metadata first for efficiency
        project_metadata = self._read_project_meta(project_id)
        if character_id not in project_metadata.get('characters', {}):
             # If not in meta, check if file exists just in case of inconsistency
             character_path_check = file_service._get_character_path(project_id, character_id)
             if not file_service.path_exists(character_path_check):
                  raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Character not found")
             else:
                  print(f"Warning: Character {character_id} found on filesystem but not in metadata.")
                  # Proceed to delete file and attempt index deletion

        character_path = file_service._get_character_path(project_id, character_id)

        # --- Trigger Deletion from Index FIRST ---
        try:
            print(f"Attempting deletion from index for character: {character_path}")
            index_manager.delete_doc(character_path)
        except Exception as e:
            # Log error but proceed with file/meta deletion
            print(f"Warning: Error deleting character {character_id} from index: {e}")

        # Delete the markdown file if it exists
        if file_service.path_exists(character_path):
            try:
                file_service.delete_file(character_path)
            except HTTPException as e:
                 print(f"Warning: Character file {character_path.name} found but failed to delete: {e.detail}")
                 if e.status_code != 404: raise e # Re-raise if not already deleted
        else:
             print(f"Info: Character file {character_path.name} was already deleted.")

        # Update project metadata (re-read to be safe)
        project_metadata = self._read_project_meta(project_id)
        if character_id in project_metadata.get('characters', {}):
            del project_metadata['characters'][character_id]
            self._write_project_meta(project_id, project_metadata)
        else:
             print(f"Info: Character {character_id} was already missing from project metadata during delete.")


# Create a single instance
character_service = CharacterService()