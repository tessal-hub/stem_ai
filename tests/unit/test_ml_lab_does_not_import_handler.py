"""
Architecture Boundary Test: Verify that ml_lab NEVER imports Handler, DataStore, or Shell.
"""

from __future__ import annotations

import ast
from pathlib import Path
import pytest


FORBIDDEN_MODULES = {
    "logic.handler",
    "logic.data_store",
    "ui.mac_shell",
    "ui.main_window",
    "ui.main",
    "logic.serial_worker",
    "logic.udp_worker",
    "logic.flash_worker",
    "logic.idf_worker",
}


def get_all_imports(file_path: Path) -> list[str]:
    """Parse AST to extract all module imports in a python file."""
    imports: list[str] = []
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)
    return imports


def test_ml_lab_does_not_import_forbidden_modules():
    """Assert zero forbidden imports across all files in ml_lab."""
    ml_lab_root = Path(__file__).resolve().parent.parent.parent / "ml_lab"
    assert ml_lab_root.exists(), f"ml_lab directory not found at {ml_lab_root}"

    python_files = list(ml_lab_root.rglob("*.py"))
    assert len(python_files) > 0, "No python files found in ml_lab"

    violations: list[str] = []

    for py_file in python_files:
        module_imports = get_all_imports(py_file)
        rel_path = py_file.relative_to(ml_lab_root)

        for imp in module_imports:
            for forbidden in FORBIDDEN_MODULES:
                if imp == forbidden or imp.startswith(f"{forbidden}."):
                    violations.append(f"{rel_path}: imports forbidden module '{imp}'")

    assert len(violations) == 0, "Architecture Boundary Violations found:\n" + "\n".join(violations)
