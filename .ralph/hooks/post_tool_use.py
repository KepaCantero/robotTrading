#!/usr/bin/env python3
"""
Post-tool-use hook for .ralph
Validates tool outputs after execution, including ruff/mypy checks on edited files
"""
import json
import os
import subprocess
import sys


def _run_ruff_check(file_path: str) -> list[str]:
    """Run ruff lint check on a single file and return issues."""
    issues = []
    try:
        result = subprocess.run(
            ["ruff", "check", file_path, "--output-format", "concise"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                issues.append(f"ruff: {line.strip()}")
    except FileNotFoundError:
        issues.append("ruff not found - install with: pip install ruff")
    except subprocess.TimeoutExpired:
        issues.append("ruff check timed out")
    except Exception as exc:
        issues.append(f"ruff check error: {exc}")
    return issues


def _run_ruff_format_check(file_path: str) -> list[str]:
    """Run ruff format check on a single file and return issues."""
    issues = []
    try:
        result = subprocess.run(
            ["ruff", "format", "--check", file_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode != 0 and result.stdout.strip():
            issues.append(f"ruff format: {file_path} needs formatting")
    except FileNotFoundError:
        pass  # Already reported in lint check
    except subprocess.TimeoutExpired:
        issues.append("ruff format check timed out")
    except Exception as exc:
        issues.append(f"ruff format check error: {exc}")
    return issues


def _run_mypy_check(file_path: str) -> list[str]:
    """Run mypy type check on a single file and return issues."""
    issues = []
    try:
        result = subprocess.run(
            ["mypy", file_path, "--no-error-summary", "--no-color-output"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0 and result.stdout.strip():
            for line in result.stdout.strip().splitlines():
                if "error:" in line.lower():
                    issues.append(f"mypy: {line.strip()}")
    except FileNotFoundError:
        issues.append("mypy not found - install with: pip install mypy")
    except subprocess.TimeoutExpired:
        issues.append("mypy check timed out")
    except Exception as exc:
        issues.append(f"mypy check error: {exc}")
    return issues


def main():
    """Main hook function."""
    # Read hook input from stdin
    input_data = json.load(sys.stdin)

    tool_name = input_data.get("tool_name", "")
    tool_output = input_data.get("tool_output", {})

    # Check for required patterns in output
    issues = []

    # Convert output to string for checking
    output_str = str(tool_output) if tool_output else ""

    # Check for TODO/FIXME comments that should be resolved
    if tool_output:
        if "TODO:" in output_str or "FIXME:" in output_str:
            issues.append("Output contains TODO/FIXME - should be resolved")

    # Check for empty outputs
    if not output_str or output_str.strip() == "":
        issues.append("Empty output - no work done")

    # Check for error patterns
    error_patterns = [
        "Error:",
        "Exception:",
        "Traceback:",
        "Failed:",
    ]

    for pattern in error_patterns:
        if pattern in output_str:
            issues.append(f"Output contains error pattern: {pattern}")

    # Run ruff/mypy validation on edited Python files
    file_tools = {"Write", "Edit", "MultiEdit"}
    if tool_name in file_tools:
        file_path = ""
        if tool_name == "Write":
            file_path = input_data.get("tool_input", {}).get("file_path", "")
        elif tool_name == "Edit":
            file_path = input_data.get("tool_input", {}).get("file_path", "")
        elif tool_name == "MultiEdit":
            file_path = input_data.get("tool_input", {}).get("file_path", "")

        if file_path and file_path.endswith(".py") and os.path.isfile(file_path):
            ruff_lint_issues = _run_ruff_check(file_path)
            issues.extend(ruff_lint_issues)

            ruff_fmt_issues = _run_ruff_format_check(file_path)
            issues.extend(ruff_fmt_issues)

            mypy_issues = _run_mypy_check(file_path)
            issues.extend(mypy_issues)

    # Report issues
    if issues:
        print(
            json.dumps(
                {
                    "status": "warn",
                    "issues": issues,
                    "suggestion": "Review and fix the issues before continuing",
                }
            )
        )
    else:
        print(json.dumps({"status": "allow", "issues": [], "message": "Output validated"}))


if __name__ == "__main__":
    main()
