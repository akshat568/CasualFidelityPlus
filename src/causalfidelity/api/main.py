"""Main FastAPI application factory and entry point for CausalFidelityPlus API."""

import logging
import os
import time
from typing import List

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.exceptions import HTTPException

from causalfidelity.api import __title__, __version__
from causalfidelity.api.exceptions import (
    CausalAPIException,
    custom_http_exception_handler,
    global_exception_handler,
)
from causalfidelity.api.routes import causal, evaluation, health, perturbation, pipeline, reports

# Setup API logger
logger = logging.getLogger("causalfidelity.api")


def get_cors_origins() -> List[str]:
    """Parse CORS allowed origins from environment variable or use safe default local development origins."""
    env_origins = os.getenv("CORS_ORIGINS", "")
    if env_origins:
        return [origin.strip() for origin in env_origins.split(",") if origin.strip()]
    return ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]


def create_app() -> FastAPI:
    """FastAPI application factory."""
    app = FastAPI(
        title=__title__,
        version=__version__,
        description="RESTful API backend for CausalFidelityPlus interactive causal faithfulness and distortion stress testing.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # CORS Middleware
    origins = get_cors_origins()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Request Logging Middleware (logs request method, path, status, and duration without logging sensitive payload text)
    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        start_t = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start_t) * 1000, 2)
        logger.info(f"{request.method} {request.url.path} -> {response.status_code} ({duration_ms}ms)")
        return response

    # Exception Handlers
    app.add_exception_handler(HTTPException, custom_http_exception_handler)
    app.add_exception_handler(CausalAPIException, custom_http_exception_handler)
    app.add_exception_handler(Exception, global_exception_handler)

    # Register API Routers under /api/v1
    prefix = "/api/v1"
    app.include_router(health.router, prefix=prefix)
    app.include_router(causal.router, prefix=prefix)
    app.include_router(perturbation.router, prefix=prefix)
    app.include_router(evaluation.router, prefix=prefix)
    app.include_router(pipeline.router, prefix=prefix)
    app.include_router(reports.router, prefix=prefix)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    host = os.getenv("HOST", "127.0.0.1")
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("causalfidelity.api.main:app", host=host, port=port, reload=True)
