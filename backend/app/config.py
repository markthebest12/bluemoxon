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

    # Redis cache
    redis_url: str = Field(
        default="",
        description="Redis URL for caching (empty = caching disabled)",
        validation_alias=AliasChoices("BMX_REDIS_URL", "REDIS_URL"),
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

    # Entity validation
    entity_validation_mode: str = Field(
        default="enforce",
        description="Entity validation mode: 'log' (warn but allow) or 'enforce' (reject)",
        validation_alias=AliasChoices("BMX_ENTITY_VALIDATION_MODE", "ENTITY_VALIDATION_MODE"),
    )
    entity_match_threshold_publisher: float = Field(
        default=0.80,
        description="Fuzzy match threshold for publishers (0.0-1.0)",
        validation_alias=AliasChoices(
            "BMX_ENTITY_MATCH_THRESHOLD_PUBLISHER", "ENTITY_MATCH_THRESHOLD_PUBLISHER"
        ),
    )
    entity_match_threshold_binder: float = Field(
        default=0.80,
        description="Fuzzy match threshold for binders (0.0-1.0)",
        validation_alias=AliasChoices(
            "BMX_ENTITY_MATCH_THRESHOLD_BINDER", "ENTITY_MATCH_THRESHOLD_BINDER"
        ),
    )
    entity_match_threshold_author: float = Field(
        default=0.75,
        description="Fuzzy match threshold for authors (0.0-1.0, lower due to name variations)",
        validation_alias=AliasChoices(
            "BMX_ENTITY_MATCH_THRESHOLD_AUTHOR", "ENTITY_MATCH_THRESHOLD_AUTHOR"
        ),
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

    # Notifications
    notification_from_email: str | None = Field(
        default=None,
        validation_alias=AliasChoices("BMX_NOTIFICATION_FROM_EMAIL", "NOTIFICATION_FROM_EMAIL"),
    )

    @property
    def is_aws_lambda(self) -> bool:
        """True when running in AWS Lambda (staging or production).

        Detects AWS environment by checking for database secret configuration,
        which is only set when running in Lambda with Secrets Manager.
        Handles empty strings as "not set".
        """
        return bool(self.database_secret_arn) or bool(self.database_secret_name)

    @property
    def is_production(self) -> bool:
        """True only in production environment."""
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    # Debug: log env var directly
    logger.info("CORS_ORIGINS env: %s", os.environ.get("CORS_ORIGINS", "NOT SET"))
    settings = Settings()
    logger.info("cors_origins setting: %s", settings.cors_origins)
    return settings


def get_scraper_environment() -> str:
    """Get environment name for scraper Lambda function naming.

    Uses BMX_SCRAPER_ENVIRONMENT if set (for prod where scraper Lambda is named
    bluemoxon-prod-scraper but BMX_ENVIRONMENT is "production"), otherwise
    falls back to BMX_ENVIRONMENT or ENVIRONMENT.

    Returns:
        Environment string for building scraper function name (e.g., "staging", "prod")
    """
    return (
        os.getenv("BMX_SCRAPER_ENVIRONMENT")
        or os.getenv("BMX_ENVIRONMENT")
        or os.getenv("ENVIRONMENT", "staging")
    )
