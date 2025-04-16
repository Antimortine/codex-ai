# Codex AI ✍️

**Codex AI is an AI-powered assistant designed to help writers structure, develop, and write long-form creative works, leveraging large language models like Google's Gemini and the power of Retrieval-Augmented Generation (RAG) with multilingual support.**

It aims to address the challenges of maintaining coherence and context in long-form writing by providing an interactive environment where writers collaborate with an AI aware of their work-in-progress.

For more details on the system's design, see:

-   [Architecture Document](docs/architecture.md)    
-   [Design Principles Document](docs/design_principles.md)
    

## Key Features

-   **Project Management:** Create, list, update, and delete writing projects.
    
-   **Hierarchical Structure:** Organize your work into **Chapters** and **Scenes** (using 1-based ordering).
    
-   **Content Blocks:** Manage core project documents like Plan, Synopsis, and Worldbuilding notes (at both Project and Chapter levels).
    
-   **Character Profiles:** Create and manage character descriptions.
    
-   **Project Notes:**  (New!) Create, view, edit, delete, and organize project-level notes (stored as Markdown files).
    
    -   **Virtual Folders:** Organize notes into a hierarchical folder structure using metadata.
        
    -   **Tree View:** Visualize and navigate notes and folders in an interactive tree.
        
    -   **Drag-and-Drop:** Easily move notes between folders or re-organize folders within the tree view.
        
-   **Markdown Editor:** Write and edit all content using a familiar Markdown format (@uiw/react-md-editor).
    
-   **Context-Aware Q&A:** Ask questions about your own story ("What was Character X's motivation in Chapter 2?", "Remind me of the description of Location Y?", "Summarize the 'Magic System Ideas' note"). The AI uses the specific project's indexed content (including Plan, Synopsis, Notes) to answer, ensuring relevance and isolation between projects.
    
-   **Multiple Chat Sessions per Project:** Maintain separate, independent chat conversations within a single project. Create, rename, delete, and switch between sessions.
    
-   **AI-Powered Scene Generation:** Generate scene drafts (including title and content) based on previous scenes, plan, synopsis, retrieved context, and optional user prompts (using a <textarea> for detailed input).
    
-   **AI-Powered Editing (Rephrase):** Get suggestions for rephrasing selected text directly within the editor.
    
-   **AI Chapter Splitting:** Analyze full chapter text (pasted into the UI) and receive AI-proposed scene splits with suggested titles and content.
    
-   **Source Node Retrieval:** API responses for AI queries include the specific text chunks (source nodes) used by the AI to generate the answer, providing transparency.
    
-   **RAG Integration (LlamaIndex + ChromaDB + HuggingFace):** The AI maintains awareness of project context by indexing Markdown content (Scenes, Characters, Plan, Synopsis, World, Notes) into a vector database (ChromaDB) using multilingual embeddings (sentence-transformers/paraphrase-multilingual-mpnet-base-v2). Project-specific metadata filtering ensures the AI only retrieves context relevant to the current project during queries.
    
-   **Configurable LLM Temperature:** Set a global temperature for LLM generation via environment variable.
    
-   **Project Sorting:** Projects are listed sorted by their last content modification time (most recent first).
    
-   **Compile Chapter Content:** Compile all scenes within a chapter into a single downloadable Markdown file, with options to include titles and customize separators.
    
-   **Extensible Architecture:** Designed with abstractions (via LlamaIndex) to potentially support different LLMs and Vector Databases in the future.
    
-   **Testing:** Backend tests using pytest. Frontend tests using vitest (including refactored async tests).
    
-   **Markdown Export (Planned):** Compile selected Chapters or the entire manuscript into a single Markdown file.
    

## Technology Stack

-   **Backend:** Python, FastAPI
    
-   **Frontend:** React, Vite, @uiw/react-md-editor, Axios, react-router-dom, react-arborist (for Note Tree)
    
-   **AI/RAG Orchestration:** LlamaIndex
    
-   **LLM:** Google Gemini (via llama-index-llms-google-genai)
    
-   **Embeddings:** HuggingFace Multilingual (sentence-transformers/paraphrase-multilingual-mpnet-base-v2)
    
-   **Vector Database:** ChromaDB (local persistence)
    
-   **Dependency Management (Backend):** pip-tools (requirements.in, requirements.txt)
    
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
    
-   **Rust Compiler:** The tokenizers library (a dependency) often requires Rust for building extensions. Install it via https://rustup.rs/. if you encounter installation errors related to cargo.
    

### Installation & Setup

1.  **Clone the repository:**
    
```bash
git clone https://github.com/Antimortine/codex-ai.git
cd codex-ai
```
        
    
-   **Setup Backend:**
    
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
# AND set the desired LLM_TEMPERATURE (e.g., LLM_TEMPERATURE=0.7)
# AND set MAX_CONTEXT_LENGTH if desired (e.g., MAX_CONTEXT_LENGTH=15000)
nano .env # Or your preferred editor

# Go back to root directory
cd ..``
```


(Note: The first run of pip install -r requirements.txt or the first time the backend starts might take longer as the embedding model is downloaded.)
    
-   **Setup Frontend:**
    
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
(Remember to delete backend/chroma_db if you change embedding models or suspect index corruption).

2. **Run Frontend (Vite dev server):**
    
```bash
cd frontend
npm run dev # or yarn dev
# Keep this terminal running
```

    
3.  **Access Codex AI:** Open your web browser and navigate to http://localhost:5173Vite default).
    

**(Optional) Using Docker Compose:**

(Instructions remain the same, assuming docker-compose.yml will be added later)

## Project Structure

```codex-ai/
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
│ │   └── {project_id}/
│ │       ├── chapters/
│ │       ├── characters/
│ │       ├── notes/ # <-- ADDED: Notes directory
│ │       ├── plan.md
│ │       ├── synopsis.md
│ │       ├── world.md
│ │       ├── project_meta.json # <-- Includes notes metadata
│ │       └── chat_history.json
│ ├── .env # Local environment variables (added by .gitignore)
│ ├── .env.example
│ ├── requirements.in # Direct backend dependencies
│ └── requirements.txt # Locked backend dependencies (generated)
├── frontend/ # React application (JavaScript/JSX)
│ ├── public/
│ ├── src/ # Source code
│ │ ├── api/ # API client (codexApi.js)
│ │ ├── components/ # Reusable UI components (NoteTreeViewer, etc.)
│ │ ├── layouts/ # Main layout structure
│ │ ├── pages/ # Page components (ProjectNotesPage, NoteEditPage, etc.)
│ │ ├── App.jsx
│ │ ├── App.css
│ │ └── index.jsx # Entry point
│ ├── .env.example # Optional frontend env vars
│ ├── index.html
│ └── package.json
├── docs/ # Project documentation
│ ├── architecture.md
│ ├── design_principles.md
│ └── testing_notes.md # Frontend testing guidelines
├── scripts/ # Utility scripts (inspect_chroma.py, etc.)
├── .gitignore
└── README.md
```

## Known Issues

-   **Rate Limiting (Free Tier):** While backend retry logic exists, the free tier of the Google Gemini API has strict limits (Requests Per Minute and Daily). Heavy use of AI features (Generation, Splitting, Query, Rephrase) may still hit these limits, resulting in temporary unavailability errors (HTTP 429). Using a paid plan (or free credits) is recommended for reliable usage.
    
-   **SuggestionPopup Limitations:** The popup for rephrasing suggestions might have positioning issues near screen edges and could benefit from styling improvements.
    

## Roadmap

**P0: Critical / Bug Fixes**

-   (None)
    

**P1: High Priority**

-   (All previously listed P1 tasks are now complete)
    

**P2: Medium Priority**

1.  **Task B.3: AI Editing Features (Summarize)**
    
    -   **Description:** Implement the "Summarize" AI action in the editor.
        
    -   **Status:** Not Started
        
    -   **Priority:**  **Medium (Current Highest Priority)**
        
2.  **Task G.8: Frontend Modal/Component Tests**
    
    -   **Description:** Add tests for modal components (GeneratedSceneModal, SplitChapterModal, CompiledContentModal, Modal) and ensure adequate coverage for other reusable components (NoteTreeViewer, QueryInterface, etc.).
        
    -   **Status:** Not Started
        
    -   **Priority:**  **Medium**
        
3.  **Task C.3.2: Other UI/UX Refinements**
    
    -   **Description:** Improve Split Chapter modal, add AI feedback/cooldown indicators, address SuggestionPopup limitations, improve Move Note modal UX.
        
    -   **Status:** Not Started
        
    -   **Priority:**  **Medium**
        
4.  **Task G.10: Backend Prompt Builder Refactor**
    
    -   **Description:** Refactor prompt construction logic in backend RAG processors into a shared utility/class.
        
    -   **Status:** Not Started
        
    -   **Priority:**  **Medium**
        

**P3: Low Priority**

1.  **Task C.2: Delete Last Chat Entry**
    
    -   **Status:** Not Started
        
    -   **Priority:**  **Low**
        
2.  **Task G.11: RAG Edge Case Tests**
    
    -   **Status:** Not Started
        
    -   **Priority:**  **Low**
        
3.  **Task G.12: Centralize Frontend Error Helper**
    
    -   **Status:** Not Started
        
    -   **Priority:**  **Low**
        
4.  **Task D.2.2: Further Configuration & Refactoring**
    
    -   **Status:** Not Started
        
    -   **Priority:**  **Low**
        
5.  **Task E.1: Deployment Strategy**
    
    -   **Status:** Not Started
        
    -   **Priority:**  **Low**
        
6.  **Task E.3: Integrate other LLMs/Vector DBs**
    
    -   **Status:** Not Started
        
    -   **Priority:**  **Low**
        

**Completed Tasks (Recent):**

-   Task G.1: Project Notes Feature (CRUD, Tree View, D&D)
    
-   Task C.3.1: Improve Scene Gen Prompt Input (UI/UX)
    
-   Task E.2.1: Compile Chapter Content
    
-   Task F.1: Configurable LLM Parameters
    
-   Task F.2: Order Projects by Last Modified
    
-   Task D.1: Expand Test Coverage (RAG Filtering & IndexManager)
    
-   Task B.1: Multiple Chat Sessions
    
-   Task C.4: Show Chapter Titles in Query Sources (UI)
    
-   Task B.2: Chapter-Level Plan/Synopsis (Backend + Frontend Edit)
    
-   Task D.2.1: Refactor AIService._load_context
    
-   Global context truncation constant and prompt size logging.
    
-   Fixed duplicate node indexing issue.
    
-   Refactored ProjectDetailPage.test.jsx for stability.
    

## Contributing

Contributions are welcome! Please feel free to open an issue or submit a pull request.

## License

This project is licensed under the [Apache License, Version 2.0](https://www.google.com/url?sa=E&q=LICENSE).

## Author / Contact

Codex AI is developed and maintained by Antimortine.

-   **Email:** [antimortine@gmail.com](mailto:antimortine@gmail.com)
-   **Telegram:** [https://t.me/antimortine](https://t.me/antimortine)
-   **GitHub:** [https://github.com/Antimortine](https://github.com/Antimortine)