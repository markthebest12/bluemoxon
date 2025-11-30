"""Data import handler for Lambda - imports SQL from S3 into Aurora."""

import io
import json
import logging
import os
import re

import boto3
import psycopg2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_db_credentials() -> dict:
    """Get database credentials from Secrets Manager."""
    secret_arn = os.environ.get("DATABASE_SECRET_ARN")
    if not secret_arn:
        raise ValueError("DATABASE_SECRET_ARN environment variable not set")

    region = os.environ.get("AWS_REGION", "us-west-2")
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])


def import_from_s3(bucket: str, key: str) -> dict:
    """Import SQL from S3 file into database using COPY format."""
    logger.info(f"Importing data from s3://{bucket}/{key}")

    # Download SQL from S3
    s3 = boto3.client("s3")
    response = s3.get_object(Bucket=bucket, Key=key)
    sql_content = response["Body"].read().decode("utf-8")

    # Get database credentials
    creds = get_db_credentials()

    # Connect using psycopg2 directly for COPY support
    conn = psycopg2.connect(
        host=creds['host'],
        port=creds['port'],
        database=creds['dbname'],
        user=creds['username'],
        password=creds['password']
    )

    success_count = 0
    error_count = 0
    errors = []

    try:
        cursor = conn.cursor()

        # Parse COPY blocks and execute them
        # COPY format: COPY tablename (cols) FROM stdin; data... \.
        copy_pattern = re.compile(
            r'COPY\s+([\w.]+)\s*\(([^)]+)\)\s+FROM\s+stdin;(.*?)\\\.',
            re.DOTALL | re.IGNORECASE
        )

        for match in copy_pattern.finditer(sql_content):
            table = match.group(1)
            columns = match.group(2)
            data = match.group(3).strip()

            if not data:
                continue

            logger.info(f"Importing data into {table}")

            try:
                # Use copy_expert for COPY FROM stdin
                copy_sql = f"COPY {table} ({columns}) FROM stdin"
                cursor.copy_expert(copy_sql, io.StringIO(data))
                success_count += 1
            except Exception as e:
                error_count += 1
                error_msg = f"Table {table}: {str(e)[:200]}"
                errors.append(error_msg)
                logger.warning(error_msg)
                # Rollback and continue with a new transaction
                conn.rollback()
                continue

        conn.commit()
        logger.info(f"Import completed: {success_count} tables imported, {error_count} errors")

    except Exception as e:
        conn.rollback()
        logger.error(f"Import failed: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    return {
        "success_count": success_count,
        "error_count": error_count,
        "errors": errors[:10],
    }


def handler(event, context):
    """Lambda handler for data import."""
    try:
        bucket = event.get("bucket", "bluemoxon-images")
        key = event.get("key", "data-import/bluemoxon-data.sql")

        result = import_from_s3(bucket, key)

        return {
            "statusCode": 200,
            "body": json.dumps({
                "message": "Data import completed",
                **result
            })
        }
    except Exception as e:
        logger.error(f"Data import failed: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }


if __name__ == "__main__":
    # For local testing
    import sys
    if len(sys.argv) > 2:
        result = import_from_s3(sys.argv[1], sys.argv[2])
        print(json.dumps(result, indent=2))
