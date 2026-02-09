#!/usr/bin/env python3
"""
Script to generate a comprehensive audit summary of requirements coverage.
Excludes __init__.py files from the analysis for a more accurate picture.
Usage: python scripts/audit_requirements_summary.py
"""

import os
from pathlib import Path
from typing import Set, List, Tuple, Dict

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


def categorize_files() -> Dict[str, Dict[str, List[Path]]]:
    """Categorize files by directory and status."""
    py_files = get_all_python_files()
    req_files = get_all_requirements_files()

    categorized = {}

    for py_file in py_files:
        # Skip __init__.py files
        if py_file.name == "__init__.py":
            continue

        relative_dir = str(py_file.parent.relative_to("app"))

        if relative_dir not in categorized:
            categorized[relative_dir] = {"with": [], "without": []}

        pattern1, pattern2 = python_file_to_requirement_path(py_file)
        if pattern1 in req_files or pattern2 in req_files:
            categorized[relative_dir]["with"].append(py_file)
        else:
            categorized[relative_dir]["without"].append(py_file)

    return categorized


def calculate_gap_priority(category: str, missing_count: int) -> str:
    """Assign priority level based on category and missing files."""
    layer_mapping = {
        "domain": "P0 - CRITICAL",
        "application": "P1 - HIGH",
        "backtesting": "P1 - HIGH",
        "strategies": "P2 - MEDIUM",
        "core": "P2 - MEDIUM",
        "api": "P3 - LOW",
        "infrastructure": "P2 - MEDIUM",
        "database": "P2 - MEDIUM",
        "ensemble": "P3 - LOW",
        "market_microstructure": "P2 - MEDIUM",
        "microstructure": "P2 - MEDIUM",
        "middleware": "P3 - LOW",
        "optimization": "P2 - MEDIUM",
        "services": "P3 - LOW",
    }

    for key, priority in layer_mapping.items():
        if key in category:
            return priority

    return "P3 - LOW"


def main():
    """Main function to generate comprehensive audit summary."""
    print("=" * 100)
    print("📊 COMPREHENSIVE REQUIREMENTS AUDIT SUMMARY")
    print("=" * 100)
    print(f"⚠️  Note: __init__.py files excluded from analysis (typically don't need requirements)")
    print()

    py_files = get_all_python_files()
    py_files_no_init = [f for f in py_files if f.name != "__init__.py"]
    req_files = get_all_requirements_files()

    print(f"📊 OVERVIEW:")
    print(f"   🐍 Total Python files:          {len(py_files):4d}")
    print(f"   🐍 Excluding __init__.py:       {len(py_files_no_init):4d}")
    print(f"   📋 Requirements files:           {len(req_files):4d}")
    print()

    categorized = categorize_files()

    total_with = sum(len(v["with"]) for v in categorized.values())
    total_without = sum(len(v["without"]) for v in categorized.values())
    total_analyzed = total_with + total_without

    coverage_pct = (total_with / total_analyzed * 100) if total_analyzed > 0 else 0
    missing_pct = (total_without / total_analyzed * 100) if total_analyzed > 0 else 0

    print(f"   ✅ Files WITH requirements:     {total_with:4d} ({coverage_pct:5.1f}%)")
    print(f"   ❌ Files WITHOUT requirements:  {total_without:4d} ({missing_pct:5.1f}%)")
    print(f"{'=' * 100}\n")

    # Sort by priority (critical first)
    prioritized = sorted(
        categorized.items(),
        key=lambda x: (
            len(x[1]["without"]),  # Fewest missing first (quick wins)
            calculate_gap_priority(x[0], len(x[1]["without"])),  # Then by priority
        )
    )

    # Print detailed breakdown
    print(f"📋 DETAILED BREAKDOWN BY DIRECTORY:")
    print(f"{'=' * 100}\n")

    p0_count = 0
    p1_count = 0
    p2_count = 0
    p3_count = 0

    for dir_name, status in prioritized:
        with_req = len(status["with"])
        without_req = len(status["without"])
        total = with_req + without_req

        if total == 0:
            continue

        coverage = (with_req / total * 100) if total > 0 else 0
        priority = calculate_gap_priority(dir_name, without_req)

        # Count by priority
        if without_req > 0:
            if "P0" in priority:
                p0_count += without_req
            elif "P1" in priority:
                p1_count += without_req
            elif "P2" in priority:
                p2_count += without_req
            elif "P3" in priority:
                p3_count += without_req

        status_emoji = "✅" if coverage == 100 else "⚠️" if coverage >= 50 else "❌"
        priority_emoji = "🔴" if "P0" in priority else "🟠" if "P1" in priority else "🟡" if "P2" in priority else "🟢"

        print(f"{priority_emoji} {status_emoji} {dir_name:60s} {with_req:3d}/{total:3d} ({coverage:5.1f}%)  [{priority}]")

        # Show missing files if any (only for critical/priority areas)
        if without_req > 0 and ("P0" in priority or "P1" in priority):
            for file in sorted(status["without"]):
                print(f"      ❌ {file.name}")

    print(f"\n{'=' * 100}")
    print(f"📊 PRIORITY SUMMARY:")
    print(f"{'=' * 100}")
    print(f"   🔴 P0 - CRITICAL (Domain):      {p0_count:3d} files missing")
    print(f"   🟠 P1 - HIGH (Application):     {p1_count:3d} files missing")
    print(f"   🟡 P2 - MEDIUM (Core/Services): {p2_count:3d} files missing")
    print(f"   🟢 P3 - LOW (API/Utils):        {p3_count:3d} files missing")
    print(f"{'=' * 100}\n")

    # Show quick wins (near completion)
    print(f"🎯 QUICK WINS (nearly complete - 1-3 files missing):")
    print(f"{'=' * 100}\n")

    quick_wins = [
        (dir_name, status)
        for dir_name, status in prioritized
        if 0 < len(status["without"]) <= 3 and len(status["without"]) + len(status["with"]) > 0
    ]

    for dir_name, status in sorted(quick_wins, key=lambda x: len(x[1]["without"])):
        without_req = len(status["without"])
        total = len(status["with"]) + len(status["without"])
        coverage = (len(status["with"]) / total * 100) if total > 0 else 0
        priority = calculate_gap_priority(dir_name, without_req)
        priority_emoji = "🔴" if "P0" in priority else "🟠" if "P1" in priority else "🟡" if "P2" in priority else "🟢"

        print(f"   {priority_emoji} {dir_name}: {without_req} missing ({coverage:.1f}% coverage)")
        for file in sorted(status["without"]):
            print(f"      - {file.name}")

    print(f"\n{'=' * 100}\n")

    # Recommendations
    print(f"💡 RECOMMENDATIONS:")
    print(f"{'=' * 100}\n")

    if p0_count > 0:
        print(f"   1. 🔴 URGENT: Create requirements for {p0_count} P0 (Domain) files")
        print(f"      These are critical business logic files that MUST have requirements.")
    if p1_count > 0:
        print(f"   2. 🟠 HIGH: Create requirements for {p1_count} P1 (Application) files")
        print(f"      These are use cases and application services.")
    if quick_wins:
        print(f"   3. 🎯 QUICK WINS: Complete the {len(quick_wins)} nearly-complete directories")
        print(f"      Start with these to get quick wins and boost coverage.")
    print(f"   4. 📋 MAINTAIN: Keep creating requirements for new files")
    print(f"      Aim for 100% coverage of non-__init__ files.")
    print()


if __name__ == "__main__":
    main()
