#!/usr/bin/env python3
"""
Requirements Compliance Checker

Verifies that each production Python file in app/ complies with the rules
defined in its corresponding .requirements file.

Runs these automated checks per file:
  - SRP-001:       Single responsibility heuristic (file < 300 lines, or one primary class)
  - GOD-CLASS:     File under 300 lines
  - TYPE-HINTS:    All public functions have return type annotations
  - CC-001:        No functions with cyclomatic complexity >= 10 (via radon)
  - SEC-001:       No hardcoded secrets (excludes os.environ / getenv / Settings / Field)
  - ARCH-006:      Value objects are immutable (frozen dataclasses where applicable)
  - ANTI-PATTERNS: No ``# type: ignore``, ``# pylint: disable``, ``# noqa``, ``# nosec``,
                   or bare ``Any`` type hints

Generates:
    .ralph/outputs/REQUIREMENTS_COMPLIANCE_REPORT.json

Usage:
    .venv/bin/python scripts/requirements_compliance_checker.py
"""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path("/Users/kepa.cantero/Projects/algoTrading")
REQUIREMENTS_DIR = PROJECT_ROOT / ".requirements" / "app"
OUTPUT_PATH = PROJECT_ROOT / ".ralph" / "outputs" / "REQUIREMENTS_COMPLIANCE_REPORT.json"

RADON_BIN = str(PROJECT_ROOT / ".venv" / "bin" / "radon")

MAX_FILE_LINES = 300
MAX_CC = 10

RULE_IDS = [
    "SRP-001",
    "GOD-CLASS",
    "TYPE-HINTS",
    "CC-001",
    "SEC-001",
    "ARCH-006",
    "ANTI-PATTERNS",
]

# Patterns that look like hardcoded secrets but are benign
_SEC_SAFE_RE = re.compile(
    r"os\.environ|getenv|Settings|Field\(|environ\.get|config\.get|"
    r"getattr.*settings|os\.getenv|env\(|\.env",
    re.IGNORECASE,
)

# Suspicious secret-like tokens
_SEC_SECRET_RE = re.compile(
    r"""
    (?:
        (?:api_key|apikey|api[-_]?secret|secret[-_]?key)\s*[=:]\s*['"][^'"]{8,}['"]
        |
        (?:password|passwd|pwd)\s*[=:]\s*['"][^'"]{3,}['"]
        |
        (?:token|auth[-_]?token|access[-_]?token|bearer)\s*[=:]\s*['"][^'"]{8,}['"]
        |
        (?:private[-_]?key|secret)\s*[=:]\s*['"][^'"]{8,}['"]
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Anti-pattern regex (matches any of the forbidden comment directives)
_ANTI_PATTERN_RE = re.compile(
    r"#\s*type:\s*ignore|#\s*pylint:\s*disable|#\s*noqa|#\s*nosec",
)

# ``Any`` used as a type annotation (from ``typing`` import or ``typing.Any``)
_ANY_IMPORT_RE = re.compile(r"\bAny\b")


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------

@dataclass
class FileResult:
    """Compliance result for a single production file."""

    file: str
    requirements_file: str = ""
    source_exists: bool = True
    rules: Dict[str, str] = field(default_factory=dict)  # rule_id -> "passed" | "failed" | "partial"
    details: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def get_production_py_files() -> List[str]:
    """Return sorted list of production .py files under app/ (relative paths)."""

    exclude_substrings = (
        "tests/",
        "/tests/",
        "test_",
        "_test.py",
        "conftest.py",
        "__pycache__",
        "migrations/",
    )

    py_files: List[str] = []
    for dirpath, _dirnames, filenames in os.walk(PROJECT_ROOT / "app"):
        rel_dir = os.path.relpath(dirpath, PROJECT_ROOT)
        # Skip __pycache__ directories
        if "__pycache__" in rel_dir:
            continue
        for fname in sorted(filenames):
            if not fname.endswith(".py"):
                continue
            rel_path = os.path.join(rel_dir, fname)
            # Skip excluded patterns
            if any(pat in rel_path for pat in exclude_substrings):
                continue
            py_files.append(rel_path)

    return sorted(py_files)


def find_requirements_file(py_file: str) -> Optional[str]:
    """Locate the .requirements file for *py_file* (relative path like ``app/foo.py``)."""

    base = REQUIREMENTS_DIR.parent  # .requirements/
    rel = py_file  # e.g. "app/backtesting/metrics.py"

    for ext in (".requirements.md", ".requirements.txt"):
        candidate = base / f"{rel}{ext}"
        if candidate.exists():
            return str(candidate)

    return None


# ---------------------------------------------------------------------------
# Individual checks (pure / file-scoped)
# ---------------------------------------------------------------------------

def _count_loc(source: str) -> int:
    """Count lines of code (non-blank, non-comment-only)."""
    count = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            count += 1
    return count


def check_srp_and_god_class(source: str, tree: ast.Module) -> Tuple[str, str, Dict[str, Any]]:
    """SRP-001 & GOD-CLASS checks.

    Returns (srp_status, god_status, details_dict).
    """
    loc = _count_loc(source)

    # GOD-CLASS: simple line-count check
    god_status = "passed" if loc < MAX_FILE_LINES else "failed"

    # SRP-001 heuristic:
    #   - If file < 300 lines, consider it compliant.
    #   - Otherwise, check if there is one primary class (the largest class
    #     takes >50 % of the class-bearing lines).
    classes = [n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
    top_level_funcs = [
        n for n in tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]

    if loc < MAX_FILE_LINES:
        srp_status = "passed"
    elif len(classes) <= 1 and len(top_level_funcs) <= 5:
        srp_status = "passed"
    else:
        # Heuristic: if more than 3 classes or many top-level functions, flag it
        if len(classes) > 3 or len(top_level_funcs) > 8:
            srp_status = "failed"
        else:
            srp_status = "partial"

    details: Dict[str, Any] = {
        "loc": loc,
        "classes": len(classes),
        "top_level_functions": len(top_level_funcs),
    }
    return srp_status, god_status, details


def check_type_hints(tree: ast.Module) -> Tuple[str, List[str]]:
    """TYPE-HINTS: All public functions/methods must have return type annotations.

    Returns (status, list_of_missing).
    """
    missing: List[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        name = node.name
        # Skip dunder methods (they are conventionally untyped or inherited)
        if name.startswith("__") and name.endswith("__"):
            continue
        # Skip private / protected methods
        if name.startswith("_"):
            continue
        # Check return annotation
        if node.returns is None:
            missing.append(name)

    status = "passed" if not missing else "failed"
    return status, missing


def check_cc_001(py_path_abs: str) -> Tuple[str, List[str]]:
    """CC-001: No function with cyclomatic complexity >= 10.

    Uses ``radon cc <file> -s -nc`` and parses the output.

    Returns (status, list of offending "funcname (CC)" strings).
    """
    try:
        result = subprocess.run(
            [RADON_BIN, "cc", py_path_abs, "-s", "-nc"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        # If radon fails, we cannot determine -- mark partial
        return "partial", ["radon unavailable"]

    offenders: List[str] = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        # radon output lines look like:
        #   "    M 93:4 MetricsCalculator.calculate_all_metrics - F (43)"
        # The complexity number is in parentheses at the end
        m = re.search(r"\((\d+)\)\s*$", line)
        if m:
            cc_val = int(m.group(1))
            if cc_val >= MAX_CC:
                # Extract a short identifier from the line
                offenders.append(f"{line.strip()}")

    status = "passed" if not offenders else "failed"
    return status, offenders


def check_sec_001(source: str) -> Tuple[str, List[str]]:
    """SEC-001: No hardcoded secrets.

    Scans for suspicious ``api_key = "..."`` style patterns but excludes
    lines referencing os.environ, getenv, Settings, Field, etc.

    Returns (status, list of findings).
    """
    findings: List[str] = []
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _SEC_SAFE_RE.search(line):
            continue
        match = _SEC_SECRET_RE.search(line)
        if match:
            findings.append(f"L{lineno}: {line.strip()}")

    status = "passed" if not findings else "failed"
    return status, findings


def check_arch_006(source: str, tree: ast.Module) -> Tuple[str, List[str]]:
    """ARCH-006: Value objects are immutable (frozen dataclasses where applicable).

    For each ``@dataclass``-decorated class, check if ``frozen=True`` is present.
    Only flags classes that live in ``value_objects`` / ``models`` / ``entities``
    packages (value-object territory).

    Returns (status, list of unfrozen dataclass names).
    """
    unfrozen: List[str] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        # Check if class has @dataclass decorator
        has_dataclass = False
        for dec in node.decorator_list:
            if isinstance(dec, ast.Name) and dec.id == "dataclass":
                has_dataclass = True
            elif isinstance(dec, ast.Call) and isinstance(dec.func, ast.Name) and dec.func.id == "dataclass":
                has_dataclass = True

        if not has_dataclass:
            continue

        # Check for frozen=True argument
        is_frozen = False
        for dec in node.decorator_list:
            if isinstance(dec, ast.Call):
                for kw in dec.keywords:
                    if kw.arg == "frozen" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                        is_frozen = True

        if not is_frozen:
            unfrozen.append(node.name)

    if not unfrozen:
        return "passed", []
    return "failed", unfrozen


def check_anti_patterns(source: str, tree: ast.Module) -> Tuple[str, List[str]]:
    """ANTI-PATTERNS: No ``# type: ignore``, ``# pylint: disable``, ``# noqa``,
    ``# nosec``, or ``Any`` type hints in source.

    Returns (status, list of findings).
    """
    findings: List[str] = []

    # 1. Forbidden comment patterns
    for lineno, line in enumerate(source.splitlines(), start=1):
        if _ANTI_PATTERN_RE.search(line):
            findings.append(f"L{lineno}: {line.strip()}")

    # 2. Bare ``Any`` used in annotations (from ``typing`` import)
    #    Walk the AST and check annotations for ``Name(id="Any")`` references.
    uses_any = False
    for node in ast.walk(tree):
        # Check function argument annotations and return annotations
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            all_annotations: List[ast.expr] = []
            if node.returns:
                all_annotations.append(node.returns)
            for arg in node.args.args:
                if arg.annotation:
                    all_annotations.append(arg.annotation)
            for ann in all_annotations:
                for child in ast.walk(ann):
                    if isinstance(child, ast.Name) and child.id == "Any":
                        uses_any = True

        # Check class-level annotations
        if isinstance(node, ast.AnnAssign) and node.annotation:
            for child in ast.walk(node.annotation):
                if isinstance(child, ast.Name) and child.id == "Any":
                    uses_any = True

    if uses_any:
        findings.append("Uses 'typing.Any' in annotations")

    status = "passed" if not findings else "failed"
    return status, findings


# ---------------------------------------------------------------------------
# Per-file orchestrator
# ---------------------------------------------------------------------------

def analyse_file(py_file_rel: str, req_path: Optional[str]) -> FileResult:
    """Run all checks on a single file and return a ``FileResult``."""

    result = FileResult(file=py_file_rel, requirements_file=req_path or "")
    abs_path = PROJECT_ROOT / py_file_rel

    if not abs_path.exists():
        result.source_exists = False
        for rid in RULE_IDS:
            result.rules[rid] = "failed"
        return result

    # Read source
    try:
        source = abs_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        result.source_exists = False
        for rid in RULE_IDS:
            result.rules[rid] = "failed"
        return result

    # Parse AST
    try:
        tree = ast.parse(source, filename=str(abs_path))
    except SyntaxError:
        for rid in RULE_IDS:
            result.rules[rid] = "failed"
        result.details["syntax_error"] = True
        return result

    # SRP-001 & GOD-CLASS
    srp, god, size_details = check_srp_and_god_class(source, tree)
    result.rules["SRP-001"] = srp
    result.rules["GOD-CLASS"] = god
    result.details.update(size_details)

    # TYPE-HINTS
    th_status, th_missing = check_type_hints(tree)
    result.rules["TYPE-HINTS"] = th_status
    if th_missing:
        result.details["missing_return_types"] = len(th_missing)
        result.details["missing_return_type_functions"] = th_missing[:10]  # cap list

    # CC-001 (cyclomatic complexity via radon)
    cc_status, cc_offenders = check_cc_001(str(abs_path))
    result.rules["CC-001"] = cc_status
    if cc_offenders:
        result.details["high_cc_functions"] = cc_offenders[:10]

    # SEC-001
    sec_status, sec_findings = check_sec_001(source)
    result.rules["SEC-001"] = sec_status
    if sec_findings:
        result.details["secret_findings"] = sec_findings[:5]

    # ARCH-006
    arch_status, arch_unfrozen = check_arch_006(source, tree)
    result.rules["ARCH-006"] = arch_status
    if arch_unfrozen:
        result.details["unfrozen_dataclasses"] = arch_unfrozen[:10]

    # ANTI-PATTERNS
    anti_status, anti_findings = check_anti_patterns(source, tree)
    result.rules["ANTI-PATTERNS"] = anti_status
    if anti_findings:
        result.details["anti_pattern_findings"] = anti_findings[:10]

    return result


# ---------------------------------------------------------------------------
# Batch radon invocation for efficiency
# ---------------------------------------------------------------------------

def batch_radon_cc(py_files_abs: List[str]) -> Dict[str, List[str]]:
    """Run radon cc on many files in one subprocess call for speed.

    Returns {abs_path: [offender_lines]}.
    """
    if not py_files_abs:
        return {}

    try:
        proc = subprocess.run(
            [RADON_BIN, "cc"] + py_files_abs + ["-s", "-nc"],
            capture_output=True,
            text=True,
            timeout=300,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
        return {}

    # Parse output -- radon groups by file header lines
    current_file: Optional[str] = None
    results: Dict[str, List[str]] = defaultdict(list)

    for line in proc.stdout.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        # File header: an absolute path (starts with / or a letter and contains .py)
        if stripped.endswith(".py") and not stripped[0].isspace():
            current_file = stripped
            continue

        # Complexity line: has (N) at end
        m = re.search(r"\((\d+)\)\s*$", stripped)
        if m and current_file:
            cc_val = int(m.group(1))
            if cc_val >= MAX_CC:
                results[current_file].append(stripped)

    return dict(results)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def classify_overall(rules: Dict[str, str]) -> str:
    """Classify a file as compliant / partially_compliant / non_compliant."""
    actionable = {k: v for k, v in rules.items() if v != "na"}
    if not actionable:
        return "compliant"

    failed = sum(1 for v in actionable.values() if v == "failed")
    partial = sum(1 for v in actionable.values() if v == "partial")
    total = len(actionable)

    if failed == 0 and partial == 0:
        return "compliant"
    if failed > total // 2:
        return "non_compliant"
    return "partially_compliant"


def main() -> None:
    print("=" * 60)
    print("  Requirements Compliance Checker")
    print("=" * 60)
    print()

    # ------------------------------------------------------------------
    # Step 1: Discover production files
    # ------------------------------------------------------------------
    prod_files = get_production_py_files()
    print(f"Discovered {len(prod_files)} production Python files in app/")

    # ------------------------------------------------------------------
    # Step 2: Pre-compute radon CC results in one batch call
    # ------------------------------------------------------------------
    print("Running radon cyclomatic-complexity analysis (batch)...", end=" ", flush=True)
    existing_files = [
        str(PROJECT_ROOT / f) for f in prod_files if (PROJECT_ROOT / f).exists()
    ]
    radon_results = batch_radon_cc(existing_files)
    print(f"done ({len(radon_results)} files with CC >= {MAX_CC})")

    # ------------------------------------------------------------------
    # Step 3: Analyse each file
    # ------------------------------------------------------------------
    results: List[FileResult] = []
    files_with_req = 0
    missing_source = 0

    for i, py_file in enumerate(prod_files):
        req_path = find_requirements_file(py_file)

        if req_path:
            files_with_req += 1

        result = analyse_file(py_file, req_path)

        # Overlay the batch radon result
        abs_py = str(PROJECT_ROOT / py_file)
        if abs_py in radon_results:
            result.rules["CC-001"] = "failed"
            result.details["high_cc_functions"] = radon_results[abs_py][:10]
        elif result.source_exists:
            result.rules["CC-001"] = "passed"

        if not result.source_exists:
            missing_source += 1

        results.append(result)

        if (i + 1) % 200 == 0:
            print(f"  Analysed {i + 1}/{len(prod_files)} files...")

    print(f"  Analysed {len(prod_files)}/{len(prod_files)} files.")
    print()

    # ------------------------------------------------------------------
    # Step 4: Aggregate
    # ------------------------------------------------------------------
    rule_stats: Dict[str, Dict[str, int]] = {rid: {"passed": 0, "failed": 0} for rid in RULE_IDS}

    fully_compliant = 0
    partially_compliant = 0
    non_compliant = 0

    for r in results:
        if not r.source_exists:
            # Count missing source files as non-compliant for every rule
            non_compliant += 1
            for rid in RULE_IDS:
                rule_stats[rid]["failed"] += 1
            continue

        overall = classify_overall(r.rules)
        if overall == "compliant":
            fully_compliant += 1
        elif overall == "partially_compliant":
            partially_compliant += 1
        else:
            non_compliant += 1

        for rid in RULE_IDS:
            status = r.rules.get(rid, "failed")
            if status == "passed":
                rule_stats[rid]["passed"] += 1
            else:
                rule_stats[rid]["failed"] += 1

    files_checked = len(prod_files) - missing_source
    total_applicable = sum(v["passed"] + v["failed"] for v in rule_stats.values())
    total_passed = sum(v["passed"] for v in rule_stats.values())
    compliance_rate = round(total_passed / total_applicable * 100, 1) if total_applicable else 0.0

    # ------------------------------------------------------------------
    # Step 5: Build JSON report
    # ------------------------------------------------------------------
    report: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_files": len(prod_files),
        "files_checked": files_checked,
        "fully_compliant": fully_compliant,
        "partially_compliant": partially_compliant,
        "non_compliant": non_compliant,
        "missing_source": missing_source,
        "compliance_by_rule": rule_stats,
        "compliance_rate": compliance_rate,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, ensure_ascii=False)

    # ------------------------------------------------------------------
    # Step 6: Print summary
    # ------------------------------------------------------------------
    print(f"Report written to: {OUTPUT_PATH}")
    print()
    print("-" * 60)
    print("  SUMMARY")
    print("-" * 60)
    print(f"  Total files:           {len(prod_files)}")
    print(f"  Files checked:         {files_checked}")
    print(f"  Fully compliant:       {fully_compliant}")
    print(f"  Partially compliant:   {partially_compliant}")
    print(f"  Non-compliant:         {non_compliant}")
    print(f"  Missing source:        {missing_source}")
    print(f"  Compliance rate:       {compliance_rate}%")
    print()
    print("-" * 60)
    print("  COMPLIANCE BY RULE")
    print("-" * 60)
    for rid in RULE_IDS:
        stats = rule_stats[rid]
        total = stats["passed"] + stats["failed"]
        rate = stats["passed"] / total * 100 if total else 0
        bar = "+" * int(rate // 5) + "." * (20 - int(rate // 5))
        print(f"  {rid:<16} {stats['passed']:>4}/{total:<4} ({rate:5.1f}%) |{bar}|")
    print()


if __name__ == "__main__":
    main()
