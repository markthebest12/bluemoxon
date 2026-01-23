"""Database session management."""

import json
from collections.abc import Generator

import boto3
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.config import get_settings

settings = get_settings()


def get_database_url() -> str:
    """Get database URL, fetching from Secrets Manager if in AWS."""
    secret_id = settings.database_secret_arn or settings.database_secret_name
    if secret_id:
        # Fetch credentials from Secrets Manager
        client = boto3.client("secretsmanager", region_name=settings.aws_region)
        response = client.get_secret_value(SecretId=secret_id)
        secret = json.loads(response["SecretString"])

        # Support both 'dbname' and 'database' key names
        db_name = secret.get("dbname") or secret.get("database", "bluemoxon")

        return (
            f"postgresql://{secret['username']}:{secret['password']}"
            f"@{secret['host']}:{secret['port']}/{db_name}"
        )

    return settings.database_url


engine = create_engine(
    get_database_url(),
    poolclass=NullPool,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """Dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
