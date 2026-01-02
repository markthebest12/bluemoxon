"""Integration tests package.

Tests in this package make real API calls and require proper AWS credentials.
They are skipped by default and only run when RUN_INTEGRATION_TESTS=1 is set.

Usage:
    AWS_PROFILE=bmx-staging RUN_INTEGRATION_TESTS=1 poetry run pytest \
        tests/integration/ -v -s
"""
