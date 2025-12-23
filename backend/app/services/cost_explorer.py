"""AWS Cost Explorer service for retrieving Bedrock costs."""

from datetime import UTC, datetime, timedelta
from typing import Any

import boto3
from botocore.exceptions import ClientError

from app.services.bedrock import MODEL_USAGE

# Cache for cost data (simple in-memory cache)
_cost_cache: dict[str, Any] = {}
CACHE_TTL_SECONDS = 3600  # 1 hour

# Map AWS service names to our model names
AWS_SERVICE_TO_MODEL = {
    "Claude Sonnet 4.5 (Amazon Bedrock Edition)": "Sonnet 4.5",
    "Claude Opus 4.5 (Amazon Bedrock Edition)": "Opus 4.5",
    "Claude 3 Haiku (Amazon Bedrock Edition)": "Haiku 3",
    "Claude 3.5 Sonnet (Amazon Bedrock Edition)": "Sonnet 3.5",
    "Claude 3.5 Sonnet v2 (Amazon Bedrock Edition)": "Sonnet 3.5 v2",
}

# Model name to usage description mapping
MODEL_USAGE_DESCRIPTIONS = {
    "Sonnet 4.5": MODEL_USAGE.get("sonnet", "Primary analysis"),
    "Opus 4.5": MODEL_USAGE.get("opus", "High quality analysis"),
    "Haiku 3": MODEL_USAGE.get("haiku", "Fast extraction"),
    "Sonnet 3.5": "Legacy analysis",
    "Sonnet 3.5 v2": "Legacy analysis",
}

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


def _get_cache_key() -> str:
    """Generate cache key based on current month."""
    now = datetime.now(UTC)
    return f"costs_{now.year}_{now.month}"


def _is_cache_valid() -> bool:
    """Check if cache is still valid."""
    cache_key = _get_cache_key()
    if cache_key not in _cost_cache:
        return False
    cached_at = _cost_cache[cache_key].get("cached_at")
    if not cached_at:
        return False
    age = (datetime.now(UTC) - datetime.fromisoformat(cached_at)).total_seconds()
    return age < CACHE_TTL_SECONDS


def get_costs() -> dict[str, Any]:
    """Get cost data from AWS Cost Explorer.

    Returns cached data if available and fresh, otherwise fetches from AWS.
    """
    cache_key = _get_cache_key()

    if _is_cache_valid():
        return _cost_cache[cache_key]

    try:
        costs = _fetch_costs_from_aws()
        _cost_cache[cache_key] = costs
        return costs
    except ClientError as e:
        # Return error response, cache for 5 minutes to avoid hammering
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


def _fetch_costs_from_aws() -> dict[str, Any]:
    """Fetch cost data from AWS Cost Explorer."""
    client = boto3.client("ce", region_name="us-east-1")  # CE is only in us-east-1

    # Get current account ID for filtering in consolidated billing orgs
    account_id = _get_current_account_id()
    account_filter = {"Dimensions": {"Key": "LINKED_ACCOUNT", "Values": [account_id]}}

    now = datetime.now(UTC)
    period_start = now.replace(day=1).strftime("%Y-%m-%d")
    period_end = (now + timedelta(days=1)).strftime("%Y-%m-%d")

    # Get monthly costs grouped by service (filtered by current account)
    monthly_response = client.get_cost_and_usage(
        TimePeriod={"Start": period_start, "End": period_end},
        Granularity="MONTHLY",
        Metrics=["UnblendedCost"],
        GroupBy=[{"Type": "DIMENSION", "Key": "SERVICE"}],
        Filter=account_filter,
    )

    # Get daily costs for trend (last 14 days)
    trend_start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    daily_response = client.get_cost_and_usage(
        TimePeriod={"Start": trend_start, "End": period_end},
        Granularity="DAILY",
        Metrics=["UnblendedCost"],
        Filter={
            "And": [
                account_filter,
                {
                    "Dimensions": {
                        "Key": "SERVICE",
                        "Values": list(AWS_SERVICE_TO_MODEL.keys()),
                    }
                },
            ]
        },
    )

    # Parse monthly costs
    bedrock_models = []
    other_costs = {}
    total_aws_cost = 0.0

    for result in monthly_response.get("ResultsByTime", []):
        for group in result.get("Groups", []):
            service_name = group["Keys"][0]
            cost = float(group["Metrics"]["UnblendedCost"]["Amount"])
            total_aws_cost += cost

            if service_name in AWS_SERVICE_TO_MODEL:
                model_name = AWS_SERVICE_TO_MODEL[service_name]
                bedrock_models.append(
                    {
                        "model_name": model_name,
                        "usage": MODEL_USAGE_DESCRIPTIONS.get(model_name, ""),
                        "mtd_cost": round(cost, 2),
                    }
                )
            elif service_name in OTHER_SERVICES:
                # Shorten service names
                short_name = (
                    service_name.replace("Amazon ", "").replace("AWS ", "").replace(" Service", "")
                )
                other_costs[short_name] = round(cost, 2)

    # Sort bedrock models by cost descending
    bedrock_models.sort(key=lambda x: x["mtd_cost"], reverse=True)
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
