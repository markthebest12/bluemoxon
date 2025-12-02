"""Database migration handler for Lambda."""

import json
import logging
import os
import sys

# Add the app directory to the path for alembic to find the models
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import boto3  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url() -> str:
    """Get database URL from Secrets Manager."""
    secret_arn = os.environ.get("DATABASE_SECRET_ARN")
    if not secret_arn:
        raise ValueError("DATABASE_SECRET_ARN environment variable not set")

    region = os.environ.get("AWS_REGION", "us-west-2")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_arn)
    secret = json.loads(response["SecretString"])

    return (
        f"postgresql://{secret['username']}:{secret['password']}"
        f"@{secret['host']}:{secret['port']}/{secret['dbname']}"
    )


def run_migrations():
    """Run Alembic migrations."""
    database_url = get_database_url()
    logger.info("Running database migrations...")

    # Get the directory where this script is located
    script_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    alembic_cfg = Config(os.path.join(script_dir, "alembic.ini"))

    # Override the database URL
    alembic_cfg.set_main_option("sqlalchemy.url", database_url)
    alembic_cfg.set_main_option("script_location", os.path.join(script_dir, "alembic"))

    # Run the migration
    command.upgrade(alembic_cfg, "head")
    logger.info("Migrations completed successfully!")


def handler(event, context):
    """Lambda handler for running migrations."""
    try:
        run_migrations()
        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Migrations completed successfully"}),
        }
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}


if __name__ == "__main__":
    run_migrations()
