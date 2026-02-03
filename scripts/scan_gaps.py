#!/usr/bin/env python3
"""
GAP Audit Scanner - Scans current code and reports actual GAP violations.
Does NOT rely on requirements files - analyzes code directly.
"""

import ast
import json
import re
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set


@dataclass
class GapViolation:
    """A single GAP violation found in code."""
    rule_id: str
    description: str
    priority: str
    line_number: Optional[int] = None
    code_snippet: Optional[str] = None


@dataclass
class QACommands:
    """QA commands for validating a file."""
    syntax_check: str
    type_check: str
    lint_check: str
    format_check: str
    test_check: str


@dataclass
class FileWithGaps:
    """A Python file with GAP violations."""
    python_file: str
    layer: str
    priority: str
    gaps: List[GapViolation]
    qa_commands: QACommands

    def to_dict(self):
        return {
            "python_file": self.python_file,
            "layer": self.layer,
            "priority": self.priority,
            "gap_count": len(self.gaps),
            "needs_fix": len(self.gaps) > 0,
            "qa_commands": asdict(self.qa_commands),
        }


class CodeGapAnalyzer:
    """Analyzes Python code to find GAP violations."""

    # Priority rules
    PRIORITY_RULES = {
        # P0 - Critical
        "TRD-001": "P0", "TRD-005": "P0", "SEC-001": "P0", "SEC-002": "P0", "SEC-003": "P0", "CC-006": "P0",
        # P1 - High
        "LOG-004": "P1", "LOG-001": "P1", "TRD-004": "P1", "TRD-007": "P1", "SEC-007": "P1",
        # P2 - Medium
        "TYP-001": "P2", "TYP-003": "P2", "ARCH-004": "P2", "ARCH-006": "P2",
        # P3 - Low
        "FMT-001": "P3", "PERF-001": "P3",
    }

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.app_dir = repo_root / "app"

    def get_priority(self, rule_id: str) -> str:
        """Get priority for a rule ID."""
        return self.PRIORITY_RULES.get(rule_id, "P3")

    def get_layer(self, python_path: str) -> str:
        """Get layer from Python file path."""
        layer_map = {
            "market_microstructure": "L1_Microstructure",
            "ensemble": "L2_Ensemble",
            "backtesting/core": "L3_Backtesting_Core",
            "backtesting/labeling": "L4_Backtesting_Labeling",
            "backtesting/validation": "L5_Backtesting_Validation",
            "domain/services": "L6_Domain_Services",
            "domain/strategies": "L6_Domain_Services",
            "domain/entities": "L7_Domain_Entities",
            "domain/value_objects": "L7_Domain_Entities",
            "application": "L8_Application",
            "core": "L9_Core",
            "database": "L10_Data",
            "repositories": "L10_Data",
            "analysis": "L11_Analysis",
            "api": "L12_API",
            "middleware": "L13_Middleware",
        }
        for path_part, layer in layer_map.items():
            if path_part in python_path:
                return layer
        return "L0_Other"

    def get_test_path(self, python_path: str) -> str:
        """Get test file path for a Python file."""
        # Convert app/path/file.py to tests/path/test_file.py
        test_path = python_path.replace("app/", "tests/")
        test_path = test_path.replace(".py", "_test.py")
        # Ensure test_ prefix
        filename = Path(test_path).name
        if not filename.startswith("test_"):
            dirname = str(Path(test_path).parent)
            test_path = str(Path(dirname) / f"test_{filename}")
        return test_path

    def analyze_file(self, python_file: Path) -> List[GapViolation]:
        """Analyze a Python file for GAP violations."""
        gaps = []

        try:
            content = python_file.read_text()
            lines = content.split('\n')

            # Check LOG-001: f-strings in logging
            for i, line in enumerate(lines, 1):
                if re.search(r'logger\.(debug|info|warning|error|critical)\(f["\']', line):
                    gaps.append(GapViolation(
                        rule_id="LOG-001",
                        description="f-string in logging call",
                        priority=self.get_priority("LOG-001"),
                        line_number=i,
                        code_snippet=line.strip()
                    ))

            # Check LOG-004: exception logging without exc_info
            for i in range(len(lines)):
                line = lines[i]
                if re.search(r'\bexcept\b', line) and ':' in line:
                    # Look ahead for logger calls
                    for j in range(i + 1, min(i + 5, len(lines))):
                        next_line = lines[j]
                        if 'logger.' in next_line and ('error' in next_line or 'exception' in next_line):
                            if 'exc_info=True' not in next_line and 'exc_info = True' not in next_line:
                                gaps.append(GapViolation(
                                    rule_id="LOG-004",
                                    description="Exception logging without exc_info=True",
                                    priority=self.get_priority("LOG-004"),
                                    line_number=j + 1,
                                    code_snippet=next_line.strip()
                                ))
                                break
                        if next_line.strip() and not next_line.startswith('#'):
                            break

            # Check CC-006: generic Exception catching
            if re.search(r'\bexcept\s*Exception\b', content):
                # Find the line
                for i, line in enumerate(lines, 1):
                    if re.search(r'\bexcept\s*Exception\b', line):
                        gaps.append(GapViolation(
                            rule_id="CC-006",
                            description="Generic Exception catching instead of specific exception",
                            priority=self.get_priority("CC-006"),
                            line_number=i,
                            code_snippet=line.strip()
                        ))
                        break

            # Check TYP-001: missing return types
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.FunctionDef):
                        if node.returns is None and not node.name.startswith('_'):
                            gaps.append(GapViolation(
                                rule_id="TYP-001",
                                description=f"Missing return type annotation for function '{node.name}'",
                                priority=self.get_priority("TYP-001"),
                                line_number=node.lineno,
                                code_snippet=f"def {node.name}(...)"
                            ))
            except SyntaxError:
                pass  # Skip files with syntax errors

            # Check TYP-003: using Any without justification
            if re.search(r':\s*Any\b', content) or re.search(r'->\s*Any\b', content):
                for i, line in enumerate(lines, 1):
                    if (re.search(r':\s*Any\b', line) or re.search(r'->\s*Any\b', line)):
                        # Check if there's a justification comment
                        if 'justif' not in line.lower() and 'becaus' not in line.lower():
                            gaps.append(GapViolation(
                                rule_id="TYP-003",
                                description="Using Any type without justification",
                                priority=self.get_priority("TYP-003"),
                                line_number=i,
                                code_snippet=line.strip()
                            ))

        except Exception:
            pass

        return gaps

    def get_qa_commands(self, python_path: str) -> QACommands:
        """Get QA commands for a file."""
        test_path = self.get_test_path(python_path)

        return QACommands(
            syntax_check=f"python -m py_compile {python_path}",
            type_check=f"mypy --strict {python_path}",
            lint_check=f"ruff check {python_path}",
            format_check=f"black --check {python_path}",
            test_check=f"pytest {test_path} -v"
        )

    def scan_app_directory(self) -> List[FileWithGaps]:
        """Scan all Python files in app directory for GAP violations."""
        files_with_gaps = []

        for py_file in self.app_dir.rglob("*.py"):
            if "__pycache__" in str(py_file) or py_file.name.startswith("_"):
                continue

            python_path = str(py_file.relative_to(self.repo_root))
            gaps = self.analyze_file(py_file)

            if gaps:
                # Get highest priority
                highest_priority = "P3"
                for gap in gaps:
                    if gap.priority == "P0":
                        highest_priority = "P0"
                        break
                    elif gap.priority == "P1" and highest_priority != "P0":
                        highest_priority = "P1"
                    elif gap.priority == "P2" and highest_priority not in ["P0", "P1"]:
                        highest_priority = "P2"

                layer = self.get_layer(python_path)
                qa_commands = self.get_qa_commands(python_path)

                files_with_gaps.append(FileWithGaps(
                    python_file=python_path,
                    layer=layer,
                    priority=highest_priority,
                    gaps=gaps,
                    qa_commands=qa_commands
                ))

        return files_with_gaps


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="GAP Audit Scanner - Analyzes current code")
    parser.add_argument("--format", choices=["json", "text", "count"], default="text",
                       help="Output format")
    parser.add_argument("--priority", choices=["P0", "P1", "P2", "P3"],
                       help="Filter by priority")
    parser.add_argument("--layer", help="Filter by layer")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--with-qa", action="store_true",
                       help="Include QA commands in output")

    args = parser.parse_args()

    repo_root = Path.cwd()
    analyzer = CodeGapAnalyzer(repo_root)

    # Scan all files
    all_files = analyzer.scan_app_directory()

    # Filter by priority/layer if requested
    if args.priority:
        files = [f for f in all_files if f.priority == args.priority]
    elif args.layer:
        files = [f for f in all_files if f.layer == args.layer]
    else:
        files = all_files

    # Sort by priority
    priority_order = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}
    files.sort(key=lambda f: priority_order.get(f.priority, 4))

    if args.format == "json":
        output = json.dumps([f.to_dict() for f in files], indent=2)
    elif args.format == "count":
        counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for f in all_files:
            counts[f.priority] += 1
        output = json.dumps(counts)
    else:  # text
        lines = []

        if args.with_qa:
            lines.append("# GAP Audit Results - Code Analysis with QA Commands\n")
            lines.append("For each file with GAPs, run these QA commands after fixing:\n")
        else:
            lines.append("# GAP Audit Results - Code Analysis\n")

        lines.append(f"Files with GAPs: {len(files)}\n")

        for f in files:
            lines.append(f"\n## {f.python_file}")
            lines.append(f"Layer: {f.layer} | Priority: {f.priority} | GAPs: {len(f.gaps)}\n")

            if args.with_qa:
                lines.append("### QA Commands (run after fixing)\n")
                lines.append("```bash")
                qa = f.qa_commands
                lines.append(f"# 1. Syntax check")
                lines.append(qa.syntax_check)
                lines.append(f"\n# 2. Type check (if mypy available)")
                lines.append(qa.type_check)
                lines.append(f"\n# 3. Lint (if ruff available)")
                lines.append(qa.lint_check)
                lines.append(f"\n# 4. Format check (if black available)")
                lines.append(qa.format_check)
                lines.append(f"\n# 5. Tests (if test file exists)")
                lines.append(qa.test_check)
                lines.append("```")
                lines.append("")

            lines.append("### GAP Violations:\n")
            for gap in f.gaps:
                line_info = f":{gap.line_number}" if gap.line_number else ""
                lines.append(f"- **{gap.rule_id}**{line_info}: {gap.description}")
                if gap.code_snippet:
                    lines.append(f"  ```python")
                    lines.append(f"  {gap.code_snippet[:80]}")
                    lines.append(f"  ```")
                lines.append("")

        output = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Output written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
