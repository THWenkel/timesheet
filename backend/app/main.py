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

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.security import require_admin, require_user, security_headers_middleware
from app.db.session import check_connection
from app.routers import auth, backup, employees, export, projects, timesheets

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
            "Cannot reach database %s/%s. Check connection settings and ODBC driver installation.",
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

# Security headers (nosniff, no-store, HSTS when cookies are HTTPS-only).
# Authentication itself is enforced per router via dependencies, see "Routers" below.
app.middleware("http")(security_headers_middleware)

# CORS middleware
# In development the Vite proxy handles /api → no CORS issues for the frontend.
# This CORS config is provided for cases where the API is accessed directly
# (e.g. Swagger UI, curl, external clients).
# Allowed origins come from CORS_ORIGINS (JSON list in .env). With cookies
# (allow_credentials) the wildcard "*" is not allowed by browsers.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =============================================================================
# Routers
# =============================================================================
# Default-deny: every router requires a logged-in user (no-op while AUTH_ENABLED=false).
# Routes tighten this themselves (own-data checks, admin only). Only /api/auth is open.
_user = [Depends(require_user)]
_admin = [Depends(require_admin)]
app.include_router(auth.router)
app.include_router(employees.router, dependencies=_user)
app.include_router(timesheets.router, dependencies=_user)
app.include_router(export.router, dependencies=_user)
app.include_router(backup.router, dependencies=_admin)
app.include_router(projects.router, dependencies=_admin)
app.include_router(projects.customers_router, dependencies=_admin)
app.include_router(projects.country_codes_router, dependencies=_user)


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
