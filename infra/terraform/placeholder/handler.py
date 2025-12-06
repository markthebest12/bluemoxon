"""Placeholder Lambda handler - replaced by CI/CD deploy."""

def handler(event, context):
    """Placeholder handler - deploy via CI/CD to update."""
    return {
        "statusCode": 200,
        "headers": {"Content-Type": "application/json"},
        "body": '{"status": "placeholder - deploy to update"}'
    }
