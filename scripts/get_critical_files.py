#!/usr/bin/env python3
"""
Script to identify the 20 most critical files from the 696 non-PASSED files.
Excludes test files and prioritizes by:
1. Security-related files
2. Core domain files
3. Files with high complexity/impact
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Set, Tuple


def get_all_requirements_files() -> Set[Path]:
    """Get all requirements files in .requirements/ directory."""
    req_path = Path(".requirements/app")
    if not req_path.exists():
        return set()
    return set(req_path.rglob("*.requirements.md"))


def is_already_passed(req_file: Path) -> bool:
    """Check if requirements file already has PASSED status."""
    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return False

    if re.search(r'## Audit Status.*?\*\*Status:\*\*\s*PASSED', content, re.DOTALL | re.IGNORECASE):
        return True
    return False


def is_test_file(py_file: str) -> bool:
    """Check if file is a test file."""
    return ('test_' in py_file or
            '/tests/' in py_file or
            '/conftest' in py_file or
            '_test.py' in py_file)


def get_criticality_score(py_file: str) -> int:
    """Calculate criticality score (higher = more critical)."""
    score = 0

    # Security files - HIGHEST priority
    if '/security/' in py_file or py_file.startswith('security/'):
        score += 1000
    if 'csrf' in py_file or 'auth' in py_file or 'secrets' in py_file:
        score += 500

    # Core domain files - HIGH priority
    if py_file.startswith('domain/entities/'):
        score += 300
    if py_file.startswith('domain/services/'):
        score += 250
    if py_file.startswith('domain/value_objects/'):
        score += 200

    # Core infrastructure
    if py_file.startswith('core/'):
        score += 200

    # Risk management - HIGH priority
    if 'risk' in py_file:
        score += 400
    if 'portfolio' in py_file:
        score += 300

    # Trading execution - HIGH priority
    if 'trading' in py_file or 'execution' in py_file or 'order' in py_file:
        score += 350

    # Data integrity
    if 'database' in py_file or 'persistence' in py_file or 'storage' in py_file:
        score += 250

    # API/Controllers - MEDIUM priority (external facing)
    if 'controllers/' in py_file or 'api/' in py_file:
        score += 150

    # Backtesting - LOWER priority (not production critical)
    if 'backtesting' in py_file:
        score += 50

    # Dashboard/UI - LOWEST priority
    if 'dashboard' in py_file or 'views' in py_file or 'presentation' in py_file:
        score += 20

    # Engine files - HIGH complexity
    if 'engines/' in py_file:
        score += 180

    # Service files
    if 'services/' in py_file:
        score += 100

    # Strategy files
    if 'strategies/' in py_file:
        score += 120

    # Optimizer files
    if 'optimization' in py_file or 'optimizer' in py_file:
        score += 150

    return score


def get_non_passed_files(exclude_tests: bool = True) -> List[Tuple[str, Path, int]]:
    """Get files that have requirements but are not PASSED."""
    req_files = get_all_requirements_files()
    non_passed = []

    for req_file in req_files:
        if is_already_passed(req_file):
            continue

        # Get corresponding Python file path
        py_path_str = str(req_file.relative_to(".requirements/app"))
        py_path_str = py_path_str.replace('.requirements.md', '')
        py_path_str = "app/" + py_path_str

        # Exclude tests if requested
        if exclude_tests and is_test_file(py_path_str):
            continue

        # Calculate criticality score
        score = get_criticality_score(py_path_str)

        non_passed.append((py_path_str, req_file, score))

    # Sort by score (descending)
    non_passed.sort(key=lambda x: x[2], reverse=True)

    return non_passed


def main():
    """Main function."""
    print("=" * 100)
    print("🔍 TOP 20 CRITICAL FILES - NON PASSED AUDIT")
    print("=" * 100)
    print()

    non_passed = get_non_passed_files(exclude_tests=True)

    print(f"📊 Total non-PASSED files (excluding tests): {len(non_passed)}")
    print()

    # Group by category for summary
    categories = {
        "🔴 SECURITY": [],
        "🟠 CORE DOMAIN": [],
        "🟡 TRADING/RISK": [],
        "🟢 INFRASTRUCTURE": [],
        "🔵 API/CONTROLLERS": [],
        "⚪ OTHER": [],
    }

    # Categorize top 20
    top_20 = non_passed[:20]

    for py_file, req_file, score in top_20:
        # Determine category
        if '/security/' in py_file or py_file.startswith('security/') or 'csrf' in py_file or 'secrets' in py_file:
            categories["🔴 SECURITY"].append((py_file, score))
        elif py_file.startswith('domain/entities/') or py_file.startswith('domain/services/') or py_file.startswith('domain/value_objects/'):
            categories["🟠 CORE DOMAIN"].append((py_file, score))
        elif 'risk' in py_file or 'portfolio' in py_file or 'trading' in py_file or 'execution' in py_file or 'order' in py_file:
            categories["🟡 TRADING/RISK"].append((py_file, score))
        elif 'core/' in py_file or 'engines/' in py_file or 'database' in py_file or 'persistence' in py_file:
            categories["🟢 INFRASTRUCTURE"].append((py_file, score))
        elif 'controllers/' in py_file or 'api/' in py_file:
            categories["🔵 API/CONTROLLERS"].append((py_file, score))
        else:
            categories["⚪ OTHER"].append((py_file, score))

    # Print by category
    print("=" * 100)
    print("🎯 TOP 20 CRITICAL FILES BY CATEGORY")
    print("=" * 100)
    print()

    rank = 1
    for category, files in categories.items():
        if not files:
            continue
        print(f"{category}")
        print("-" * 100)
        for py_file, score in files:
            print(f"   #{rank} (Score: {score})")
            print(f"      {py_file}")
            rank += 1
            if rank > 20:
                break
        print()

    # Print list for scripting
    print("=" * 100)
    print("📋 TOP 20 FILES FOR SCRIPTING")
    print("=" * 100)
    for py_file, _, score in top_20:
        print(f"{py_file}")

    print()
    print("=" * 100)
    print(f"✅ Top 20 critical files identified")
    print(f"📊 Total remaining: {len(non_passed)} files")
    print(f"{'=' * 100}\n")


if __name__ == "__main__":
    main()
