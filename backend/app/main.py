# =============================================================================
# backend/app/main.py
#
# FastAPI application entrypoint.
#
# This module creates the FastAPI app instance, registers all routers,
# adds the authentication middleware scaffold, and configures the OpenAPI
# schema export.
#
# Start the application:
#   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
# =============================================================================

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.security import auth_middleware
from app.db.session import check_connection
from app.routers import employees, export, timesheets

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """
    Application lifespan context manager.

    Runs startup logic before yielding (app is ready to accept requests)
    and shutdown logic after the yield (app is shutting down).

    Startup:
      - Verify database connectivity and log a warning if unreachable.
        The app still starts even if the DB is unreachable, so that the
        /health endpoint can report the degraded state.
    """
    # --- Startup ---
    db_ok = check_connection()
    if db_ok:
        logger.info(
            "Database connection to %s/%s OK",
            settings.db_server,
            settings.db_name,
        )
    else:
        logger.warning(
            "Cannot reach database %s/%s. "
            "Check connection settings and ODBC driver installation.",
            settings.db_server,
            settings.db_name,
        )

    yield  # Application is now running and handling requests

    # --- Shutdown ---
    logger.info("Timesheet API shutting down.")


# =============================================================================
# Create FastAPI application
# =============================================================================
app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "Timesheet management API. "
        "Provides endpoints for managing employees, timesheet entries, "
        "and exporting data as CSV, Excel, or PDF.\n\n"
        "**Authentication**: Not enforced in v1. "
        "See `app/core/security.py` for the auth scaffold."
    ),
    lifespan=lifespan,
    # OpenAPI schema is available at /openapi.json (FastAPI default)
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc",
)

# =============================================================================
# Middleware
# =============================================================================

# Authentication middleware scaffold (no-op in v1 when AUTH_ENABLED=False)
# ⚠️  TODO: Enable by setting AUTH_ENABLED=true in .env (v2+)
app.middleware("http")(auth_middleware)

# CORS middleware
# In development the Vite proxy handles /api → no CORS issues for the frontend.
# This CORS config is provided for cases where the API is accessed directly
# (e.g. Swagger UI, curl, external clients).
# ⚠️  TODO: Restrict origins to the production frontend domain before go-live.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict this in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Routers
# =============================================================================
app.include_router(employees.router)
app.include_router(timesheets.router)
app.include_router(export.router)


# =============================================================================
# Health check endpoint
# =============================================================================
@app.get("/health", tags=["health"], summary="Application health check")
def health() -> dict[str, str]:
    """
    Simple health check endpoint.

    Returns the application status and database connectivity status.
    Does NOT require authentication even when AUTH_ENABLED=True.
    """
    db_status = "ok" if check_connection() else "unreachable"
    return {
        "status": "ok",
        "version": settings.app_version,
        "database": db_status,
    }
