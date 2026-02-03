#!/usr/bin/env python3
"""
Script to get files that REALLY need auditing.
Excludes:
- Test files (test_*.py, /tests/)
- Files not imported anywhere (unused code)
- __init__.py files
"""

import subprocess
import sys
from pathlib import Path
from typing import Set


def get_unused_files() -> Set[str]:
    """Get list of unused files from analyze_unused_files.py"""
    result = subprocess.run(
        ["python", "scripts/analyze_unused_files.py"],
        capture_output=True,
        text=True
    )

    # Parse output to get unused files
    unused = set()
    in_list = False

    for line in result.stdout.split('\n'):
        if 'LIST FOR SCRIPTING:' in line:
            in_list = True
            continue
        if in_list and line.startswith('app/'):
            unused.add(line.strip())

    return unused


def get_files_without_requirements() -> Set[str]:
    """Get files without requirements from get_missing_requirements_by_layer.py"""
    result = subprocess.run(
        ["python", "scripts/get_missing_requirements_by_layer.py", "--format=list"],
        capture_output=True,
        text=True
    )

    # Parse output
    missing = set()
    for line in result.stdout.split('\n'):
        if line.startswith('app/'):
            missing.add(line.strip())

    return missing


def is_test_file(file_path: str) -> bool:
    """Check if file is a test file."""
    return ('test_' in file_path or
            '/tests/' in file_path or
            file_path.endswith('_test.py'))


def main():
    """Main function."""
    print("=" * 100)
    print("🔍 FILES THAT REALLY NEED AUDITING")
    print("=" * 100)
    print()
    print("Excluding:")
    print("  - Test files (test_*.py, /tests/)")
    print("  - Files not imported anywhere (unused code)")
    print("  - __init__.py files")
    print()

    # Get data
    unused = get_unused_files()
    missing_requirements = get_files_without_requirements()

    # Filter out:
    # 1. Test files
    # 2. Unused files
    # 3. __init__.py files
    need_audit = set()

    for file_path in missing_requirements:
        if is_test_file(file_path):
            continue
        if file_path in unused:
            continue
        if file_path.endswith('__init__.py'):
            continue

        need_audit.add(file_path)

    # Group by layer
    by_layer = {}

    for file_path in sorted(need_audit):
        # Determine layer
        if file_path.startswith("app/domain/"):
            layer = "Layer 1 - Domain"
        elif file_path.startswith("app/database/") or file_path.startswith("app/infrastructure/"):
            layer = "Layer 2 - Infrastructure"
        elif file_path.startswith("app/core/"):
            layer = "Layer 3 - Core"
        elif file_path.startswith("app/application/"):
            layer = "Layer 4 - Application"
        elif file_path.startswith("app/backtesting/"):
            layer = "Layer 5 - Backtesting"
        elif file_path.startswith("app/strategies/"):
            layer = "Layer 6 - Strategies"
        elif file_path.startswith("app/market_microstructure/") or file_path.startswith("app/microstructure/") or file_path.startswith("app/ensemble/") or file_path.startswith("app/optimization/"):
            layer = "Layer 7 - Advanced Features"
        elif file_path.startswith("app/api/") or file_path.startswith("app/presentation/") or file_path.startswith("app/security/") or file_path.startswith("app/middleware/"):
            layer = "Layer 8 - API/Presentation"
        else:
            layer = "Layer 9 - Other"

        if layer not in by_layer:
            by_layer[layer] = []
        by_layer[layer].append(file_path)

    total = sum(len(files) for files in by_layer.values())

    if total == 0:
        print("✅ No files need auditing!")
        print()
        return

    print(f"📊 SUMMARY: {total} files need auditing\n")

    layer_order = [
        "Layer 1 - Domain",
        "Layer 2 - Infrastructure",
        "Layer 3 - Core",
        "Layer 4 - Application",
        "Layer 5 - Backtesting",
        "Layer 6 - Strategies",
        "Layer 7 - Advanced Features",
        "Layer 8 - API/Presentation",
        "Layer 9 - Other",
    ]

    for layer in layer_order:
        if layer not in by_layer or not by_layer[layer]:
            continue

        files = by_layer[layer]
        print(f"{'=' * 100}")
        print(f"📍 {layer}")
        print(f"{'=' * 100}")
        print(f"   📁 Total: {len(files)} files\n")

        for file_path in files:
            print(f"   ❌ {file_path}")

    print(f"\n{'=' * 100}")
    print(f"✅ TOTAL: {total} files need auditing (excluding tests and unused)")
    print(f"{'=' * 100}\n")

    # Print list for scripting
    print("\n📋 LIST FOR SCRIPTING:")
    print("=" * 50)
    for file_path in sorted(need_audit):
        print(file_path)

    return 0 if total == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
