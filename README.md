
# Codex AI ✍️

**Codex AI is an AI-powered assistant designed to help writers structure, develop, and write long-form creative works, leveraging large language models like Google's Gemini 1.5 Pro and the power of Retrieval-Augmented Generation (RAG).**

## The Problem

Writing long-form content like novels or complex narratives presents challenges in maintaining plot coherence, character consistency, and overall structure over potentially hundreds of pages. Traditional writing tools often lack the means to effectively track and utilize the vast context of an evolving story.

Codex AI aims to alleviate these challenges by providing an interactive environment where writers can collaborate with an AI that has persistent, context-aware knowledge of their work-in-progress.

## Key Features

-   **Project Management:** Create, list, update, and delete writing projects.
    
-   **Hierarchical Structure:** Organize your work into **Chapters** and **Scenes** (using 1-based ordering).
    
-   **Content Blocks:** Manage core project documents like Plan, Synopsis, and Worldbuilding notes.
    
-   **Character Profiles:** Create and manage character descriptions.
    
-   **Markdown Editor:** Write and edit all content using a familiar Markdown format (@uiw/react-md-editor).
    
-   **Context-Aware Q&A (Backend Implemented):** Ask questions about your own story ("What was Character X's motivation in Chapter 2?", "Remind me of the description of Location Y?"). The AI uses the specific project's indexed content to answer, ensuring relevance and isolation between projects.
    
-   **Source Node Retrieval:** API responses for AI queries include the specific text chunks (source nodes) used by the AI to generate the answer, providing transparency.
    
-   **RAG Integration (LlamaIndex + ChromaDB):** The AI maintains awareness of project context by indexing Markdown content into a vector database (ChromaDB). Project-specific metadata filtering ensures the AI only retrieves context relevant to the current project during queries.
    
-   **Extensible Architecture:** Designed with abstractions (via LlamaIndex) to potentially support different LLMs (OpenAI, Anthropic, local models) and Vector Databases in the future.
    
-   **Markdown Export (Planned):** Compile selected Chapters or the entire manuscript into a single Markdown file.
    

(Frontend integration for AI features is the next major step)

## Technology Stack

-   **Backend:** Python, FastAPI
    
-   **Frontend:** React, @uiw/react-md-editor, Axios
    
-   **AI/RAG Orchestration:** LlamaIndex
    
-   **LLM:** Google Gemini 1.5 Pro (via Google Generative AI API)
    
-   **Embeddings:** Google text-embedding-004
    
-   **Vector Database:** ChromaDB (local persistence)
    
-   **API Communication:** REST API between Frontend and Backend
    
-   **Data Models & Validation:** Pydantic
    
-   **(Optional) Containerization:** Docker, Docker Compose (config files not yet implemented)
    

## Getting Started

These instructions will get you a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

-   Python 3.9+ and Pip
    
-   Node.js and npm (or yarn)
    
-   Git
    
-   Access to Google Generative AI API (API Key for Gemini and Embeddings)
    

### Installation & Setup

1.  **Clone the repository:**
    
```
git clone https://your-repository-url/codex-ai.git
cd codex-ai
```
    
    
-   **Setup Backend:**
    
```
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
    
-   **Setup Frontend:**
    
```
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
    
```
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# Keep this terminal running
```

    
-   **Run Frontend (React dev server):**
    
```
cd frontend
npm start # or yarn start (or `vite` if using Vite directly)
# Keep this terminal running
```
        

2.  **Access Codex AI:** Open your web browser and navigate to http://localhost:5173 (Vite default) or http://localhost:3000 (CRA default).
    

**(Optional) Using Docker Compose:**

(Instructions remain the same, assuming docker-compose.yml will be added later)

## Project Structure

```
codex-ai/
├── backend/        # FastAPI application (Python)
│   ├── app/        # Core application code
│   │   ├── api/    # API endpoints (routers, deps)
│   │   │   └── v1/ # API version 1
│   │   │       ├── endpoints/ # Specific endpoint files (projects, ai, etc.)
│   │   │       └── api.py     # Main v1 router
│   │   ├── core/   # Configuration (config.py)
│   │   ├── models/ # Pydantic data models (project, chapter, ai, etc.)
│   │   ├── rag/    # LlamaIndex RAG logic
│   │   │   ├── index_manager.py # Index setup & CUD operations
│   │   │   └── engine.py        # RAG query/retrieval engine
│   │   ├── services/ # Business logic (project, chapter, ai_service, etc.)
│   │   └── main.py # FastAPI entry point
│   ├── tests/      # Backend tests (To be added)
│   ├── chroma_db/  # Local vector store data (added by .gitignore)
│   ├── user_projects/ # User's project data (added by .gitignore)
│   ├── .env        # Local environment variables (added by .gitignore)
│   ├── .env.example
│   └── requirements.txt
├── frontend/       # React application (JavaScript/JSX)
│   ├── public/
│   ├── src/        # Source code
│   │   ├── api/    # API client (codexApi.js)
│   │   ├── components/ # Reusable UI components (To be added)
│   │   ├── layouts/  # Main layout structure
│   │   ├── pages/    # Page components (ProjectList, ProjectDetail, editors)
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── index.jsx # Entry point
│   ├── .env.example # Optional frontend env vars
│   ├── index.html
│   └── package.json
├── docs/           # Project documentation (architecture.md, design_principles.md)
├── scripts/        # Utility scripts (inspect_chroma.py, etc.)
├── .gitignore
└── README.md
```


(Note: user_projects/ and chroma_db/ are created during runtime and excluded by .gitignore)

## Roadmap

-   **Frontend Integration:** Build UI components for AI query interaction (input field, response display, source node visualization).
    
-   **AI-Powered Generation:** Implement endpoints and logic for generating scene drafts, character ideas, etc., using RAG context.
    
-   **AI-Powered Editing:** Implement features for refining text using AI suggestions.
    
-   **Prompt Engineering:** Optimize prompts sent to the LLM for better quality and control over AI responses.
    
-   **Enhanced UI/UX:** Improve navigation, editor features, and overall user experience.
    
-   **Testing:** Add unit and integration tests for backend and frontend.
    
-   **Configuration:** Move hardcoded values (e.g., SIMILARITY_TOP_K) to configuration.
    
-   **Deployment Strategy:** Define and implement deployment (e.g., Docker).
    
-   **(Future)** Integration with additional LLM providers/Vector DBs.
    
-   **(Future)** Real-time collaboration features.
    

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.  
(Optional: Add more specific contribution guidelines or link to a CONTRIBUTING.md file)

## License

This project is licensed under the [Apache License, Version 2.0](https://www.google.com/url?sa=E&q=LICENSE).

## Author / Contact

Codex AI is developed and maintained by Antimortine.

-   **Email:**  [antimortine@gmail.com](https://www.google.com/url?sa=E&q=mailto%3Aantimortine%40gmail.com)
    
-   **Telegram:**  [https://t.me/antimortine](https://www.google.com/url?sa=E&q=https%3A%2F%2Ft.me%2Fantimortine)
    
-   **GitHub:**  [https://github.com/Antimortine](https://www.google.com/url?sa=E&q=https%3A%2F%2Fgithub.com%2FAntimortine)
