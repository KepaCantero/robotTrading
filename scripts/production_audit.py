#!/usr/bin/env python3
"""Production Audit: verify each app/ source file against its .requirements/ stub.

Checks both directions:
  - GAP: a class/function promised by the spec is missing from the code.
  - STALE: the code has public classes/functions the spec does not list.

Run from anywhere; paths are anchored to the repo root. Exits 1 if anything
is missing, stale, or out of sync. JSON report: logs/production_audit_report.json

If drift is found, fix it with: python scripts/generate_requirements.py
"""

import ast
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
APP_DIR = PROJECT_ROOT / "app"
REQ_DIR = PROJECT_ROOT / ".requirements" / "app"
REPORT_PATH = PROJECT_ROOT / "logs" / "production_audit_report.json"

CLASS_RE = re.compile(r"^-\s+`(_?[A-Z][A-Za-z_0-9]*)`", re.MULTILINE)
FUNCTION_RE = re.compile(r"^-\s+`([A-Za-z_][A-Za-z_0-9]*)\(\)`", re.MULTILINE)


def parse_requirements(req_path: Path):
    """Extract the classes and public functions a spec stub promises."""
    if not req_path.exists():
        return None, [], []

    content = req_path.read_text(encoding="utf-8")
    classes = CLASS_RE.findall(content)
    functions = FUNCTION_RE.findall(content)
    return content, classes, functions


def parse_source(src_path: Path):
    """Extract all classes and public functions from the source file."""
    classes, functions = [], []

    try:
        tree = ast.parse(src_path.read_text(encoding="utf-8"))
    except (SyntaxError, UnicodeDecodeError):
        return classes, functions

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            classes.append(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if not node.name.startswith("_"):
                functions.append(node.name)

    return classes, functions


def main() -> int:
    results = []
    total = compliant = missing_req = 0

    for src in sorted(APP_DIR.rglob("*.py")):
        if "__pycache__" in src.parts:
            continue
        total += 1
        rel_path = src.relative_to(PROJECT_ROOT).as_posix()
        req_path = REQ_DIR / f"{src.relative_to(APP_DIR).as_posix()}.requirements.txt"

        req_content, req_classes, req_functions = parse_requirements(req_path)
        src_classes, src_functions = parse_source(src)

        if req_content is None:
            missing_req += 1
            results.append(
                (rel_path, [f"missing spec: {req_path.relative_to(PROJECT_ROOT).as_posix()}"])
            )
            continue

        issues = []
        # GAP: spec promises something the code no longer has.
        for cls in req_classes:
            if cls not in src_classes:
                issues.append(f"GAP missing class: {cls}")
        for fn in req_functions:
            if fn not in src_functions:
                issues.append(f"GAP missing function: {fn}()")

        # STALE: code grew public surface the spec does not list.
        for cls in src_classes:
            if cls not in req_classes:
                issues.append(f"STALE spec (class not listed): {cls}")
        for fn in src_functions:
            if fn not in req_functions:
                issues.append(f"STALE spec (function not listed): {fn}()")

        if issues:
            results.append((rel_path, issues))
        else:
            compliant += 1

    gap_count = sum(len(i) for _, i in results) + missing_req

    print(f"Total files: {total}")
    print(f"Compliant: {compliant}")
    print(f"Files with issues: {len(results)}")
    print(f"Total issues: {gap_count}")
    print(f"Missing specs: {missing_req}")
    print()

    if results:
        print("=== DETAILS ===")
        for path, issues in results:
            for issue in issues:
                print(f"  {path}: {issue}")

    report = {
        "total": total,
        "compliant": compliant,
        "files_with_issues": len(results),
        "total_issues": gap_count,
        "missing_specs": missing_req,
        "issues": [{"file": p, "issues": i} for p, i in sorted(results)],
    }
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2))
    print(f"\nJSON report written to {REPORT_PATH.relative_to(PROJECT_ROOT)}")

    return 1 if results else 0


if __name__ == "__main__":
    sys.exit(main())
