#!/usr/bin/env python3
"""
More thorough analysis of file usage.
Checks: imports, string references, config files, entry points.
"""

import ast
import json
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def get_all_python_files() -> Set[Path]:
    """Get all Python files in app/ directory."""
    app_path = Path("app")
    if not app_path.exists():
        return set()
    return {f for f in app_path.rglob("*.py") if f.name != "__init__.py"}


def get_module_name(file_path: Path) -> str:
    """Convert file path to module name."""
    relative = file_path.relative_to("app")
    parts = list(relative.parts[:-1])
    if relative.stem != "__init__":
        parts.append(relative.stem)
    return ".".join(parts)


def get_file_references(file_path: Path) -> Set[str]:
    """Get all references that might indicate this file is used."""
    module_name = get_module_name(file_path)
    file_name = file_path.stem
    parent_dir = file_path.parent.name if file_path.parent != Path("app") else ""

    references = set()

    # Module name variations
    references.add(module_name)
    references.add(file_name)

    # Add parent modules
    parts = module_name.split(".")
    for i in range(len(parts)):
        references.add(".".join(parts[:i+1]))

    # File path as string
    file_str = str(file_path).replace("/", ".")

    return references


def search_file_usage(file_path: Path, all_files: Set[Path]) -> Tuple[bool, List[str]]:
    """Search if a file is referenced anywhere in the codebase."""
    references = get_file_references(file_path)
    found_references = []

    # Check all Python files
    for other_file in all_files:
        if other_file == file_path:
            continue

        try:
            with open(other_file, 'r', encoding='utf-8') as f:
                content = f.read()
        except Exception:
            continue

        # Check for imports
        try:
            tree = ast.parse(content, filename=str(other_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if any(ref in alias.name for ref in references):
                            found_references.append(f"import in {other_file}")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and any(ref in node.module for ref in references):
                        found_references.append(f"from import in {other_file}")
        except Exception:
            pass

        # Check for string references (dynamic imports, etc.)
        for ref in references:
            # Look for the module/file in string literals
            if ref in content and f'"{ref}' in content:
                found_references.append(f"string reference in {other_file}")
            elif ref in content and f"'{ref}'" in content:
                found_references.append(f"string reference in {other_file}")

        # Check for common patterns
        file_name = file_path.stem
        if file_name in content and f'"{file_name}' in content:
            found_references.append(f"filename reference in {other_file}")
        elif file_name in content and f"'{file_name}'" in content:
            found_references.append(f"filename reference in {other_file}")

    # Check config files
    config_extensions = ['.yaml', '.yml', '.json', '.toml', '.cfg', '.ini', '.conf']
    for config_file in Path('.').rglob('*'):
        if config_file.suffix in config_extensions:
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                for ref in references:
                    if ref in content:
                        found_references.append(f"config in {config_file}")
                        break
            except Exception:
                pass

    return len(found_references) > 0, found_references


def main():
    """Main function."""
    print("=" * 100)
    print("🔍 DEEP FILE USAGE ANALYSIS")
    print("=" * 100)
    print()

    py_files = get_all_python_files()
    py_files = {f for f in py_files if 'test_' not in f.name and '/tests/' not in str(f)}

    # Check a sample of potentially unused files
    potentially_unused = [
        "app/domain/entities/backtest.py",
        "app/domain/entities/trade.py",
        "app/domain/services/risk_calculator.py",
        "app/domain/services/tax_calculator.py",
        "app/backtesting/engine.py",
        "app/backtesting/metrics.py",
        "app/strategies/fx_carry_trade/fx_carry_trade_strategy.py",
        "app/api/health.py",
        "app/api/strategies.py",
        "app/services/market_data_service.py",
        "app/services/portfolio_service.py",
    ]

    print("📊 SAMPLING: Checking usage of potentially unused files\n")

    truly_unused = []
    actually_used = []

    for file_str in potentially_unused:
        file_path = Path(file_str)
        if not file_path.exists():
            continue

        is_used, refs = search_file_usage(file_path, py_files)

        if is_used:
            actually_used.append((file_str, refs[:3]))  # Show first 3 refs
        else:
            truly_unused.append(file_str)

    print(f"✅ ACTUALLY USED ({len(actually_used)} files):")
    print("-" * 100)
    for file_str, refs in actually_used:
        print(f"   ✓ {file_str}")
        for ref in refs:
            print(f"      → {ref}")
        print()

    print(f"\n❌ TRULY UNUSED ({len(truly_unused)} files):")
    print("-" * 100)
    for file_str in truly_unused:
        print(f"   ✗ {file_str}")

    print(f"\n{'=' * 100}")
    print(f"Summary: {len(actually_used)} actually used, {len(truly_unused)} truly unused")
    print(f"{'=' * 100}\n")


if __name__ == "__main__":
    main()
