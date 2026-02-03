#!/usr/bin/env python3
"""
Script to list all requirements files (.requirements.md) in the project.
Usage: python scripts/list_requirements_files.py
"""

import os
from pathlib import Path
from typing import List

def find_requirements_files(root_dir: str = ".requirements") -> List[Path]:
    """
    Find all .requirements.md files in the project.

    Args:
        root_dir: Root directory to search (default: .requirements)

    Returns:
        List of Path objects for all requirements files
    """
    root_path = Path(root_dir)
    if not root_path.exists():
        print(f"⚠️  Directory '{root_dir}' not found")
        return []

    requirements_files = list(root_path.rglob("*.requirements.md"))
    return sorted(requirements_files)


def main():
    """Main function to list all requirements files."""
    print("=" * 80)
    print("📋 LISTING ALL REQUIREMENTS FILES")
    print("=" * 80)

    req_files = find_requirements_files()

    if not req_files:
        print("⚠️  No requirements files found")
        return

    # Count by layer/category
    by_layer = {}
    for req_file in req_files:
        # Extract layer/category from path
        parts = req_file.parts
        if "app" in parts:
            app_idx = parts.index("app")
            if app_idx + 1 < len(parts):
                layer = f"app/{parts[app_idx + 1]}"
            else:
                layer = "app/other"
        else:
            layer = str(req_file.parent.relative_to(".requirements"))

        by_layer.setdefault(layer, []).append(req_file)

    # Print summary
    print(f"\n📊 SUMMARY: Found {len(req_files)} requirements files\n")

    # Print by layer
    for layer, files in sorted(by_layer.items()):
        print(f"\n{'─' * 80}")
        print(f"📁 {layer}/ ({len(files)} files)")
        print(f"{'─' * 80}")
        for file in sorted(files):
            relative_path = file.relative_to(".requirements")
            print(f"   ✅ {relative_path}")

    # Print total count
    print(f"\n{'=' * 80}")
    print(f"✅ TOTAL: {len(req_files)} requirements files")
    print(f"{'=' * 80}\n")


if __name__ == "__main__":
    main()
