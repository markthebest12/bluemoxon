#!/usr/bin/env python3
"""Extract BMX_* environment variables from config.py using AST parsing.

This script parses the backend config.py file and extracts all environment
variables that use the BMX_* naming convention from AliasChoices definitions.
"""

import ast
import json
from pathlib import Path
from typing import TypedDict


class VarInfo(TypedDict):
    """Information about an extracted variable."""

    name: str
    line: int


class ExtractResult(TypedDict):
    """Result of extracting config variables."""

    required: list[VarInfo]
    optional: list[VarInfo]


def parse_config_source(source: str) -> ExtractResult:
    """Parse Python source code and extract BMX_* variables from AliasChoices.

    Args:
        source: Python source code as string

    Returns:
        Dict with 'required' and 'optional' lists of variable info
    """
    tree = ast.parse(source)
    result: ExtractResult = {"required": [], "optional": []}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    _process_field(item, result)

    return result


def _process_field(node: ast.AnnAssign, result: ExtractResult) -> None:
    """Process a single annotated assignment (field definition).

    Args:
        node: AST annotated assignment node
        result: Result dict to populate
    """
    if node.value is None:
        return

    if not isinstance(node.value, ast.Call):
        return

    bmx_var = _extract_bmx_var_from_field(node.value)
    if bmx_var is None:
        return

    var_info: VarInfo = {"name": bmx_var, "line": node.lineno}

    if _is_optional_field(node):
        result["optional"].append(var_info)
    else:
        result["required"].append(var_info)


def _extract_bmx_var_from_field(call_node: ast.Call) -> str | None:
    """Extract BMX_* variable name from a Field() call.

    Args:
        call_node: AST Call node for Field(...)

    Returns:
        The BMX_* variable name if found, None otherwise
    """
    for keyword in call_node.keywords:
        if keyword.arg == "validation_alias":
            if isinstance(keyword.value, ast.Call):
                func = keyword.value.func
                if isinstance(func, ast.Name) and func.id == "AliasChoices":
                    for arg in keyword.value.args:
                        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
                            if arg.value.startswith("BMX_"):
                                return arg.value
    return None


def _is_optional_field(node: ast.AnnAssign) -> bool:
    """Determine if a field is optional based on type annotation and default.

    Optional if:
    - Type includes | None (union with None)
    - Has a default value that is not ... (Ellipsis)

    Required if:
    - No default
    - default=...

    Args:
        node: AST annotated assignment node

    Returns:
        True if field is optional, False if required
    """
    has_none_type = _type_includes_none(node.annotation)

    if has_none_type:
        return True

    if not isinstance(node.value, ast.Call):
        return False

    has_default = False
    default_is_ellipsis = False

    for keyword in node.value.keywords:
        if keyword.arg == "default":
            has_default = True
            if isinstance(keyword.value, ast.Constant) and keyword.value.value is ...:
                default_is_ellipsis = True
            break

    if not has_default:
        return False

    if default_is_ellipsis:
        return False

    return True


def _type_includes_none(annotation: ast.expr | None) -> bool:
    """Check if type annotation includes None (e.g., str | None).

    Args:
        annotation: AST expression for type annotation

    Returns:
        True if type includes None
    """
    if annotation is None:
        return False

    if isinstance(annotation, ast.BinOp) and isinstance(annotation.op, ast.BitOr):
        if isinstance(annotation.right, ast.Constant) and annotation.right.value is None:
            return True
        if isinstance(annotation.left, ast.Constant) and annotation.left.value is None:
            return True
        return _type_includes_none(annotation.left) or _type_includes_none(annotation.right)

    return False


def extract_config_vars(config_path: Path) -> ExtractResult:
    """Extract BMX_* variables from a config.py file.

    Args:
        config_path: Path to config.py file

    Returns:
        Dict with 'required' and 'optional' lists of variable info
    """
    source = config_path.read_text()
    return parse_config_source(source)


def main() -> None:
    """Main entry point for CLI usage."""
    import argparse

    parser = argparse.ArgumentParser(description="Extract BMX_* config variables")
    parser.add_argument("config_path", type=Path, help="Path to config.py")
    args = parser.parse_args()

    result = extract_config_vars(args.config_path)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
