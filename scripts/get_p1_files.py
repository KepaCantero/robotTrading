#!/usr/bin/env python3
"""
Script to get list of P1 (HIGH priority) files that need requirements created.
Usage: python scripts/get_p1_files.py
"""

import os
from pathlib import Path
from typing import Set, List, Tuple

def get_all_python_files() -> Set[Path]:
    """Get all Python files in app/ directory."""
    app_path = Path("app")
    if not app_path.exists():
        return set()
    return set(app_path.rglob("*.py"))


def get_all_requirements_files() -> Set[Path]:
    """Get all requirements files in .requirements/ directory."""
    req_path = Path(".requirements")
    if not req_path.exists():
        return set()
    return set(req_path.rglob("*.requirements.md"))


def python_file_to_requirement_path(py_file: Path) -> Tuple[Path, Path]:
    """Convert a Python file path to its expected requirements file paths."""
    relative_path = py_file.relative_to("app")
    req_base = Path(".requirements") / "app" / relative_path
    pattern1 = Path(str(req_base) + ".requirements.md")
    pattern2 = Path(str(req_base.with_suffix('')) + ".requirements.md")
    return pattern1, pattern2


def get_p1_files_without_requirements() -> List[Path]:
    """Get P1 (HIGH priority) files without requirements."""
    py_files = get_all_python_files()
    req_files = get_all_requirements_files()

    # P1 directories
    p1_dirs = [
        "backtesting/acceptance",
        "backtesting/services",
        "services/risk_scaling_application",
        "tests/backtesting",
        "services/backtesting_orchestration",
    ]

    p1_files = []
    for py_file in py_files:
        # Skip __init__.py
        if py_file.name == "__init__.py":
            continue

        # Check if file is in P1 directory
        relative_path = str(py_file.parent.relative_to("app"))
        if not any(p1_dir in relative_path for p1_dir in p1_dirs):
            continue

        # Check if requirements exist
        pattern1, pattern2 = python_file_to_requirement_path(py_file)
        if pattern1 not in req_files and pattern2 not in req_files:
            p1_files.append(py_file)

    return sorted(p1_files)


def main():
    """Main function."""
    p1_files = get_p1_files_without_requirements()

    print(f"📋 P1 (HIGH PRIORITY) FILES WITHOUT REQUIREMENTS: {len(p1_files)}")
    print("=" * 80)

    for py_file in p1_files:
        relative_path = py_file.relative_to("app")
        print(f"app/{relative_path}")


if __name__ == "__main__":
    main()
