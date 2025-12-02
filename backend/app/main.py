"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.api.v1 import router as api_router
from app.config import get_settings

settings = get_settings()

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
    version="0.1.0",
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


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "0.1.0"}


# Include API router
app.include_router(api_router, prefix="/api/v1")

# Lambda handler
handler = Mangum(app, lifespan="off")
