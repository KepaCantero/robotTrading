#!/usr/bin/env python3
"""
Script to find Python files that don't have a corresponding requirements document.
Usage: python scripts/find_missing_requirements.py
"""

import os
from pathlib import Path
from typing import List, Tuple, Set

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


def python_file_to_requirement_path(py_file: Path) -> Path:
    """
    Convert a Python file path to its expected requirements file path.

    Example:
        app/domain/entities/portfolio.py
        -> .requirements/app/domain/entities/portfolio.py.requirements.md
        OR .requirements/app/domain/entities/portfolio.requirements.md
    """
    relative_path = py_file.relative_to("app")
    req_base = Path(".requirements") / "app" / relative_path

    # Try two common patterns
    pattern1 = Path(str(req_base) + ".requirements.md")
    pattern2 = Path(str(req_base.with_suffix('')) + ".requirements.md")

    return pattern1, pattern2


def find_files_without_requirements() -> Tuple[List[Path], List[Path]]:
    """
    Find Python files without corresponding requirements documents.

    Returns:
        Tuple of (files_with_requirements, files_without_requirements)
    """
    py_files = get_all_python_files()
    req_files = get_all_requirements_files()

    files_without = []
    files_with = []

    for py_file in py_files:
        pattern1, pattern2 = python_file_to_requirement_path(py_file)

        if pattern1 in req_files or pattern2 in req_files:
            files_with.append(py_file)
        else:
            files_without.append(py_file)

    return sorted(files_with), sorted(files_without)


def categorize_by_directory(files: List[Path]) -> dict:
    """Categorize files by their directory."""
    by_dir = {}
    for file in files:
        relative_dir = file.parent.relative_to("app")
        dir_key = str(relative_dir)
        by_dir.setdefault(dir_key, []).append(file)
    return by_dir


def main():
    """Main function to find and display files without requirements."""
    print("=" * 80)
    print("🔍 FINDING PYTHON FILES WITHOUT REQUIREMENTS")
    print("=" * 80)

    py_files = get_all_python_files()
    req_files = get_all_requirements_files()

    print(f"\n📊 OVERVIEW:")
    print(f"   🐍 Python files in app/:     {len(py_files)}")
    print(f"   📋 Requirements files:        {len(req_files)}")
    print(f"")

    files_with, files_without = find_files_without_requirements()

    coverage_pct = (len(files_with) / len(py_files) * 100) if py_files else 0
    missing_pct = (len(files_without) / len(py_files) * 100) if py_files else 0

    print(f"   ✅ Files WITH requirements:   {len(files_with):3d} ({coverage_pct:.1f}%)")
    print(f"   ❌ Files WITHOUT requirements: {len(files_without):3d} ({missing_pct:.1f}%)")
    print(f"{'=' * 80}\n")

    if files_without:
        # Categorize by directory
        without_by_dir = categorize_by_directory(files_without)

        print(f"📁 FILES WITHOUT REQUIREMENTS (by directory):\n")

        for dir_name, files in sorted(without_by_dir.items()):
            print(f"{'─' * 80}")
            print(f"❌ app/{dir_name}/ ({len(files)} files missing)")
            print(f"{'─' * 80}")
            for file in sorted(files):
                # Show expected requirements path
                pattern1, pattern2 = python_file_to_requirement_path(file)
                expected_req = pattern1 if pattern1.exists() or not pattern2.exists() else pattern2
                relative_req = expected_req.relative_to(".requirements")
                print(f"   📄 {file.name}")
                print(f"      Expected: {relative_req}")

        print(f"\n{'=' * 80}")
        print(f"⚠️  TOTAL: {len(files_without)} files need requirements documents")
        print(f"{'=' * 80}\n")
    else:
        print(f"🎉 EXCELLENT! All Python files have requirements documents!\n")

    # Show coverage by directory
    print(f"📈 COVERAGE BY DIRECTORY:\n")
    all_by_dir = {}
    for py_file in py_files:
        relative_dir = str(py_file.parent.relative_to("app"))
        if relative_dir not in all_by_dir:
            all_by_dir[relative_dir] = {"total": 0, "with": 0}
        all_by_dir[relative_dir]["total"] += 1
        if py_file in files_with:
            all_by_dir[relative_dir]["with"] += 1

    # Sort by lowest coverage
    sorted_dirs = sorted(
        all_by_dir.items(),
        key=lambda x: (x[1]["with"] / x[1]["total"] if x[1]["total"] > 0 else 0)
    )

    for dir_name, stats in sorted_dirs[:20]:  # Show bottom 20
        total = stats["total"]
        with_req = stats["with"]
        coverage = (with_req / total * 100) if total > 0 else 0
        status = "✅" if coverage == 100 else "⚠️" if coverage >= 50 else "❌"
        print(f"   {status} {dir_name:50s} {with_req:3d}/{total:3d} ({coverage:5.1f}%)")


if __name__ == "__main__":
    main()
