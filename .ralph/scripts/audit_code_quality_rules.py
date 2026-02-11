#!/usr/bin/env python3
"""
Code Quality Audit Script - Reads per-file requirements + general rules

This script audits Python files by:
1. Reading SERVICE_REQUIREMENTS.md for general rules (SOLID, R1-R29, SpainTax)
2. Reading each file's .requirements.md file if it exists
3. Combining both to audit the file against all applicable rules

Usage:
    python audit_code_quality_rules.py --app-dir app/ --output audit_results.json
    python audit_code_quality_rules.py --file app/services/currency_hedging_engine.py --check
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Rule:
    """A quality rule to check."""
    id: str
    name: str
    category: str  # SOLID, R1-R29, SpainTax, PythonQA, etc.
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW
    description: str
    pattern: Optional[str] = None
    check_function: Optional[str] = None


@dataclass
class AuditResult:
    """Result of auditing a single file."""
    file_path: str
    has_requirements_file: bool
    requirements_content: str = ""
    issues: List[Dict[str, Any]] = field(default_factory=list)
    rules_checked: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class RequirementsParser:
    """Parser for requirements files."""

    def __init__(self, requirements_dir: Path):
        self.requirements_dir = requirements_dir

    def get_requirements_file(self, source_file: Path) -> Optional[Path]:
        """Get the requirements file for a source file."""
        # Convert app/services/file.py to .requirements/app/services/file.py.requirements.md

        # Handle both absolute and relative paths
        file_str = str(source_file)

        # If path starts with app/, use it directly
        if file_str.startswith("app/"):
            relative_path = file_str
        # If path contains app/ somewhere, extract from there
        elif "app/" in file_str:
            relative_path = "app/" + file_str.split("app/")[1]
        else:
            # No app/ in path, use as-is
            relative_path = file_str

        # Build requirements path
        requirements_path = self.requirements_dir / relative_path
        requirements_path = requirements_path.with_suffix(requirements_path.suffix + ".requirements.md")

        if requirements_path.exists():
            return requirements_path
        return None

    def parse_requirements_file(self, requirements_path: Path) -> Dict[str, Any]:
        """Parse a requirements file and extract rules/gaps."""
        content = requirements_path.read_text()

        result = {
            "exists": True,
            "has_gaps": False,
            "gaps": [],
            "acceptance_criteria": [],
            "function_contracts": [],
            "rule_compliance": {}
        }

        # Check for Critical Gaps section
        if "## Critical Gaps" in content:
            result["has_gaps"] = True
            # Extract gap items
            gap_section = content.split("## Critical Gaps")[-1].split("##")[0]
            for line in gap_section.split("\n"):
                if "### Gap #" in line or "- **" in line:
                    result["gaps"].append(line.strip())

        # Check for Acceptance Criteria
        if "## Acceptance Criteria" in content:
            ac_section = content.split("## Acceptance Criteria")[-1].split("##")[0]
            for line in ac_section.split("\n"):
                if "### AC-" in line or "- [ ]" in line or "- [x]" in line:
                    result["acceptance_criteria"].append(line.strip())

        # Check for Function Contracts
        if "## Function Contracts" in content or "### `" in content:
            for line in content.split("\n"):
                if "### `" in line and "(" in line and ")" in line and "->" in line:
                    result["function_contracts"].append(line.strip())

        # Check Rule Compliance table
        if "## Rule Compliance" in content or "## Rule Compliance Analysis" in content:
            compliance_section = content.split("## Rule Compliance")[-1].split("##")[0] if "## Rule Compliance" in content else content.split("## Rule Compliance Analysis")[-1].split("##")[0]
            for line in compliance_section.split("\n"):
                if "|" in line and ("✅" in line or "❌" in line):
                    result["rule_compliance"][line] = line.strip()

        return result


class GeneralRulesParser:
    """Parser for SERVICE_REQUIREMENTS.md general rules."""

    def __init__(self, requirements_file: Path):
        self.requirements_file = requirements_file

    def parse(self) -> List[Rule]:
        """Parse SERVICE_REQUIREMENTS.md and extract rules."""
        if not self.requirements_file.exists():
            return []

        content = self.requirements_file.read_text()
        rules = []

        # Parse SOLID principles (5 requirements)
        if "### 1. Principio SOLID" in content or "SOLID" in content:
            solid_section = content[content.find("### 1. Principio SOLID"):content.find("### 2", content.find("### 1. Principio SOLID") + 1)] if "### 1. Principio SOLID" in content else ""
            if not solid_section and "SOLID" in content:
                # Try alternative section finding
                for line in content.split("\n"):
                    if "SOLID" in line and "|" in line:
                        rules.append(Rule(
                            id=f"SOLID-{len(rules)}",
                            name="SOLID Principle",
                            category="SOLID",
                            severity="HIGH",
                            description=line.strip()
                        ))

        # Parse R1-R29 trading rules
        for i in range(1, 30):
            if f"**R{i}**" in content or f"| **R{i}**" in content:
                rules.append(Rule(
                    id=f"R{i}",
                    name=f"Trading Rule R{i}",
                    category="R1-R29",
                    severity="CRITICAL" if i <= 5 else "HIGH",
                    description=f"Trading rule R{i} from SERVICE_REQUIREMENTS.md"
                ))

        # Parse Spain Tax rules
        if "IRPF" in content or "Spain Tax" in content:
            for tax_rule in ["IRPF", "Dividendos UE", "Modelo 720"]:
                if tax_rule in content:
                    rules.append(Rule(
                        id=f"SPAIN_TAX_{tax_rule.replace(' ', '_')}",
                        name=tax_rule,
                        category="SpainTax",
                        severity="HIGH",
                        description=f"Spain tax rule: {tax_rule}"
                    ))

        return rules


class CodeQualityAuditor:
    """Main auditor that combines general and per-file rules."""

    def __init__(self, app_dir: Path, requirements_dir: Path, general_requirements: Path):
        self.app_dir = app_dir
        self.requirements_parser = RequirementsParser(requirements_dir)
        self.general_rules_parser = GeneralRulesParser(general_requirements)
        self.general_rules = self.general_rules_parser.parse()

    def audit_file(self, file_path: Path) -> AuditResult:
        """Audit a single file against all applicable rules."""
        result = AuditResult(file_path=str(file_path), has_requirements_file=False)

        # Check if requirements file exists
        requirements_file = self.requirements_parser.get_requirements_file(file_path)
        if requirements_file:
            result.has_requirements_file = True
            result.requirements_content = requirements_file.read_text()
            parsed = self.requirements_parser.parse_requirements_file(requirements_file)

            # Add issues from gaps in requirements file
            if parsed.get("has_gaps"):
                for gap in parsed.get("gaps", []):
                    result.issues.append({
                        "type": "requirements_gap",
                        "severity": "HIGH",
                        "message": gap,
                        "source": "requirements_file"
                    })

        # Check against general rules
        for rule in self.general_rules:
            result.rules_checked.append(rule.id)

            # Apply rule based on category
            if rule.category == "SOLID":
                self._check_solid(file_path, rule, result)
            elif rule.category == "R1-R29":
                self._check_trading_rule(file_path, rule, result)
            elif rule.category == "SpainTax":
                self._check_spain_tax(file_path, rule, result)

        # Check for common code quality issues
        self._check_code_quality(file_path, result)

        return result

    def _check_solid(self, file_path: Path, rule: Rule, result: AuditResult):
        """Check SOLID principles."""
        try:
            content = file_path.read_text()

            # SRP: Check for multiple responsibilities
            if rule.id == "SOLID-0" or "SRP" in rule.name:
                classes = re.findall(r'class (\w+)', content)
                for cls in classes:
                    # Count methods - if >15, possible SRP violation
                    class_methods = re.findall(rf'class {cls}.*?(?=\nclass|\Z)', content, re.DOTALL)
                    if class_methods:
                        method_count = len(re.findall(r'def \w+', class_methods[0]))
                        if method_count > 15:
                            result.issues.append({
                                "type": "solid_violation",
                                "severity": rule.severity,
                                "rule": rule.id,
                                "message": f"Class {cls} has {method_count} methods - possible SRP violation",
                                "source": "solid_check"
                            })
        except Exception as e:
            result.warnings.append(f"Error checking SOLID: {e}")

    def _check_trading_rule(self, file_path: Path, rule: Rule, result: AuditResult):
        """Check trading rules R1-R29."""
        try:
            content = file_path.read_text()
            lines = content.split('\n')

            # R1: Kelly Criterion + 2% max
            if rule.id == "R1":
                if "position" in content.lower() or "risk" in content.lower():
                    # Check for hardcoded 0.02 instead of config
                    # But allow it as fallback in getattr()
                    for line_num, line in enumerate(lines, 1):
                        # Get context - check previous and next lines
                        context_lines = []
                        if line_num > 1:
                            context_lines.append(lines[line_num - 2])  # Previous line
                        context_lines.append(line)
                        if line_num < len(lines):
                            context_lines.append(lines[line_num])  # Next line

                        context = '\n'.join(context_lines)

                        # Skip if context uses getattr with config (correct pattern)
                        if any(pattern in context for pattern in ['getattr(config.trading', 'getattr(tt,', 'getattr(config.', 'getattr(config.compliance,']):
                            continue

                        # Check for hardcoded 0.02
                        if ('0.02' in line or 'Decimal("0.02")' in line):
                            # Make sure it's not just a default fallback
                            if not any(pattern in context for pattern in ['getattr', 'default=', '=0.02,']):
                                result.issues.append({
                                    "type": "trading_rule_violation",
                                    "severity": rule.severity,
                                    "rule": rule.id,
                                    "line": line_num,
                                    "message": "R1: Kelly 2% max should use config, not hardcoded 0.02",
                                    "source": "trading_rules"
                                })

            # R2: Drawdown 15% stop
            elif rule.id == "R2":
                if "drawdown" in content.lower():
                    if '0.15' in content or '0.25' in content:
                        if 'getattr(config.trading' not in content:
                            result.issues.append({
                                "type": "trading_rule_violation",
                                "severity": rule.severity,
                                "rule": rule.id,
                                "message": "R2: Drawdown limit should use config",
                                'source': "trading_rules"
                            })

            # R4: R:R 2:1 minimum
            elif rule.id == "R4":
                if "stop_loss" in content.lower() or "take_profit" in content.lower():
                    if '2.0' in content or '2:' in content:
                        if 'getattr(config.trading' not in content:
                            result.issues.append({
                                "type": "trading_rule_violation",
                                "severity": rule.severity,
                                "rule": rule.id,
                                "message": "R4: Risk-Reward ratio should use config",
                                "source": "trading_rules"
                            })

        except Exception as e:
            result.warnings.append(f"Error checking {rule.id}: {e}")

    def _check_spain_tax(self, file_path: Path, rule: Rule, result: AuditResult):
        """Check Spain Tax rules."""
        try:
            content = file_path.read_text()

            # Check for tax-related code
            if "tax" in content.lower() or "hacienda" in content.lower() or "spain" in content.lower():
                # Check for hardcoded tax rates
                if any(rate in content for rate in ['0.19', '0.21', '0.23', '19%', '21%', '23%']):
                    if 'getattr(config.spain_tax' not in content and 'getattr(config.trading' not in content:
                        result.issues.append({
                            "type": "tax_rule_violation",
                            "severity": rule.severity,
                            "rule": rule.id,
                            "message": f"{rule.name}: Tax rate should use config, not hardcoded value",
                            "source": "spain_tax"
                        })
        except Exception as e:
            result.warnings.append(f"Error checking Spain Tax: {e}")

    def _check_code_quality(self, file_path: Path, result: AuditResult):
        """Check for common code quality issues."""
        try:
            content = file_path.read_text()
            lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                # Hardcoded decimals
                if re.search(r'Decimal\("0\\.[0-9]+"\)', line):
                    result.issues.append({
                        "type": "hardcoded_decimal",
                        "severity": "HIGH",
                        "line": line_num,
                        "code": line.strip()[:100],
                        "message": "Hardcoded Decimal value found - should use config",
                        "source": "code_quality"
                    })

                # Hardcoded floats (excluding version numbers)
                if re.search(r'(?<![\w.])0\\.[0-9]+(?![\w])', line):
                    if not any(excl in line for excl in ['version', 'python 3.', 'http://', 'https://', '# 0.']):
                        result.issues.append({
                            "type": "hardcoded_float",
                            "severity": "HIGH",
                            "line": line_num,
                            "code": line.strip()[:100],
                            "message": "Hardcoded float value found - should use config",
                            "source": "code_quality"
                        })

                # TODO/FIXME comments
                if re.search(r'# (TODO|FIXME|XXX|HACK):', line):
                    result.issues.append({
                        "type": "todo_comment",
                        "severity": "MEDIUM",
                        "line": line_num,
                        "code": line.strip()[:100],
                        "message": "TODO/FIXME comment found - should be implemented",
                        "source": "code_quality"
                    })

                # NotImplementedError
                if 'raise NotImplementedError' in line:
                    result.issues.append({
                        "type": "not_implemented",
                        "severity": "HIGH",
                        "line": line_num,
                        "code": line.strip()[:100],
                        "message": "NotImplementedError found - function not implemented",
                        "source": "code_quality"
                    })

        except Exception as e:
            result.warnings.append(f"Error checking code quality: {e}")


def main():
    parser = argparse.ArgumentParser(description="Audit code quality with per-file requirements")
    parser.add_argument("--app-dir", default="app/", help="App directory to audit")
    parser.add_argument("--requirements-dir", default=".requirements/", help="Requirements files directory")
    parser.add_argument("--general-requirements", default=".ralph/docs/requirements/SERVICE_REQUIREMENTS.md",
                        help="General requirements file")
    parser.add_argument("--file", help="Specific file to audit")
    parser.add_argument("--check", action="store_true", help="Quick check of a file")
    parser.add_argument("--output", default=".ralph/outputs/CODE_QUALITY_AUDIT.json", help="Output JSON file")
    args = parser.parse_args()

    app_dir = Path(args.app_dir)
    requirements_dir = Path(args.requirements_dir)
    general_requirements = Path(args.general_requirements)

    auditor = CodeQualityAuditor(app_dir, requirements_dir, general_requirements)

    if args.file:
        # Audit single file
        file_path = Path(args.file)
        result = auditor.audit_file(file_path)

        if args.check:
            # Quick check output
            print(f"\n=== Audit: {file_path} ===")
            print(f"Requirements file: {'✅' if result.has_requirements_file else '❌'}")
            print(f"Rules checked: {len(result.rules_checked)}")
            print(f"Issues found: {len(result.issues)}")

            if result.issues:
                print("\n🚨 Issues:")
                for issue in result.issues[:10]:
                    print(f"  [{issue['severity']}] {issue.get('line', '?')}: {issue['message']}")
            else:
                print("\n✅ No issues found!")

            return 0 if not result.issues else 1
        else:
            # Full JSON output
            print(json.dumps({
                "file": str(file_path),
                "has_requirements_file": result.has_requirements_file,
                "rules_checked": result.rules_checked,
                "issues": result.issues,
                "warnings": result.warnings
            }, indent=2))
            return 0

    # Audit all files
    print("Scanning for Python files...")
    python_files = list(app_dir.rglob("*.py"))

    # Filter out test files
    python_files = [
        f for f in python_files
        if 'test' not in str(f).lower()
        and '__pycache__' not in str(f)
        and 'venv' not in str(f)
        and '.venv' not in str(f)
    ]

    print(f"Found {len(python_files)} files to audit")

    results = {
        "task": "CODE_QUALITY_AUDIT",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "total_files": len(python_files),
        "files_with_requirements": 0,
        "files_with_issues": [],
        "summary": {
            "total_issues": 0,
            "by_severity": {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "by_type": {}
        }
    }

    for i, file_path in enumerate(python_files, 1):
        if i % 100 == 0:
            print(f"Progress: {i}/{len(python_files)} files audited")

        result = auditor.audit_file(file_path)

        if result.has_requirements_file:
            results["files_with_requirements"] += 1

        if result.issues:
            results["files_with_issues"].append({
                "path": str(file_path),
                "has_requirements_file": result.has_requirements_file,
                "issue_count": len(result.issues),
                "issues": result.issues[:10]  # First 10 issues
            })
            results["summary"]["total_issues"] += len(result.issues)

            for issue in result.issues:
                severity = issue.get("severity", "LOW")
                if severity in results["summary"]["by_severity"]:
                    results["summary"]["by_severity"][severity] += 1

                issue_type = issue.get("type", "unknown")
                if issue_type not in results["summary"]["by_type"]:
                    results["summary"]["by_type"][issue_type] = 0
                results["summary"]["by_type"][issue_type] += 1

    # Write output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2))

    print(f"\n=== Audit Complete ===")
    print(f"Total files: {results['total_files']}")
    print(f"Files with requirements: {results['files_with_requirements']}")
    print(f"Files with issues: {len(results['files_with_issues'])}")
    print(f"Total issues: {results['summary']['total_issues']}")
    print(f"\nBy severity:")
    for severity, count in results['summary']['by_severity'].items():
        print(f"  {severity}: {count}")
    print(f"\nOutput: {output_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
