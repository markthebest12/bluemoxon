"""Alembic environment configuration."""

import json
import os
from logging.config import fileConfig

import boto3
from sqlalchemy import engine_from_config, pool

from alembic import context
from app.models import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_database_url() -> str:
    """Get database URL, fetching from Secrets Manager if configured."""
    # Check if URL already set (e.g., by migrate.py)
    url = config.get_main_option("sqlalchemy.url")
    if url and "localhost" not in url:
        return url

    # Check for Secrets Manager ARN
    secret_arn = os.environ.get("DATABASE_SECRET_ARN")
    if secret_arn:
        region = os.environ.get("AWS_REGION", "us-west-2")
        client = boto3.client("secretsmanager", region_name=region)
        response = client.get_secret_value(SecretId=secret_arn)
        secret = json.loads(response["SecretString"])
        return (
            f"postgresql://{secret['username']}:{secret['password']}"
            f"@{secret['host']}:{secret['port']}/{secret['dbname']}"
        )

    # Fall back to config/env var
    return url or os.environ.get(
        "DATABASE_URL", "postgresql://bluemoxon:bluemoxon_dev@localhost:5432/bluemoxon"
    )


# Set database URL (supports both local dev and AWS Lambda)
config.set_main_option("sqlalchemy.url", get_database_url())


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
