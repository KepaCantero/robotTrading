#!/usr/bin/env python3
"""
Verify Domain-Infrastructure Separation

This script checks that the domain layer has no dependencies on infrastructure.
It's part of FASE 1.5 - Separar domain de infrastructure.

Run: python app/scripts/check_domain_dependencies.py
"""

import logging

import ast
import os
import sys
from pathlib import Path
from typing import List, Set, Tuple


# Infrastructure modules that domain should NOT depend on
INFRASTRUCTURE_MODULES = {
    "database",
    "api",
    "infrastructure",
    "persistence",
    "external",
    "messaging",
    "dashboard",
    "engines",  # If they contain infrastructure
    "services",  # If they contain infrastructure
    "sqlalchemy",
    "psycopg2",
    "redis",
    "celery",
    "fastapi",
    "pydantic",  # For models (domain should use domain models)
    "requests",  # External API calls
}


def get_imports_from_file(file_path: Path) -> List[str]:
    """Extract all imports from a Python file."""
    imports = []

    try:
        with open(file_path, "r") as f:
            tree = ast.parse(f.read(), filename=str(file_path))

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
    except (SyntaxError, UnicodeDecodeError) as e:
        logger.debug(f"Warning: Could not parse {file_path}: {e}")

    return imports


def check_file(file_path: Path, base_path: Path) -> List[Tuple[str, str]]:
    """Check a single file for infrastructure dependencies."""
    violations = []

    # Get relative path from app/
    try:
        rel_path = file_path.relative_to(base_path)
    except ValueError:
        return violations

    # Only check files in domain/
    if "domain" not in rel_path.parts:
        return violations

    imports = get_imports_from_file(file_path)

    for imp in imports:
        # Check if import is from infrastructure
        for infra_mod in INFRASTRUCTURE_MODULES:
            if imp.startswith(f"app.{infra_mod}") or imp.startswith(infra_mod):
                violations.append((str(rel_path), imp))

    return violations


def check_domain_directory() -> bool:
    """Check all files in domain directory for infrastructure dependencies."""
    base_path = Path.cwd()
    domain_path = base_path / "app" / "domain"

    if not domain_path.exists():
        logger.debug(f"Error: {domain_path} does not exist")
        return False

    all_violations = []

    for py_file in domain_path.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue

        violations = check_file(py_file, base_path)
        all_violations.extend(violations)

    if all_violations:
        logger.debug("\n❌ FOUND INFRASTRUCTURE DEPENDENCIES IN DOMAIN LAYER:\n")
        for file_path, imp in all_violations:
            logger.debug(f"  {file_path}: imports {imp}")
        logger.debug(f"\nTotal violations: {len(all_violations)}")
        return False
    else:
        logger.debug("✅ No infrastructure dependencies found in domain layer!")
        return True


def main() -> int:
    """Main entry point."""
    logger.debug("=" * 70)
    logger.debug("Domain-Infrastructure Separation Checker")
    logger.debug("=" * 70)
    logger.debug()

    success = check_domain_directory()

    logger.debug()
    logger.debug("=" * 70)

    if success:
        logger.debug("✅ Domain layer is clean - no infrastructure dependencies!")
        return 0
    else:
        logger.debug("❌ Found infrastructure dependencies in domain layer")
        return 1


if __name__ == "__main__":
    sys.exit(main())
