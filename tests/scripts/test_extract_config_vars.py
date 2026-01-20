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
