"""Cognito client service with caching."""

from functools import lru_cache
from typing import TYPE_CHECKING

import boto3

from app.config import get_settings

if TYPE_CHECKING:
    from mypy_boto3_cognito_idp import CognitoIdentityProviderClient


@lru_cache
def get_cognito_client() -> "CognitoIdentityProviderClient":
    """Get cached Cognito Identity Provider client.

    Raises:
        ValueError: If AWS region is not configured.
    """
    settings = get_settings()
    if not settings.aws_region:
        raise ValueError("AWS region not configured (settings.aws_region is empty)")
    return boto3.client("cognito-idp", region_name=settings.aws_region)
