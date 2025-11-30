"""Application configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/bluemoxon"
    database_secret_arn: str | None = None

    # AWS
    aws_region: str = "us-east-1"

    # Cognito
    cognito_user_pool_id: str = ""
    cognito_app_client_id: str = ""

    # S3
    images_bucket: str = "bluemoxon-images"
    backup_bucket: str = "bluemoxon-backups"

    # Local images path (for development)
    local_images_path: str = "/tmp/bluemoxon-images"  # noqa: S108 # nosec B108

    # CORS
    cors_origins: str = "*"

    # App
    environment: str = "development"
    debug: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
