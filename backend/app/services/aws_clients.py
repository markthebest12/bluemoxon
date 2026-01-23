"""Centralized AWS client factories with caching.

This module provides cached boto3 client instances to avoid creating
multiple client instances for the same AWS service. All clients use
consistent region configuration from AWS_REGION env var or settings.

Usage:
    from app.services.aws_clients import get_s3_client, get_sqs_client, get_lambda_client

    s3 = get_s3_client()
    sqs = get_sqs_client()
    lambda_client = get_lambda_client()
"""

import os
from functools import lru_cache

import boto3

from app.config import get_settings


@lru_cache(maxsize=1)
def get_s3_client():
    """Get cached boto3 S3 client.

    Returns:
        boto3 S3 client configured with the appropriate region.
    """
    settings = get_settings()
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("s3", region_name=region)


@lru_cache(maxsize=1)
def get_sqs_client():
    """Get cached boto3 SQS client.

    Returns:
        boto3 SQS client configured with the appropriate region.
    """
    settings = get_settings()
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("sqs", region_name=region)


@lru_cache(maxsize=1)
def get_lambda_client():
    """Get cached boto3 Lambda client.

    Returns:
        boto3 Lambda client configured with the appropriate region.
    """
    settings = get_settings()
    region = os.environ.get("AWS_REGION", settings.aws_region)
    return boto3.client("lambda", region_name=region)
