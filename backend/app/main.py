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
import time
from contextlib import asynccontextmanager # Import asynccontextmanager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import the main API router
from app.api.v1.api import api_router
# Assuming config will be needed soon
# from app.core.config import settings


# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logger.info("Lifespan: Starting up Codex AI Backend...")
    # Log registered routes (optional, can be verbose)
    logger.info("Lifespan: Registered routes:")
    for route in app.routes:
        if hasattr(route, 'path'):
             logger.info(f"  Route: {route.path}, Name: {route.name if hasattr(route, 'name') else 'N/A'}, Methods: {route.methods if hasattr(route, 'methods') else 'Middleware/Other'}")
    print("Lifespan: Startup complete.") # Keep print for visual confirmation if needed

    yield # The application runs while yielded

    # Code to run on shutdown
    logger.info("Lifespan: Shutting down Codex AI Backend...")
    print("Lifespan: Shutdown complete.")


# --- FastAPI App Initialization ---
# Pass the lifespan manager to the FastAPI constructor
app = FastAPI(title="Codex AI Backend", lifespan=lifespan)


# --- ADDED: Simple Request Logging Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # --- ADDED PRINT STATEMENT ---
    print(f"--- Entering log_requests middleware for: {request.method} {request.url.path} ---")
    # --- END ADDED PRINT STATEMENT ---
    start_time = time.time()
    logger.info(f"MIDDLEWARE: Incoming request: {request.method} {request.url.path}")
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        logger.info(f"MIDDLEWARE: Finished request: {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.4f}s")
        return response
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"MIDDLEWARE: Exception during request: {request.method} {request.url.path} - Error: {e} - Time: {process_time:.4f}s", exc_info=True)
        # Re-raise the exception so the global handler can catch it
        raise e
# --- END ADDED MIDDLEWARE ---


# Global exception handler (Keep this AFTER the logging middleware)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"GLOBAL HANDLER: Unhandled exception for {request.method} {request.url.path}: {exc}", exc_info=True)
    # logger.error(traceback.format_exc()) # exc_info=True in logger.error does this
    return JSONResponse(
        status_code=500,
        content={
            "message": "An unexpected error occurred",
            "error_type": type(exc).__name__, # Add type for clarity
            "error_details": str(exc),
            # "trace": traceback.format_exc().split('\n') # Maybe too verbose for client
        }
    )

# --- CORS Middleware (Keep this AFTER the logging middleware if you want to see logs even for CORS-rejected requests) ---
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
    logger.debug("Root endpoint handler called!")
    # print("Root endpoint was called! CORS seems to be working.") # Redundant with logger
    return {"message": "Welcome to Codex AI Backend!"}

# --- Test Endpoint ---
@app.get("/test")
async def test_endpoint():
    """
    Simple test endpoint to verify routing.
    """
    logger.debug("Test endpoint handler called!")
    # print("Test endpoint was called!") # Redundant with logger
    return {"status": "test successful"}

# --- Include API Routers ---
# Mount the version 1 API router under the /api/v1 prefix
# Using settings.API_V1_STR is cleaner if defined in config.py
app.include_router(api_router, prefix="/api/v1")

# --- REMOVED Old Startup/Shutdown Event Handlers ---
# @app.on_event("startup")
# async def startup_event():
#     logger.info("Starting up Codex AI Backend...")
#     # print("Starting up Codex AI Backend...") # Redundant with logger
#
#     # Log all registered routes for debugging
#     logger.info("Registered routes:")
#     for route in app.routes:
#         # Filter out middleware routes for cleaner logging if desired
#         if hasattr(route, 'path'):
#              logger.info(f"Route: {route.path}, Name: {route.name if hasattr(route, 'name') else 'N/A'}, Methods: {route.methods if hasattr(route, 'methods') else 'Middleware/Other'}")
#
# @app.on_event("shutdown")
# async def shutdown_event():
#     logger.info("Shutting down Codex AI Backend...")
# --- END REMOVED ---