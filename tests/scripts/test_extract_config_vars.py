"""Tests for extract_config_vars.py script."""

import textwrap
from pathlib import Path

import pytest

from scripts.extract_config_vars import extract_config_vars, parse_config_source


class TestExtractsBmxSettingFromAliasChoices:
    """Test basic extraction of BMX_* variables from AliasChoices."""

    def test_extracts_single_bmx_var(self):
        """Extract a single BMX variable from AliasChoices."""
        source = textwrap.dedent('''
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                my_setting: str = Field(
                    default="value",
                    validation_alias=AliasChoices("BMX_MY_SETTING", "MY_SETTING"),
                )
        ''')
        result = parse_config_source(source)

        assert len(result["required"]) + len(result["optional"]) == 1
        all_vars = [v["name"] for v in result["required"] + result["optional"]]
        assert "BMX_MY_SETTING" in all_vars

    def test_extracts_multiple_bmx_vars(self):
        """Extract multiple BMX variables from different fields."""
        source = textwrap.dedent('''
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
        ''')
        result = parse_config_source(source)

        all_vars = [v["name"] for v in result["required"] + result["optional"]]
        assert "BMX_SETTING_A" in all_vars
        assert "BMX_SETTING_B" in all_vars

    def test_ignores_non_bmx_vars(self):
        """Only extract BMX_* prefixed variables."""
        source = textwrap.dedent('''
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                my_setting: str = Field(
                    default="value",
                    validation_alias=AliasChoices("OTHER_SETTING", "LEGACY_SETTING"),
                )
        ''')
        result = parse_config_source(source)

        all_vars = [v["name"] for v in result["required"] + result["optional"]]
        assert len(all_vars) == 0


class TestDetectsRequiredSettingNoDefault:
    """Test detection of required settings (no default value)."""

    def test_field_without_default_is_required(self):
        """A field with no default keyword is required."""
        source = textwrap.dedent('''
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                api_key: str = Field(
                    validation_alias=AliasChoices("BMX_API_KEY", "API_KEY"),
                )
        ''')
        result = parse_config_source(source)

        required_names = [v["name"] for v in result["required"]]
        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_API_KEY" in required_names
        assert "BMX_API_KEY" not in optional_names


class TestDetectsRequiredSettingEllipsisDefault:
    """Test detection of required settings (default=... ellipsis)."""

    def test_field_with_ellipsis_default_is_required(self):
        """A field with default=... is required."""
        source = textwrap.dedent('''
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                database_url: str = Field(
                    default=...,
                    validation_alias=AliasChoices("BMX_DATABASE_URL", "DATABASE_URL"),
                )
        ''')
        result = parse_config_source(source)

        required_names = [v["name"] for v in result["required"]]
        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_DATABASE_URL" in required_names
        assert "BMX_DATABASE_URL" not in optional_names


class TestDetectsOptionalWithNoneType:
    """Test detection of optional settings (type includes | None)."""

    def test_field_with_none_type_is_optional(self):
        """A field with str | None type is optional."""
        source = textwrap.dedent('''
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                api_key: str | None = Field(
                    default=None,
                    validation_alias=AliasChoices("BMX_API_KEY", "API_KEY"),
                )
        ''')
        result = parse_config_source(source)

        required_names = [v["name"] for v in result["required"]]
        optional_names = [v["name"] for v in result["optional"]]

        assert "BMX_API_KEY" not in required_names
        assert "BMX_API_KEY" in optional_names

    def test_field_with_none_type_even_without_explicit_default(self):
        """A field with None in union type is optional even without explicit default."""
        source = textwrap.dedent('''
            from pydantic import AliasChoices, Field
            from pydantic_settings import BaseSettings

            class Settings(BaseSettings):
                optional_setting: str | None = Field(
                    validation_alias=AliasChoices("BMX_OPTIONAL", "OPTIONAL"),
                )
        ''')
        result = parse_config_source(source)

        optional_names = [v["name"] for v in result["optional"]]
        assert "BMX_OPTIONAL" in optional_names


class TestIncludesLineNumbers:
    """Test that line numbers are included in output."""

    def test_line_number_matches_field_definition(self):
        """Line number should point to the field definition line."""
        source = textwrap.dedent('''
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
        ''')
        result = parse_config_source(source)

        all_vars = result["required"] + result["optional"]
        first_var = next(v for v in all_vars if v["name"] == "BMX_FIRST")
        second_var = next(v for v in all_vars if v["name"] == "BMX_SECOND")

        assert first_var["line"] == 6
        assert second_var["line"] == 10

    def test_line_number_present_in_all_vars(self):
        """All extracted variables must have a line number."""
        source = textwrap.dedent('''
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
        ''')
        result = parse_config_source(source)

        for var in result["required"]:
            assert "line" in var
            assert isinstance(var["line"], int)
            assert var["line"] > 0

        for var in result["optional"]:
            assert "line" in var
            assert isinstance(var["line"], int)
            assert var["line"] > 0
