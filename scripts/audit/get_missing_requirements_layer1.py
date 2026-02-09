#!/usr/bin/env python3
"""
Script to find Python files WITHOUT requirements documents in Layer 1 (Domain).
Layer 1 is the deepest layer with no dependencies on outer layers.
Usage: python scripts/get_missing_requirements_layer1.py
"""

import os
from pathlib import Path
from typing import List, Set, Tuple


def get_all_python_files_in_layer1() -> Set[Path]:
    """Get all Python files in Layer 1 (Domain)."""
    app_path = Path("app")
    if not app_path.exists():
        return set()

    layer1_dirs = [
        "domain/entities",
        "domain/value_objects",
        "domain/services",
        "domain/services/portfolio_optimization",
        "domain/strategies",
        "domain/repositories",
        "domain/models",
        "domain/configurators",
        "domain/portfolio_optimization",
    ]

    python_files = set()
    for dir_path in layer1_dirs:
        full_path = app_path / dir_path
        if full_path.exists():
            for py_file in full_path.rglob("*.py"):
                # Skip __init__.py files
                if py_file.name != "__init__.py":
                    python_files.add(py_file)

    return python_files


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


def get_files_without_requirements_layer1() -> List[Tuple[str, Path]]:
    """
    Get all Python files in Layer 1 that DON'T have requirements documents.
    Returns: List of (sublayer_name, py_file) tuples ordered by sublayer
    """
    py_files = get_all_python_files_in_layer1()
    req_files = get_all_requirements_files()

    # Group by sublayer
    sublayers = {
        "1.1 Domain Entities": "domain/entities",
        "1.2 Value Objects": "domain/value_objects",
        "1.3 Domain Services": "domain/services",
        "1.4 Portfolio Optimization (Services)": "domain/services/portfolio_optimization",
        "1.5 Strategy Definitions": "domain/strategies",
        "1.6 Repository Interfaces": "domain/repositories",
        "1.7 Domain Models": "domain/models",
        "1.8 Domain Configurators": "domain/configurators",
        "1.9 Portfolio Optimization (Alt)": "domain/portfolio_optimization",
    }

    missing_by_sublayer = {name: [] for name in sublayers.keys()}

    for py_file in py_files:
        relative_path = str(py_file.relative_to("app"))

        # Check if requirements exist
        pattern1, pattern2 = python_file_to_requirement_path(py_file)
        has_requirements = pattern1 in req_files or pattern2 in req_files

        if not has_requirements:
            # Determine sublayer
            for sublayer_name, dir_path in sublayers.items():
                if relative_path.startswith(dir_path):
                    missing_by_sublayer[sublayer_name].append(py_file)
                    break

    # Flatten to ordered list
    result = []
    for sublayer_name in sublayers.keys():
        for py_file in missing_by_sublayer[sublayer_name]:
            result.append((sublayer_name, py_file))

    return result


def main():
    """Main function."""
    print("=" * 100)
    print("🔍 LAYER 1 (DOMAIN) - Files WITHOUT Requirements")
    print("=" * 100)
    print()

    missing_files = get_files_without_requirements_layer1()

    if not missing_files:
        print("✅ All Layer 1 files have requirements documents!")
        print()
        return

    # Group by sublayer for display
    by_sublayer = {}
    for sublayer, py_file in missing_files:
        if sublayer not in by_sublayer:
            by_sublayer[sublayer] = []
        by_sublayer[sublayer].append(py_file)

    # Print summary
    print(f"📊 SUMMARY: {len(missing_files)} Layer 1 files WITHOUT requirements\\n")

    # Print by sublayer
    for sublayer in sorted(by_sublayer.keys()):
        files = by_sublayer[sublayer]
        print(f"{'=' * 100}")
        print(f"📍 {sublayer}")
        print(f"{'=' * 100}")
        print(f"   📁 Total: {len(files)} files\\n")

        for py_file in sorted(files):
            relative_py = py_file.relative_to("app")
            print(f"   ❌ app/{relative_py}")
            expected_req = Path(".requirements") / "app" / relative_py
            print(f"      → Missing: {expected_req}.requirements.md")

    # Print list for scripting
    print(f"\\n{'=' * 100}")
    print("📋 FILES FOR BATCH PROCESSING:")
    print(f"{'=' * 100}")
    for sublayer, py_file in missing_files:
        relative_py = py_file.relative_to("app")
        print(f"app/{relative_py}")

    print(f"\\n{'=' * 100}")
    print(f"✅ TOTAL: {len(missing_files)} Layer 1 files WITHOUT requirements")
    print(f"{'=' * 100}\\n")

    # Return exit code based on whether files are missing
    return 1 if missing_files else 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
