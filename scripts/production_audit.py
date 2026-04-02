#!/usr/bin/env python3
"""Production Audit: Verify each source file against its .requirements/ file."""

import ast
import os
import re
import sys
import json
from pathlib import Path


def parse_requirements(req_path: str) -> tuple:
    """Extract classes, functions, and dependencies from requirements file."""
    classes: list[str] = []
    functions: list[str] = []
    deps: list[str] = []

    if not os.path.exists(req_path):
        return None, classes, functions, deps

    with open(req_path, "r") as f:
        content = f.read()

    # Extract classes (capitalized identifiers in backticks)
    for m in re.finditer(r"^-\s+`([A-Z][A-Za-z_]+)`", content, re.MULTILINE):
        classes.append(m.group(1))

    # Extract public functions (lowercase with parens in backticks)
    for m in re.finditer(r"^-\s+`([a-z_]+)\(\)`", content, re.MULTILINE):
        functions.append(m.group(1))

    # Extract dependencies section
    dep_section = False
    for line in content.split("\n"):
        if "## 2. Dependencies" in line:
            dep_section = True
            continue
        if dep_section and line.startswith("## "):
            dep_section = False
            continue
        if dep_section and line.strip().startswith("- `"):
            dep = re.search(r"`([^`]+)`", line)
            if dep:
                deps.append(dep.group(1))

    return content, classes, functions, deps


def parse_source(src_path: str) -> tuple:
    """Extract classes and functions from source file."""
    classes: list[str] = []
    functions: list[str] = []

    if not os.path.exists(src_path):
        return classes, functions

    try:
        with open(src_path, "r") as f:
            tree = ast.parse(f.read())
    except SyntaxError:
        return classes, functions

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            functions.append(node.name)

    return classes, functions


def main() -> None:
    app_dir = "app"
    req_dir = ".requirements/app"
    results: list[tuple[str, list[str]]] = []
    total = 0
    compliant = 0
    gap_count = 0
    missing_req = 0

    for root, dirs, files in os.walk(app_dir):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in sorted(files):
            if not f.endswith(".py"):
                continue
            total += 1
            src_path = os.path.join(root, f)
            rel_path = src_path
            req_name = rel_path[len(app_dir) + 1 :] + ".requirements.txt"
            req_path = os.path.join(req_dir, req_name)

            req_content, req_classes, req_functions, req_deps = parse_requirements(
                req_path
            )
            src_classes, src_functions = parse_source(src_path)

            file_issues: list[str] = []

            if req_content is None:
                missing_req += 1
                continue

            # Check classes
            for cls in req_classes:
                if cls not in src_classes:
                    file_issues.append(f"Missing class: {cls}")

            # Check functions
            for fn in req_functions:
                if fn not in src_functions:
                    file_issues.append(f"Missing function: {fn}")

            if file_issues:
                gap_count += len(file_issues)
                results.append((rel_path, file_issues))
            else:
                compliant += 1

    # Output summary
    print(f"Total files: {total}")
    print(f"Compliant: {compliant}")
    print(f"Files with gaps: {len(results)}")
    print(f"Total gaps: {gap_count}")
    print(f"Missing requirements: {missing_req}")
    print()

    if results:
        print("=== GAP DETAILS ===")
        for path, issues in sorted(results):
            for issue in issues:
                print(f"  {path}: {issue}")

    # Write JSON report for further processing
    report = {
        "total": total,
        "compliant": compliant,
        "files_with_gaps": len(results),
        "total_gaps": gap_count,
        "missing_requirements": missing_req,
        "gaps": [{"file": p, "issues": i} for p, i in sorted(results)],
    }
    report_path = "logs/production_audit_report.json"
    os.makedirs("logs", exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2)
    print(f"\nJSON report written to {report_path}")


if __name__ == "__main__":
    main()
