# Codex AI ✍️

**Codex AI is an AI-powered assistant designed to help writers structure, develop, and write long-form creative works, leveraging large language models like Google's Gemini 1.5 Pro and the power of Retrieval-Augmented Generation (RAG).**

## The Problem

Writing long-form content like novels or complex narratives presents challenges in maintaining plot coherence, character consistency, and overall structure over potentially hundreds of pages. Traditional writing tools often lack the means to effectively track and utilize the vast context of an evolving story.

Codex AI aims to alleviate these challenges by providing an interactive environment where writers can collaborate with an AI that has persistent, context-aware knowledge of their work-in-progress.

## Key Features

*   **Project Management:** Create new writing projects or load existing ones.
*   **Hierarchical Structure:** Organize your work into **Chapters** and **Scenes**.
*   **Markdown Editor:** Write and edit your Plan, Synopsis, Character Profiles, Worldbuilding notes, and Scene content using a familiar Markdown format (`@uiw/react-md-editor`).
*   **AI-Powered Generation:**
    *   Generate scene drafts based on your plan, characters, and previous context.
    *   Brainstorm ideas for plot points, characters, or world details.
    *   Get help continuing or expanding existing text.
*   **AI-Powered Editing:** Refine generated or manually written text using AI suggestions (e.g., "rewrite this paragraph in a more formal tone", "make this dialogue tenser").
*   **Context-Aware Q&A:** Ask questions about your own story ("What was Character X's motivation in Chapter 2?", "Remind me of the description of Location Y?") and get answers based on the project's content.
*   **RAG Integration (LlamaIndex + ChromaDB):** The AI maintains awareness of the entire project context by indexing your Markdown content (scenes, notes) into a vector database (ChromaDB) and retrieving relevant information before generating text or answering questions. This ensures better coherence and consistency.
*   **Extensible Architecture:** Designed with abstractions (via LlamaIndex) to potentially support different LLMs (OpenAI, Anthropic, local models) and Vector Databases in the future.
*   **Markdown Export:** Compile selected Chapters or the entire manuscript into a single Markdown file.

## Technology Stack

*   **Backend:** Python, FastAPI
*   **Frontend:** React, `@uiw/react-md-editor`
*   **AI/RAG Orchestration:** LlamaIndex
*   **LLM:** Google Gemini 1.5 Pro (via Google Generative AI API)
*   **Embeddings:** Google `text-embedding-004`
*   **Vector Database:** ChromaDB (initially, designed to be replaceable)
*   **API Communication:** REST API between Frontend and Backend
*   **(Optional) Containerization:** Docker, Docker Compose

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

*   Python 3.9+ and Pip
*   Node.js and npm (or yarn)
*   Git
*   Access to Google Generative AI API (API Key for Gemini and Embeddings)

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
    # Install Python dependencies
    pip install -r requirements.txt
    # Set up environment variables
    cp .env.example .env
    # Edit the .env file with your actual secrets (e.g., GOOGLE_API_KEY)
    nano .env # Or your preferred editor
    # Go back to root directory
    cd ..
    ```

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
    uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
    # Keep this terminal running
    ```

2.  **Run Frontend (React dev server):**
    ```bash
    cd frontend
    npm start # or yarn start
    # Keep this terminal running
    ```

3.  **Access Codex AI:** Open your web browser and navigate to `http://localhost:3000` (or the port specified by React).

**(Optional) Using Docker Compose:**

If a `docker-compose.yml` file is provided in the root directory:

```bash
# Make sure you have Docker and Docker Compose installed
# Ensure your backend/.env file is configured correctly
docker-compose up --build
```

This command should build the necessary images and start both the backend and frontend services. Access the application via the frontend port defined in the Docker Compose configuration (likely http://localhost:3000).

## Project Structure

```
codex-ai/
├── backend/        # FastAPI application (Python)
│   ├── app/        # Core application code
│   │   ├── api/    # API endpoints (routers)
│   │   ├── core/   # Configuration
│   │   ├── models/ # Pydantic data models
│   │   ├── rag/    # LlamaIndex RAG logic
│   │   ├── services/ # Business logic
│   │   └── main.py # FastAPI entry point
│   ├── tests/      # Backend tests
│   └── requirements.txt
├── frontend/       # React application (JavaScript/TypeScript)
│   ├── src/        # Source code
│   └── package.json
├── data/           # Example data (NOT user project data)
├── docs/           # Project documentation
├── scripts/        # Utility scripts
├── .gitignore
└── README.md
```

(Note: User-generated project data and local vector stores like ChromaDB files are stored outside the repository, typically configured via environment variables or application settings, and should be added to .gitignore)

## Roadmap

-   Enhanced UI/UX for managing complex narratives.
-   Integration with additional LLM providers (OpenAI, Anthropic).
-   Support for alternative Vector Databases (Weaviate, Pinecone).
-   More sophisticated RAG strategies (HyDE, Re-ranking, etc.).
-   Real-time collaboration features (optional).
-   Improved Markdown editor features (e.g., custom syntax highlighting).
    

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.  
(Optional: Add more specific contribution guidelines or link to a CONTRIBUTING.md file)

## License

This project is licensed under the [Apache License, Version 2.0](LICENSE).