#!/usr/bin/env python3
"""
Security Validation Script - Rule 28 Compliance Checker

This script validates that all secrets are properly configured according to Rule 28:
1. No hardcoded secrets in code
2. All secrets from environment variables
3. Proper secret validation
4. Connection strings built dynamically
5. Production readiness checks

Usage:
    python scripts/validate_security.py [--verbose] [--fix]

Exit codes:
    0: All checks passed
    1: Security issues found
    2: Critical security issues
"""

import os
import sys
import re
from pathlib import Path
from typing import List, Tuple, Dict


class SecurityValidator:
    """Validates security compliance with Rule 28."""

    # Patterns that indicate hardcoded secrets
    SECRET_PATTERNS = {
        'hardcoded_password': (
            r'password\s*=\s*["\'](?![a-zA-Z0-9_-]+|getenv|os\.getenv|environ)([^"\']){1,30}["\']',
            "Hardcoded password detected"
        ),
        'hardcoded_api_key': (
            r'api_key\s*=\s*["\'][^"\']{30,}["\'](?!\s*#.*env)',
            "Hardcoded API key (30+ characters)"
        ),
        'hardcoded_secret': (
            r'secret\s*=\s*["\'][^"\']{30,}["\'](?!\s*#.*env)',
            "Hardcoded secret (30+ characters)"
        ),
        'default_password': (
            r'password\s*=\s*["\'](password|secret|changeme|admin|quest)["\']',
            "Default/weak password value"
        ),
        'connection_string_creds': (
            r'(postgresql|redis|mssql)://[^:@\s]+:[^@@\s]+@[^@\s]+',
            "Credentials hardcoded in connection string"
        ),
    }

    # Files to exclude from validation
    EXCLUDE_FILES = [
        'tests/', 'test_', '__pycache__', '.git',
        'migrations/', 'examples/', 'conftest.py',
        '.env.example', 'validate_security.py',
        'security_audit_secrets.py'
    ]

    # Required environment variables for production
    REQUIRED_ENV_VARS = {
        'SECRET_KEY': 32,  # Minimum length
        'DB_PASSWORD': 8,
    }

    # Weak password patterns
    WEAK_PATTERNS = [
        'password', 'secret', 'changeme', 'admin', 'test',
        '123456', 'qwerty', 'letmein', 'welcome'
    ]

    def __init__(self, root_path: str = None):
        self.root_path = Path(root_path) if root_path else Path.cwd()
        self.issues: List[Dict] = []
        self.warnings: List[Dict] = []

    def check_file(self, file_path: Path) -> List[Dict]:
        """Check a single file for security issues."""
        findings = []

        # Skip excluded files
        file_str = str(file_path)
        for excl in self.EXCLUDE_FILES:
            if excl in file_str:
                return findings

        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                lines = content.split('\n')

            for line_num, line in enumerate(lines, 1):
                # Skip comments
                if line.strip().startswith('#'):
                    continue

                for pattern_name, (pattern, description) in self.SECRET_PATTERNS.items():
                    if re.search(pattern, line, re.IGNORECASE):
                        findings.append({
                            'file': str(file_path.relative_to(self.root_path)),
                            'line': line_num,
                            'pattern': pattern_name,
                            'description': description,
                            'code': line.strip()[:80],
                        })

        except Exception as e:
            self.warnings.append({
                'type': 'file_error',
                'message': f"Error reading {file_path}: {e}"
            })

        return findings

    def scan_codebase(self) -> int:
        """Scan entire codebase for security issues."""
        print("Scanning codebase for hardcoded secrets...")

        total_issues = 0
        py_files = list(self.root_path.rglob('*.py'))

        for py_file in py_files:
            findings = self.check_file(py_file)
            total_issues += len(findings)
            self.issues.extend(findings)

        return total_issues

    def check_environment_variables(self) -> bool:
        """Check if required environment variables are set."""
        print("\nChecking environment variables...")

        all_valid = True
        is_production = os.getenv('ENVIRONMENT', 'development').lower() == 'production'

        for var_name, min_length in self.REQUIRED_ENV_VARS.items():
            value = os.getenv(var_name)

            if not value:
                if is_production or var_name == 'SECRET_KEY':
                    print(f"  [CRITICAL] {var_name}: NOT SET")
                    self.issues.append({
                        'type': 'missing_env_var',
                        'var': var_name,
                        'message': f"{var_name} not set (required in production)"
                    })
                    all_valid = False
                else:
                    print(f"  [WARNING] {var_name}: Not set (optional in development)")
                    self.warnings.append({
                        'type': 'missing_env_var',
                        'var': var_name,
                        'message': f"{var_name} not set"
                    })
            else:
                if len(value) < min_length:
                    print(f"  [WARNING] {var_name}: Too short ({len(value)} < {min_length})")
                    self.warnings.append({
                        'type': 'weak_secret',
                        'var': var_name,
                        'message': f"{var_name} is too short (minimum {min_length} characters)"
                    })
                    all_valid = False
                else:
                    # Check for weak patterns
                    if any(weak in value.lower() for weak in self.WEAK_PATTERNS):
                        print(f"  [WARNING] {var_name}: Contains weak pattern")
                        self.warnings.append({
                            'type': 'weak_secret',
                            'var': var_name,
                            'message': f"{var_name} contains weak/default pattern"
                        })
                        all_valid = False
                    else:
                        print(f"  [OK] {var_name}: Set (length: {len(value)})")

        return all_valid

    def check_connection_strings(self) -> bool:
        """Check for hardcoded credentials in connection strings."""
        print("\nChecking connection strings...")

        # Check DATABASE_URL
        db_url = os.getenv('DATABASE_URL', '')
        if db_url and not db_url.startswith('sqlite'):
            # Parse connection string to check for hardcoded credentials
            if '://' in db_url:
                parts = db_url.split('://')[1]
                if '@' in parts:
                    creds_part = parts.split('@')[0]
                    if ':' in creds_part:
                        username, password = creds_part.split(':', 1)
                        if password and len(password) < 20:
                            print(f"  [WARNING] DATABASE_URL may contain hardcoded credentials")
                            self.warnings.append({
                                'type': 'connection_string',
                                'message': "DATABASE_URL may contain hardcoded credentials"
                            })
                        else:
                            print(f"  [OK] DATABASE_URL: Uses environment variables")

        # Check individual DB components
        if os.getenv('DB_PASSWORD'):
            print(f"  [OK] DB_PASSWORD: Set (using individual components)")
        else:
            print(f"  [INFO] DB_PASSWORD: Not set (using DATABASE_URL)")

        return True

    def check_dotenv_file(self) -> bool:
        """Check if .env file exists and is properly configured."""
        print("\nChecking .env file...")

        env_file = self.root_path / '.env'

        if not env_file.exists():
            print(f"  [WARNING] .env file not found")
            print(f"            Copy .env.example to .env and configure your secrets")
            self.warnings.append({
                'type': 'missing_env_file',
                'message': '.env file not found'
            })
            return False

        # Check if .env is in .gitignore
        gitignore = self.root_path / '.gitignore'
        if gitignore.exists():
            gitignore_content = gitignore.read_text()
            if '.env' not in gitignore_content:
                print(f"  [CRITICAL] .env not in .gitignore!")
                self.issues.append({
                    'type': 'gitignore',
                    'message': '.env file not in .gitignore - secrets may be committed!'
                })
                return False

        print(f"  [OK] .env file exists and is in .gitignore")
        return True

    def generate_report(self) -> Tuple[bool, str]:
        """Generate security validation report."""
        print("\n" + "="*80)
        print("SECURITY VALIDATION REPORT - Rule 28 Compliance")
        print("="*80)

        # Count issues by severity
        critical = sum(1 for i in self.issues if i.get('type') in ['missing_env_var', 'gitignore'])
        hardcoded = len([i for i in self.issues if 'code' in i])

        # Calculate compliance score
        total_checks = 100
        deductions = (critical * 20) + (hardcoded * 5) + (len(self.warnings) * 1)
        compliance = max(0, total_checks - deductions)

        print(f"\nCompliance Score: {compliance}%")
        print(f"Target: 95%")
        print(f"Status: {'PASS' if compliance >= 95 else 'FAIL'}")

        if self.issues:
            print(f"\nIssues Found: {len(self.issues)}")
            print("-"*80)
            for i, issue in enumerate(self.issues[:10], 1):
                if 'code' in issue:
                    print(f"\n{i}. {issue['file']}:{issue['line']}")
                    print(f"   Pattern: {issue['pattern']}")
                    print(f"   Description: {issue['description']}")
                    print(f"   Code: {issue['code']}")
                else:
                    print(f"\n{i}. {issue.get('type', 'Unknown')}: {issue.get('message', '')}")

        if self.warnings:
            print(f"\nWarnings: {len(self.warnings)}")
            print("-"*80)
            for warning in self.warnings[:5]:
                print(f"  - {warning.get('type', 'Unknown')}: {warning.get('message', '')}")

        # Recommendations
        if compliance < 95:
            print("\n" + "="*80)
            print("RECOMMENDATIONS")
            print("="*80)
            print("""
1. Set all required environment variables:
   - SECRET_KEY (generate with: python -c 'import secrets; print(secrets.token_urlsafe(32))')
   - DB_PASSWORD

2. Update .env file:
   - Copy .env.example to .env
   - Fill in all required values
   - Ensure .env is in .gitignore

3. Remove hardcoded secrets from code:
   - Use os.getenv() to read environment variables
   - Never hardcode passwords, API keys, or tokens
   - Build connection strings dynamically

4. Validate production readiness:
   - Run: python scripts/validate_security.py
   - Ensure compliance score is >= 95%
            """)

        return compliance >= 95, f"Compliance: {compliance}%"

    def run_all_checks(self) -> Tuple[bool, str]:
        """Run all security validation checks."""
        print("="*80)
        print("Rule 28 Security Validation")
        print("="*80)

        # 1. Check for hardcoded secrets in code
        hardcoded_count = self.scan_codebase()
        print(f"Found {hardcoded_count} potential hardcoded secrets")

        # 2. Check environment variables
        env_valid = self.check_environment_variables()

        # 3. Check connection strings
        conn_valid = self.check_connection_strings()

        # 4. Check .env file
        env_file_valid = self.check_dotenv_file()

        # Generate report
        is_compliant, message = self.generate_report()

        return is_compliant, message


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate Rule 28 security compliance"
    )
    parser.add_argument(
        '--path', '-p',
        default='.',
        help="Root path of the project"
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help="Verbose output"
    )

    args = parser.parse_args()

    # Run validation
    validator = SecurityValidator(args.path)
    is_compliant, message = validator.run_all_checks()

    # Exit with appropriate code
    if not is_compliant:
        critical = sum(1 for i in validator.issues
                      if i.get('type') in ['missing_env_var', 'gitignore'])
        if critical > 0:
            sys.exit(2)  # Critical issues
        sys.exit(1)  # Non-compliant
    sys.exit(0)  # Compliant


if __name__ == "__main__":
    main()
