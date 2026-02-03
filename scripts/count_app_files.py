#!/usr/bin/env python3
"""
Script to count all Python files in the app/ directory.
Usage: python scripts/count_app_files.py
"""

import os
from pathlib import Path
from typing import Dict, List

def count_app_files() -> Dict[str, List[Path]]:
    """
    Count all .py files in the app/ directory.

    Returns:
        Dictionary mapping directory paths to lists of Python files
    """
    app_path = Path("app")
    if not app_path.exists():
        print(f"⚠️  Directory 'app/' not found")
        return {}

    python_files = {}
    for py_file in sorted(app_path.rglob("*.py")):
        # Get parent directory relative to app/
        relative_dir = py_file.parent.relative_to(app_path)
        dir_key = str(relative_dir)

        python_files.setdefault(dir_key, []).append(py_file)

    return python_files


def main():
    """Main function to count and display Python files."""
    print("=" * 80)
    print("🐍 COUNTING PYTHON FILES IN app/")
    print("=" * 80)

    files_by_dir = count_app_files()

    if not files_by_dir:
        print("⚠️  No Python files found in app/")
        return

    total_files = sum(len(files) for files in files_by_dir.values())
    total_dirs = len(files_by_dir)

    # Print summary by directory
    print(f"\n📊 SUMMARY: {total_files} Python files in {total_dirs} directories\n")

    for dir_name, files in sorted(files_by_dir.items()):
        print(f"{'─' * 80}")
        print(f"📁 app/{dir_name}/ ({len(files)} files)")
        print(f"{'─' * 80}")
        for file in sorted(files):
            print(f"   📄 {file.name}")

    # Print total count
    print(f"\n{'=' * 80}")
    print(f"✅ TOTAL: {total_files} Python files in app/")
    print(f"✅ TOTAL: {total_dirs} directories with Python files")
    print(f"{'=' * 80}\n")

    # Print top 10 directories by file count
    print(f"📈 TOP 10 DIRECTORIES BY FILE COUNT:")
    sorted_dirs = sorted(files_by_dir.items(), key=lambda x: len(x[1]), reverse=True)
    for i, (dir_name, files) in enumerate(sorted_dirs[:10], 1):
        print(f"   {i:2d}. app/{dir_name}/: {len(files):3d} files")


if __name__ == "__main__":
    main()
