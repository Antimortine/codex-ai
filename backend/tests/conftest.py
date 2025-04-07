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

import pytest
from pathlib import Path
import sys
import os

# Add the project root to the Python path to allow imports like `from app.services...`
project_root = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(project_root))

# Fixture to provide a temporary directory for tests that interact with the filesystem
@pytest.fixture(scope="function") # 'function' scope means a new temp dir for each test function
def temp_project_dir(tmp_path: Path) -> Path:
    """
    Creates a temporary directory mimicking the BASE_PROJECT_DIR structure
    for isolated testing of file operations.
    """
    # tmp_path is a built-in pytest fixture providing a temporary directory unique to each test function
    test_dir = tmp_path / "user_projects_test"
    test_dir.mkdir()
    print(f"Created temporary test directory: {test_dir}")
    return test_dir

# You can add more fixtures here later, e.g., for creating a TestClient instance
# or mocking external services.