#!/usr/bin/env python3
"""
Deterministic GAP Audit Script
Scans .requirements/ for GAP violations and processes them systematically.
"""

import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional


@dataclass
class GapViolation:
    """Represents a single GAP violation."""
    rule_id: str
    description: str
    current_status: str
    line_number: Optional[int] = None


@dataclass
class FileWithGaps:
    """Represents a Python file with GAP violations."""
    python_file: str
    requirements_file: str
    layer: str
    gaps: List[GapViolation] = field(default_factory=list)
    priority: str = "P3"  # P0, P1, P2, P3


class GapAuditor:
    """Deterministic GAP violation auditor."""

    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.requirements_dir = repo_root / ".requirements"
        self.app_dir = repo_root / "app"
        self.tasks_dir = repo_root / ".tasks"
        self.templates_dir = self.tasks_dir / "templates"

        # Priority rules (P0 = Critical, P3 = Low)
        self.priority_rules = {
            # P0 - Critical: Security, crashes, data loss
            "TRD-001": "P0",  # Trading system validation
            "TRD-005": "P0",  # Price validation
            "SEC-001": "P0",  # Security issues
            "SEC-002": "P0",  # Security issues
            "SEC-003": "P0",  # Security issues
            "CC-006": "P0",   # Explicit error handling (crashes)

            # P1 - High: Production standards
            "LOG-004": "P1",  # Error logging with stack traces
            "LOG-001": "P1",  # Structured logging
            "TRD-004": "P1",  # Audit trail logging
            "TRD-007": "P1",  # Trading days constant
            "SEC-007": "P1",  # Input validation

            # P2 - Medium: Code quality
            "TYP-001": "P2",  # Type coverage
            "TYP-003": "P2",  # No Any without justification
            "ARCH-004": "P2", # Small functions
            "ARCH-006": "P2", # Value objects immutable
            "CC-001": "P2",   # Cyclomatic complexity
            "CC-002": "P2",   # Code duplication

            # P3 - Low: Nice to have
            "FMT-001": "P3",  # Formatting
            "PERF-001": "P3", # Performance
            "ASYNC-001": "P3",# Async
            "TST-004": "P3",  # Testing mocks
            "TST-005": "P3",  # Test coverage
            "QL-007": "P3",   # Parameters count
            "PERF-005": "P3", # Numba
        }

    def find_all_gap_violations(self) -> Dict[str, FileWithGaps]:
        """Scan all requirements files for GAP violations."""
        files_with_gaps = {}

        # Find all .requirements.md files
        for req_file in self.requirements_dir.rglob("*.requirements.md"):
            # Parse GAP violations from requirements file
            gaps = self._parse_gaps_from_file(req_file)

            if gaps:
                # Extract corresponding Python file path
                python_path = self._get_python_path_from_requirements(req_file)

                if not python_path:
                    continue

                # Check if Python file exists
                py_file = self.repo_root / python_path
                if not py_file.exists():
                    print(f"Warning: Python file not found: {python_path}")
                    continue

                layer = self._get_layer(python_path)
                priority = self._get_overall_priority(gaps)

                files_with_gaps[python_path] = FileWithGaps(
                    python_file=python_path,
                    requirements_file=str(req_file.relative_to(self.repo_root)),
                    layer=layer,
                    gaps=gaps,
                    priority=priority
                )

        return files_with_gaps

    def _parse_gaps_from_file(self, req_file: Path) -> List[GapViolation]:
        """Parse GAP violations from a requirements file."""
        gaps = []
        content = req_file.read_text()

        # Pattern: | RULE-ID | SOURCE | REQUIREMENT | STATUS |
        # STATUS contains: ❌ GAP - Description
        # Note: The ❌ is U+274C (Cross Mark) - using a more flexible pattern
        patterns = [
            # Match: | RULE-ID | ... | ... | [status with GAP] |
            # The status column contains "GAP" which is what we're looking for
            r'\|([A-Z]+-\d+)\s*\|[^|]*\|[^|]*\|([^|]*GAP[^|]*)\|',
        ]

        for pattern in patterns:
            for match in re.finditer(pattern, content):
                rule_id = match.group(1).strip()
                description = match.group(2).strip()

                # Extract line number if present in description
                line_match = re.search(r'line\s*(\d+)', description, re.IGNORECASE)
                line_number = int(line_match.group(1)) if line_match else None

                gaps.append(GapViolation(
                    rule_id=rule_id,
                    description=description,
                    current_status="❌ GAP",
                    line_number=line_number
                ))

        return gaps

    def _get_python_path_from_requirements(self, req_file: Path) -> Optional[str]:
        """Extract Python file path from requirements file path."""
        rel_path = req_file.relative_to(self.requirements_dir)
        parts = list(rel_path.parts)

        if not parts or parts[0] != "app":
            return None

        # Remove .requirements.md from the end
        full_path = "/".join(parts)
        if full_path.endswith(".requirements.md"):
            full_path = full_path[:-17]  # Remove .requirements.md

        # Ensure .py extension
        if not full_path.endswith(".py"):
            full_path += ".py"

        return full_path

    def _get_layer(self, python_path: str) -> str:
        """Determine the layer from Python file path."""
        if "market_microstructure" in python_path:
            return "L1_Microstructure"
        elif "ensemble" in python_path:
            return "L2_Ensemble"
        elif "backtesting/core" in python_path:
            return "L3_Backtesting_Core"
        elif "backtesting/labeling" in python_path:
            return "L4_Backtesting_Labeling"
        elif "backtesting/validation" in python_path:
            return "L5_Backtesting_Validation"
        elif "domain/services" in python_path or "domain/strategies" in python_path:
            return "L6_Domain_Services"
        elif "domain/entities" in python_path or "domain/value_objects" in python_path:
            return "L7_Domain_Entities"
        elif "application" in python_path:
            return "L8_Application"
        elif "core" in python_path:
            return "L9_Core"
        elif "database" in python_path or "repositories" in python_path:
            return "L10_Data"
        else:
            return "L0_Other"

    def _get_overall_priority(self, gaps: List[GapViolation]) -> str:
        """Get the highest priority from a list of gaps."""
        priorities = []
        for gap in gaps:
            priority = self.priority_rules.get(gap.rule_id, "P3")
            priorities.append(priority)

        # Return highest priority (P0 > P1 > P2 > P3)
        if "P0" in priorities:
            return "P0"
        elif "P1" in priorities:
            return "P1"
        elif "P2" in priorities:
            return "P2"
        else:
            return "P3"

    def group_by_priority(self, files_with_gaps: Dict[str, FileWithGaps]) -> Dict[str, List[FileWithGaps]]:
        """Group files by priority."""
        groups = {"P0": [], "P1": [], "P2": [], "P3": []}
        for file_data in files_with_gaps.values():
            groups[file_data.priority].append(file_data)
        return groups

    def generate_task_file(self, file_data: FileWithGaps, task_id: int) -> str:
        """Generate a task file for a file with GAP violations."""
        layer_dir = self.tasks_dir / file_data.layer
        layer_dir.mkdir(parents=True, exist_ok=True)

        filename = f"TASK-{task_id:03d}-{Path(file_data.python_file).stem}.md"
        task_file = layer_dir / filename

        # Get simple filename
        simple_filename = Path(file_data.python_file).name

        # Build gaps list
        gaps_md = []
        for gap in file_data.gaps:
            line_info = f" (line {gap.line_number})" if gap.line_number else ""
            gaps_md.append(f"- **{gap.rule_id}**: {gap.description}{line_info}")

        task_content = f"""# Task: TASK-{task_id:03d} - Fix GAP violations in {simple_filename}

## Objective

Fix all documented GAP violations in `{file_data.python_file}` to comply with BASE_RULES.md requirements.

## Requirements

- Requirement 1: Fix LOG-001 violations - Use structured logging with keyword arguments (Source: {file_data.requirements_file})
- Requirement 2: Fix LOG-004 violations - Add exc_info=True to error logging (Source: {file_data.requirements_file})
- Requirement 3: Fix all other documented GAP violations (Source: {file_data.requirements_file})

## Acceptance Criteria

- [ ] Criterion 1: All GAP violations are fixed according to BASE_RULES.md
- [ ] Criterion 2: Code passes syntax validation (python -m py_compile)
- [ ] Criterion 3: Code passes type checking (mypy --strict, if available)
- [ ] Criterion 4: Code passes linting (ruff check, if available)
- [ ] Criterion 5: Unit tests pass (pytest)
- [ ] Criterion 6: Requirements document updated with ✅ FIXED status

## Rules to Follow

Extracted from `{file_data.requirements_file}`:

| Rule      | Source        | Requirement | Current Status |
| --------- | ------------- | ----------- | -------------- |
{chr(10).join([f"| {gap.rule_id} | BASE_RULES.md | {gap.description[:50]}... | ❌ GAP |" for gap in file_data.gaps[:5]])}
{"| ... | ... | ... | ... |" if len(file_data.gaps) > 5 else ""}

## Files to Modify

- `{file_data.python_file}`
- `{file_data.requirements_file}` (to update status)

## Implementation Mode

**Mode:** Minimal

Add only the minimum code necessary to fix the documented GAP violations. Auditor will only audit newly added/modified code sections.

## Dependencies

- BASE_RULES.md: .requirements/BASE_RULES.md
- Requirements Document: {file_data.requirements_file}
- Templates: .tasks/templates/

## Notes

**Layer:** {file_data.layer}
**Priority:** {file_data.priority}
**Total GAPs:** {len(file_data.gaps)}

**GAP Violations:**
{chr(10).join(gaps_md)}

**Workflow:**
1. Read requirements document: `{file_data.requirements_file}`
2. Read current code: `{file_data.python_file}`
3. Fix each GAP violation following BASE_RULES.md patterns
4. Validate: python -m py_compile {file_data.python_file}
5. Update requirements document to mark GAPs as ✅ FIXED

---

**Status:** PLANNED
**Created:** {datetime.now().isoformat()}
**Planner:** audit_gaps_deterministic.py
**Implementer:** @agent-python-expert
**Validator:** @agent-code-reviewer → @agent-code-auditor
"""

        task_file.write_text(task_content)
        return str(task_file.relative_to(self.repo_root))

    def generate_summary_report(self, files_with_gaps: Dict[str, FileWithGaps], task_files: List[str]) -> str:
        """Generate a comprehensive audit summary report."""
        lines = [
            "# GAP Audit Summary Report",
            f"Generated: {datetime.now().isoformat()}",
            f"Repository: {self.repo_root}",
            "",
            "## Summary",
            "",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Total files with GAPs | {len(files_with_gaps)} |",
            f"| Total GAP violations | {sum(len(f.gaps) for f in files_with_gaps.values())} |",
            f"| Tasks created | {len(task_files)} |",
            "",
        ]

        # Group by priority
        by_priority = self.group_by_priority(files_with_gaps)
        lines.append("## By Priority\n")
        for priority in ["P0", "P1", "P2", "P3"]:
            files_list = by_priority[priority]
            if files_list:
                lines.append(f"### {priority} ({len(files_list)} files)\n")
                for f in sorted(files_list, key=lambda x: x.python_file):
                    lines.append(f"- `{f.python_file}` ({len(f.gaps)} GAPs)")
                lines.append("")

        # Task files list
        lines.append("## Task Files Created\n")
        for task_file in sorted(task_files):
            lines.append(f"- `{task_file}`")
        lines.append("")

        # Next steps
        lines.append("## Next Steps\n")
        lines.append("1. Call @agent-tech-lead-orchestrator with the task files")
        lines.append("2. The orchestrator will coordinate:")
        lines.append("   - @agent-requirement-expert (if requirements missing)")
        lines.append("   - @agent-python-expert (to implement fixes)")
        lines.append("   - @agent-python-testing-expert (to create tests)")
        lines.append("   - @agent-code-reviewer (to review and QA)")
        lines.append("   - @agent-code-auditor (to audit requirements compliance)")
        lines.append("")

        return "\n".join(lines)


def main():
    """Main entry point."""
    repo_root = Path(__file__).parent.parent

    print(f"🔍 GAP Audit Tool")
    print(f"Repository: {repo_root}")
    print(f"Requirements: {repo_root / '.requirements'}")
    print()

    auditor = GapAuditor(repo_root)

    # Find all GAP violations
    print("Scanning for GAP violations...")
    files_with_gaps = auditor.find_all_gap_violations()

    if not files_with_gaps:
        print("✅ No GAP violations found!")
        return 0

    print(f"Found {len(files_with_gaps)} files with GAP violations")

    # Group by priority
    by_priority = auditor.group_by_priority(files_with_gaps)

    # Print summary
    print()
    print("Summary by Priority:")
    for priority in ["P0", "P1", "P2", "P3"]:
        count = len(by_priority[priority])
        if count > 0:
            print(f"  {priority}: {count} files")

    # Generate task files
    print()
    print("Generating task files...")
    task_files = []
    task_id = 1

    # Process by priority order
    for priority in ["P0", "P1", "P2", "P3"]:
        files_list = sorted(by_priority[priority], key=lambda x: x.python_file)
        for file_data in files_list:
            task_file = auditor.generate_task_file(file_data, task_id)
            task_files.append(task_file)
            print(f"  Created: {task_file}")
            task_id += 1

    # Generate summary report
    report = auditor.generate_summary_report(files_with_gaps, task_files)
    report_file = repo_root / "GAP_AUDIT_SUMMARY.md"
    report_file.write_text(report)
    print()
    print(f"Summary report: {report_file}")

    print()
    print("Next: Call @agent-tech-lead-orchestrator to process the tasks")

    return 0


if __name__ == "__main__":
    sys.exit(main())
