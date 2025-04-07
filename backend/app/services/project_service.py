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
from app.models.project import ProjectCreate, ProjectUpdate, ProjectRead, ProjectList
from app.services.file_service import file_service, BASE_PROJECT_DIR
from app.models.common import generate_uuid
import uuid # Import uuid for validation
import logging # Import logging

logger = logging.getLogger(__name__) # Get logger for this module

class ProjectService:

    def create(self, project_in: ProjectCreate) -> ProjectRead:
        """Creates a new project structure and metadata."""
        project_id = generate_uuid()
        project_path = file_service._get_project_path(project_id)
        logger.info(f"Attempting to create project '{project_in.name}' with ID {project_id} at path {project_path}")

        if file_service.path_exists(project_path):
            # This should be extremely rare with UUIDs, but handle just in case
            logger.error(f"Project ID collision for {project_id}")
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project ID collision")

        # Create directories and initial files (including indexing initial content blocks)
        logger.debug(f"Setting up project structure for {project_id}")
        file_service.setup_project_structure(project_id)
        logger.debug(f"Project structure setup complete for {project_id}")

        # Store project name in metadata
        metadata_path = file_service._get_project_metadata_path(project_id)
        # Read metadata (should exist now after setup_project_structure)
        logger.debug(f"Reading metadata file {metadata_path} to add project name")
        project_metadata = file_service.read_json_file(metadata_path)
        project_metadata['project_name'] = project_in.name
        # Ensure these keys exist if setup didn't guarantee it
        if 'chapters' not in project_metadata: project_metadata['chapters'] = {}
        if 'characters' not in project_metadata: project_metadata['characters'] = {}
        logger.debug(f"Writing updated metadata for {project_id}")
        file_service.write_json_file(metadata_path, project_metadata)

        logger.info(f"Project {project_id} created successfully.")
        return ProjectRead(id=project_id, name=project_in.name)

    def get_by_id(self, project_id: str) -> ProjectRead:
        """Gets project details by ID."""
        logger.debug(f"Attempting to get project by ID: {project_id}")
        project_path = file_service._get_project_path(project_id)
        if not file_service.path_exists(project_path) or not project_path.is_dir():
            logger.warning(f"Project directory not found for ID: {project_id} at path {project_path}")
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

        metadata_path = file_service._get_project_metadata_path(project_id)
        try:
             logger.debug(f"Reading project metadata from {metadata_path}")
             project_metadata = file_service.read_json_file(metadata_path)
             project_name = project_metadata.get('project_name', f"Project {project_id}") # Default name if missing
             logger.debug(f"Found project name '{project_name}' for ID {project_id}")
        except HTTPException as e:
             if e.status_code == 404: # Metadata file missing? Use default name
                 project_name = f"Project {project_id}"
                 logger.warning(f"Project metadata file missing for {project_id}, using default name.")
             else:
                 logger.error(f"Error reading metadata for project {project_id}: {e.detail}", exc_info=True)
                 raise e # Re-raise other errors

        return ProjectRead(id=project_id, name=project_name)

    def get_all(self) -> ProjectList:
        """Lists all available projects."""
        logger.info(f"Attempting to list all projects in {BASE_PROJECT_DIR}")
        projects = []
        try:
            project_ids = file_service.list_subdirectories(BASE_PROJECT_DIR)
            logger.debug(f"Found potential project directories: {project_ids}")
            for pid in project_ids:
                logger.debug(f"Processing potential project directory: {pid}")
                try:
                    # Validate it looks like a UUID before trying to read
                    uuid.UUID(pid) # Raises ValueError if not a valid UUID
                    logger.debug(f"Directory name '{pid}' is a valid UUID format.")
                    project_data = self.get_by_id(pid) # Reuse get_by_id logic
                    projects.append(project_data)
                    logger.debug(f"Successfully added project {pid} to list.")
                except ValueError:
                    logger.warning(f"Skipping directory '{pid}': Name is not a valid UUID.")
                    continue
                except HTTPException as e:
                    # Log error if get_by_id fails (e.g., dir exists but metadata missing)
                    logger.warning(f"Skipping directory '{pid}': Error during get_by_id - {e.status_code} {e.detail}")
                    continue
                except Exception as e:
                    # Catch any other unexpected errors during processing of one directory
                    logger.error(f"Skipping directory '{pid}': Unexpected error - {e}", exc_info=True)
                    continue
            logger.info(f"Finished listing projects. Found {len(projects)} valid projects.")
            return ProjectList(projects=projects)
        except Exception as e:
            # Catch errors during the initial listing of subdirectories
            logger.error(f"Failed to list subdirectories in {BASE_PROJECT_DIR}: {e}", exc_info=True)
            # Return empty list or raise, depending on desired behavior
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Error reading project directory: {e}")


    def update(self, project_id: str, project_in: ProjectUpdate) -> ProjectRead:
        """Updates project details (currently only name)."""
        logger.info(f"Attempting to update project {project_id}")
        project_data = self.get_by_id(project_id) # Checks existence

        if project_in.name is not None and project_in.name != project_data.name:
            logger.info(f"Updating project {project_id} name to '{project_in.name}'")
            metadata_path = file_service._get_project_metadata_path(project_id)
            # Read existing metadata, handling potential 404 if inconsistent
            try:
                project_metadata = file_service.read_json_file(metadata_path)
            except HTTPException as e:
                 if e.status_code == 404:
                      logger.warning(f"Project metadata file missing during update for {project_id}. Creating new metadata.")
                      project_metadata = {} # Start fresh if missing
                 else: raise e

            project_metadata['project_name'] = project_in.name
            file_service.write_json_file(metadata_path, project_metadata)
            project_data.name = project_in.name # Update the name in the returned object
            logger.info(f"Project {project_id} name updated successfully.")

            # Note: Project name update does NOT require re-indexing anything,
            # as only content files (scenes, characters, plan etc.) are indexed.
        else:
            logger.info(f"No name change requested or name is the same for project {project_id}.")

        return project_data # Return the updated project data

    def delete(self, project_id: str):
        """Deletes a project directory and all its contents, including index cleanup."""
        logger.info(f"Attempting to delete project {project_id}")
        project_path = file_service._get_project_path(project_id)
        # get_by_id checks existence and raises 404 if not found
        self.get_by_id(project_id)

        # --- Call the enhanced delete_directory ---
        # This method in FileService now handles deleting docs from the index
        # *before* removing the directory structure.
        logger.info(f"Calling file_service.delete_directory for: {project_path}")
        file_service.delete_directory(project_path)
        logger.info(f"Project {project_id} deleted successfully.")
        # No need to return anything specific on successful delete in service layer


# Create a single instance
project_service = ProjectService()