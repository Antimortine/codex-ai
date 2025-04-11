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
from contextlib import asynccontextmanager

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import the main API router
from app.api.v1.api import api_router
# --- REMOVED: Initializers (instances created at module level now) ---
# from app.rag.index_manager import initialize_index_manager
# from app.rag.engine import initialize_rag_engine
# from app.services.ai_service import initialize_ai_service
# --- END REMOVED ---


# --- Lifespan Event Handler ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code to run on startup
    logger.info("Lifespan: Starting up Codex AI Backend...")
    # --- REMOVED: Explicit Singleton Initialization ---
    # logger.info("Lifespan: Initializing IndexManager...")
    # initialize_index_manager()
    # logger.info("Lifespan: Initializing RagEngine...")
    # initialize_rag_engine()
    # logger.info("Lifespan: Initializing AIService...")
    # initialize_ai_service()
    # --- END REMOVED ---

    # --- ADDED: Check if singletons initialized (optional but good practice) ---
    try:
        # Attempt to import the instances to trigger their module-level creation
        from app.rag.index_manager import index_manager
        from app.rag.engine import rag_engine
        from app.services.ai_service import ai_service
        if index_manager is None: raise RuntimeError("IndexManager failed to initialize.")
        if rag_engine is None: raise RuntimeError("RagEngine failed to initialize.")
        if ai_service is None: raise RuntimeError("AIService failed to initialize.")
        logger.info("Lifespan: Core singletons appear initialized.")
    except Exception as e:
        logger.critical(f"Lifespan: CRITICAL ERROR during singleton initialization check: {e}", exc_info=True)
        # Decide how to handle - exit? Or let it potentially fail later?
        # For now, log critical error and continue startup.
    # --- END ADDED ---

    print("Lifespan: Startup complete.")

    yield # The application runs while yielded

    # Code to run on shutdown
    logger.info("Lifespan: Shutting down Codex AI Backend...")
    print("Lifespan: Shutdown complete.")


# --- FastAPI App Initialization ---
app = FastAPI(title="Codex AI Backend", lifespan=lifespan)


# --- Request Logging Middleware ---
@app.middleware("http")
async def log_requests(request: Request, call_next):
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
        raise e

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"GLOBAL HANDLER: Unhandled exception for {request.method} {request.url.path}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={ "message": "An unexpected error occurred", "error_type": type(exc).__name__, "error_details": str(exc), }
    )

# --- CORS Middleware ---
origins = [ "http://localhost", "http://127.0.0.1", "http://localhost:3000", "http://127.0.0.1:3000", "http://localhost:5173", "http://127.0.0.1:5173", ]
app.add_middleware( CORSMiddleware, allow_origins=origins, allow_credentials=True, allow_methods=["*"], allow_headers=["*"], expose_headers=["*"] )

# --- Root Endpoint / Health Check ---
@app.get("/")
async def read_root():
    logger.debug("Root endpoint handler called!")
    return {"message": "Welcome to Codex AI Backend!"}

# --- Test Endpoint ---
@app.get("/test")
async def test_endpoint():
    logger.debug("Test endpoint handler called!")
    return {"status": "test successful"}

# --- Include API Routers ---
app.include_router(api_router, prefix="/api/v1")