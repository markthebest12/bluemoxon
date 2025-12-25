"""Tests for Cost Explorer service."""

from unittest.mock import MagicMock, patch

from app.services.cost_explorer import (
    _is_management_account,
    get_costs,
)


class TestIsManagementAccount:
    """Tests for management account detection."""

    def test_returns_true_when_account_is_management_account(self):
        """When current account equals org master account, return True."""
        with (
            patch("app.services.cost_explorer.boto3.client") as mock_boto,
        ):
            # Mock STS to return account ID
            mock_sts = MagicMock()
            mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

            # Mock Organizations to return same account as master
            mock_orgs = MagicMock()
            mock_orgs.describe_organization.return_value = {
                "Organization": {"MasterAccountId": "123456789012"}
            }

            def client_factory(service_name, **kwargs):
                if service_name == "sts":
                    return mock_sts
                if service_name == "organizations":
                    return mock_orgs
                return MagicMock()

            mock_boto.side_effect = client_factory

            result = _is_management_account()
            assert result is True

    def test_returns_false_when_account_is_linked_account(self):
        """When current account differs from org master, return False."""
        with (
            patch("app.services.cost_explorer.boto3.client") as mock_boto,
        ):
            # Mock STS to return staging account ID
            mock_sts = MagicMock()
            mock_sts.get_caller_identity.return_value = {"Account": "652617421195"}

            # Mock Organizations to return different (management) account
            mock_orgs = MagicMock()
            mock_orgs.describe_organization.return_value = {
                "Organization": {"MasterAccountId": "266672885920"}
            }

            def client_factory(service_name, **kwargs):
                if service_name == "sts":
                    return mock_sts
                if service_name == "organizations":
                    return mock_orgs
                return MagicMock()

            mock_boto.side_effect = client_factory

            result = _is_management_account()
            assert result is False

    def test_returns_false_when_not_in_organization(self):
        """When account is not in an org, return False (safe default)."""
        from botocore.exceptions import ClientError

        with (
            patch("app.services.cost_explorer.boto3.client") as mock_boto,
        ):
            mock_sts = MagicMock()
            mock_sts.get_caller_identity.return_value = {"Account": "123456789012"}

            mock_orgs = MagicMock()
            mock_orgs.describe_organization.side_effect = ClientError(
                {"Error": {"Code": "AWSOrganizationsNotInUseException"}},
                "DescribeOrganization",
            )

            def client_factory(service_name, **kwargs):
                if service_name == "sts":
                    return mock_sts
                if service_name == "organizations":
                    return mock_orgs
                return MagicMock()

            mock_boto.side_effect = client_factory

            result = _is_management_account()
            assert result is False


class TestGetCostsAccountFilter:
    """Tests that LINKED_ACCOUNT filter is correctly applied."""

    def _make_mock_response(self):
        """Create a valid Cost Explorer response structure."""
        return {
            "ResultsByTime": [
                {
                    "TimePeriod": {"Start": "2025-12-01", "End": "2025-12-02"},
                    "Groups": [],
                    "Total": {"UnblendedCost": {"Amount": "0", "Unit": "USD"}},
                }
            ]
        }

    def test_management_account_does_not_use_linked_account_filter(self):
        """Management account should NOT use LINKED_ACCOUNT filter."""
        with (
            patch("app.services.cost_explorer._is_management_account", return_value=True),
            patch(
                "app.services.cost_explorer._get_current_account_id", return_value="266672885920"
            ),
            patch("app.services.cost_explorer._is_cache_valid", return_value=False),
            patch("app.services.cost_explorer.boto3.client") as mock_boto,
        ):
            mock_ce = MagicMock()
            mock_ce.get_cost_and_usage.return_value = self._make_mock_response()
            mock_boto.return_value = mock_ce

            # Clear cache
            from app.services.cost_explorer import _cost_cache

            _cost_cache.clear()

            get_costs()

            # Check that the monthly call does NOT have LINKED_ACCOUNT filter
            monthly_call = mock_ce.get_cost_and_usage.call_args_list[0]
            call_kwargs = monthly_call[1]
            assert "Filter" not in call_kwargs, "Management account should NOT have Filter"

    def test_linked_account_uses_linked_account_filter(self):
        """Linked account SHOULD use LINKED_ACCOUNT filter."""
        with (
            patch("app.services.cost_explorer._is_management_account", return_value=False),
            patch(
                "app.services.cost_explorer._get_current_account_id", return_value="652617421195"
            ),
            patch("app.services.cost_explorer._is_cache_valid", return_value=False),
            patch("app.services.cost_explorer.boto3.client") as mock_boto,
        ):
            mock_ce = MagicMock()
            mock_ce.get_cost_and_usage.return_value = self._make_mock_response()
            mock_boto.return_value = mock_ce

            # Clear cache
            from app.services.cost_explorer import _cost_cache

            _cost_cache.clear()

            get_costs()

            # Check that the monthly call HAS LINKED_ACCOUNT filter
            monthly_call = mock_ce.get_cost_and_usage.call_args_list[0]
            call_kwargs = monthly_call[1]
            assert "Filter" in call_kwargs, "Linked account SHOULD have Filter"
            assert call_kwargs["Filter"]["Dimensions"]["Key"] == "LINKED_ACCOUNT"
