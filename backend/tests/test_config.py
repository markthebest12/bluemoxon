"""Tests for application configuration."""

import os
from unittest.mock import patch

from app.config import Settings


class TestBMXPrefixSupport:
    """Test that BMX_ prefixed env vars take precedence over legacy names."""

    def test_bmx_images_bucket_takes_precedence(self):
        """BMX_IMAGES_BUCKET should override IMAGES_BUCKET."""
        env = {
            "BMX_IMAGES_BUCKET": "bmx-bucket",
            "IMAGES_BUCKET": "legacy-bucket",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.images_bucket == "bmx-bucket"

    def test_legacy_images_bucket_fallback(self):
        """IMAGES_BUCKET should work when BMX_ not set."""
        env = {"IMAGES_BUCKET": "legacy-bucket"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.images_bucket == "legacy-bucket"

    def test_s3_bucket_legacy_fallback(self):
        """S3_BUCKET (prod legacy) should work as fallback."""
        env = {"S3_BUCKET": "prod-bucket"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.images_bucket == "prod-bucket"

    def test_bmx_cognito_takes_precedence(self):
        """BMX_COGNITO_USER_POOL_ID should override legacy names."""
        env = {
            "BMX_COGNITO_USER_POOL_ID": "bmx-pool",
            "COGNITO_USER_POOL_ID": "legacy-pool",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.cognito_user_pool_id == "bmx-pool"

    def test_bmx_cognito_client_id(self):
        """BMX_COGNITO_CLIENT_ID should work."""
        env = {"BMX_COGNITO_CLIENT_ID": "bmx-client"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.cognito_app_client_id == "bmx-client"

    def test_legacy_cognito_client_id_fallback(self):
        """COGNITO_APP_CLIENT_ID should work as fallback."""
        env = {"COGNITO_APP_CLIENT_ID": "legacy-client"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.cognito_app_client_id == "legacy-client"

    def test_bmx_cors_origins(self):
        """BMX_CORS_ORIGINS should override CORS_ORIGINS."""
        env = {
            "BMX_CORS_ORIGINS": "https://bmx.example.com",
            "CORS_ORIGINS": "https://legacy.example.com",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.cors_origins == "https://bmx.example.com"

    def test_bmx_api_key_hash(self):
        """BMX_API_KEY_HASH should work."""
        env = {"BMX_API_KEY_HASH": "sha256-hash-value"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.api_key_hash == "sha256-hash-value"

    def test_legacy_api_key_hash_fallback(self):
        """API_KEY_HASH should work as fallback."""
        env = {"API_KEY_HASH": "legacy-hash"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.api_key_hash == "legacy-hash"

    def test_bmx_images_cdn_url(self):
        """BMX_IMAGES_CDN_URL should override legacy names."""
        env = {
            "BMX_IMAGES_CDN_URL": "https://bmx.cloudfront.net",
            "CLOUDFRONT_URL": "https://legacy.cloudfront.net",
        }
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.images_cdn_url == "https://bmx.cloudfront.net"

    def test_cloudfront_url_legacy_fallback(self):
        """CLOUDFRONT_URL (prod legacy) should work as fallback."""
        env = {"CLOUDFRONT_URL": "https://prod.cloudfront.net"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.images_cdn_url == "https://prod.cloudfront.net"

    def test_bmx_allowed_editor_emails(self):
        """BMX_ALLOWED_EDITOR_EMAILS should work."""
        env = {"BMX_ALLOWED_EDITOR_EMAILS": "user@example.com"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.allowed_editor_emails == "user@example.com"

    def test_bmx_maintenance_mode(self):
        """BMX_MAINTENANCE_MODE should work."""
        env = {"BMX_MAINTENANCE_MODE": "true"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.maintenance_mode == "true"

    def test_bmx_analysis_queue_name(self):
        """BMX_ANALYSIS_QUEUE_NAME should work."""
        env = {"BMX_ANALYSIS_QUEUE_NAME": "my-queue"}
        with patch.dict(os.environ, env, clear=True):
            settings = Settings()
            assert settings.analysis_queue_name == "my-queue"


class TestDefaultValues:
    """Test that default values are set correctly in code.

    Note: pydantic-settings reads from .env file, so we test defaults by
    checking the Field definitions rather than instantiating Settings.
    """

    def test_default_images_bucket_in_code(self):
        """Default images bucket should be bluemoxon-images."""
        # Check the Field default directly
        field_info = Settings.model_fields["images_bucket"]
        assert field_info.default == "bluemoxon-images"

    def test_default_cors_origins_in_code(self):
        """Default CORS should allow all (*)."""
        field_info = Settings.model_fields["cors_origins"]
        assert field_info.default == "*"

    def test_default_environment_in_code(self):
        """Default environment should be development."""
        field_info = Settings.model_fields["environment"]
        assert field_info.default == "development"

    def test_default_cognito_empty_in_code(self):
        """Cognito IDs should default to empty string."""
        pool_field = Settings.model_fields["cognito_user_pool_id"]
        client_field = Settings.model_fields["cognito_app_client_id"]
        assert pool_field.default == ""
        assert client_field.default == ""

    def test_default_maintenance_mode_in_code(self):
        """Maintenance mode should default to false."""
        field_info = Settings.model_fields["maintenance_mode"]
        assert field_info.default == "false"


class TestAliasConfiguration:
    """Test that alias choices are configured correctly."""

    def test_images_bucket_aliases(self):
        """images_bucket should accept BMX_, IMAGES_, and S3_ prefixes."""
        field_info = Settings.model_fields["images_bucket"]
        alias = field_info.validation_alias
        assert "BMX_IMAGES_BUCKET" in alias.choices
        assert "IMAGES_BUCKET" in alias.choices
        assert "S3_BUCKET" in alias.choices

    def test_cognito_client_aliases(self):
        """cognito_app_client_id should accept multiple legacy names."""
        field_info = Settings.model_fields["cognito_app_client_id"]
        alias = field_info.validation_alias
        assert "BMX_COGNITO_CLIENT_ID" in alias.choices
        assert "COGNITO_APP_CLIENT_ID" in alias.choices
        assert "COGNITO_CLIENT_ID" in alias.choices

    def test_images_cdn_url_aliases(self):
        """images_cdn_url should accept CLOUDFRONT_URL legacy name."""
        field_info = Settings.model_fields["images_cdn_url"]
        alias = field_info.validation_alias
        assert "BMX_IMAGES_CDN_URL" in alias.choices
        assert "CLOUDFRONT_URL" in alias.choices
