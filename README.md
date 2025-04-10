
# Codex AI ✍️

**Codex AI is an AI-powered assistant designed to help writers structure, develop, and write long-form creative works, leveraging large language models like Google's Gemini and the power of Retrieval-Augmented Generation (RAG) with multilingual support.**

It aims to address the challenges of maintaining coherence and context in long-form writing by providing an interactive environment where writers collaborate with an AI aware of their work-in-progress.

For more details on the system's design, see:

*   [Architecture Document](docs/architecture.md)
*   [Design Principles Document](docs/design_principles.md)

## Key Features

-   **Project Management:** Create, list, update, and delete writing projects.
-   **Hierarchical Structure:** Organize your work into **Chapters** and **Scenes** (using 1-based ordering).
-   **Content Blocks:** Manage core project documents like Plan, Synopsis, and Worldbuilding notes.
-   **Character Profiles:** Create and manage character descriptions.
-   **Markdown Editor:** Write and edit all content using a familiar Markdown format (@uiw/react-md-editor).
-   **Context-Aware Q&A:** Ask questions about your own story ("What was Character X's motivation in Chapter 2?", "Remind me of the description of Location Y?"). The AI uses the specific project's indexed content (including Plan & Synopsis) to answer, ensuring relevance and isolation between projects.
-   **AI-Powered Scene Generation:** Generate scene drafts (including title and content) based on previous scenes, plan, synopsis, retrieved context, and optional user prompts.
-   **AI-Powered Editing (Rephrase):** Get suggestions for rephrasing selected text directly within the editor.
-   **AI Chapter Splitting:** Analyze full chapter text (pasted into the UI) and receive AI-proposed scene splits with suggested titles and content.
-   **Source Node Retrieval:** API responses for AI queries include the specific text chunks (source nodes) used by the AI to generate the answer, providing transparency.
-   **RAG Integration (LlamaIndex + ChromaDB + HuggingFace):** The AI maintains awareness of project context by indexing Markdown content into a vector database (ChromaDB) using multilingual embeddings (`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`). Project-specific metadata filtering ensures the AI only retrieves context relevant to the current project during queries.
-   **Extensible Architecture:** Designed with abstractions (via LlamaIndex) to potentially support different LLMs and Vector Databases in the future.
-   **Testing:** Backend tests using `pytest`. Frontend tests using `vitest`.
-   **Markdown Export (Planned):** Compile selected Chapters or the entire manuscript into a single Markdown file.

## Technology Stack

-   **Backend:** Python, FastAPI
-   **Frontend:** React, Vite, @uiw/react-md-editor, Axios, react-router-dom
-   **AI/RAG Orchestration:** LlamaIndex
-   **LLM:** Google Gemini (via `llama-index-llms-google-genai`)
-   **Embeddings:** HuggingFace Multilingual (`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`)
-   **Vector Database:** ChromaDB (local persistence)
-   **Dependency Management (Backend):** pip-tools (`requirements.in`, `requirements.txt`)
-   **Testing (Backend):** pytest, httpx
-   **Testing (Frontend):** vitest, @testing-library/react
-   **API Communication:** REST API between Frontend and Backend
-   **Data Models & Validation:** Pydantic
-   **(Optional) Containerization:** Docker, Docker Compose (config files not yet implemented)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

-   Python 3.9+ (tested up to 3.13, but check library compatibility if using very new versions) and Pip
-   Node.js and npm (or yarn)
-   Git
-   Access to Google Generative AI API (API Key for Gemini - Paid tier recommended for reliable use)
-   **Rust Compiler:** The `tokenizers` library (a dependency) often requires Rust for building extensions. Install it via [https://rustup.rs/](https://rustup.rs/) if you encounter installation errors related to `cargo`.

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Antimortine/codex-ai.git
    cd codex-ai
    ```

2.  **Setup Backend:**
    ```bash
    cd backend
    # Create and activate a virtual environment (recommended)
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`

    # Upgrade pip and install pip-tools
    python -m pip install --upgrade pip
    pip install pip-tools

    # Compile the full requirements.txt lock file
    pip-compile requirements.in --output-file requirements.txt

    # Install all dependencies from the lock file
    pip install -r requirements.txt

    # Set up environment variables
    cp .env.example .env
    # Edit the .env file with your actual secrets (GOOGLE_API_KEY)
    nano .env # Or your preferred editor

    # Go back to root directory
    cd ..
    ```
    *(Note: The first run of `pip install -r requirements.txt` or the first time the backend starts might take longer as the embedding model is downloaded.)*

3.  **Setup Frontend:**
    ```bash
    cd frontend
    # Install Node.js dependencies
    npm install  # or yarn install
    # Go back to root directory
    cd ..
    ```

### Running the Application

1.  **Run Backend (FastAPI server):**
    ```bash
    cd backend
    # Ensure venv is active
    source venv/bin/activate # Or venv\Scripts\activate
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    # Keep this terminal running
    ```
    *(Remember to delete `backend/chroma_db` if you change embedding models or suspect index corruption).*

2.  **Run Frontend (Vite dev server):**
    ```bash
    cd frontend
    npm run dev # or yarn dev
    # Keep this terminal running
    ```

3.  **Access Codex AI:** Open your web browser and navigate to http://localhost:5173 (Vite default).

**(Optional) Using Docker Compose:**

(Instructions remain the same, assuming docker-compose.yml will be added later)

## Project Structure
```
codex-ai/  
├── backend/ # FastAPI application (Python)  
│ ├── app/ # Core application code  
│ │ ├── api/ # API endpoints (routers, deps)  
│ │ ├── core/ # Configuration (config.py)  
│ │ ├── models/ # Pydantic data models  
│ │ ├── rag/ # LlamaIndex RAG logic (IndexManager, Processors, Engine)  
│ │ ├── services/ # Business logic (FileService, CRUD, AIService)  
│ │ └── main.py # FastAPI entry point  
│ ├── tests/ # Backend tests (pytest)  
│ ├── chroma_db/ # Local vector store data (added by .gitignore)  
│ ├── user_projects/ # User's project data (added by .gitignore)  
│ ├── .env # Local environment variables (added by .gitignore)  
│ ├── .env.example  
│ ├── requirements.in # Direct backend dependencies  
│ └── requirements.txt # Locked backend dependencies (generated)  
├── frontend/ # React application (JavaScript/JSX)  
│ ├── public/  
│ ├── src/ # Source code  
│ │ ├── api/ # API client (codexApi.js)  
│ │ ├── components/ # Reusable UI components  
│ │ ├── layouts/ # Main layout structure  
│ │ ├── pages/ # Page components  
│ │ ├── App.jsx  
│ │ ├── App.css  
│ │ └── index.jsx # Entry point  
│ ├── .env.example # Optional frontend env vars  
│ ├── index.html  
│ └── package.json  
├── docs/ # Project documentation  
│ ├── architecture.md  
│ └── design_principles.md  
├── scripts/ # Utility scripts (inspect_chroma.py, etc.)  
├── .gitignore  
└── README.md
```

## Known Issues

*   **Scene Order Conflict:** When creating a scene from an AI draft immediately after deleting another scene, the frontend might calculate an incorrect `nextOrder` value, potentially leading to a "Scene order X already exists" error from the backend upon saving. (Workaround: Update page).
*   **Rate Limiting (Free Tier):** While backend retry logic exists, the free tier of the Google Gemini API has strict limits (Requests Per Minute and Daily). Heavy use of AI features (Generation, Splitting, Query, Rephrase) may still hit these limits, resulting in temporary unavailability errors (HTTP 429). Using a paid plan (or free credits) is recommended for reliable usage.

## Roadmap

*   **AI-Powered Editing:** Implement more features (Summarize, Expand, Tone Change) using the `AIEditorWrapper`.
*   **Testing:** Expand backend test coverage (services, RAG components). Add frontend tests for cooldowns and specific modal interactions.
*   **UI/UX Refinements:** Improve the "Split Chapter" modal display and interaction. Provide clearer visual feedback during AI operations and cooldowns. Address `SuggestionPopup` limitations. Fix the scene order calculation bug when creating from AI draft.
*   **Configuration:** Move more hardcoded values (e.g., RAG parameters, cooldown durations) to configuration/settings.
*   **Refactoring:** Address deprecation warnings (e.g., FastAPI lifespan events). Consider `PromptBuilder` abstraction if prompt logic grows complex.
*   **Deployment Strategy:** Define and implement deployment (e.g., Docker).
*   **(Future)** Integration with additional LLM providers/Vector DBs.
*   **(Future)** Markdown Export feature.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the [Apache License, Version 2.0](LICENSE).

## Author / Contact

Codex AI is developed and maintained by Antimortine.

-   **Email:** [antimortine@gmail.com](mailto:antimortine@gmail.com)
-   **Telegram:** [https://t.me/antimortine](https://t.me/antimortine)
-   **GitHub:** [https://github.com/Antimortine](https://github.com/Antimortine)

