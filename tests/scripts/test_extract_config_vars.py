"""Tests for extract_config_vars.py script."""

import textwrap
from pathlib import Path


from scripts.extract_config_vars import extract_config_vars, parse_config_source


class TestExtractsBmxSettingFromAliasChoices:
    """Test basic extraction of BMX_* variables from AliasChoices."""

    def test_extracts_single_bmx_var(self):
        """Extract a single BMX variable from AliasChoices."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                my_setting: str = Field(
                    default="value",
                    validation_alias=AliasChoices("BMX_MY_SETTING", "MY_SETTING"),
                )
        """)
        result = parse_config_source(source)

        assert len(result["required"]) + len(result["optional"]) == 1
        all_vars = [v["name"] for v in result["required"] + result["optional"]]
        assert "BMX_MY_SETTING" in all_vars

    def test_extracts_multiple_bmx_vars(self):
        """Extract multiple BMX variables from different fields."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                setting_a: str = Field(
                    default="a",
                    validation_alias=AliasChoices("BMX_SETTING_A", "SETTING_A"),
                )
                setting_b: str = Field(
                    default="b",
                    validation_alias=AliasChoices("BMX_SETTING_B", "SETTING_B"),
                )
        """)
        result = parse_config_source(source)

        all_vars = [v["name"] for v in result["required"] + result["optional"]]
        assert "BMX_SETTING_A" in all_vars
        assert "BMX_SETTING_B" in all_vars

    def test_ignores_non_bmx_vars(self):
        """Only extract BMX_* prefixed variables."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                my_setting: str = Field(
                    default="value",
                    validation_alias=AliasChoices("OTHER_SETTING", "LEGACY_SETTING"),
                )
        """)
        result = parse_config_source(source)

        all_vars = [v["name"] for v in result["required"] + result["optional"]]
        assert len(all_vars) == 0


class TestDetectsRequiredSettingNoDefault:
    """Test detection of required settings (no default value)."""

    def test_field_without_default_is_required(self):
        """A field with no default keyword is required."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                api_key: str = Field(
                    validation_alias=AliasChoices("BMX_API_KEY", "API_KEY"),
                )
        """)
        result = parse_config_source(source)

        required_names = [v["name"] for v in result["required"]]
        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_API_KEY" in required_names
        assert "BMX_API_KEY" not in optional_names


class TestDetectsRequiredSettingEllipsisDefault:
    """Test detection of required settings (default=... ellipsis)."""

    def test_field_with_ellipsis_default_is_required(self):
        """A field with default=... is required."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                database_url: str = Field(
                    default=...,
                    validation_alias=AliasChoices("BMX_DATABASE_URL", "DATABASE_URL"),
                )
        """)
        result = parse_config_source(source)

        required_names = [v["name"] for v in result["required"]]
        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_DATABASE_URL" in required_names
        assert "BMX_DATABASE_URL" not in optional_names


class TestDetectsOptionalWithNoneType:
    """Test detection of optional settings (type includes None)."""

    def test_field_with_union_none_type_is_optional(self):
        """A field with str | None type is optional."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                api_key: str | None = Field(
                    default=None,
                    validation_alias=AliasChoices("BMX_API_KEY", "API_KEY"),
                )
        """)
        result = parse_config_source(source)

        required_names = [v["name"] for v in result["required"]]
        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_API_KEY" not in required_names
        assert "BMX_API_KEY" in optional_names

    def test_field_with_none_type_even_without_explicit_default(self):
        """A field with None in union type is optional even without explicit default."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                optional_setting: str | None = Field(
                    validation_alias=AliasChoices("BMX_OPTIONAL", "OPTIONAL"),
                )
        """)
        result = parse_config_source(source)

        optional_names = [v["name"] for v in result["optional"]]
        assert "BMX_OPTIONAL" in optional_names

    def test_field_with_typing_optional_is_optional(self):
        """A field with Optional[str] type is optional."""
        source = textwrap.dedent("""
            from typing import Optional
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                api_key: Optional[str] = Field(
                    default=None,
                    validation_alias=AliasChoices("BMX_API_KEY", "API_KEY"),
                )
        """)
        result = parse_config_source(source)

        required_names = [v["name"] for v in result["required"]]
        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_API_KEY" not in required_names
        assert "BMX_API_KEY" in optional_names

    def test_field_with_typing_union_none_is_optional(self):
        """A field with Union[str, None] type is optional."""
        source = textwrap.dedent("""
            from typing import Union
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                api_key: Union[str, None] = Field(
                    default=None,
                    validation_alias=AliasChoices("BMX_API_KEY", "API_KEY"),
                )
        """)
        result = parse_config_source(source)

        required_names = [v["name"] for v in result["required"]]
        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_API_KEY" not in required_names
        assert "BMX_API_KEY" in optional_names


class TestIncludesSourceInfo:
    """Test that source info (filename:line) is included in output."""

    def test_source_includes_line_number(self):
        """Source should include filename and line number."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                first_setting: str = Field(
                    default="value",
                    validation_alias=AliasChoices("BMX_FIRST", "FIRST"),
                )
                second_setting: str = Field(
                    default="value2",
                    validation_alias=AliasChoices("BMX_SECOND", "SECOND"),
                )
        """)
        result = parse_config_source(source, "test.py")

        all_vars = result["required"] + result["optional"]
        first_var = next(v for v in all_vars if v["name"] == "BMX_FIRST")
        second_var = next(v for v in all_vars if v["name"] == "BMX_SECOND")

        assert first_var["source"] == "test.py:6"
        assert second_var["source"] == "test.py:10"

    def test_source_present_in_all_vars(self):
        """All extracted variables must have source info."""
        source = textwrap.dedent("""
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                req_setting: str = Field(
                    validation_alias=AliasChoices("BMX_REQ", "REQ"),
                )
                opt_setting: str | None = Field(
                    default=None,
                    validation_alias=AliasChoices("BMX_OPT", "OPT"),
                )
        """)
        result = parse_config_source(source, "config.py")

        for var in result["required"]:
            assert "source" in var
            assert isinstance(var["source"], str)
            assert ":" in var["source"]

        for var in result["optional"]:
            assert "source" in var
            assert isinstance(var["source"], str)
            assert ":" in var["source"]


class TestParsesRealConfigFile:
    """Integration test against the actual config.py file."""

    def test_extracts_known_bmx_vars(self, backend_config_path: Path):
        """Extract known BMX variables from the real config file."""
        result = extract_config_vars(backend_config_path)

        all_names = [v["name"] for v in result["required"] + result["optional"]]

        assert "BMX_DATABASE_URL" in all_names
        assert "BMX_AWS_REGION" in all_names
        assert "BMX_COGNITO_USER_POOL_ID" in all_names
        assert "BMX_IMAGES_BUCKET" in all_names
        assert "BMX_ENVIRONMENT" in all_names

    def test_correctly_classifies_optional_vars(self, backend_config_path: Path):
        """Variables with | None type should be classified as optional."""
        result = extract_config_vars(backend_config_path)

        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_DATABASE_SECRET_ARN" in optional_names
        assert "BMX_DATABASE_SECRET_NAME" in optional_names
        assert "BMX_IMAGES_CDN_URL" in optional_names
        assert "BMX_API_KEY" in optional_names

    def test_all_vars_have_source_info(self, backend_config_path: Path):
        """All extracted variables should have source info (filename:line)."""
        result = extract_config_vars(backend_config_path)

        for var in result["required"] + result["optional"]:
            assert "source" in var
            assert isinstance(var["source"], str)
            assert "config.py:" in var["source"]

    def test_extracts_reasonable_number_of_vars(self, backend_config_path: Path):
        """Should extract a reasonable number of variables (sanity check)."""
        result = extract_config_vars(backend_config_path)

        total = len(result["required"]) + len(result["optional"])
        assert total >= 10
        assert total <= 50
