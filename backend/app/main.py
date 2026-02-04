"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from mangum import Mangum

from app.api.v1 import router as api_router
from app.cold_start import clear_cold_start, get_cold_start_status
from app.config import get_settings
from app.utils.errors import BMXError, to_http_exception
from app.version import get_version

# Configure logging for Lambda - set level on root logger directly
# (basicConfig doesn't work because Lambda pre-configures handlers)
logger = logging.getLogger()
logger.setLevel(logging.INFO)

settings = get_settings()
app_version = get_version()

# Enable interactive API docs on staging and in debug mode.
# Staging is already protected by Cognito auth at the ALB/API-Gateway level,
# so no additional middleware is needed for /docs or /openapi.json.
_enable_docs = settings.debug or settings.environment.lower() == "staging"

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

### API Compatibility

This API follows additive compatibility within major versions:
- New optional fields may be added to responses at any time
- Clients should ignore unknown fields (do not use `additionalProperties: false`)
- Breaking changes (removal, rename, type changes) require a new API version

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
    docs_url="/docs" if _enable_docs else None,
    redoc_url="/redoc" if _enable_docs else None,
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

# CORS header configuration. Update these constants when adding new custom
# headers to requests or responses. Note: API Gateway has its own CORS config
# in infra/terraform/modules/api-gateway/ that must be kept in sync.

# Headers the browser is allowed to send in cross-origin requests
CORS_ALLOW_HEADERS: list[str] = [
    "Authorization",  # Cognito JWT bearer tokens for authenticated users
    "Content-Type",  # Required for application/json POST/PUT/PATCH requests
    "X-API-Key",  # API key authentication for CLI/automation tools
]

# Headers the browser is allowed to read from cross-origin responses
CORS_EXPOSE_HEADERS: list[str] = [
    "X-App-Version",  # Deployed version string (set by add_version_headers middleware)
    "X-Environment",  # Current environment name (set by add_version_headers middleware)
    "X-Cold-Start",  # Lambda cold start indicator (set by cold_start_middleware)
]

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
    allow_headers=CORS_ALLOW_HEADERS,
    expose_headers=CORS_EXPOSE_HEADERS,
)


@app.exception_handler(BMXError)
async def bmx_error_handler(request: Request, exc: BMXError):
    """Global handler for BMX custom exceptions."""
    http_exc = to_http_exception(exc)
    return JSONResponse(
        status_code=http_exc.status_code,
        content={"detail": http_exc.detail},
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

# Mangum handler for HTTP requests from API Gateway
handler = Mangum(app, lifespan="off")
