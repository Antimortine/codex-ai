# Codex AI - Software Design Principles

Based on the structure and implementation choices made for Codex AI, here are the key software design principles and patterns being utilized:

1.  **Separation of Concerns (SoC):**
    *   **Frontend/Backend Split:** Clear division between UI (React) and logic/data/AI (FastAPI).
    *   **Layered Backend Architecture:**
        *   **API Layer (`app/api/`):** Handles HTTP, routing, request/response validation (FastAPI/Pydantic).
        *   **Service Layer (`app/services/`):** Contains business logic orchestration. `AIService` loads explicit context and calls RAG processors. CRUD services call `FileService`.
        *   **RAG Subsystem (`app/rag/`):** Isolates AI-specific logic. Further divided into:
            *   `IndexManager`: Index lifecycle, setup, CUD operations, embedding generation.
            *   `QueryProcessor`: Handles RAG queries, including prompt construction with explicit context.
            *   `SceneGenerator`: Handles scene generation, including prompt construction with explicit context.
            *   `Rephraser`: Handles rephrasing logic and prompt construction.
            *   `RagEngine`: Facade simplifying access to the RAG processors from `AIService`.
        *   **Utility/Data Access Layer (`FileService`):** Centralizes file system interactions (Markdown content, JSON metadata) and triggers indexing via `IndexManager`.
    *   **Modular Routers (FastAPI):** API endpoints organized by feature (projects, chapters, ai, etc.).

2.  **API-First Design:**
    *   Defined data contracts (Pydantic models) and API signatures early, facilitating clear communication between frontend and backend. FastAPI's auto-docs reinforce this.

3.  **Dependency Injection (via FastAPI):**
    *   FastAPI manages dependencies for API endpoints (like `get_project_dependency`), promoting testability and decoupling. Manual singleton management is used for services/engines currently.

4.  **Modularity and Extensibility (via LlamaIndex Abstractions):**
    *   Using LlamaIndex's `LLM`, `VectorStore`, `BaseEmbedding` interfaces allows swapping core AI components (e.g., different LLMs, vector stores, or embedding models like the switch from Google to HuggingFace) primarily by changing configuration/adapters in `IndexManager` with relatively minimal impact on the RAG processors or `AIService`. This embodies the **Strategy Pattern** or **Adapter Pattern**.

5.  **Single Responsibility Principle (SRP) (Applied to Modules/Classes):**
    *   Each module/class aims for a focused responsibility (e.g., `projects.py` for project API, `project_service.py` for project logic, `FileService` for file ops, `IndexManager` for index CUD, specific RAG processors for specific AI tasks). The refactoring of RAG logic into specific processors strengthened this.

6.  **Don't Repeat Yourself (DRY):**
    *   Centralizing file system access and metadata I/O (`project_meta.json`, `chapter_meta.json`) within `FileService` reduces duplication across CRUD services.
    *   Path construction logic is centralized in `FileService`.
    *   Pydantic models prevent redefining data structures.
    *   *(Area for Improvement):* Prompt construction logic is currently duplicated across RAG processors; a `PromptBuilder` abstraction could improve DRY here.

7.  **Explicit Context Management (for RAG):**
    *   A core principle is ensuring AI operations are scoped to the correct project and have relevant context. This is handled by:
        *   Injecting `project_id` into document metadata during indexing (`IndexManager`).
        *   Applying `MetadataFilters` during retrieval (RAG Processors).
        *   Explicitly loading and passing key context (Plan, Synopsis, previous scenes) from `AIService` to RAG processors when needed (e.g., for Queries and Scene Generation).

8.  **Configuration Management:**
    *   `.env` files and `app/core/config.py` (using Pydantic `BaseSettings`) manage settings and secrets, separating configuration from code.

9.  **Clear Data Contracts (Pydantic):**
    *   Models define API request/response structures, providing validation and documentation. Includes models for AI requests/responses (`AIQueryRequest`, `AISceneGenerationRequest`, `AIRephraseRequest`, etc.).

10. **Reproducible Dependencies (`pip-tools`):**
    *   Using `requirements.in` to define direct dependencies and `pip-compile` to generate a locked `requirements.txt` ensures reproducible backend environments.

11. **Testability:**
    *   Initial tests using `pytest` and `TestClient` have been added for basic API validation (mocking services) and `FileService` operations (using temporary directories). Mocking is used to isolate units.

**Principles We Should Keep in Mind Going Forward:**

*   **Keep It Simple, Stupid (KISS):** Avoid over-engineering. Add complexity only when needed (e.g., deferring `PromptBuilder` until prompt logic becomes more complex or duplicated).
*   **Error Handling:** Continue refining error handling for robustness and user feedback (both API responses and logging).
*   **Testability:** Continue expanding test coverage (services, RAG components with mocking, frontend tests).
*   **Prompt Engineering:** Recognize that prompt design is crucial for RAG quality and requires dedicated effort and iteration.
*   **Scalability:** Consider potential bottlenecks (e.g., LLM API calls, vector DB performance, embedding generation time) as the application grows. FastAPI's async nature helps.
*   **Maintainability:** Refactor as needed (e.g., address deprecation warnings like FastAPI lifespan events, consider `PromptBuilder`).

Overall, the project follows standard practices for modern web applications, emphasizing separation, clear interfaces, and leveraging framework features. Recent refactoring (RAG processors, explicit context loading) and the introduction of testing and robust dependency management have strengthened the foundation.