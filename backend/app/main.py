"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.api.v1 import router as api_router
from app.cold_start import clear_cold_start, get_cold_start_status
from app.config import get_settings
from app.version import get_version

# Configure logging for Lambda - set level on root logger directly
# (basicConfig doesn't work because Lambda pre-configures handlers)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

settings = get_settings()
app_version = get_version()

API_DESCRIPTION = """
## BlueMoxon API

Victorian Book Collection Management API for cataloging and managing
a curated collection of Victorian-era books with premium bindings.

### Features

- **Books**: CRUD operations for book records with full metadata
- **Images**: Upload and manage book images with S3 storage
- **Search**: Full-text search across the collection
- **Statistics**: Collection analytics and reporting
- **Health**: Deep health checks for monitoring and CI/CD

### Authentication

- **Cognito JWT**: For web application users
- **API Key**: For CLI/automation tools (X-API-Key header)

### Health Endpoints

| Endpoint | Purpose |
|----------|---------|
| `/health` | Simple liveness check |
| `/api/v1/health/live` | Kubernetes liveness probe |
| `/api/v1/health/ready` | Kubernetes readiness probe |
| `/api/v1/health/deep` | Full dependency validation |
| `/api/v1/health/info` | Service metadata |
"""

app = FastAPI(
    title="BlueMoxon API",
    description=API_DESCRIPTION,
    version=app_version,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_tags=[
        {"name": "health", "description": "Health check and monitoring endpoints"},
        {"name": "books", "description": "Book CRUD operations"},
        {"name": "images", "description": "Book image management"},
        {"name": "search", "description": "Full-text search"},
        {"name": "statistics", "description": "Collection analytics"},
        {"name": "publishers", "description": "Publisher reference data"},
        {"name": "authors", "description": "Author reference data"},
        {"name": "binders", "description": "Binder reference data"},
        {"name": "export", "description": "Data export endpoints"},
        {"name": "users", "description": "User management (admin)"},
    ],
)

# CORS middleware - production uses specific origins via CORS_ORIGINS env var
# Default "*" is for local development only
if settings.cors_origins == "*":
    # Local development: allow all origins
    origins = ["*"]
else:
    # Production: use comma-separated list from environment
    origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    # nosemgrep: python.fastapi.security.wildcard-cors.wildcard-cors
    allow_origins=origins,  # Controlled by CORS_ORIGINS env var in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_version_headers(request: Request, call_next):
    """Add version and environment headers to all responses."""
    response = await call_next(request)
    response.headers["X-App-Version"] = app_version
    response.headers["X-Environment"] = settings.environment
    return response


@app.middleware("http")
async def cold_start_middleware(request: Request, call_next):
    """Track cold start status in response headers."""
    is_cold = get_cold_start_status()
    response = await call_next(request)
    response.headers["X-Cold-Start"] = str(is_cold)
    clear_cold_start()
    return response


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": app_version}


# Include API router
app.include_router(api_router, prefix="/api/v1")

# Lambda handler
handler = Mangum(app, lifespan="off")
