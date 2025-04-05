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

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import the main API router
from app.api.v1.api import api_router
# Assuming config will be needed soon
# from app.core.config import settings

# --- FastAPI App Initialization ---
# Create the main FastAPI application instance.
# Metadata like title, description, version can be added here later.
app = FastAPI(title="Codex AI Backend")

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "message": "An unexpected error occurred",
            "error": str(exc),
            "trace": traceback.format_exc().split('\n')
        }
    )

# --- CORS Middleware ---
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

# --- Root Endpoint / Health Check ---
# A simple GET endpoint at the root URL ("/") to check if the server is running.
@app.get("/")
async def read_root():
    """
    Health check endpoint. Returns a welcome message.
    """
    logger.debug("Root endpoint was called!")
    print("Root endpoint was called! CORS seems to be working.")
    return {"message": "Welcome to Codex AI Backend!"}

# --- Test Endpoint ---
@app.get("/test")
async def test_endpoint():
    """
    Simple test endpoint to verify routing.
    """
    logger.debug("Test endpoint was called!")
    print("Test endpoint was called!")
    return {"status": "test successful"}

# --- Include API Routers ---
# Mount the version 1 API router under the /api/v1 prefix
# Using settings.API_V1_STR is cleaner if defined in config.py
app.include_router(api_router, prefix="/api/v1")

# Startup logging
@app.on_event("startup")
async def startup_event():
    logger.info("Starting up Codex AI Backend...")
    print("Starting up Codex AI Backend...")
    
    # Log all registered routes for debugging
    logger.info("Registered routes:")
    for route in app.routes:
        logger.info(f"Route: {route.path}, Methods: {route.methods}")