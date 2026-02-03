#!/usr/bin/env python3
"""
Find files with GAP violations and generate task list.
Simple, deterministic script using subprocess to call grep.
"""

import subprocess
import sys
from pathlib import Path


def main():
    repo_root = Path(__file__).parent.parent
    requirements_dir = repo_root / ".requirements"
    summary_file = repo_root / "GAP_AUDIT_SUMMARY.md"

    print("🔍 GAP Audit Tool")
    print(f"Repository: {repo_root}")
    print()

    # Find all requirements files with GAP violations using grep
    print("Scanning for GAP violations...")
    result = subprocess.run(
        ["grep", "-r", "-l", "GAP", str(requirements_dir), "--include=*.md"],
        capture_output=True,
        text=True,
    )

    if result.returncode != 0 or not result.stdout.strip():
        print("✅ No GAP violations found!")
        return 0

    gap_files = [f.strip() for f in result.stdout.strip().split("\n") if f.strip()]
    print(f"Found {len(gap_files)} files with GAP violations")
    print()

    # Parse each file for GAP violations
    all_gaps = []
    priority_counts = {"P0": 0, "P1": 0, "P2": 0, "P3": 0}

    for req_file in gap_files:
        # Get GAP violations from file
        result = subprocess.run(
            ["grep", "GAP", req_file],
            capture_output=True,
            text=True,
        )

        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if not line.strip():
                    continue

                # Parse the line to extract rule ID and description
                parts = line.split("|")
                if len(parts) >= 4:
                    rule_id = parts[1].strip() if len(parts) > 1 else ""
                    status_col = parts[4].strip() if len(parts) > 4 else ""

                    if "GAP" in status_col and rule_id and "-" in rule_id:
                        # Extract description (everything after "GAP -")
                        description = status_col
                        if "GAP -" in description:
                            description = description.split("GAP -", 1)[1].strip()
                        elif "GAP" in description:
                            description = description.split("GAP", 1)[1].strip()
                            description = description.lstrip("-").strip()

                        # Get Python file path
                        python_path = str(Path(req_file).relative_to(repo_root))
                        python_path = python_path.replace(".requirements/", "")
                        python_path = python_path.replace(".requirements.md", ".py")

                        # Determine priority
                        priority = "P3"
                        if rule_id.startswith("TRD-001") or rule_id.startswith("TRD-005") or \
                           rule_id.startswith("SEC-001") or rule_id.startswith("SEC-002") or \
                           rule_id.startswith("SEC-003") or rule_id == "CC-006":
                            priority = "P0"
                        elif rule_id.startswith("LOG-004") or rule_id.startswith("LOG-001") or \
                             rule_id.startswith("TRD-004") or rule_id.startswith("TRD-007") or \
                             rule_id.startswith("SEC-007"):
                            priority = "P1"
                        elif rule_id.startswith("TYP-001") or rule_id.startswith("TYP-003") or \
                             rule_id.startswith("ARCH-004") or rule_id.startswith("ARCH-006") or \
                             rule_id.startswith("CC-001") or rule_id.startswith("CC-002"):
                            priority = "P2"

                        # Get layer
                        layer = "L0_Other"
                        if "market_microstructure" in python_path:
                            layer = "L1_Microstructure"
                        elif "ensemble" in python_path:
                            layer = "L2_Ensemble"
                        elif "backtesting/core" in python_path:
                            layer = "L3_Backtesting_Core"
                        elif "backtesting/labeling" in python_path:
                            layer = "L4_Backtesting_Labeling"
                        elif "backtesting/validation" in python_path:
                            layer = "L5_Backtesting_Validation"
                        elif "domain/services" in python_path or "domain/strategies" in python_path:
                            layer = "L6_Domain_Services"
                        elif "domain/entities" in python_path or "domain/value_objects" in python_path:
                            layer = "L7_Domain_Entities"
                        elif "application" in python_path:
                            layer = "L8_Application"
                        elif "core" in python_path:
                            layer = "L9_Core"
                        elif "database" in python_path or "repositories" in python_path:
                            layer = "L10_Data"

                        all_gaps.append({
                            "file": python_path,
                            "rule": rule_id,
                            "description": description,
                            "priority": priority,
                            "layer": layer,
                        })
                        priority_counts[priority] += 1

    # Write summary
    with open(summary_file, "w") as f:
        f.write("# GAP Audit Summary Report\n\n")
        f.write(f"Generated: {subprocess.run(['date', '-u', '+%Y-%m-%dT%H:%M:%SZ'], capture_output=True, text=True).stdout.strip()}\n")
        f.write(f"Repository: {repo_root}\n\n")
        f.write("## Summary\n\n")
        f.write("| Metric | Count |\n")
        f.write("|--------|-------|\n")
        f.write(f"| Files with GAPs | {len(set(g['file'] for g in all_gaps))} |\n")
        f.write(f"| Total GAP violations | {len(all_gaps)} |\n\n")
        f.write("## Files with GAP Violations\n\n")

        # Group by priority
        by_priority = {"P0": [], "P1": [], "P2": [], "P3": []}
        for gap in all_gaps:
            by_priority[gap["priority"]].append(gap)

        for priority in ["P0", "P1", "P2", "P3"]:
            gaps = by_priority[priority]
            if gaps:
                f.write(f"### {priority} Priority ({len(gaps)} violations)\n\n")
                for gap in sorted(gaps, key=lambda x: x["file"]):
                    f.write(f"- `{gap['file']}` - **{gap['rule']}**: {gap['description']}\n")
                f.write("\n")

        f.write("## Summary by Priority\n\n")
        f.write("| Priority | Count |\n")
        f.write("|----------|-------|\n")
        f.write(f"| P0 (Critical) | {priority_counts['P0']} |\n")
        f.write(f"| P1 (High) | {priority_counts['P1']} |\n")
        f.write(f"| P2 (Medium) | {priority_counts['P2']} |\n")
        f.write(f"| P3 (Low) | {priority_counts['P3']} |\n\n")
        f.write("## Next Steps\n\n")
        f.write("1. Call @agent-tech-lead-orchestrator with this summary\n")
        f.write("2. The orchestrator will coordinate the workflow:\n")
        f.write("   - @agent-requirement-expert (if requirements missing)\n")
        f.write("   - @agent-python-expert (to implement fixes)\n")
        f.write("   - @agent-python-testing-expert (to create tests)\n")
        f.write("   - @agent-code-reviewer (to review and QA)\n")
        f.write("   - @agent-code-auditor (to audit requirements compliance)\n")

    # Print summary
    print("Summary by Priority:")
    print(f"  P0 (Critical): {priority_counts['P0']}")
    print(f"  P1 (High):     {priority_counts['P1']}")
    print(f"  P2 (Medium):   {priority_counts['P2']}")
    print(f"  P3 (Low):      {priority_counts['P3']}")
    print()
    print(f"Summary report: {summary_file}")
    print()
    print("Next: Call @agent-tech-lead-orchestrator to process the workflow")

    return 0


if __name__ == "__main__":
    sys.exit(main())
