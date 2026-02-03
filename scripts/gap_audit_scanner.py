#!/usr/bin/env python3
"""
Deterministic GAP audit tool.
Scans requirements files and verifies GAP violations against CURRENT code.
Only reports GAPs that actually exist in the current codebase.
"""

import ast
import json
import re
import subprocess
import sys
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Set


@dataclass
class GapViolation:
    """A single GAP violation."""
    rule_id: str
    description: str
    priority: str
    line_number: Optional[int] = None
    verified: bool = False  # Whether we verified it still exists


@dataclass
class FileWithGaps:
    """A Python file with GAP violations."""
    python_file: str
    requirements_file: str
    layer: str
    priority: str
    all_gaps: List[GapViolation]  # All gaps from requirements
    verified_gaps: List[GapViolation]  # Gaps that still exist in current code
    fixed_gaps: List[GapViolation]  # Gaps that were already fixed

    def to_dict(self):
        return {
            "python_file": self.python_file,
            "requirements_file": self.requirements_file,
            "layer": self.layer,
            "priority": self.priority,
            "all_gaps": len(self.all_gaps),
            "verified_gaps": len(self.verified_gaps),
            "fixed_gaps": len(self.fixed_gaps),
            "needs_fix": len(self.verified_gaps) > 0,
        }


class CodeAnalyzer:
    """Analyzes Python code to verify GAP violations."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root

    def verify_log_001(self, python_file: Path, line_number: Optional[int]) -> bool:
        """Verify LOG-001: Structured logging (f-strings in logging)."""
        try:
            content = python_file.read_text()
            lines = content.split('\n')

            # Check for f-strings in logger calls
            f_string_pattern = r'logger\.(debug|info|warning|error|critical)\(f["\']'

            for i, line in enumerate(lines, 1):
                if re.search(f_string_pattern, line):
                    return True  # GAP still exists

            return False  # No f-strings in logging, GAP fixed

        except Exception:
            return False

    def verify_log_004(self, python_file: Path) -> bool:
        """Verify LOG-004: Exception logging with stack traces (exc_info=True)."""
        try:
            content = python_file.read_text()

            # Look for except blocks without exc_info=True
            # Pattern: except ... as e: followed by logger.error WITHOUT exc_info=True
            lines = content.split('\n')
            i = 0
            while i < len(lines):
                line = lines[i]

                # Find except clause
                if re.search(r'\bexcept\b', line) and ':' in line:
                    # Look ahead for logger calls
                    j = i + 1
                    while j < len(lines) and not lines[j].strip() and not lines[j].startswith('except'):
                        if 'logger.' in lines[j] and ('error' in lines[j] or 'exception' in lines[j]):
                            # Check if exc_info=True is present
                            if 'exc_info=True' not in lines[j] and 'exc_info = True' not in lines[j]:
                                return True  # GAP still exists
                        if lines[j].strip() and not lines[j].startswith('#'):
                            if lines[j].startswith('except'):
                                continue
                            break
                        j += 1

                i += 1

            return False

        except Exception:
            return False

    def verify_cc_006(self, python_file: Path) -> bool:
        """Verify CC-006: Explicit error handling (generic Exception)."""
        try:
            content = python_file.read_text()

            # Look for "except Exception" or bare except
            if re.search(r'\bexcept\s*Exception\b', content):
                return True  # GAP still exists
            if re.search(r'\bexcept\s*:\s*$', content, re.MULTILINE):
                return True  # Bare except

            return False

        except Exception:
            return False

    def verify_typ_001(self, python_file: Path) -> bool:
        """Verify TYP-001: Missing return type annotations."""
        try:
            content = python_file.read_text()
            tree = ast.parse(content)

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    # Check if return type is missing
                    if node.returns is None:
                        return True  # GAP still exists

            return False

        except Exception:
            return False

    def verify_typ_003(self, python_file: Path) -> bool:
        """Verify TYP-003: Using Any without justification."""
        try:
            content = python_file.read_text()

            # Look for "Any" in type hints
            # If Any is used, check if there's a justification comment
            if ': Any' in content or '-> Any' in content:
                return True  # Potentially a GAP

            return False

        except Exception:
            return False

    def verify_trd_005(self, python_file: Path) -> bool:
        """Verify TRD-005: Price validation missing."""
        try:
            content = python_file.read_text()

            # Look for price-related functions without validation
            # This is a simplified check - real implementation would need AST
            price_functions = re.findall(r'def\s+\w*price\w*\s*\(', content, re.IGNORECASE)

            if price_functions:
                # Check if validation exists
                if 'ValueError' not in content and 'raise' not in content:
                    return True  # Likely missing validation

            return False

        except Exception:
            return False

    def verify_gap(self, python_file: Path, rule_id: str, description: str) -> bool:
        """Verify if a GAP violation still exists in the code."""
        verifiers = {
            "LOG-001": self.verify_log_001,
            "LOG-004": self.verify_log_004,
            "CC-006": self.verify_cc_006,
            "TYP-001": self.verify_typ_001,
            "TYP-003": self.verify_typ_003,
            "TRD-005": self.verify_trd_005,
        }

        verifier = verifiers.get(rule_id)
        if verifier:
            try:
                return verifier(python_file)
            except Exception:
                # If verification fails, assume GAP still exists
                return True

        # For rules we can't auto-verify, assume they exist
        return True


class GapAuditScanner:
    """Scans for GAP violations and verifies against current code."""

    # Priority rules
    PRIORITY_RULES = {
        # P0 - Critical
        "TRD-001": "P0", "TRD-005": "P0", "SEC-001": "P0", "SEC-002": "P0", "SEC-003": "P0", "CC-006": "P0",
        # P1 - High
        "LOG-004": "P1", "LOG-001": "P1", "TRD-004": "P1", "TRD-007": "P1", "SEC-007": "P1",
        # P2 - Medium
        "TYP-001": "P2", "TYP-003": "P2", "ARCH-004": "P2", "ARCH-006": "P2", "CC-001": "P2", "CC-002": "P2",
        # P3 - Low (default)
    }

    # Layer mappings
    LAYER_MAP = {
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

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.requirements_dir = repo_root / ".requirements"
        self.code_analyzer = CodeAnalyzer(repo_root)

    def get_priority(self, rule_id: str) -> str:
        """Get priority for a rule ID."""
        return self.PRIORITY_RULES.get(rule_id, "P3")

    def get_layer(self, python_path: str) -> str:
        """Get layer from Python file path."""
        for path_part, layer in self.LAYER_MAP.items():
            if path_part in python_path:
                return layer
        return "L0_Other"

    def parse_requirements_file(self, req_file: Path) -> List[Dict]:
        """Parse GAP violations from a requirements file."""
        gaps = []
        content = req_file.read_text()

        # Find the Critical Rules table
        in_table = False
        for line in content.split('\n'):
            if 'Critical Rules' in line:
                in_table = True
                continue

            if in_table:
                if line.startswith('|'):
                    parts = [p.strip() for p in line.split('|')]
                    # Table format: | Rule | Source | Requirement | Current Status |
                    # After split: ['', 'Rule', 'Source', 'Requirement', 'Current Status', '']
                    # So we need parts[1] for rule_id and parts[4] for status
                    if len(parts) >= 5:
                        rule_id = parts[1] if len(parts) > 1 else ""
                        status = parts[4] if len(parts) > 4 else ""

                        if 'GAP' in status and rule_id and '-' in rule_id:
                            # Extract description
                            description = status
                            if 'GAP -' in description:
                                description = description.split('GAP -', 1)[1].strip()
                            elif 'GAP' in description:
                                description = description.split('GAP', 1)[1].strip()
                                description = description.lstrip('-').strip()

                            # Extract line number if present
                            line_number = None
                            line_match = re.search(r'line\s*(\d+)', description, re.IGNORECASE)
                            if line_match:
                                line_number = int(line_match.group(1))

                            gaps.append({
                                'rule_id': rule_id,
                                'description': description,
                                'line_number': line_number,
                                'status': status
                            })
                elif line.strip() and not line.startswith('|') and '---' not in line:
                    break

        return gaps

    def scan(self) -> List[FileWithGaps]:
        """Scan for GAP violations and verify against current code."""
        files_with_gaps = []

        # Find all requirements files
        req_files = list(self.requirements_dir.rglob("*.requirements.md"))

        for req_file in req_files:
            # Get Python file path
            python_path = str(req_file.relative_to(self.repo_root))
            python_path = python_path.replace(".requirements/", "")
            python_path = python_path.replace(".requirements.md", ".py")

            python_file = self.repo_root / python_path
            if not python_file.exists():
                continue

            # Parse GAP violations from requirements
            all_gaps_data = self.parse_requirements_file(req_file)
            if not all_gaps_data:
                continue

            # Convert to GapViolation objects
            all_gaps = []
            verified_gaps = []
            fixed_gaps = []

            for gap_data in all_gaps_data:
                rule_id = gap_data['rule_id']
                description = gap_data['description']
                line_number = gap_data.get('line_number')
                priority = self.get_priority(rule_id)

                gap = GapViolation(
                    rule_id=rule_id,
                    description=description,
                    priority=priority,
                    line_number=line_number
                )

                # Verify if GAP still exists in current code
                still_exists = self.code_analyzer.verify_gap(python_file, rule_id, description)
                gap.verified = True

                all_gaps.append(gap)

                if still_exists:
                    verified_gaps.append(gap)
                else:
                    fixed_gaps.append(gap)

            # Only include file if there are verified gaps
            if verified_gaps:
                # Get highest priority
                highest_priority = "P3"
                for gap in all_gaps:
                    if gap.priority == "P0":
                        highest_priority = "P0"
                        break
                    elif gap.priority == "P1" and highest_priority != "P0":
                        highest_priority = "P1"
                    elif gap.priority == "P2" and highest_priority not in ["P0", "P1"]:
                        highest_priority = "P2"

                layer = self.get_layer(python_path)

                files_with_gaps.append(FileWithGaps(
                    python_file=python_path,
                    requirements_file=str(req_file.relative_to(self.repo_root)),
                    layer=layer,
                    priority=highest_priority,
                    all_gaps=all_gaps,
                    verified_gaps=verified_gaps,
                    fixed_gaps=fixed_gaps
                ))

        return files_with_gaps

    def get_files_by_priority(self, priority: str) -> List[FileWithGaps]:
        """Get files filtered by priority."""
        all_files = self.scan()
        return [f for f in all_files if f.priority == priority]

    def get_files_by_layer(self, layer: str) -> List[FileWithGaps]:
        """Get files filtered by layer."""
        all_files = self.scan()
        return [f for f in all_files if f.layer == layer]


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="GAP Audit Scanner - Verifies GAPs against current code")
    parser.add_argument("--format", choices=["json", "text", "count"], default="text",
                       help="Output format")
    parser.add_argument("--priority", choices=["P0", "P1", "P2", "P3"],
                       help="Filter by priority")
    parser.add_argument("--layer", help="Filter by layer")
    parser.add_argument("--output", "-o", help="Output file")
    parser.add_argument("--verbose", "-v", action="store_true",
                       help="Show detailed information including fixed gaps")

    args = parser.parse_args()

    repo_root = Path.cwd()
    scanner = GapAuditScanner(repo_root)

    if args.priority:
        files = scanner.get_files_by_priority(args.priority)
    elif args.layer:
        files = scanner.get_files_by_layer(args.layer)
    else:
        files = scanner.scan()

    if args.format == "json":
        output = json.dumps([f.to_dict() for f in files], indent=2)
    elif args.format == "count":
        counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}
        for f in files:
            counts[f.priority] += 1
        output = json.dumps(counts)
    else:  # text
        lines = []
        total_verified = 0
        total_fixed = 0

        for f in files:
            total_verified += len(f.verified_gaps)
            total_fixed += len(f.fixed_gaps)

            if args.verbose:
                lines.append(f"{f.python_file} | {f.priority} | {len(f.verified_gaps)} active | {len(f.fixed_gaps)} fixed")
            else:
                lines.append(f"{f.python_file} | {f.priority} | {len(f.verified_gaps)} GAPs")

            for gap in f.verified_gaps:
                line_info = f" (line {gap.line_number})" if gap.line_number else ""
                lines.append(f"  ✓ {gap.rule_id}: {gap.description}{line_info}")

            if args.verbose and f.fixed_gaps:
                lines.append(f"  Fixed ({len(f.fixed_gaps)}):")
                for gap in f.fixed_gaps:
                    lines.append(f"    ✗ {gap.rule_id}: {gap.description}")

        # Add summary
        lines.insert(0, f"# GAP Audit Results - Verified Against Current Code")
        lines.insert(1, f"Files with active GAPs: {len(files)}")
        lines.insert(2, f"Total active GAPs: {total_verified}")
        if args.verbose:
            lines.insert(3, f"Total fixed GAPs (since requirements created): {total_fixed}")
        lines.insert(len(lines), "")
        lines.append("Legend: ✓ = Active GAP | ✗ = Already Fixed")

        output = "\n".join(lines)

    if args.output:
        Path(args.output).write_text(output)
        print(f"Output written to {args.output}")
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())
