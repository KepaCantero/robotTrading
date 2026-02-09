#!/usr/bin/env python3
"""
Handle Blocked Files in GAP Audit

Analyzes blocked files, determines blocking reason, and suggests resolution.
"""
import ast
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set


class BlockReason(Enum):
    """Reason why a file is blocked."""
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    CIRCULAR_DEPENDENCY = "circular_dependency"
    MISSING_REQUIREMENTS = "missing_requirements"
    COMPLEXITY_TOO_HIGH = "complexity_too_high"
    TYPE_ERROR = "type_error"
    SECURITY_ISSUE = "security_issue"
    TEST_FAILURE = "test_failure"
    OTHER = "other"


@dataclass
class BlockedFile:
    """A blocked file with analysis."""
    path: str
    reason: BlockReason
    details: str
    can_auto_fix: bool
    suggestions: List[str] = field(default_factory=list)
    depends_on: List[str] = field(default_factory=list)
    blocking: List[str] = field(default_factory=list)


class BlockedFileAnalyzer:
    """Analyze and handle blocked files."""

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.blocked_file = self.project_root / ".ralph" / "blocked_files.json"
        self.checkpoint_file = self.project_root / ".ralph" / "checkpoint_progress.json"

    def load_blocked_files(self) -> Dict[str, dict]:
        """Load blocked files registry."""
        if self.blocked_file.exists():
            with open(self.blocked_file, "r") as f:
                return json.load(f)
        return {}

    def save_blocked_files(self, data: dict):
        """Save blocked files registry."""
        self.blocked_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.blocked_file, "w") as f:
            json.dump(data, f, indent=2)

    def analyze_file(self, file_path: str) -> BlockedFile:
        """Analyze a blocked file to determine the issue."""
        full_path = self.project_root / file_path

        # 1. Check syntax
        try:
            with open(full_path, "r") as f:
                ast.parse(f.read())
        except SyntaxError as e:
            return BlockedFile(
                path=file_path,
                reason=BlockReason.SYNTAX_ERROR,
                details=f"Line {e.lineno}: {e.msg}",
                can_auto_fix=False,
                suggestions=[
                    "Fix the syntax error manually",
                    f"Check line {e.lineno} near '{e.text.strip() if e.text else ''}'",
                ],
            )

        # 2. Check imports
        try:
            result = subprocess.run(
                ["python", "-c", f"import ast; ast.parse(open('{full_path}').read())"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode != 0 and "ImportError" in result.stderr:
                module = result.stderr.split("'")[1] if "'" in result.stderr else "unknown"
                return BlockedFile(
                    path=file_path,
                    reason=BlockReason.IMPORT_ERROR,
                    details=f"Missing import: {module}",
                    can_auto_fix=True,
                    suggestions=[
                        f"Install missing module: pip install {module}",
                        "Or remove the import if not needed",
                    ],
                )
        except Exception:
            pass

        # 3. Check type errors with mypy
        try:
            result = subprocess.run(
                ["mypy", "--ignore-missing-imports", str(full_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                error_count = result.stderr.count("error:")
                if error_count > 10:  # Threshold for "too many errors"
                    return BlockedFile(
                        path=file_path,
                        reason=BlockReason.TYPE_ERROR,
                        details=f"{error_count} type errors found",
                        can_auto_fix=False,
                        suggestions=[
                            "Fix type annotations step by step",
                            "Run 'mypy file.py' to see all errors",
                        ],
                    )
        except Exception:
            pass

        # 4. Check security issues with bandit
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", str(full_path)],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode != 0:
                try:
                    bandit_data = json.loads(result.stdout)
                    high_severity = sum(1 for r in bandit_data.get("results", []) if r.get("issue_severity") == "HIGH")
                    if high_severity > 0:
                        return BlockedFile(
                            path=file_path,
                            reason=BlockReason.SECURITY_ISSUE,
                            details=f"{high_severity} high-severity security issues",
                            can_auto_fix=False,
                            suggestions=[
                                "Review security issues manually",
                                "Run 'bandit -r file.py' for details",
                            ],
                        )
                except json.JSONDecodeError:
                    pass
        except Exception:
            pass

        # 5. Check complexity
        try:
            result = subprocess.run(
                ["radon", "cc", str(full_path), "-a", "-s"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.stdout:
                # Parse average complexity
                lines = result.stdout.strip().split("\n")
                complexities = []
                for line in lines:
                    if "(" in line:
                        try:
                            comp_str = line.split("(")[-1].split(")")[0]
                            complexities.append(float(comp_str))
                        except (ValueError, IndexError):
                            pass

                if complexities and max(complexities) > 20:
                    return BlockedFile(
                        path=file_path,
                        reason=BlockReason.COMPLEXITY_TOO_HIGH,
                        details=f"Max complexity: {max(complexities):.1f}",
                        can_auto_fix=False,
                        suggestions=[
                            "Refactor complex functions into smaller ones",
                            "Consider using design patterns",
                        ],
                    )
        except Exception:
            pass

        # Default: unknown reason
        return BlockedFile(
            path=file_path,
            reason=BlockReason.OTHER,
            details="Unable to determine specific issue",
            can_auto_fix=False,
            suggestions=["Review file manually"],
        )

    def find_circular_dependencies(self) -> List[List[str]]:
        """Find circular dependencies in the codebase."""
        # Build import graph
        graph: Dict[str, Set[str]] = {}
        app_dir = self.project_root / "app"

        for py_file in app_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or py_file.name.startswith("__"):
                continue

            rel_path = str(py_file.relative_to(self.project_root))
            imports = set()

            try:
                with open(py_file, "r") as f:
                    tree = ast.parse(f.read())

                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            imports.add(alias.name.split(".")[0])
                    elif isinstance(node, ast.ImportFrom):
                        if node.module:
                            imports.add(node.module.split(".")[0])
            except Exception:
                continue

            # Filter to app imports only
            app_imports = {i for i in imports if i.startswith("app.") or i == "app"}
            graph[rel_path] = app_imports

        # Find cycles
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: List[str]):
            if node in rec_stack:
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                dfs(neighbor, path + [node])

            rec_stack.remove(node)

        for node in graph:
            if node not in visited:
                dfs(node, [])

        return cycles

    def handle_blocked_file(self, file_path: str, max_retries: int = 3) -> dict:
        """Handle a blocked file with retry logic."""
        blocked_data = self.load_blocked_files()

        if file_path not in blocked_data:
            blocked_data[file_path] = {
                "path": file_path,
                "attempts": 0,
                "first_blocked": datetime.utcnow().isoformat() + "Z",
                "last_attempt": None,
                "reason": None,
                "details": None,
                "can_auto_fix": False,
                "resolved": False,
            }

        entry = blocked_data[file_path]

        if entry["attempts"] >= max_retries:
            return {
                "status": "max_retries_exceeded",
                "message": f"File {file_path} has exceeded max retry attempts ({max_retries})",
                "entry": entry,
            }

        # Analyze the file
        analysis = self.analyze_file(file_path)

        entry["attempts"] += 1
        entry["last_attempt"] = datetime.utcnow().isoformat() + "Z"
        entry["reason"] = analysis.reason.value
        entry["details"] = analysis.details
        entry["can_auto_fix"] = analysis.can_auto_fix
        entry["suggestions"] = analysis.suggestions

        # Try auto-fix if possible
        if analysis.can_auto_fix:
            success = self._attempt_auto_fix(analysis)
            if success:
                entry["resolved"] = True
                self.save_blocked_files(blocked_data)
                return {
                    "status": "resolved",
                    "message": f"File {file_path} was auto-fixed",
                    "entry": entry,
                }

        self.save_blocked_files(blocked_data)

        return {
            "status": "blocked",
            "message": f"File {file_path} is blocked",
            "analysis": analysis,
            "entry": entry,
        }

    def _attempt_auto_fix(self, analysis: BlockedFile) -> bool:
        """Attempt to automatically fix a blocked file."""
        if analysis.reason == BlockReason.IMPORT_ERROR:
            # Try to install missing module
            module = analysis.details.split(": ")[-1]
            try:
                subprocess.run(
                    ["pip", "install", module],
                    capture_output=True,
                    timeout=60,
                )
                return True
            except Exception:
                return False

        return False

    def generate_report(self) -> dict:
        """Generate a comprehensive report of blocked files."""
        blocked_data = self.load_blocked_files()

        total = len(blocked_data)
        resolved = sum(1 for e in blocked_data.values() if e.get("resolved", False))
        by_reason = {}

        for entry in blocked_data.values():
            reason = entry.get("reason", "unknown")
            by_reason[reason] = by_reason.get(reason, 0) + 1

        # Find circular dependencies
        cycles = self.find_circular_dependencies()

        return {
            "summary": {
                "total_blocked": total,
                "resolved": resolved,
                "still_blocked": total - resolved,
                "by_reason": by_reason,
            },
            "circular_dependencies": len(cycles),
            "cycles": cycles[:5],  # First 5 cycles
            "blocked_files": list(blocked_data.values()),
        }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Handle blocked files in GAP audit")
    parser.add_argument("command", choices=["analyze", "report", "fix", "check-deps"])
    parser.add_argument("--file", help="File path to analyze")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retry attempts")

    args = parser.parse_args()

    analyzer = BlockedFileAnalyzer()

    if args.command == "analyze":
        if not args.file:
            print("Error: --file required for analyze command")
            return 1

        result = analyzer.handle_blocked_file(args.file, args.max_retries)
        print(json.dumps(result, indent=2))

    elif args.command == "report":
        report = analyzer.generate_report()
        print(json.dumps(report, indent=2))

    elif args.command == "check-deps":
        cycles = analyzer.find_circular_dependencies()
        print(f"Found {len(cycles)} circular dependencies:")
        for i, cycle in enumerate(cycles, 1):
            print(f"\n{i}. {' -> '.join(cycle)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
