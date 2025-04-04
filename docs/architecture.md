
# Codex AI - Architecture Overview

  

## 1. Introduction

  

This document outlines the system architecture for Codex AI, an AI-powered writing assistant designed to help users create and manage long-form narrative content. The core goal is to leverage Large Language Models (LLMs) and Retrieval-Augmented Generation (RAG) to provide context-aware assistance throughout the writing process, from planning to drafting and editing.

  

The architecture emphasizes modularity and extensibility, allowing for future integration of different LLMs, vector databases, and embedding models.

  

## 2. High-Level Diagram

  

The system follows a typical client-server architecture with distinct components for the user interface, backend logic, AI orchestration, and data storage.

  

```mermaid

graph LR

A[User @ Browser] -- HTTP Requests --> B(React Frontend);

B -- REST API Calls --> C(FastAPI Backend);

C -- Uses --> D{LlamaIndex Orchestrator};

D -- Loads/Saves --> E[File System (Markdown Content)];

D -- Indexes/Retrieves --> F[Vector DB (ChromaDB)];

D -- Calls --> G[LLM API (Gemini 1.5 Pro)];

D -- Calls --> H[Embedding API (text-embedding-004)];

G -- Response --> D;

H -- Embeddings --> D;

F -- Context Chunks --> D;

E -- Raw Content --> D;

D -- Processed Data/Responses --> C;

C -- REST API Responses --> B;

B -- Renders UI --> A;

  

style F fill:#f9d,stroke:#333,stroke-width:2px

style G fill:#ccf,stroke:#333,stroke-width:2px

style H fill:#ccf,stroke:#333,stroke-width:2px

style D fill:#dfd,stroke:#333,stroke-width:2px

```

  
  

**Flow Description:**

  

1. The **User** interacts with the **React Frontend** in their browser.

2. The **Frontend** communicates with the **FastAPI Backend** via a REST API.

3. The **Backend** handles business logic and orchestrates AI tasks using **LlamaIndex**.

4.  **LlamaIndex** interacts with:

- The **File System** to read/write the user's Markdown project files (plan, scenes, characters, etc.).

- The **Embedding API** (Google text-embedding-004) to generate vector representations of text chunks.

- The **Vector DB** (ChromaDB) to store and retrieve relevant text chunks based on vector similarity.

- The **LLM API** (Google Gemini 1.5 Pro) to generate text, answer questions, or perform editing tasks based on the provided context.

5. Responses flow back through the layers to the user.

  

## 3. Component Breakdown

  

### 3.1. Frontend (React)

  

-  **Technology:** React, JavaScript/TypeScript, CSS.

-  **UI Components:** Standard React components, @uiw/react-md-editor for Markdown editing.

-  **Responsibilities:**

- Rendering the user interface (project navigation, editors, chat interfaces).

- Handling user input and interactions.

- Managing client-side state.

- Communicating with the Backend via REST API calls.

  

### 3.2. Backend (FastAPI)

  

-  **Technology:** Python, FastAPI.

-  **Responsibilities:**

- Providing a RESTful API for the Frontend.

- Handling user authentication and authorization (if implemented later).

- Managing project data (reading/writing Markdown files).

- Orchestrating RAG workflows via LlamaIndex.

- Handling business logic (e.g., assembling chapters/projects for export).

- Validating incoming data using Pydantic models.

  

### 3.3. RAG Orchestration (LlamaIndex)

  

-  **Technology:** LlamaIndex library (Python).

-  **Responsibilities:**

-  **Data Loading:** Loading Markdown documents from the file system.

-  **Chunking/Parsing:** Splitting documents into manageable, meaningful chunks (NodeParser).

-  **Embedding:** Calling the Embedding API (text-embedding-004) to get vectors for chunks.

-  **Indexing:** Storing text chunks and their vectors in the Vector DB (VectorStoreIndex using ChromaDB adapter).

-  **Retrieval:** Querying the Vector DB to find relevant context chunks based on user queries or generation tasks (Retriever).

-  **Prompt Engineering:** Constructing appropriate prompts for the LLM, incorporating retrieved context (PromptTemplate).

-  **LLM Interaction:** Calling the configured LLM (Gemini 1.5 Pro) with the constructed prompt (LLM interface).

-  **Abstraction:** Provides interfaces (LLM, VectorStore, BaseEmbedding) allowing replacement of core components (Gemini, ChromaDB, Google Embeddings) with minimal code changes in the core application logic.

  

### 3.4. LLM Service (Google Gemini 1.5 Pro)

  

-  **Technology:** External API (Google Generative AI).

-  **Responsibilities:**

- Understanding natural language prompts.

- Generating coherent and contextually relevant text (scenes, answers, edits).

- Processing potentially large amounts of context provided via RAG.

  

### 3.5. Embedding Service (Google text-embedding-004)

  

-  **Technology:** External API (Google Generative AI).

-  **Responsibilities:**

- Converting text chunks into dense vector representations (embeddings) suitable for semantic similarity search.

  

### 3.6. Vector Database (ChromaDB)

  

-  **Technology:** ChromaDB (Python library/server).

-  **Responsibilities:**

- Storing text chunks (or references) and their corresponding vector embeddings.

- Performing efficient Approximate Nearest Neighbor (ANN) searches to find chunks semantically similar to a query vector.

- (Potentially) Storing metadata alongside vectors for filtering.

- Accessed via LlamaIndex's VectorStore abstraction.

  

### 3.7. Data Storage (File System)

  

-  **Technology:** Server's local file system (or potentially cloud storage like S3 in a future deployment).

-  **Responsibilities:**

- Persisting the user's project data in its native Markdown format (scenes, plan, characters, worldbuilding notes).

- Organizing project data in a hierarchical structure (e.g., user_projects/<project_id>/chapters/<chapter_id>/scene_N.md).

- Note: Vector DB data (ChromaDB persistence) might also reside on the file system but is managed separately.

  

## 4. Key Workflows

  

### 4.1. Content Indexing (RAG - Ingestion)

  

1. User saves/updates a Markdown file (Scene, Plan, etc.) via the Frontend.

2. Frontend sends the update to the Backend API.

3. Backend saves the Markdown file to the File System.

4. Backend triggers LlamaIndex ingestion pipeline:

- Load the updated/new Markdown document.

- Parse the document into text chunks (Nodes).

- Generate embeddings for each chunk using the Embedding API.

- Insert/update the chunks and their embeddings in ChromaDB.

  

### 4.2. AI Query/Generation (RAG - Retrieval & Synthesis)

  

1. User submits a request (Q&A query, scene generation prompt) via the Frontend.

2. Frontend sends the request to the Backend API.

3. Backend determines the core query/task.

4. Backend uses LlamaIndex retrieval pipeline:

- Generate an embedding for the user's query/task description.

- Query ChromaDB using the Retriever to find the top-K most relevant context chunks from the project's indexed data.

- (Optional) Retrieve other structured context like current plan section, character profiles directly from files.

5. Backend uses LlamaIndex synthesis pipeline:

- Construct a detailed prompt for the LLM (Gemini 1.5 Pro) including the original request and the retrieved context chunks.

- Call the LLM API via the LlamaIndex LLM interface.

6. LLM processes the prompt and generates the response (answer, scene text, etc.).

7. Backend receives the LLM response.

8. If it's new content (e.g., generated scene), save it to the File System and potentially trigger indexing (see 4.1).

9. Backend sends the final response back to the Frontend.

10. Frontend displays the response to the User.

  

## 5. Design Decisions & Principles

  

-  **API-First:** Decoupled Frontend and Backend via a REST API promotes separation of concerns.

-  **Async Backend:** FastAPI enables efficient handling of I/O-bound operations (API calls to LLM/Embeddings, DB queries, file access).

-  **Modularity & Extensibility:** Heavy reliance on LlamaIndex abstractions allows swapping core AI components (LLM, Vector DB, Embeddings) with minimal disruption.

-  **Markdown as Source of Truth:** User content remains in a human-readable, portable format.

-  **RAG for Context:** Retrieval-Augmented Generation is central to providing the AI with relevant, up-to-date context from the user's project, improving coherence and reducing hallucinations.

-  **Developer Experience:** FastAPI (auto-docs), React (component model), and LlamaIndex (high-level RAG abstractions) aim for a productive development workflow.

  

## 6. Data Storage Summary

  

-  **User Content (Source):** Markdown files on the server's file system. Structure: user_projects/<project_id>/.... **Must be excluded from Git.**

-  **Vector Embeddings & Index:** Managed by ChromaDB. Persistence likely on the file system (in a configured directory) or potentially a separate DB server. **Must be excluded from Git.**

-  **Application Configuration:** Environment variables (.env file, excluded from Git) or config files.

-  **(Optional) Metadata:** Potentially a small relational DB (like SQLite) for managing project/chapter/scene order or relationships, if file-based management becomes too complex.

  

## 7. Deployment (Future Consideration)

  

A likely deployment strategy would involve containerizing the Backend (FastAPI + LlamaIndex + ChromaDB logic) and Frontend (React app served via e.g., Nginx) using Docker and orchestrating them with Docker Compose for local development and potentially for simple deployments. Cloud-native deployments (e.g., Kubernetes, Serverless functions, managed DBs) are possible future extensions.
