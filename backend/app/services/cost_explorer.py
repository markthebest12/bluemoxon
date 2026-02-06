"""AWS Cost Explorer service for retrieving Bedrock costs.

Fixes #590: Management account detection for proper cost reporting.
"""

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

import boto3
from botocore.exceptions import ClientError

from app.services.bedrock import MODEL_DISPLAY_NAMES, MODEL_USAGE

logger = logging.getLogger(__name__)

# Cache for cost data (simple in-memory cache)
_cost_cache: dict[str, Any] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour

# Map AWS service names to our model names.
# Current models — derive from MODEL_DISPLAY_NAMES so model bumps auto-propagate.
# Legacy models — static, won't change.
# Note: AWS billing may list "Claude 3 Haiku" or "Claude 3.5 Haiku" depending on
# when the model was provisioned; include both variants so costs are always captured.
AWS_SERVICE_TO_MODEL = {
    # Current models — derive billing names from single source of truth.
    # Pattern: "Claude <DisplayName> (Amazon Bedrock Edition)"
    # Works for Opus/Sonnet; Haiku uses legacy "Claude 3.5 Haiku" naming in AWS billing.
    **{
        f"Claude {display} (Amazon Bedrock Edition)": display
        for key, display in MODEL_DISPLAY_NAMES.items()
        if key != "haiku"  # Haiku billing name doesn't follow this pattern
    },
    # Haiku — AWS bills as "Claude 3.5 Haiku", not "Claude Haiku 3.5"
    "Claude 3.5 Haiku (Amazon Bedrock Edition)": MODEL_DISPLAY_NAMES.get("haiku", "Haiku 3.5"),
    # Legacy models — static (no longer in MODEL_IDS, billing names won't change)
    "Claude Opus 4.5 (Amazon Bedrock Edition)": "Opus 4.5",
    "Claude 3 Haiku (Amazon Bedrock Edition)": "Haiku 3.5",
    "Claude 3.5 Sonnet (Amazon Bedrock Edition)": "Sonnet 3.5",
    "Claude 3.5 Sonnet v2 (Amazon Bedrock Edition)": "Sonnet 3.5 v2",
}

# Build from MODEL_DISPLAY_NAMES so model bumps auto-propagate
MODEL_USAGE_DESCRIPTIONS = {
    display: MODEL_USAGE.get(key, "Analysis") for key, display in MODEL_DISPLAY_NAMES.items()
}
# Legacy models (no longer in MODEL_IDS) — static, won't change
MODEL_USAGE_DESCRIPTIONS["Opus 4.5"] = "Legacy analysis"
MODEL_USAGE_DESCRIPTIONS["Sonnet 3.5"] = "Legacy analysis"
MODEL_USAGE_DESCRIPTIONS["Sonnet 3.5 v2"] = "Legacy analysis"

# Other AWS services to track
OTHER_SERVICES = [
    "AWS Lambda",
    "Amazon Relational Database Service",
    "Amazon Virtual Private Cloud",
    "Amazon Simple Storage Service",
    "Amazon CloudFront",
    "Amazon API Gateway",
    "EC2 - Other",
]


def _get_cache_key(timezone: str | None = None) -> str:
    """Generate cache key based on current month and timezone.

    Args:
        timezone: IANA timezone name. Different timezones may see different
                  "current month" at month boundaries, so we cache separately.
    """
    now = datetime.now(UTC)
    tz_key = timezone or "UTC"
    return f"costs_{now.year}_{now.month}_{tz_key}"


def _is_cache_valid(timezone: str | None = None) -> bool:
    """Check if cache is still valid for the given timezone."""
    cache_key = _get_cache_key(timezone)
    if cache_key not in _cost_cache:
        return False
    cached_at = _cost_cache[cache_key].get("cached_at")
    if not cached_at:
        return False
    age = (datetime.now(UTC) - datetime.fromisoformat(cached_at)).total_seconds()
    return age < CACHE_TTL_SECONDS


def get_costs(timezone: str | None = None, force_refresh: bool = False) -> dict[str, Any]:
    """Get cost data from AWS Cost Explorer.

    Args:
        timezone: Optional IANA timezone name (e.g., "America/Los_Angeles").
                  If provided, uses that timezone to determine the current month.
                  If None, uses UTC.
        force_refresh: If True, bypass cache and fetch fresh data from AWS.

    Returns cached data if available and fresh, otherwise fetches from AWS.
    """
    cache_key = _get_cache_key(timezone)

    if not force_refresh and _is_cache_valid(timezone):
        logger.info("Returning cached cost data")
        return _cost_cache[cache_key]

    try:
        logger.info(f"Fetching fresh cost data from AWS (force_refresh={force_refresh})")
        costs = _fetch_costs_from_aws(timezone=timezone)
        _cost_cache[cache_key] = costs
        return costs
    except ClientError as e:
        # Return error response, cache for 5 minutes to avoid hammering
        logger.error(f"AWS Cost Explorer API error: {e}")
        error_response = {
            "error": str(e),
            "cached_at": datetime.now(UTC).isoformat(),
            "period_start": "",
            "period_end": "",
            "bedrock_models": [],
            "bedrock_total": 0.0,
            "daily_trend": [],
            "other_costs": {},
            "total_aws_cost": 0.0,
        }
        _cost_cache[cache_key] = error_response
        return error_response


def _get_current_account_id() -> str:
    """Get the current AWS account ID."""
    sts = boto3.client("sts")
    return sts.get_caller_identity()["Account"]


def _is_management_account() -> bool:
    """Check if current account is the AWS Organizations management account.

    Returns True if the current account is the management/payer account.
    Returns False if it's a linked/member account or not in an organization.

    The LINKED_ACCOUNT dimension in Cost Explorer doesn't work for the
    management account's own costs - those costs don't appear when filtering
    by the management account's ID.
    """
    try:
        account_id = _get_current_account_id()
        orgs = boto3.client("organizations")
        org = orgs.describe_organization()
        master_account_id = org["Organization"]["MasterAccountId"]
        return account_id == master_account_id
    except ClientError as e:
        # STS or Organizations API call failed. Could be:
        # - Account not in an organization
        # - No permissions for organizations:DescribeOrganization
        # - STS identity check failed
        # Default to False (linked account behavior - apply filter) as conservative fallback.
        logger.warning(f"Could not determine management account status: {e}")
        return False


def _fetch_costs_from_aws(timezone: str | None = None) -> dict[str, Any]:
    """Fetch cost data from AWS Cost Explorer.

    Args:
        timezone: Optional IANA timezone name. If provided, uses that timezone
                  to determine the current month for MTD calculations.
    """
    client = boto3.client("ce", region_name="us-east-1")  # CE is only in us-east-1

    # Check if we're in the management account - if so, skip LINKED_ACCOUNT filter
    # The LINKED_ACCOUNT dimension doesn't work for management account's own costs
    is_mgmt = _is_management_account()

    # Only apply LINKED_ACCOUNT filter for linked/member accounts
    account_filter = None
    if not is_mgmt:
        account_id = _get_current_account_id()
        account_filter = {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [account_id]}}

    # Use provided timezone or default to UTC
    if timezone:
        try:
            tz = ZoneInfo(timezone)
            now = datetime.now(tz)
        except KeyError:
            logger.warning(f"Invalid timezone '{timezone}', falling back to UTC")
            now = datetime.now(UTC)
    else:
        now = datetime.now(UTC)

    period_start = now.replace(day=1).strftime("%Y-%m-%d")
    period_end = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # Build monthly query - with or without account filter
    monthly_query = {
        "TimePeriod": {"Start": period_start, "End": period_end},
        "Granularity": "MONTHLY",
        "Metrics": ["UnblendedCost"],
        "GroupBy": [{"Type": "DIMENSION", "Key": "SERVICE"}],
    }
    if account_filter:
        monthly_query["Filter"] = account_filter

    monthly_response = client.get_cost_and_usage(**monthly_query)

    # Build daily query for trend (last 14 days) - Bedrock services only
    trend_start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    bedrock_filter = {
        "Dimensions": {
            "Key": "SERVICE",
            "Values": list(AWS_SERVICE_TO_MODEL.keys()),
        }
    }

    # Combine filters if we have an account filter
    if account_filter:
        daily_filter = {"And": [account_filter, bedrock_filter]}
    else:
        daily_filter = bedrock_filter

    daily_response = client.get_cost_and_usage(
        TimePeriod={"Start": trend_start, "End": period_end},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        Filter=daily_filter,
    )

    # Seed all known models at $0.00 so they always appear, even with no MTD usage.
    # AWS Cost Explorer only returns services with non-zero spend, so without
    # seeding, models like Haiku would disappear when not used in the current month.
    bedrock_costs: dict[str, dict] = {}
    for model_name in dict.fromkeys(AWS_SERVICE_TO_MODEL.values()):
        bedrock_costs[model_name] = {
            "model_name": model_name,
            "usage": MODEL_USAGE_DESCRIPTIONS.get(model_name, ""),
            "mtd_cost": 0.0,
        }

    # Parse monthly costs — overlay actual AWS data onto seeded models
    other_costs = {}
    total_aws_cost = 0.0

    for result in monthly_response.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            service_name = group["Keys"][0]
            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
            total_aws_cost += cost

            if service_name in AWS_SERVICE_TO_MODEL:
                model_name = AWS_SERVICE_TO_MODEL[service_name]
                bedrock_costs[model_name]["mtd_cost"] = round(
                    bedrock_costs[model_name]["mtd_cost"] + cost, 2
                )
            elif service_name in OTHER_SERVICES:
                # Shorten service names
                short_name = (
                    service_name.replace("Amazon ", "").replace("AWS ", "").replace(" Service", "")
                )
                other_costs[short_name] = round(cost, 2)

    # Sort bedrock models by cost descending
    bedrock_models = sorted(bedrock_costs.values(), key=lambda x: x["mtd_cost"], reverse=True)
    bedrock_total = sum(m["mtd_cost"] for m in bedrock_models)

    # Parse daily trend
    daily_trend = []
    for result in daily_response.get("ResultsByTime", []):
        date = result["TimePeriod"]["Start"]
        cost = float(result.get("Total", {}).get("UnblendedCost", {}).get("Amount", 0))
        if cost > 0:
            daily_trend.append({"date": date, "cost": round(cost, 2)})

    return {
        "period_start": period_start,
        "period_end": period_end,
        "bedrock_models": bedrock_models,
        "bedrock_total": round(bedrock_total, 2),
        "daily_trend": daily_trend,
        "other_costs": other_costs,
        "total_aws_cost": round(total_aws_cost, 2),
        "cached_at": datetime.now(UTC).isoformat(),
    }
