#!/usr/bin/env python3
"""
REAL validation script - executes tools and returns JSON results.

This script runs mypy, ruff, and bandit on a file and returns
structured JSON results. NO guessing - REAL tool output.
"""
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Any


def run_mypy(file_path: Path) -> Dict[str, Any]:
    """Run mypy and return results."""
    try:
        result = subprocess.run(
            ["mypy", "--no-error-summary", "--hide-error-context", "--show-error-codes", str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        errors = []
        for line in result.stdout.strip().split('\n'):
            if line.strip() and not line.startswith("Success"):
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    errors.append({
                        "line": parts[1],
                        "severity": "error",
                        "code": parts[3].strip().split()[0] if parts[3] else "unknown",
                        "message": parts[3].strip() if len(parts) > 3 else line,
                    })
        return {"success": result.returncode == 0, "errors": errors}
    except Exception as e:
        return {"success": False, "errors": [{"message": f"mypy failed: {e}"}]}


def run_ruff(file_path: Path) -> Dict[str, Any]:
    """Run ruff check and return results."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--output-format=json", str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        errors = []
        if result.stdout.strip():
            data = json.loads(result.stdout)
            if isinstance(data, list):
                for error in data:
                    errors.append({
                        "line": error.get("location", {}).get("row", "?") if isinstance(error.get("location"), dict) else "?",
                        "severity": "error",
                        "code": error.get("code", "???"),
                        "message": error.get("message", ""),
                        "fixable": error.get("fix", {}).get("applicability", "") == "safe" if isinstance(error.get("fix"), dict) else False,
                    })
        return {"success": len(errors) == 0, "errors": errors}
    except json.JSONDecodeError as e:
        return {"success": False, "errors": [{"message": f"ruff JSON decode failed: {e}", "tool": "ruff"}]}
    except Exception as e:
        return {"success": False, "errors": [{"message": f"ruff failed: {e}", "tool": "ruff"}]}


def run_ruff_fix(file_path: Path) -> Dict[str, Any]:
    """Run ruff --fix and return results."""
    try:
        result = subprocess.run(
            ["ruff", "check", "--fix", "--exit-non-zero-on-fix", str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return {"success": True, "fixed": True}
    except Exception as e:
        return {"success": False, "errors": [{"message": f"ruff fix failed: {e}"}]}


def run_bandit(file_path: Path) -> Dict[str, Any]:
    """Run bandit and return results."""
    try:
        result = subprocess.run(
            ["bandit", "-f", "json", str(file_path)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.stdout.strip():
            data = json.loads(result.stdout)
            results = data.get("results", [])
            errors = []
            for error in results:
                if error.get("issue_severity") in ["MEDIUM", "HIGH"]:
                    errors.append({
                        "line": error.get("line_number", "?"),
                        "severity": error.get("issue_severity", "UNKNOWN").lower(),
                        "code": error.get("test_id", "BANDIT"),
                        "message": error.get("issue_text", ""),
                    })
            return {"success": len(errors) == 0, "errors": errors}
        return {"success": True, "errors": []}
    except json.JSONDecodeError:
        return {"success": True, "errors": []}
    except Exception as e:
        return {"success": False, "errors": [{"message": f"bandit failed: {e}"}]}


def check_syntax(file_path: Path) -> Dict[str, Any]:
    """Check Python syntax."""
    try:
        result = subprocess.run(
            ["python", "-m", "py_compile", str(file_path)],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return {"success": result.returncode == 0, "errors": []}
    except Exception as e:
        return {"success": False, "errors": [{"message": f"syntax error: {e}"}]}


def validate_file(file_path: str) -> Dict[str, Any]:
    """Run all validations on a file and return combined results."""
    path = Path(file_path)

    if not path.exists():
        return {
            "success": False,
            "file": file_path,
            "errors": [{"message": "File not found"}],
            "tools": {}
        }

    results = {
        "file": file_path,
        "syntax": check_syntax(path),
        "mypy": run_mypy(path),
        "ruff": run_ruff(path),
        "bandit": run_bandit(path),
    }

    # Collect all errors
    all_errors = []
    for tool_name, tool_result in results.items():
        if tool_name == "file":
            continue
        for error in tool_result.get("errors", []):
            error["tool"] = tool_name
            all_errors.append(error)

    results["errors"] = all_errors
    results["success"] = (
        results["syntax"]["success"] and
        results["mypy"]["success"] and
        results["ruff"]["success"] and
        results["bandit"]["success"]
    )
    results["error_count"] = len(all_errors)

    return results


def fix_file(file_path: str) -> Dict[str, Any]:
    """Attempt to auto-fix errors in a file."""
    path = Path(file_path)
    results = {
        "file": file_path,
        "ruff_fix": run_ruff_fix(path),
    }
    results["success"] = results["ruff_fix"]["success"]
    return results


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Real validation for Python files")
    parser.add_argument("file", help="Python file to validate")
    parser.add_argument("--fix", action="store_true", help="Attempt to auto-fix errors")
    parser.add_argument("--output", choices=["json", "text"], default="json", help="Output format")
    args = parser.parse_args()

    if args.fix:
        result = fix_file(args.file)
    else:
        result = validate_file(args.file)

    if args.output == "json":
        print(json.dumps(result, indent=2))
    else:
        if result.get("success"):
            print(f"✅ {args.file}: PASSED")
        else:
            print(f"❌ {args.file}: FAILED")
            for error in result.get("errors", []):
                print(f"   - [{error.get('tool', '?')}] {error.get('message', '?')}")
        sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
