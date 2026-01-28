#!/usr/bin/env python3
"""
Clean Architecture Compliance Checker

This script checks the codebase for Clean Architecture compliance
without importing any application code.
"""

import sys
from pathlib import Path
import re
from typing import List, Tuple, Dict


def check_domain_layer_independence(project_root: Path) -> List[Tuple[Path, int, str]]:
    """Check that domain layer has no external dependencies."""
    domain_dir = project_root / "app" / "domain"
    violations = []

    if not domain_dir.exists():
        return violations

    for py_file in domain_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        with open(py_file) as f:
            content = f.read()
            lines = content.split('\n')

        for i, line in enumerate(lines[:30], 1):
            if re.search(r'^from app\.(services|infrastructure|api)', line):
                violations.append((py_file, i, line.strip()))
            if re.search(r'^import app\.(services|infrastructure|api)', line):
                violations.append((py_file, i, line.strip()))

    return violations


def check_application_layer_dependencies(project_root: Path) -> List[Tuple[Path, int, str]]:
    """Check that application layer depends only on domain."""
    app_dir = project_root / "app" / "application"
    violations = []

    if not app_dir.exists():
        return violations

    for py_file in app_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        with open(py_file) as f:
            content = f.read()
            lines = content.split('\n')

        for i, line in enumerate(lines[:30], 1):
            if re.search(r'^from app\.infrastructure', line):
                violations.append((py_file, i, line.strip()))
            if re.search(r'^from app\.services', line):
                violations.append((py_file, i, line.strip()))
            if re.search(r'^from app\.api', line):
                violations.append((py_file, i, line.strip()))

    return violations


def check_file_size_limits(project_root: Path, max_lines: int = 300) -> List[Tuple[Path, int]]:
    """Check that files don't exceed size limits."""
    app_dir = project_root / "app"
    large_files = []

    if not app_dir.exists():
        return large_files

    for py_file in app_dir.rglob("*.py"):
        if py_file.name == "__init__.py":
            continue

        with open(py_file) as f:
            line_count = sum(1 for _ in f)

        if line_count > max_lines:
            large_files.append((py_file, line_count))

    return large_files


def count_files_by_layer(project_root: Path) -> Dict[str, int]:
    """Count files by architectural layer."""
    app_dir = project_root / "app"
    layers = ['domain', 'application', 'infrastructure', 'api']
    counts = {}

    for layer in layers:
        layer_dir = app_dir / layer
        if layer_dir.exists():
            counts[layer] = len(list(layer_dir.rglob("*.py")))
        else:
            counts[layer] = 0

    return counts


def print_results(
    domain_violations: List,
    app_violations: List,
    large_files: List,
    layer_counts: Dict[str, int],
    project_root: Path
) -> None:
    """Print check results."""
    print("\n" + "="*70)
    print("CLEAN ARCHITECTURE COMPLIANCE REPORT")
    print("="*70)

    # Domain layer check
    print("\n1. DOMAIN LAYER INDEPENDENCE")
    print("-" * 70)
    if domain_violations:
        print("❌ FAILED: Domain layer has external dependencies")
        for file_path, line_num, line in domain_violations:
            rel_path = file_path.relative_to(project_root)
            print(f"   {rel_path}:{line_num}")
            print(f"     {line}")
    else:
        print("✅ PASSED: Domain layer has no external dependencies")

    # Application layer check
    print("\n2. APPLICATION LAYER DEPENDENCIES")
    print("-" * 70)
    if app_violations:
        print("❌ FAILED: Application layer has improper dependencies")
        for file_path, line_num, line in app_violations[:5]:
            rel_path = file_path.relative_to(project_root)
            print(f"   {rel_path}:{line_num}")
            print(f"     {line}")
        if len(app_violations) > 5:
            print(f"   ... and {len(app_violations) - 5} more")
    else:
        print("✅ PASSED: Application layer depends only on domain")

    # File size check
    print("\n3. FILE SIZE LIMITS (SRP)")
    print("-" * 70)
    if large_files:
        print(f"❌ FAILED: {len(large_files)} files exceed 300 lines")
        print("\n   Top 10 largest files:")
        large_files.sort(key=lambda x: x[1], reverse=True)
        for file_path, line_count in large_files[:10]:
            rel_path = file_path.relative_to(project_root)
            print(f"   {line_count:4d} lines - {rel_path}")
        if len(large_files) > 10:
            print(f"   ... and {len(large_files) - 10} more")
    else:
        print("✅ PASSED: All files under 300 lines")

    # Layer statistics
    print("\n4. LAYER STATISTICS")
    print("-" * 70)
    total_files = sum(layer_counts.values())
    for layer, count in layer_counts.items():
        percentage = (count / total_files * 100) if total_files > 0 else 0
        print(f"   {layer:20s}: {count:4d} files ({percentage:5.1f}%)")

    # Overall compliance
    print("\n" + "="*70)
    print("OVERALL COMPLIANCE")
    print("="*70)

    passed_checks = sum([
        not domain_violations,
        not app_violations,
        not large_files
    ])
    total_checks = 3
    compliance = (passed_checks / total_checks) * 100

    print(f"Current Compliance: {compliance:.0f}%")
    print(f"Target Compliance: 95%")
    print(f"Passed: {passed_checks}/{total_checks} checks")

    if compliance == 100:
        print("\n✅ EXCELLENT: All Clean Architecture rules pass!")
    elif compliance >= 80:
        print("\n⚠️  GOOD: Most rules pass, see issues above")
    else:
        print("\n❌ NEEDS WORK: Multiple violations detected")

    print("="*70 + "\n")


def main():
    """Run architecture compliance checks."""
    # Get project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Run checks
    domain_violations = check_domain_layer_independence(project_root)
    app_violations = check_application_layer_dependencies(project_root)
    large_files = check_file_size_limits(project_root)
    layer_counts = count_files_by_layer(project_root)

    # Print results
    print_results(
        domain_violations,
        app_violations,
        large_files,
        layer_counts,
        project_root
    )

    # Exit with error code if any violations
    if domain_violations or app_violations:
        sys.exit(1)
    elif large_files:
        sys.exit(0)  # Warning only
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()
