#!/usr/bin/env python3
"""
Script to analyze audit status of all Python files in app/.
Counts:
1. Files with requirements + PASSED audit
2. Files with requirements + NOT PASSED audit
3. Files without requirements
"""

import re
from pathlib import Path
from typing import Dict, Set, Tuple


def get_all_python_files() -> Set[Path]:
    """Get all Python files in app/ directory."""
    app_path = Path("app")
    if not app_path.exists():
        return set()
    return {f for f in app_path.rglob("*.py") if f.name != "__init__.py"}


def get_all_requirements_files() -> Set[Path]:
    """Get all requirements files in .requirements/ directory."""
    req_path = Path(".requirements/app")
    if not req_path.exists():
        return set()
    return set(req_path.rglob("*.requirements.md"))


def python_file_to_requirement_path(py_file: Path) -> Path:
    """Convert a Python file path to its expected requirements file path."""
    relative_path = py_file.relative_to("app")
    req_base = Path(".requirements/app") / relative_path
    # Try .requirements.md appended
    pattern = Path(str(req_base) + ".requirements.md")
    return pattern


def get_audit_status(req_file: Path) -> Tuple[str, str]:
    """Check if requirements file has PASSED audit."""
    if not req_file.exists():
        return "NO_REQS", "No requirements file"

    try:
        with open(req_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return "ERROR", "Could not read file"

    # Look for "## Audit Status" section
    audit_match = re.search(r'## Audit Status.*?\n(.*?)(?=##|\Z)', content, re.DOTALL)
    if not audit_match:
        return "NO_AUDIT", "No audit status section"

    audit_section = audit_match.group(1)

    # Check for PASSED status
    if re.search(r'\*\*Status:\*\*\s*PASSED', audit_section, re.IGNORECASE):
        return "PASSED", "PASSED"

    # Check for other statuses
    if re.search(r'\*\*Status:\*\*\s*(NEEDS_REVIEW|FAILED|PENDING)', audit_section, re.IGNORECASE):
        status = re.search(r'\*\*Status:\*\*\s*(NEEDS_REVIEW|FAILED|PENDING)', audit_section, re.IGNORECASE).group(1)
        return f"NOT_PASSED_{status.upper()}", status

    # If Audit Status section exists but no clear status
    return "NO_AUDIT", "Audit status section exists but unclear"


def main():
    """Main function."""
    print("=" * 100)
    print("📊 AUDIT STATUS SUMMARY FOR app/ DIRECTORY")
    print("=" * 100)
    print()

    py_files = get_all_python_files()
    req_files = get_all_requirements_files()

    # Count categories
    passed = 0
    not_passed = 0
    no_reqs = 0

    # Track details
    passed_files = []
    not_passed_files = []
    no_reqs_files = []

    for py_file in sorted(py_files):
        req_path = python_file_to_requirement_path(py_file)
        status, reason = get_audit_status(req_path)

        if status == "PASSED":
            passed += 1
            passed_files.append(py_file)
        elif status.startswith("NOT_PASSED"):
            not_passed += 1
            not_passed_files.append((py_file, reason))
        elif status == "NO_REQS":
            no_reqs += 1
            no_reqs_files.append(py_file)
        # NO_AUDIT and ERROR count as having requirements but not passed
        else:
            not_passed += 1
            not_passed_files.append((py_file, reason))

    total = passed + not_passed + no_reqs

    # Print summary
    print(f"📈 SUMMARY")
    print("-" * 100)
    print(f"   Total Python files: {total}")
    print()
    print(f"   ✅ 1. With requirements + PASSED audit: {passed} ({passed/total*100:.1f}%)")
    print(f"   ⚠️  2. With requirements + NOT PASSED audit: {not_passed} ({not_passed/total*100:.1f}%)")
    print(f"   ❌ 3. Without requirements: {no_reqs} ({no_reqs/total*100:.1f}%)")
    print()

    # Progress bar
    print(f"   Overall Audit Coverage: {(passed + not_passed) / total * 100:.1f}%")
    bar_length = 50
    filled = int(bar_length * (passed + not_passed) / total)
    bar = "█" * filled + "░" * (bar_length - filled)
    print(f"   [{bar}] {passed + not_passed}/{total} files with requirements")
    print()

    # PASSED files breakdown by layer
    print("=" * 100)
    print("✅ FILES WITH REQUIREMENTS + PASSED AUDIT")
    print("=" * 100)

    passed_by_layer = {}
    for py_file in passed_files:
        relative = str(py_file.relative_to("app"))
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

        if layer not in passed_by_layer:
            passed_by_layer[layer] = []
        passed_by_layer[layer].append(relative)

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
        if layer not in passed_by_layer:
            continue
        files = passed_by_layer[layer]
        print(f"\n📍 {layer}: {len(files)} files")
        for f in sorted(files):
            print(f"   ✅ app/{f}")

    # NOT PASSED files
    if not_passed_files:
        print(f"\n{'=' * 100}")
        print("⚠️  FILES WITH REQUIREMENTS + NOT PASSED AUDIT")
        print("=" * 100)

        by_layer = {}
        for py_file, reason in not_passed_files:
            relative = str(py_file.relative_to("app"))
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

            if layer not in by_layer:
                by_layer[layer] = []
            by_layer[layer].append((relative, reason))

        for layer in layer_order:
            if layer not in by_layer:
                continue
            files = by_layer[layer]
            print(f"\n📍 {layer}: {len(files)} files")
            for f, reason in sorted(files):
                print(f"   ⚠️  app/{f} ({reason})")

    # NO REQUIREMENTS files (just count, don't list all)
    if no_reqs_files:
        print(f"\n{'=' * 100}")
        print(f"❌ FILES WITHOUT REQUIREMENTS: {no_reqs} (showing first 20)")
        print("=" * 100)

        by_layer = {}
        for py_file in no_reqs_files:
            relative = str(py_file.relative_to("app"))
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

            if layer not in by_layer:
                by_layer[layer] = []
            by_layer[layer].append(relative)

        for layer in layer_order:
            if layer not in by_layer:
                continue
            files = by_layer[layer]
            print(f"\n📍 {layer}: {len(files)} files")
            shown = 0
            for f in sorted(files):
                if shown < 20:
                    print(f"   ❌ app/{f}")
                    shown += 1
            if len(files) > 20:
                print(f"   ... and {len(files) - 20} more")

    print(f"\n{'=' * 100}")
    print("✅ SUMMARY COMPLETE")
    print(f"{'=' * 100}\n")


if __name__ == "__main__":
    main()
