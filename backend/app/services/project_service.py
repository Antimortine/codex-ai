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
from app.services.file_service import file_service, BASE_PROJECT_DIR # Import the instance and constant
from app.models.common import generate_uuid
import uuid # Import uuid for validation

class ProjectService:

    def create(self, project_in: ProjectCreate) -> ProjectRead:
        """Creates a new project structure and metadata."""
        project_id = generate_uuid()
        project_path = file_service._get_project_path(project_id)

        if file_service.path_exists(project_path):
            # This should be extremely rare with UUIDs, but handle just in case
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project ID collision")

        # Create directories and initial files
        file_service.setup_project_structure(project_id)

        # Store project name in metadata
        metadata_path = file_service._get_project_metadata_path(project_id)
        project_metadata = file_service.read_json_file(metadata_path) # Should be {} initially
        project_metadata['project_name'] = project_in.name
        # Add other project-level metadata if needed, e.g., creation date
        project_metadata['chapters'] = {} # Ensure chapters dict exists
        project_metadata['characters'] = {} # Ensure characters dict exists
        file_service.write_json_file(metadata_path, project_metadata)

        return ProjectRead(id=project_id, name=project_in.name)

    def get_by_id(self, project_id: str) -> ProjectRead:
        """Gets project details by ID."""
        project_path = file_service._get_project_path(project_id)
        if not file_service.path_exists(project_path) or not project_path.is_dir():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Project {project_id} not found")

        metadata_path = file_service._get_project_metadata_path(project_id)
        try:
             project_metadata = file_service.read_json_file(metadata_path)
             project_name = project_metadata.get('project_name', f"Project {project_id}") # Default name if missing
        except HTTPException as e:
             if e.status_code == 404: # Metadata file missing? Use default name
                 project_name = f"Project {project_id}"
             else:
                 raise e # Re-raise other errors

        return ProjectRead(id=project_id, name=project_name)

    def get_all(self) -> ProjectList:
        """Lists all available projects."""
        project_ids = file_service.list_subdirectories(BASE_PROJECT_DIR)
        projects = []
        for pid in project_ids:
            try:
                # Validate it looks like a UUID before trying to read? Optional.
                uuid.UUID(pid) # Raises ValueError if not a valid UUID
                project_data = self.get_by_id(pid) # Reuse get_by_id logic
                projects.append(project_data)
            except (HTTPException, ValueError) as e:
                # Log error or skip invalid directory
                print(f"Skipping invalid project directory {pid}: {e}")
                continue
        return ProjectList(projects=projects)

    def update(self, project_id: str, project_in: ProjectUpdate) -> ProjectRead:
        """Updates project details (currently only name)."""
        project_data = self.get_by_id(project_id) # Checks existence

        if project_in.name is not None and project_in.name != project_data.name:
            metadata_path = file_service._get_project_metadata_path(project_id)
            project_metadata = file_service.read_json_file(metadata_path) # Read existing
            project_metadata['project_name'] = project_in.name
            file_service.write_json_file(metadata_path, project_metadata)
            project_data.name = project_in.name # Update the name in the returned object

            # Renaming the directory is tricky and potentially risky
            # Let's skip directory renaming for now to keep it simpler.
            # The ID remains the source of truth for the path.

        return project_data # Return the updated project data

    def delete(self, project_id: str):
        """Deletes a project directory and all its contents."""
        project_path = file_service._get_project_path(project_id)
        # get_by_id checks existence and raises 404 if not found
        self.get_by_id(project_id)
        file_service.delete_directory(project_path)
        # No need to return anything specific on successful delete in service layer
        # The endpoint will return the message


# Create a single instance
project_service = ProjectService()