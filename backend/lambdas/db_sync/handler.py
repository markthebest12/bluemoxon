"""
Database Sync Lambda Handler

Syncs production database to staging via pg_dump/pg_restore equivalent using psycopg2.
Runs in staging VPC with access to both databases via VPC peering.

Trigger manually via AWS CLI:
    aws lambda invoke --function-name bluemoxon-staging-db-sync \
        --profile staging \
        --payload '{}' \
        response.json

Environment Variables:
    PROD_SECRET_ARN: ARN of production database secret
    STAGING_SECRET_ARN: ARN of staging database secret
    PROD_SECRET_REGION: Region for prod secret (default: us-west-2)
"""

import json
import logging
import os
from typing import Any

import boto3
import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json, register_default_json, register_default_jsonb

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_secret(secret_arn: str, region: str = "us-west-2") -> dict:
    """Retrieve database credentials from Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_arn)
    return json.loads(response["SecretString"])


def get_connection(secret: dict, database: str | None = None):
    """Create a database connection from secret credentials."""
    return psycopg2.connect(
        host=secret["host"],
        port=secret.get("port", 5432),
        user=secret["username"],
        password=secret["password"],
        database=database or secret.get("database") or secret.get("dbname", "postgres"),
        connect_timeout=30,
    )


def get_tables(conn) -> list[str]:
    """Get list of tables in public schema."""
    with conn.cursor() as cur:
        cur.execute("""
            SELECT tablename
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY tablename
        """)
        return [row[0] for row in cur.fetchall()]


def get_table_columns(conn, table: str) -> list[str]:
    """Get column names for a table."""
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            ORDER BY ordinal_position
        """,
            (table,),
        )
        return [row[0] for row in cur.fetchall()]


def adapt_row_for_insert(row: tuple) -> tuple:
    """Convert Python dicts/lists in row to Json for psycopg2 insertion."""
    adapted = []
    for value in row:
        if isinstance(value, dict):
            # JSONB columns come back as dict, wrap for reinsertion
            adapted.append(Json(value))
        elif isinstance(value, list) and value and isinstance(value[0], dict):
            # Array of JSON objects
            adapted.append(Json(value))
        else:
            adapted.append(value)
    return tuple(adapted)


def copy_table_data(prod_conn, staging_conn, table: str, columns: list[str]) -> int:
    """Copy data from production table to staging table."""
    # Get data from production
    with prod_conn.cursor() as prod_cur:
        column_list = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
        query = sql.SQL("SELECT {} FROM {}").format(column_list, sql.Identifier(table))
        prod_cur.execute(query)
        rows = prod_cur.fetchall()

    if not rows:
        return 0

    # Adapt rows to handle JSONB columns (dicts need to be wrapped in Json())
    adapted_rows = [adapt_row_for_insert(row) for row in rows]

    # Insert into staging
    with staging_conn.cursor() as staging_cur:
        placeholders = sql.SQL(", ").join(sql.Placeholder() for _ in columns)
        column_list = sql.SQL(", ").join(sql.Identifier(c) for c in columns)
        insert_query = sql.SQL("INSERT INTO {} ({}) VALUES ({})").format(
            sql.Identifier(table), column_list, placeholders
        )

        staging_cur.executemany(insert_query, adapted_rows)
        staging_conn.commit()

    return len(rows)


def get_table_ddl(conn, table: str) -> str:
    """Get CREATE TABLE DDL for a table using pg_catalog for accurate types."""
    with conn.cursor() as cur:
        # Use pg_catalog with format_type() for accurate type names
        # This properly handles ARRAY, JSONB, TSVECTOR, etc.
        cur.execute(
            """
            SELECT
                a.attname as column_name,
                format_type(a.atttypid, a.atttypmod) as data_type,
                a.attnotnull as not_null,
                pg_get_expr(d.adbin, d.adrelid) as column_default
            FROM pg_attribute a
            LEFT JOIN pg_attrdef d ON a.attrelid = d.adrelid AND a.attnum = d.adnum
            WHERE a.attrelid = %s::regclass
              AND a.attnum > 0
              AND NOT a.attisdropped
            ORDER BY a.attnum
        """,
            (table,),
        )
        columns = cur.fetchall()

        if not columns:
            return ""

        # Build column definitions
        col_defs = []
        for col_name, data_type, not_null, default in columns:
            col_def = f'"{col_name}" {data_type}'
            if not_null:
                col_def += " NOT NULL"
            if default and "nextval" not in str(default):  # Skip sequence defaults
                col_def += f" DEFAULT {default}"
            col_defs.append(col_def)

        # Get primary key
        cur.execute(
            """
            SELECT a.attname
            FROM pg_index i
            JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey)
            WHERE i.indrelid = %s::regclass AND i.indisprimary
        """,
            (table,),
        )
        pk_cols = [row[0] for row in cur.fetchall()]

        ddl = f'CREATE TABLE IF NOT EXISTS "{table}" (\n  '
        ddl += ",\n  ".join(col_defs)
        if pk_cols:
            ddl += f",\n  PRIMARY KEY ({', '.join(pk_cols)})"
        ddl += "\n)"

        return ddl


def ensure_table_exists(prod_conn, staging_conn, table: str) -> bool:
    """Create table in staging if it doesn't exist."""
    # Check if table exists in staging
    with staging_conn.cursor() as cur:
        cur.execute(
            """
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = %s
            )
        """,
            (table,),
        )
        exists = cur.fetchone()[0]

    if exists:
        return True

    # Get DDL from prod and create in staging
    ddl = get_table_ddl(prod_conn, table)
    if not ddl:
        return False

    logger.info(f"Creating table {table} in staging...")
    try:
        with staging_conn.cursor() as cur:
            cur.execute(ddl)
            staging_conn.commit()
        logger.info(f"Created table {table}")
        return True
    except Exception as e:
        logger.error(f"Failed to create table {table}: {e}")
        staging_conn.rollback()
        return False


def validate_sync(prod_conn, staging_conn, results: dict) -> dict:
    """Validate that staging matches production after sync."""
    validation = {"passed": True, "issues": []}

    prod_tables = set(get_tables(prod_conn))
    staging_tables = set(get_tables(staging_conn))

    # Check for missing tables
    missing = prod_tables - staging_tables
    if missing:
        validation["passed"] = False
        validation["issues"].append(f"Missing tables in staging: {sorted(missing)}")

    # Verify row counts for synced tables
    synced_table_names = {t["table"] for t in results["tables_synced"]}
    for table in synced_table_names:
        with prod_conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
            prod_count = cur.fetchone()[0]

        with staging_conn.cursor() as cur:
            cur.execute(sql.SQL("SELECT COUNT(*) FROM {}").format(sql.Identifier(table)))
            staging_count = cur.fetchone()[0]

        if prod_count != staging_count:
            validation["passed"] = False
            validation["issues"].append(
                f"Row count mismatch for {table}: prod={prod_count}, staging={staging_count}"
            )

    return validation


def sync_databases(prod_secret: dict, staging_secret: dict, create_tables: bool = True) -> dict:
    """
    Sync all tables from production to staging.

    Strategy:
    1. Connect to both databases
    2. Get list of tables from production
    3. For each table:
       - Create table in staging if it doesn't exist (when create_tables=True)
       - Truncate staging table
       - Copy all data from prod to staging
    4. Validate sync results
    5. Report results
    """
    results = {
        "tables_synced": [],
        "tables_failed": [],
        "tables_created": [],
        "total_rows": 0,
        "validation": None,
    }

    prod_conn = None
    staging_conn = None

    try:
        logger.info("Connecting to production database...")
        prod_conn = get_connection(prod_secret)
        logger.info(f"Connected to production: {prod_secret['host']}")

        logger.info("Connecting to staging database...")
        staging_conn = get_connection(staging_secret)
        logger.info(f"Connected to staging: {staging_secret['host']}")

        # Get tables from production
        tables = get_tables(prod_conn)
        logger.info(f"Found {len(tables)} tables to sync: {tables}")

        # Disable foreign key checks for staging
        with staging_conn.cursor() as cur:
            cur.execute("SET session_replication_role = 'replica';")
            staging_conn.commit()

        # Sync each table
        for table in tables:
            try:
                logger.info(f"Syncing table: {table}")

                # Create table if it doesn't exist
                if create_tables:
                    if ensure_table_exists(prod_conn, staging_conn, table):
                        # Check if we just created it
                        with staging_conn.cursor() as cur:
                            cur.execute(
                                """
                                SELECT COUNT(*) FROM information_schema.tables
                                WHERE table_schema = 'public' AND table_name = %s
                            """,
                                (table,),
                            )
                        results["tables_created"].append(table)

                columns = get_table_columns(prod_conn, table)

                if not columns:
                    logger.warning(f"No columns found for table {table}, skipping")
                    continue

                # Truncate staging table
                with staging_conn.cursor() as cur:
                    cur.execute(sql.SQL("TRUNCATE TABLE {} CASCADE").format(sql.Identifier(table)))
                    staging_conn.commit()

                # Copy data
                rows_copied = copy_table_data(prod_conn, staging_conn, table, columns)
                results["tables_synced"].append({"table": table, "rows": rows_copied})
                results["total_rows"] += rows_copied
                logger.info(f"Synced {table}: {rows_copied} rows")

            except Exception as e:
                logger.error(f"Failed to sync table {table}: {e}")
                results["tables_failed"].append({"table": table, "error": str(e)})
                staging_conn.rollback()

        # Re-enable foreign key checks
        with staging_conn.cursor() as cur:
            cur.execute("SET session_replication_role = 'origin';")
            staging_conn.commit()

        # Validate sync results
        logger.info("Validating sync results...")
        results["validation"] = validate_sync(prod_conn, staging_conn, results)
        if results["validation"]["passed"]:
            logger.info("Validation passed!")
        else:
            logger.warning(f"Validation issues: {results['validation']['issues']}")

    finally:
        if prod_conn:
            prod_conn.close()
        if staging_conn:
            staging_conn.close()

    return results


def handler(event: dict, context: Any) -> dict:
    """Lambda handler for database sync."""
    logger.info("Starting database sync...")
    logger.info(f"Event: {json.dumps(event)}")

    # Get configuration from environment
    staging_secret_arn = os.environ.get("STAGING_SECRET_ARN")

    # Prod credentials can come from:
    # 1. Direct environment variables (PROD_DB_HOST, PROD_DB_USER, PROD_DB_PASSWORD, PROD_DB_NAME)
    # 2. Secret ARN (requires cross-account KMS access or staging-local secret)
    prod_db_host = os.environ.get("PROD_DB_HOST")
    prod_db_user = os.environ.get("PROD_DB_USER")
    prod_db_password = os.environ.get("PROD_DB_PASSWORD")
    prod_db_name = os.environ.get("PROD_DB_NAME", "bluemoxon")
    prod_secret_arn = os.environ.get("PROD_SECRET_ARN")

    if not staging_secret_arn:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": "Missing STAGING_SECRET_ARN environment variable"}),
        }

    try:
        # Get prod credentials - prefer direct env vars over secret ARN
        logger.info("Fetching database credentials...")

        if prod_db_host and prod_db_user and prod_db_password:
            logger.info("Using production credentials from environment variables")
            prod_secret = {
                "host": prod_db_host,
                "username": prod_db_user,
                "password": prod_db_password,
                "database": prod_db_name,
                "port": int(os.environ.get("PROD_DB_PORT", "5432")),
            }
        elif prod_secret_arn:
            logger.info("Fetching production credentials from Secrets Manager...")
            prod_region = os.environ.get("PROD_SECRET_REGION", "us-west-2")
            prod_secret = get_secret(prod_secret_arn, prod_region)
        else:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "Missing production database credentials. Set PROD_DB_HOST/USER/PASSWORD or PROD_SECRET_ARN"
                    }
                ),
            }

        # Get staging credentials from secret
        staging_secret = get_secret(staging_secret_arn, "us-west-2")

        # Perform sync
        results = sync_databases(prod_secret, staging_secret)

        logger.info(f"Sync complete: {json.dumps(results)}")

        # Determine status based on failures and validation
        has_failures = len(results["tables_failed"]) > 0
        validation_failed = results.get("validation", {}).get("passed") is False

        if has_failures or validation_failed:
            return {
                "statusCode": 500,
                "body": json.dumps(
                    {
                        "error": "Database sync completed with failures",
                        "results": results,
                    }
                ),
            }

        return {
            "statusCode": 200,
            "body": json.dumps(
                {
                    "message": "Database sync completed successfully",
                    "results": results,
                }
            ),
        }

    except Exception as e:
        logger.error(f"Sync failed: {e}", exc_info=True)
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
        }
