"""FastAPI application entry point."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum

from app.api.v1 import router as api_router
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="BlueMoxon API",
    description="Victorian Book Collection Management API",
    version="0.1.0",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS middleware - production uses specific origins via CORS_ORIGINS env var
# Default "*" is for local development only
if settings.cors_origins == "*":
    # Local development: allow all origins
    # nosemgrep: python.fastapi.security.wildcard-cors.wildcard-cors
    origins = ["*"]
else:
    # Production: use comma-separated list from environment
    origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
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
