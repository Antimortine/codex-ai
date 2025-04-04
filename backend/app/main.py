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

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# --- FastAPI App Initialization ---
# Create the main FastAPI application instance.
# Metadata like title, description, version can be added here later.
app = FastAPI(title="Codex AI Backend")


# --- CORS (Cross-Origin Resource Sharing) Middleware ---
# This is CRITICAL for allowing the React frontend (running on a different port/origin)
# to communicate with this FastAPI backend. Without it, browsers will block requests.

# List of origins that are allowed to make requests to this backend.
# Include the standard ports for React dev servers (3000, Vite's 5173)
# and potentially your deployed frontend URL in the future.
origins = [
    "http://localhost",       # Allow local access if needed
    "http://127.0.0.1",       # Allow local access via IP
    "http://localhost:3000",  # Default port for create-react-app
    "http://127.0.0.1:3000",  # Also allow IP variant
    "http://localhost:5173",  # Default port for Vite dev server
    "http://127.0.0.1:5173",  # Also allow IP variant
    # Add any other origins as needed, e.g., your deployed frontend URL
    # "https://your-codex-ai-frontend.com",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # Specifies the allowed origins
    allow_credentials=True,      # Allows cookies to be included in requests (useful for auth later)
    allow_methods=["*"],         # Allows all standard HTTP methods (GET, POST, PUT, DELETE, etc.)
    allow_headers=["*"],         # Allows all headers in requests
    expose_headers=["*"]         # Expose all headers to the browser
)
# --- /CORS Middleware ---


# --- Root Endpoint / Health Check ---
# A simple GET endpoint at the root URL ("/") to check if the server is running.
@app.get("/")
async def read_root():
    """
    Health check endpoint. Returns a welcome message.
    """
    # Add logging to help debug connection issues
    print("Root endpoint was called! CORS seems to be working.")
    return {"message": "Welcome to Codex AI Backend!"}


# --- API Routers (Placeholder) ---
# We will include our versioned API routers here later in Phase 2.
# This keeps the main application file clean.
# Example:
# from app.api.v1.api import api_router
# from app.core.config import settings # Assuming settings are configured later
# app.include_router(api_router, prefix=settings.API_V1_STR)


# --- Optional Startup/Shutdown Events ---
# You can define functions to run on startup (e.g., connect to DBs)
# or shutdown (e.g., clean up resources) if needed later.
# @app.on_event("startup")
# async def startup_event():
#     print("Starting up...")

# @app.on_event("shutdown")
# async def shutdown_event():
#     print("Shutting down...")