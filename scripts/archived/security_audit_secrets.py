#!/usr/bin/env python3
"""
Security Audit Script - Rule 28 Compliance: Secret Management

This script scans the codebase for hardcoded secrets and provides compliance reporting.
It identifies:
- Hardcoded API keys, tokens, passwords
- Default credentials in config files
- Secrets in connection strings
- Credentials in test files (acceptable with documentation)

Compliance Requirements (Rule 28):
1. NO hardcoded API keys, passwords, or tokens in production code
2. Use environment variables for all secrets
3. Implement secret validation
4. Add .env file templates
5. Document secret management

Usage:
    python scripts/security_audit_secrets.py [--fix] [--report]
"""

import ast
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


class Severity(Enum):
    CRITICAL = "CRITICAL"  # Actual secrets in code
    HIGH = "HIGH"  # Default credentials that should use env vars
    MEDIUM = "MEDIUM"  # Weak patterns that should be documented
    LOW = "LOW"  # Acceptable in tests/fixtures
    INFO = "INFO"  # Documentation/acceptable usage


@dataclass
class SecurityFinding:
    """Represents a security finding."""
    file_path: str
    line_number: int
    severity: Severity
    category: str
    finding: str
    code_snippet: str
    recommendation: str
    is_test_file: bool = False


@dataclass
class AuditReport:
    """Comprehensive audit report."""
    timestamp: str = ""
    total_files_scanned: int = 0
    findings: List[SecurityFinding] = field(default_factory=list)
    files_with_issues: Dict[str, int] = field(default_factory=dict)
    compliance_score: float = 0.0

    def add_finding(self, finding: SecurityFinding):
        """Add a finding to the report."""
        self.findings.append(finding)
        if finding.file_path not in self.files_with_issues:
            self.files_with_issues[finding.file_path] = 0
        self.files_with_issues[finding.file_path] += 1

    def calculate_compliance(self) -> float:
        """Calculate compliance percentage (95% target)."""
        if not self.findings:
            return 100.0

        # Critical and High findings have major impact
        critical_count = sum(1 for f in self.findings
                           if f.severity in [Severity.CRITICAL, Severity.HIGH]
                           and not f.is_test_file)
        total_non_test = sum(1 for f in self.findings if not f.is_test_file)

        if total_non_test == 0:
            return 100.0

        # Each critical/high finding reduces compliance by 5%
        compliance = 100.0 - (critical_count * 5.0)
        return max(0.0, min(100.0, compliance))


class SecretScanner:
    """Scans codebase for hardcoded secrets."""

    # Patterns to detect secrets
    PATTERNS = {
        'hardcoded_password': (
            r'password\s*=\s*["\'][^"\']{1,20}["\']',
            "Hardcoded password found"
        ),
        'hardcoded_api_key': (
            r'api_key\s*=\s*["\'][^"\']{20,}["\']',
            "Hardcoded API key (20+ characters)"
        ),
        'hardcoded_secret': (
            r'secret\s*=\s*["\'][^"\']{20,}["\']',
            "Hardcoded secret (20+ characters)"
        ),
        'hardcoded_token': (
            r'token\s*=\s*["\'][^"\']{20,}["\']',
            "Hardcoded token (20+ characters)"
        ),
        'default_password': (
            r'(password|secret|api_key|token)\s*=\s*["\'](password|secret|changeme|admin|quest|test)["\']',
            "Default/weak credential value"
        ),
        'connection_string_creds': (
            r'(postgresql|redis|mssql|mysql)://[^:@]+:[^@]+@',
            "Credentials in connection string"
        ),
        'bearer_token': (
            r'["\']Bearer\s+[a-zA-Z0-9]{20,}["\']',
            "Hardcoded bearer token"
        ),
        'aws_key_id': (
            r'AKIA[0-9A-Z]{16}',
            "AWS Access Key ID pattern"
        ),
        'sk_api_key': (
            r'sk-[a-zA-Z0-9]{20,}',
            "Stripe/OpenAI API key pattern"
        ),
    }

    # Files/directories to skip
    SKIP_DIRS = {
        '__pycache__', '.git', '.venv', 'venv', 'env',
        'node_modules', '.pytest_cache', 'htmlcov',
        'migrations', 'data', 'logs', 'results', 'reports'
    }

    # Test file patterns
    TEST_PATTERNS = [
        r'test_.*\.py$',
        r'.*_test\.py$',
        r'tests/.*',
        r'conftest\.py$',
    ]

    def __init__(self, root_path: str):
        self.root_path = Path(root_path)
        self.report = AuditReport()

    def is_test_file(self, file_path: str) -> bool:
        """Check if file is a test file."""
        path = Path(file_path)
        for pattern in self.TEST_PATTERNS:
            if re.search(pattern, str(path)):
                return True
        return False

    def scan_file(self, file_path: Path) -> List[SecurityFinding]:
        """Scan a single file for secrets."""
        findings = []

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            is_test = self.is_test_file(file_path)

            for line_num, line in enumerate(lines, 1):
                # Skip comments and docstrings
                stripped = line.strip()
                if stripped.startswith('#') or stripped.startswith("'''") or stripped.startswith('"""'):
                    continue

                for pattern_name, (pattern, description) in self.PATTERNS.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        # Determine severity
                        if is_test:
                            severity = Severity.LOW
                        elif 'default' in pattern_name or 'weak' in pattern_name:
                            severity = Severity.HIGH
                        elif 'connection' in pattern_name:
                            severity = Severity.HIGH
                        elif any(key in pattern_name for key in ['api_key', 'secret', 'token', 'password']):
                            severity = Severity.CRITICAL
                        else:
                            severity = Severity.MEDIUM

                        # Create recommendation
                        recommendation = self._get_recommendation(pattern_name)

                        finding = SecurityFinding(
                            file_path=str(file_path.relative_to(self.root_path)),
                            line_number=line_num,
                            severity=severity,
                            category=pattern_name,
                            finding=description,
                            code_snippet=line.strip()[:100],
                            recommendation=recommendation,
                            is_test_file=is_test
                        )
                        findings.append(finding)

        except Exception as e:
            print(f"Error scanning {file_path}: {e}")

        return findings

    def _get_recommendation(self, pattern_name: str) -> str:
        """Get recommendation for a finding."""
        recommendations = {
            'hardcoded_password': "Move to environment variable (e.g., os.getenv('DB_PASSWORD'))",
            'hardcoded_api_key': "Move to environment variable with validation",
            'hardcoded_secret': "Move to environment variable with validation",
            'hardcoded_token': "Move to environment variable or secure token store",
            'default_password': "Use environment variable with proper validation",
            'connection_string_creds': "Use environment variables, construct string dynamically",
            'bearer_token': "Use environment variable or OAuth flow",
            'aws_key_id': "Use IAM roles or environment variables",
            'sk_api_key': "Move to environment variable immediately",
        }
        return recommendations.get(pattern_name, "Review and remove from code")

    def scan_directory(self, directory: Path = None) -> AuditReport:
        """Scan entire directory."""
        if directory is None:
            directory = self.root_path

        print(f"Scanning {directory}...")
        self.report.total_files_scanned = 0

        for py_file in directory.rglob('*.py'):
            # Skip specified directories
            if any(skip_dir in py_file.parts for skip_dir in self.SKIP_DIRS):
                continue

            self.report.total_files_scanned += 1
            findings = self.scan_file(py_file)

            for finding in findings:
                self.report.add_finding(finding)

        self.report.compliance_score = self.report.calculate_compliance()
        return self.report


def print_report(report: AuditReport, verbose: bool = False):
    """Print audit report."""
    print("\n" + "="*80)
    print("SECURITY AUDIT REPORT - Rule 28 Compliance")
    print("="*80)
    print(f"\nTimestamp: {report.timestamp}")
    print(f"Files Scanned: {report.total_files_scanned}")
    print(f"Total Findings: {len(report.findings)}")
    print(f"Compliance Score: {report.compliance_score:.1f}%")
    print(f"Target: 95.0%")
    print(f"Status: {'PASS' if report.compliance_score >= 95.0 else 'FAIL'}")

    # Group by severity
    by_severity = {
        Severity.CRITICAL: [],
        Severity.HIGH: [],
        Severity.MEDIUM: [],
        Severity.LOW: [],
        Severity.INFO: []
    }

    for finding in report.findings:
        by_severity[finding.severity].append(finding)

    print("\n" + "-"*80)
    print("FINDINGS BY SEVERITY")
    print("-"*80)

    for severity in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
        findings = by_severity[severity]
        if findings:
            non_test = [f for f in findings if not f.is_test_file]
            print(f"\n{severity.value}: {len(non_test)} (excluding tests)")

            if verbose or severity in [Severity.CRITICAL, Severity.HIGH]:
                for finding in findings[:10]:  # Limit output
                    if not finding.is_test_file or verbose:
                        print(f"\n  File: {finding.file_path}:{finding.line_number}")
                        print(f"  Category: {finding.category}")
                        print(f"  Finding: {finding.finding}")
                        print(f"  Code: {finding.code_snippet}")
                        print(f"  Recommendation: {finding.recommendation}")

                if len(findings) > 10:
                    print(f"  ... and {len(findings) - 10} more")

    # Files with most issues
    print("\n" + "-"*80)
    print("FILES WITH MOST ISSUES (Top 10)")
    print("-"*80)
    sorted_files = sorted(report.files_with_issues.items(),
                         key=lambda x: x[1], reverse=True)[:10]
    for file_path, count in sorted_files:
        print(f"  {count} issues: {file_path}")

    print("\n" + "="*80)


def main():
    """Main entry point."""
    import argparse
    from datetime import datetime

    parser = argparse.ArgumentParser(description="Security Audit - Secret Scanner")
    parser.add_argument('--path', default='.', help="Root path to scan")
    parser.add_argument('--verbose', '-v', action='store_true', help="Verbose output")
    parser.add_argument('--report', '-r', action='store_true',
                       help="Generate detailed report file")

    args = parser.parse_args()

    # Get absolute path
    root_path = Path(args.path).resolve()

    # Run scan
    scanner = SecretScanner(root_path)
    report = scanner.scan_directory()
    report.timestamp = datetime.now().isoformat()

    # Print report
    print_report(report, verbose=args.verbose)

    # Save detailed report if requested
    if args.report:
        report_file = root_path / "reports" / f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        report_file.parent.mkdir(exist_ok=True)

        with open(report_file, 'w') as f:
            import sys
            from io import StringIO

            # Capture stdout
            old_stdout = sys.stdout
            sys.stdout = StringIO()
            print_report(report, verbose=True)
            report_content = sys.stdout.getvalue()
            sys.stdout = old_stdout

            f.write(report_content)

        print(f"\nDetailed report saved to: {report_file}")

    # Exit with appropriate code
    sys.exit(0 if report.compliance_score >= 95.0 else 1)


if __name__ == "__main__":
    main()
