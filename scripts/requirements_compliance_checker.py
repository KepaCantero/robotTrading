#!/usr/bin/env python3
"""
Requirements Compliance Checker

Verifies that each production Python file complies with its corresponding
.requirements.md or .requirements.txt file.

Generates: .ralph/outputs/REQUIREMENTS_COMPLIANCE_REPORT.json
"""

import ast
import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class FileCompliance:
    """Compliance status for a single file."""
    file: str
    requirements_file: str
    status: str = "pending"  # compliant, partially_compliant, non_compliant, no_requirements
    rules_checked: dict = field(default_factory=dict)
    validation: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)


def get_production_files() -> list[str]:
    """Find all production Python files in app/."""
    result = subprocess.run(
        ["find", "app", "-name", "*.py", "-type", "f"],
        capture_output=True, text=True, cwd="/Users/kepa.cantero/Projects/algoTrading"
    )
    files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    # Filter out test files and other exclusions
    exclude_patterns = [
        "tests/", "test_", "_test.py", "conftest.py",
        "integration/", "__pycache__/", "migrations/"
    ]
    filtered = []
    for f in files:
        skip = False
        for pat in exclude_patterns:
            if pat in f:
                skip = True
                break
        if not skip:
            filtered.append(f)
    return sorted(filtered)


def find_requirements_file(py_file: str) -> Optional[str]:
    """Find the requirements file for a given Python file."""
    base = Path("/Users/kepa.cantero/Projects/algoTrading")
    req_md = base / f".requirements/{py_file}.requirements.md"
    req_txt = base / f".requirements/{py_file}.requirements.txt"
    if req_md.exists():
        return str(req_md)
    if req_txt.exists():
        return str(req_txt)
    return None


def parse_requirements_status(req_path: str) -> dict:
    """Parse a requirements file and extract rule statuses."""
    rules = {}
    with open(req_path, "r") as f:
        content = f.read()

    # Pattern: - [x] RULE_ID: description  (passed)
    # Pattern: - [ ] RULE_ID: description  (not checked)
    # Pattern: - [?] RULE_ID: description  (partial)
    # Pattern: - [x] description (no rule ID - map to next rule)
    # Pattern: - [ ] description (no rule ID)

    # Match checkboxes with optional rule IDs
    checkbox_pattern = re.compile(
        r'^- \[([ x?])\]\s*(?:\*{0,2})?([A-Z0-9-]+(?:-[A-Z0-9]+)*):\s*(.+?)(?:\*{0,2})\s*$',
        re.MULTILINE
    )
    checkbox_no_id = re.compile(
        r'^- \[([ x?])\]\s+(.+?)$',
        re.MULTILINE
    )

    # First pass: checkboxes with IDs
    for match in checkbox_pattern.finditer(content):
        status_char, rule_id, description = match.groups()
        if status_char == 'x':
            rules[rule_id] = "passed"
        elif status_char == '?':
            rules[rule_id] = "partial"
        else:
            rules[rule_id] = "failed"

    # Count total checkboxes (including without IDs)
    total_checkboxes = len(re.findall(r'^- \[[ x?]\]', content, re.MULTILINE))
    checked = len(re.findall(r'^- \[x\]', content, re.MULTILINE))
    partial = len(re.findall(r'^- \[\?\]', content, re.MULTILINE))
    unchecked = len(re.findall(r'^- \[ \]', content, re.MULTILINE))

    return {
        "rules": rules,
        "total_checkboxes": total_checkboxes,
        "checked": checked,
        "partial": partial,
        "unchecked": unchecked,
    }


def check_file_compliance(py_file: str, req_path: str) -> FileCompliance:
    """Check a single file's compliance against its requirements."""
    base = Path("/Users/kepa.cantero/Projects/algoTrading")
    full_path = base / py_file
    compliance = FileCompliance(
        file=py_file,
        requirements_file=req_path,
    )

    # Parse requirements file
    req_data = parse_requirements_status(req_path)

    # Check if file exists
    if not full_path.exists():
        compliance.status = "non_compliant"
        compliance.errors.append("File does not exist")
        return compliance

    # Read the Python file
    try:
        with open(full_path, "r") as f:
            source = f.read()
        lines = source.split("\n")
        loc = len([l for l in lines if l.strip() and not l.strip().startswith("#")])
    except Exception as e:
        compliance.status = "non_compliant"
        compliance.errors.append(f"Cannot read file: {e}")
        return compliance

    # Parse AST
    try:
        tree = ast.parse(source)
    except SyntaxError:
        compliance.status = "non_compliant"
        compliance.errors.append("Syntax error in file")
        return compliance

    # --- Automated checks ---

    # 1. GOD-CLASS: File < 300 lines
    god_class_pass = loc < 300
    compliance.rules_checked["GOD-CLASS"] = "passed" if god_class_pass else "failed"
    compliance.validation["loc"] = loc

    # 2. GOD-FUNC: Functions < 50 lines
    long_functions = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            func_lines = node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') and node.end_lineno else 0
            if func_lines > 50:
                long_functions.append(f"{node.name}({func_lines}L)")
    god_func_pass = len(long_functions) == 0
    compliance.rules_checked["GOD-FUNC"] = "passed" if god_func_pass else "failed"
    if long_functions:
        compliance.validation["long_functions"] = long_functions

    # 3. TYPE-HINTS: Check type hint coverage
    functions_without_hints = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Skip private/dunder methods
            if node.name.startswith("_") and not node.name.startswith("__"):
                continue
            # Check return type annotation
            if node.returns is None:
                # Check if it's a simple function in __init__.py or similar
                functions_without_hints.append(node.name)

    type_hints_pass = len(functions_without_hints) == 0
    compliance.rules_checked["TYPE-HINTS"] = "passed" if type_hints_pass else "failed"
    if functions_without_hints:
        compliance.validation["missing_type_hints"] = len(functions_without_hints)

    # 4. SRP-001: Single Responsibility (heuristic - check number of classes and top-level functions)
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    top_level_functions = [n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    # Heuristic: If file has > 5 classes or > 10 top-level functions, might violate SRP
    srp_pass = len(classes) <= 5 and len(top_level_functions) <= 10
    compliance.rules_checked["SRP-001"] = "passed" if srp_pass else "failed"
    compliance.validation["classes"] = len(classes)
    compliance.validation["top_level_functions"] = len(top_level_functions)

    # 5. COMPLEXITY: Check for deeply nested code
    max_depth = 0
    def measure_depth(node, depth=0):
        nonlocal max_depth
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
                new_depth = depth + 1
                if new_depth > max_depth:
                    max_depth = new_depth
                measure_depth(child, new_depth)
            else:
                measure_depth(child, depth)
    measure_depth(tree)
    complexity_pass = max_depth <= 5
    compliance.rules_checked["COMPLEXITY"] = "passed" if complexity_pass else "failed"
    compliance.validation["max_nesting_depth"] = max_depth

    # 6. OCP-001: Open/Closed (check for Protocol/ABC usage)
    has_protocols = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name) and base.id in ("Protocol", "ABC"):
                    has_protocols = True
                elif isinstance(base, ast.Attribute) and base.attr in ("Protocol", "ABC"):
                    has_protocols = True
    compliance.rules_checked["OCP-001"] = "passed" if has_protocols else "na"

    # 7. DIP-001: Dependency Inversion (check constructor injection)
    has_di = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                    # Check if constructor takes arguments (besides self)
                    if len(item.args.args) > 1:
                        has_di = True
    compliance.rules_checked["DIP-001"] = "passed" if has_di else "na"

    # 8. LSP-001 and ISP-001: Usually N/A unless inheritance present
    has_inheritance = False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.bases:
            has_inheritance = True
    compliance.rules_checked["LSP-001"] = "na"
    compliance.rules_checked["ISP-001"] = "na"

    # Also check requirements file checkboxes for existing status
    for rule_id, status in req_data["rules"].items():
        if rule_id not in compliance.rules_checked:
            compliance.rules_checked[rule_id] = status

    # Determine overall status
    rule_statuses = [v for v in compliance.rules_checked.values() if v != "na"]
    if not rule_statuses:
        compliance.status = "compliant"
    elif all(s == "passed" for s in rule_statuses):
        compliance.status = "compliant"
    elif any(s == "failed" for s in rule_statuses):
        failed_count = sum(1 for s in rule_statuses if s == "failed")
        if failed_count > len(rule_statuses) / 2:
            compliance.status = "non_compliant"
        else:
            compliance.status = "partially_compliant"
    else:
        compliance.status = "partially_compliant"

    return compliance


def main():
    base = Path("/Users/kepa.cantero/Projects/algoTrading")
    output_dir = base / ".ralph" / "outputs"
    output_dir.mkdir(parents=True, exist_ok=True)

    print("=== Requirements Compliance Checker ===")
    print()

    # Get all production files
    prod_files = get_production_files()
    print(f"Found {len(prod_files)} production Python files")

    # Track results
    results: list[FileCompliance] = []
    files_with_req = 0
    files_without_req = 0
    fully_compliant = 0
    partially_compliant = 0
    non_compliant = 0

    # Rule aggregation
    rule_stats: dict[str, dict[str, int]] = {}

    for i, py_file in enumerate(prod_files):
        req_path = find_requirements_file(py_file)

        if req_path is None:
            files_without_req += 1
            compliance = FileCompliance(
                file=py_file,
                requirements_file="",
                status="no_requirements",
            )
            compliance.errors.append("No requirements file found")
        else:
            files_with_req += 1
            compliance = check_file_compliance(py_file, req_path)

            # Aggregate rule stats
            for rule_id, status in compliance.rules_checked.items():
                if rule_id not in rule_stats:
                    rule_stats[rule_id] = {"passed": 0, "failed": 0, "na": 0, "partial": 0}
                if status in rule_stats[rule_id]:
                    rule_stats[rule_id][status] += 1

        # Count statuses
        if compliance.status == "compliant":
            fully_compliant += 1
        elif compliance.status == "partially_compliant":
            partially_compliant += 1
        elif compliance.status == "non_compliant":
            non_compliant += 1

        results.append(compliance)

        if (i + 1) % 100 == 0:
            print(f"  Processed {i + 1}/{len(prod_files)} files...")

    print(f"  Processed {len(prod_files)}/{len(prod_files)} files...")
    print()

    # Generate report
    report = {
        "timestamp": __import__("datetime").datetime.now().isoformat(),
        "summary": {
            "total_files": len(prod_files),
            "files_checked": files_with_req,
            "fully_compliant": fully_compliant,
            "partially_compliant": partially_compliant,
            "non_compliant": non_compliant,
            "missing_requirements": files_without_req,
        },
        "compliance_by_rule": rule_stats,
        "files": [
            {
                "file": r.file,
                "requirements_file": r.requirements_file.replace(str(base) + "/", "") if r.requirements_file else "",
                "status": r.status,
                "rules_checked": r.rules_checked,
                "validation": r.validation,
                "errors": r.errors,
            }
            for r in results
        ],
    }

    # Write report
    report_path = output_dir / "REQUIREMENTS_COMPLIANCE_REPORT.json"
    with open(report_path, "w") as f:
        json.dump(report, f, indent=2, default=str)

    print(f"Report written to: {report_path}")
    print()
    print("=== Summary ===")
    print(f"Total files: {len(prod_files)}")
    print(f"Files with requirements: {files_with_req}")
    print(f"Files without requirements: {files_without_req}")
    print(f"Fully compliant: {fully_compliant}")
    print(f"Partially compliant: {partially_compliant}")
    print(f"Non-compliant: {non_compliant}")
    print()
    print("=== Compliance by Rule ===")
    for rule_id, stats in sorted(rule_stats.items()):
        total = sum(stats.values())
        pass_rate = (stats.get("passed", 0) / total * 100) if total > 0 else 0
        print(f"  {rule_id}: {pass_rate:.1f}% pass rate ({stats})")

    return report


if __name__ == "__main__":
    main()
