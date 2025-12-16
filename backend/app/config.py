"""Application configuration.

Environment variables support both BMX_ prefixed names (preferred) and legacy names.
BMX_ prefix takes precedence when both are set.

Examples:
    BMX_IMAGES_BUCKET=my-bucket  # Preferred
    IMAGES_BUCKET=my-bucket      # Legacy fallback
"""

import logging
import os
from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings from environment variables.

    All settings support both BMX_ prefixed names (new standard) and legacy names.
    The BMX_ prefix takes precedence when both are set.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )

    # Database - supports multiple legacy names for compatibility
    database_url: str = Field(
        default="postgresql://postgres:postgres@localhost:5432/bluemoxon",
        validation_alias=AliasChoices("BMX_DATABASE_URL", "DATABASE_URL"),
    )
    database_secret_arn: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BMX_DATABASE_SECRET_ARN", "DATABASE_SECRET_ARN"),
    )
    database_secret_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BMX_DATABASE_SECRET_NAME", "DATABASE_SECRET_NAME"),
    )

    # AWS
    aws_region: str = Field(
        default="us-east-1",
        validation_alias=AliasChoices("BMX_AWS_REGION", "AWS_REGION"),
    )

    # Cognito
    cognito_user_pool_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "BMX_COGNITO_USER_POOL_ID", "COGNITO_USER_POOL_ID", "cognito_user_pool_id"
        ),
    )
    cognito_app_client_id: str = Field(
        default="",
        validation_alias=AliasChoices(
            "BMX_COGNITO_CLIENT_ID",  # New standard name
            "BMX_COGNITO_APP_CLIENT_ID",  # Alternative BMX name
            "COGNITO_APP_CLIENT_ID",
            "COGNITO_CLIENT_ID",
            "cognito_client_id",
            "cognito_app_client_id",
        ),
    )

    # S3 / CDN - support both staging (IMAGES_*) and prod (S3_BUCKET, CLOUDFRONT_*)
    images_bucket: str = Field(
        default="bluemoxon-images",
        validation_alias=AliasChoices("BMX_IMAGES_BUCKET", "IMAGES_BUCKET", "S3_BUCKET"),
    )
    images_cdn_url: str | None = Field(
        default=None,
        description="CloudFront CDN URL for images (full URL)",
        validation_alias=AliasChoices("BMX_IMAGES_CDN_URL", "IMAGES_CDN_URL", "CLOUDFRONT_URL"),
    )
    images_cdn_domain: str | None = Field(
        default=None,
        description="CloudFront domain (without protocol/path)",
        validation_alias=AliasChoices("BMX_IMAGES_CDN_DOMAIN", "IMAGES_CDN_DOMAIN"),
    )
    backup_bucket: str = Field(
        default="bluemoxon-backups",
        validation_alias=AliasChoices("BMX_BACKUP_BUCKET", "BACKUP_BUCKET"),
    )

    # Local images path (for development)
    local_images_path: str = "/tmp/bluemoxon-images"  # noqa: S108 # nosec B108

    # CORS
    cors_origins: str = Field(
        default="*",
        validation_alias=AliasChoices("BMX_CORS_ORIGINS", "CORS_ORIGINS"),
    )

    # App
    environment: str = Field(
        default="development",
        validation_alias=AliasChoices("BMX_ENVIRONMENT", "ENVIRONMENT"),
    )
    debug: bool = False

    # API Key for CLI/automation access (optional)
    # Supports both raw key (legacy) and hash (new standard)
    api_key: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BMX_API_KEY", "API_KEY"),
    )
    api_key_hash: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BMX_API_KEY_HASH", "API_KEY_HASH"),
    )

    # Editor access control
    allowed_editor_emails: str = Field(
        default="",
        validation_alias=AliasChoices("BMX_ALLOWED_EDITOR_EMAILS", "ALLOWED_EDITOR_EMAILS"),
    )

    # Maintenance mode
    maintenance_mode: str = Field(
        default="false",
        validation_alias=AliasChoices("BMX_MAINTENANCE_MODE", "MAINTENANCE_MODE"),
    )

    # Analysis worker queue
    analysis_queue_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BMX_ANALYSIS_QUEUE_NAME", "ANALYSIS_QUEUE_NAME"),
    )

    # Eval runbook worker queue
    eval_runbook_queue_name: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BMX_EVAL_RUNBOOK_QUEUE_NAME", "EVAL_RUNBOOK_QUEUE_NAME"),
    )


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    # Debug: log env var directly
    logger.info("CORS_ORIGINS env: %s", os.environ.get("CORS_ORIGINS", "NOT SET"))
    settings = Settings()
    logger.info("cors_origins setting: %s", settings.cors_origins)
    return settings
