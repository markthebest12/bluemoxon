#!/usr/bin/env python3
"""BlueMoxon AWS CDK Application."""

import os
import aws_cdk as cdk

from stacks.network import NetworkStack
from stacks.database import DatabaseStack
from stacks.auth import AuthStack
from stacks.storage import StorageStack
from stacks.api import ApiStack
from stacks.frontend import FrontendStack
from stacks.dns import DnsStack
from stacks.pipeline import PipelineStack

app = cdk.App()

# Environment
env = cdk.Environment(
    account=os.environ.get("CDK_DEFAULT_ACCOUNT"),
    region=os.environ.get("CDK_DEFAULT_REGION", "us-east-1"),
)

# Configuration
domain_name = app.node.try_get_context("domain_name") or "bluemoxon.com"
environment_name = app.node.try_get_context("environment") or "prod"

# Network Stack
network_stack = NetworkStack(
    app,
    f"BlueMoxon-{environment_name}-Network",
    env=env,
)

# Database Stack
database_stack = DatabaseStack(
    app,
    f"BlueMoxon-{environment_name}-Database",
    vpc=network_stack.vpc,
    env=env,
)
database_stack.add_dependency(network_stack)

# Auth Stack
auth_stack = AuthStack(
    app,
    f"BlueMoxon-{environment_name}-Auth",
    env=env,
)

# Storage Stack
storage_stack = StorageStack(
    app,
    f"BlueMoxon-{environment_name}-Storage",
    env=env,
)

# API Stack
api_stack = ApiStack(
    app,
    f"BlueMoxon-{environment_name}-Api",
    vpc=network_stack.vpc,
    database_secret=database_stack.db_secret,
    database_security_group=database_stack.db_security_group,
    user_pool=auth_stack.user_pool,
    images_bucket=storage_stack.images_bucket,
    env=env,
)
api_stack.add_dependency(database_stack)
api_stack.add_dependency(auth_stack)
api_stack.add_dependency(storage_stack)

# Frontend Stack
frontend_stack = FrontendStack(
    app,
    f"BlueMoxon-{environment_name}-Frontend",
    api_url=api_stack.api_url,
    env=env,
)
frontend_stack.add_dependency(api_stack)

# DNS Stack (optional - requires domain)
if domain_name:
    dns_stack = DnsStack(
        app,
        f"BlueMoxon-{environment_name}-Dns",
        domain_name=domain_name,
        frontend_distribution=frontend_stack.distribution,
        api_distribution=api_stack.api_distribution if hasattr(api_stack, 'api_distribution') else None,
        env=env,
    )
    dns_stack.add_dependency(frontend_stack)

# Pipeline Stack
pipeline_stack = PipelineStack(
    app,
    f"BlueMoxon-{environment_name}-Pipeline",
    env=env,
)

app.synth()
