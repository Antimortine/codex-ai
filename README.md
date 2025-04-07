# Codex AI ✍️

**Codex AI is an AI-powered assistant designed to help writers structure, develop, and write long-form creative works, leveraging large language models like Google's Gemini and the power of Retrieval-Augmented Generation (RAG) with multilingual support.**

## The Problem

Writing long-form content like novels or complex narratives presents challenges in maintaining plot coherence, character consistency, and overall structure over potentially hundreds of pages. Traditional writing tools often lack the means to effectively track and utilize the vast context of an evolving story.

Codex AI aims to alleviate these challenges by providing an interactive environment where writers can collaborate with an AI that has persistent, context-aware knowledge of their work-in-progress.

## Key Features

-   **Project Management:** Create, list, update, and delete writing projects.
-   **Hierarchical Structure:** Organize your work into **Chapters** and **Scenes** (using 1-based ordering).
-   **Content Blocks:** Manage core project documents like Plan, Synopsis, and Worldbuilding notes.
-   **Character Profiles:** Create and manage character descriptions.
-   **Markdown Editor:** Write and edit all content using a familiar Markdown format (@uiw/react-md-editor).
-   **Context-Aware Q&A:** Ask questions about your own story ("What was Character X's motivation in Chapter 2?", "Remind me of the description of Location Y?"). The AI uses the specific project's indexed content (including Plan & Synopsis) to answer, ensuring relevance and isolation between projects.
-   **AI-Powered Scene Generation:** Generate scene drafts based on previous scenes, plan, synopsis, retrieved context, and optional user prompts.
-   **AI-Powered Editing (Rephrase):** Get suggestions for rephrasing selected text directly within the editor.
-   **Source Node Retrieval:** API responses for AI queries include the specific text chunks (source nodes) used by the AI to generate the answer, providing transparency.
-   **RAG Integration (LlamaIndex + ChromaDB + HuggingFace):** The AI maintains awareness of project context by indexing Markdown content into a vector database (ChromaDB) using multilingual embeddings. Project-specific metadata filtering ensures the AI only retrieves context relevant to the current project during queries.
-   **Extensible Architecture:** Designed with abstractions (via LlamaIndex) to potentially support different LLMs and Vector Databases in the future.
-   **Basic Testing:** Initial backend tests using `pytest`.
-   **Markdown Export (Planned):** Compile selected Chapters or the entire manuscript into a single Markdown file.

## Technology Stack

-   **Backend:** Python, FastAPI
-   **Frontend:** React, @uiw/react-md-editor, Axios
-   **AI/RAG Orchestration:** LlamaIndex
-   **LLM:** Google Gemini (via `llama-index-llms-google-genai`)
-   **Embeddings:** HuggingFace (`sentence-transformers/paraphrase-multilingual-mpnet-base-v2`)
-   **Vector Database:** ChromaDB (local persistence)
-   **Dependency Management (Backend):** pip-tools (`requirements.in`, `requirements.txt`)
-   **Testing (Backend):** pytest, httpx
-   **API Communication:** REST API between Frontend and Backend
-   **Data Models & Validation:** Pydantic
-   **(Optional) Containerization:** Docker, Docker Compose (config files not yet implemented)

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

-   Python 3.9+ (tested up to 3.13, but check library compatibility if using very new versions) and Pip
-   Node.js and npm (or yarn)
-   Git
-   Access to Google Generative AI API (API Key for Gemini)
-   **Rust Compiler:** The `tokenizers` library (a dependency) often requires Rust for building extensions. Install it via [https://rustup.rs/](https://rustup.rs/) if you encounter installation errors related to `cargo`.

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://your-repository-url/codex-ai.git
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

    # Check/Create requirements.in (defines direct dependencies)
    # Ensure backend/requirements.in exists and lists direct dependencies.
    # Example content (adjust versions as needed):
    # # --- Core Framework ---
    # fastapi
    # uvicorn[standard]
    # python-dotenv
    # pydantic-settings
    # # --- LlamaIndex & Dependencies ---
    # llama-index>=0.10.30
    # llama-index-llms-google-genai
    # google-generativeai>=0.5.0
    # llama-index-embeddings-huggingface
    # sentence-transformers
    # accelerate
    # torch>=2.0.0
    # transformers>=4.40.0
    # llama-index-readers-file
    # llama-index-vector-stores-chroma
    # # --- Other Dependencies ---
    # chromadb>=0.4.0
    # # --- Testing ---
    # pytest
    # httpx

    # Compile the full requirements.txt lock file
    pip-compile requirements.in --output-file requirements.txt

    # Install all dependencies from the lock file
    pip install -r requirements.txt

    # Set up environment variables
    cp .env.example .env
    # Edit the .env file with your actual secrets (e.g., GOOGLE_API_KEY)
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
    # Set up environment variables (if needed, e.g., backend API URL)
    # cp .env.example .env
    # nano .env
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

2.  **Run Frontend (React dev server):**
    ```bash
    cd frontend
    npm start # or yarn start (or `vite` if using Vite directly)
    # Keep this terminal running
    ```

3.  **Access Codex AI:** Open your web browser and navigate to http://localhost:5173 (Vite default) or http://localhost:3000 (CRA default).

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
│ │ ├── rag/ # LlamaIndex RAG logic
│ │ ├── services/ # Business logic
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
├── docs/ # Project documentation (architecture.md, design_principles.md)
├── scripts/ # Utility scripts (inspect_chroma.py, etc.)
├── .gitignore
└── README.md
```


## Roadmap

-   **AI-Powered Editing:** Implement more features (Summarize, Expand, Tone Change) using the `AIEditorWrapper`.
-   **Testing:** Expand backend test coverage (services, other API endpoints, RAG components with mocking). Add frontend tests.
-   **Prompt Engineering:** Optimize prompts sent to the LLM for better quality and control over AI responses.
-   **UI/UX:** Improve navigation, editor features, error handling display, and overall user experience. Address `SuggestionPopup` limitations.
-   **Configuration:** Move more hardcoded values (e.g., RAG parameters) to configuration/settings.
-   **Refactoring:** Address deprecation warnings (e.g., FastAPI lifespan events). Consider `PromptBuilder` abstraction.
-   **Deployment Strategy:** Define and implement deployment (e.g., Docker).
-   **(Future)** Integration with additional LLM providers/Vector DBs.
-   **(Future)** Real-time collaboration features.

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.
(Optional: Add more specific contribution guidelines or link to a CONTRIBUTING.md file)

## License

This project is licensed under the [Apache License, Version 2.0](LICENSE). *(Assuming you add a LICENSE file)*

## Author / Contact

Codex AI is developed and maintained by Antimortine.

-   **Email:** [antimortine@gmail.com](mailto:antimortine@gmail.com)
-   **Telegram:** [https://t.me/antimortine](https://t.me/antimortine)
-   **GitHub:** [https://github.com/Antimortine](https://github.com/Antimortine)