
# Backend Testing Notes & Troubleshooting

This document outlines common issues encountered during backend testing with `pytest`, FastAPI, and `unittest.mock`, along with their solutions.

## 1. Mocking FastAPI Dependencies (`dependency_overrides`)

### Symptom

Running API tests (`tests/api/...`) results in a `NameError` within the dependency override fixture:

```python
# tests/api/v1/endpoints/test_some_api.py
...
@pytest.fixture(autouse=True)
def override_some_dependency():
    def mock_get_some_dependency_override(...):
        # ... mock logic ...
        pass

    # ERROR occurs on the next line:
    app.dependency_overrides[get_some_dependency] = mock_get_some_dependency_override
    yield
    app.dependency_overrides = {}
...
```

```
E       NameError: name 'get_some_dependency' is not defined
```

### Cause

The actual dependency function (e.g., get_some_dependency) that you are trying to override was not imported into the test file (test_some_api.py in the example). The app.dependency_overrides dictionary requires the actual function object as the key.

### Solution

Import the original dependency function from its source module into your API test file.
```python
# tests/api/v1/endpoints/test_some_api.py
import pytest
from fastapi.testclient import TestClient
from app.main import app
# --- Import the actual dependency function ---
from app.api.v1.endpoints.some_endpoint import get_some_dependency
# --- End Import ---

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_some_dependency():
    def mock_get_some_dependency_override(...):
        # ... mock logic ...
        pass

    # Now 'get_some_dependency' is defined and can be used as the key
    app.dependency_overrides[get_some_dependency] = mock_get_some_dependency_override
    yield
    app.dependency_overrides = {}

# ... rest of the tests ...
```

## 2. unittest.mock Call Assertion Errors

### Symptom

Tests using mock.assert_called_with(...) or mock.assert_called_once_with(...) fail with an AssertionError indicating the expected call was not found, even though the mock seems to have been called. The error message often shows a difference between positional and keyword arguments:
```
E           AssertionError: expected call not found.
E           Expected: read_project_metadata('proj_details_char')
E             Actual: read_project_metadata(project_id='proj_details_char')
```

### Cause

The code being tested calls the mocked function using keyword arguments (e.g., service.read_project_metadata(project_id='abc')), but the test assertion expects positional arguments (e.g., mock_service.read_project_metadata.assert_called_once_with('abc')). The unittest.mock library treats these as different call signatures.

This can also happen in reverse (code uses positional, test expects keyword).

### Solution

Ensure the arguments in your assert_called_with or assert_called_once_with call **exactly match** the way the function is called in the code under test, including the use of positional vs. keyword arguments.

**Example Fix:**
```python
# In the test file:
# Change this:
# mock_service.read_project_metadata.assert_called_once_with(project_id)

# To this (if the code calls it using keyword args):
mock_service.read_project_metadata.assert_called_once_with(project_id=project_id)

# Or to this (if the code calls it using positional args):
# mock_service.read_project_metadata.assert_called_once_with(project_id)
```

Also, be mindful when mocking methods using side_effect with lambdas. A simple lambda x: ... only accepts positional arguments. If the code calls the mocked method with keyword arguments, the lambda needs to be defined to accept them (e.g., lambda project_id: ... or lambda **kwargs: ...) or use a regular def function for the side effect.

## 3. Persistent Test Failures Despite Code Fixes

### Symptom

A test continues to fail with an assertion error (or other error) even after you are sure you have corrected the underlying code or the test assertion itself. The failure might seem related to an older version of the code or test.

### Cause

-   **Duplicate Test Files:** There might be multiple test files testing the same code module (e.g., having both tests/services/test_file_service.py and tests/rag/test_file_service.py). The test runner might be executing the uncorrected version from the duplicate file, leading to persistent failures.
    
-   **Stale Cache:** Less commonly, pytest or Python bytecode caches (__pycache__) might be stale.
    

### Solution

1.  **Check for Duplicate Test Files:** Carefully examine your tests/ directory structure. Ensure that code modules are only tested by files in the logically corresponding test directory (e.g., app/services/some_service.py should only be tested by tests/services/test_some_service.py). Delete any redundant test files.
    
2.  **Clear Caches (If Necessary):**
    
    -   Delete __pycache__ directories: find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf (Use with caution on Linux/macOS) or manually delete them.
        
    -   Clear the pytest cache: pytest --cache-clear
        

Removing duplicate test files is the most common fix for this type of issue in this project's context.
