#!/usr/bin/env python3
"""
Script to analyze which Python files are actually imported/used in the codebase.
Excludes test files and __init__ files.
"""

import ast
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def get_all_python_files() -> Set[Path]:
    """Get all Python files in app/ directory."""
    app_path = Path("app")
    if not app_path.exists():
        return set()
    return {f for f in app_path.rglob("*.py") if f.name != "__init__.py"}


def get_imports_in_file(file_path: Path) -> Set[str]:
    """Extract all imports from a Python file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        tree = ast.parse(content, filename=str(file_path))
    except Exception:
        return set()

    imports = set()

    for node in ast.walk(tree):
        # Handle: import module
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])

        # Handle: from module import name
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                # Get the full module path
                imports.add(node.module)

    return imports


def get_all_imports() -> Set[str]:
    """Get all imports from all Python files."""
    imports = set()
    py_files = get_all_python_files()

    # Exclude test files
    py_files = {f for f in py_files if 'test_' not in f.name and '/tests/' not in str(f)}

    for py_file in py_files:
        imports.update(get_imports_in_file(py_file))

    return imports


def path_to_module_name(file_path: Path) -> str:
    """Convert a file path to its module name."""
    relative = file_path.relative_to("app")
    parts = list(relative.parts[:-1])  # Exclude filename
    if relative.stem != "__init__":
        parts.append(relative.stem)
    return ".".join(parts) if parts else ""


def is_file_used(file_path: Path, all_imports: Set[str]) -> bool:
    """Check if a file is imported anywhere in the codebase."""
    module_name = path_to_module_name(file_path)

    # Check if module name or any parent is in imports
    parts = module_name.split('.')
    for i in range(len(parts)):
        parent_module = ".".join(parts[:i+1])
        if parent_module in all_imports:
            return True

    # Also check the file path pattern in imports
    file_str = str(file_path).replace('/', '.').replace('app.', '')

    for imp in all_imports:
        if imp in file_str or file_str in imp:
            return True

    return False


def get_entry_points() -> List[Path]:
    """Find entry point files (main.py, CLI scripts, etc.)."""
    entry_points = []
    app_path = Path("app")

    # Common entry point patterns
    patterns = [
        "main.py",
        "__main__.py",
        "cli.py",
        "wsgi.py",
        "asgi.py",
    ]

    for pattern in patterns:
        matches = list(app_path.rglob(pattern))
        entry_points.extend(matches)

    return entry_points


def analyze_unused_files() -> Dict[str, List[Tuple[str, Path, str]]]:
    """Analyze which files are not used in the codebase."""
    py_files = get_all_python_files()

    # Exclude test files
    py_files = {f for f in py_files if 'test_' not in f.name and '/tests/' not in str(f)}

    all_imports = get_all_imports()
    entry_points = get_entry_points()

    # Group by layer
    unused_by_layer = {}

    for py_file in py_files:
        if is_file_used(py_file, all_imports):
            continue

        # Check if it's an entry point
        if py_file in entry_points:
            continue

        relative = str(py_file.relative_to("app"))

        # Determine layer
        if relative.startswith("domain/"):
            layer = "Layer 1 - Domain"
        elif relative.startswith("database/") or relative.startswith("infrastructure/"):
            layer = "Layer 2 - Infrastructure"
        elif relative.startswith("core/"):
            layer = "Layer 3 - Core"
        elif relative.startswith("application/"):
            layer = "Layer 4 - Application"
        elif relative.startswith("backtesting/"):
            layer = "Layer 5 - Backtesting"
        elif relative.startswith("strategies/"):
            layer = "Layer 6 - Strategies"
        elif relative.startswith("market_microstructure/") or relative.startswith("microstructure/") or relative.startswith("ensemble/") or relative.startswith("optimization/"):
            layer = "Layer 7 - Advanced Features"
        elif relative.startswith("api/") or relative.startswith("presentation/") or relative.startswith("security/") or relative.startswith("middleware/"):
            layer = "Layer 8 - API/Presentation"
        else:
            layer = "Layer 9 - Other"

        if layer not in unused_by_layer:
            unused_by_layer[layer] = []

        # Categorize reason
        reason = "No imports found"
        if py_file.name.startswith("_"):
            reason = "Private/Internal file"

        unused_by_layer[layer].append((relative, py_file, reason))

    return unused_by_layer


def main():
    """Main function."""
    print("=" * 100)
    print("🔍 ANALYZING UNUSED FILES IN CODEBASE")
    print("=" * 100)
    print()

    unused_by_layer = analyze_unused_files()

    total_unused = sum(len(files) for files in unused_by_layer.values())

    if total_unused == 0:
        print("✅ All files are used!")
        return

    print(f"📊 SUMMARY: {total_unused} potentially unused files found\n")

    # Sort by layer
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
        if layer not in unused_by_layer or not unused_by_layer[layer]:
            continue

        files = unused_by_layer[layer]
        print(f"{'=' * 100}")
        print(f"📍 {layer}")
        print(f"{'=' * 100}")
        print(f"   📁 Total: {len(files)} files\n")

        for relative, py_file, reason in sorted(files):
            print(f"   ⚠️  {relative}")
            print(f"      → Reason: {reason}")

    print(f"\n{'=' * 100}")
    print(f"✅ TOTAL: {total_unused} potentially unused files")
    print(f"{'=' * 100}\n")

    print("\n📋 LIST FOR SCRIPTING:")
    print("=" * 50)
    for layer in layer_order:
        if layer not in unused_by_layer:
            continue
        for relative, _, _ in sorted(unused_by_layer[layer]):
            print(f"app/{relative}")


if __name__ == "__main__":
    main()
