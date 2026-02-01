"""
YUNA API - FastAPI Application.
"""

import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Callable, Optional

from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from yuna.api.auth import (
    Token,
    LoginRequest,
    UserInfo,
    authenticate_user,
    create_access_token,
    JWT_EXPIRE_HOURS,
)
from yuna.api.deps import CurrentUser, DbDep, get_db

# Version info
VERSION = "1.0.0"
API_PREFIX = "/api"


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    version: str
    timestamp: str
    database: str


class SystemStats(BaseModel):
    """System statistics."""
    anime_count: int
    series_count: int
    films_count: int
    version: str


def create_app(lifespan: Optional[Callable] = None) -> FastAPI:
    """
    Create and configure the FastAPI application.

    Args:
        lifespan: Optional lifespan context manager for startup/shutdown

    Returns:
        Configured FastAPI application
    """
    app = FastAPI(
        title="YUNA API",
        description="Media management API for YUNA System",
        version=VERSION,
        lifespan=lifespan,
        docs_url=f"{API_PREFIX}/docs",
        redoc_url=f"{API_PREFIX}/redoc",
        openapi_url=f"{API_PREFIX}/openapi.json",
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, restrict this
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routes
    register_routes(app)

    # Serve static files (PWA) if directory exists
    static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
    if os.path.exists(static_dir):
        app.mount("/", StaticFiles(directory=static_dir, html=True), name="static")

    return app


def register_routes(app: FastAPI) -> None:
    """Register all API routes."""

    # Include routers from routes/
    from yuna.api.routes import anime, search, series, films
    app.include_router(anime.router, prefix=API_PREFIX)
    app.include_router(search.router, prefix=API_PREFIX)
    app.include_router(series.router, prefix=API_PREFIX)
    app.include_router(films.router, prefix=API_PREFIX)

    # ==================== Health & Info ====================

    @app.get(f"{API_PREFIX}/health", response_model=HealthResponse, tags=["System"])
    async def health_check():
        """
        Health check endpoint.
        Returns service status and basic info.
        """
        db_status = "ok"
        try:
            db = get_db()
            # Simple query to test connection
            db.get_all_anime()
        except Exception:
            db_status = "error"

        return HealthResponse(
            status="healthy",
            version=VERSION,
            timestamp=datetime.now(timezone.utc).isoformat(),
            database=db_status,
        )

    @app.get(f"{API_PREFIX}/version", tags=["System"])
    async def get_version():
        """Get API version information."""
        return {
            "version": VERSION,
            "api_prefix": API_PREFIX,
            "name": "YUNA API",
        }

    @app.get(f"{API_PREFIX}/stats", response_model=SystemStats, tags=["System"])
    async def get_stats(db: DbDep):
        """
        Get library statistics.
        Requires authentication.
        """
        anime_list = db.get_all_anime()
        series_list = db.get_all_tv()
        films_list = db.get_all_movies()

        return SystemStats(
            anime_count=len(anime_list),
            series_count=len(series_list),
            films_count=len(films_list),
            version=VERSION,
        )

    # ==================== Authentication ====================

    @app.post(f"{API_PREFIX}/login", response_model=Token, tags=["Auth"])
    async def login(request: LoginRequest):
        """
        Authenticate and get JWT token.

        Returns access token for API authentication.
        """
        username = authenticate_user(request.username, request.password)

        if username is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        access_token = create_access_token(username)

        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=JWT_EXPIRE_HOURS * 3600,
        )

    @app.get(f"{API_PREFIX}/me", response_model=UserInfo, tags=["Auth"])
    async def get_current_user_info(user: CurrentUser):
        """
        Get current authenticated user info.

        Requires valid JWT token.
        """
        return user

    # ==================== Catch-all for SPA ====================

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """
        Serve SPA for all non-API routes.
        Falls back to index.html for client-side routing.
        """
        static_dir = os.path.join(os.path.dirname(__file__), "..", "..", "..", "static")
        index_path = os.path.join(static_dir, "index.html")

        if os.path.exists(index_path):
            return FileResponse(index_path)

        # If no static files, return API info
        return {
            "message": "YUNA API",
            "version": VERSION,
            "docs": f"{API_PREFIX}/docs",
        }


# Create default app instance
app = create_app()
