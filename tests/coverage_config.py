"""
Coverage Reporting Configuration
Testing Reviewer Audit - Phase 1: Critical Fixes
"""

# Coverage configuration for pytest-cov
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Coverage settings
COVERAGE_CONFIG = {
    "source": ["app"],
    "omit": [
        "*/tests/*",
        "*/test_*",
        "*/__pycache__/*",
        "*/venv/*",
        "*/.venv/*",
        "*/migrations/*",
        "*/alembic/*",
        "*/scripts/*",
        "*/docs/*",
        "*/config/*",
        "*/logging/*",
        "*/docker/*",
        "*/k8s/*",
        "*/terraform/*",
        "*/benchmarks/*",
        "*/coverage/*",
        "*/htmlcov/*",
        "*/logs/*",
        "*/tmp/*",
        "*/temp/*"
    ],
    "branch": True,
    "show_missing": True,
    "skip_covered": False,
    "fail_under": 80,
    "precision": 2,
    "sort": "Cover",
    "exclude_lines": [
        "pragma: no cover",
        "def __repr__",
        "if self.debug:",
        "if settings.DEBUG",
        "raise AssertionError",
        "raise NotImplementedError",
        "if 0:",
        "if __name__ == .__main__.:",
        "class .*\\bProtocol\\):",
        "@(abc\\.)?abstractmethod"
    ]
}

# HTML report configuration
HTML_REPORT_CONFIG = {
    "directory": "htmlcov",
    "title": "AlgoTrading Test Coverage Report",
    "show_contexts": True,
    "skip_empty": True
}

# XML report configuration
XML_REPORT_CONFIG = {
    "output": "coverage.xml",
    "skip_empty": True
}

# JSON report configuration
JSON_REPORT_CONFIG = {
    "output": "coverage.json",
    "skip_empty": True
}

# Terminal report configuration
TERMINAL_REPORT_CONFIG = {
    "show_missing": True,
    "skip_covered": False,
    "precision": 2,
    "sort": "Cover"
}

# Coverage thresholds by module
MODULE_THRESHOLDS = {
    "app.core": 90,
    "app.models": 85,
    "app.services": 80,
    "app.api": 75,
    "app.strategies": 80,
    "app.exceptions": 90,
    "app.middleware": 75,
    "app.database": 80,
    "app.backtesting": 75,
    "app.data": 70
}

# Critical files that must have high coverage
CRITICAL_FILES = [
    "app/core/centralized_config.py",
    "app/core/environment_config.py",
    "app/core/test_config.py",
    "app/exceptions/__init__.py",
    "app/models/signal.py",
    "app/models/portfolio.py",
    "app/models/order.py",
    "app/services/portfolio_service.py",
    "app/services/signal_scorer.py",
    "app/services/paper_trading_service.py"
]

# Files that can have lower coverage
LOW_PRIORITY_FILES = [
    "app/main.py",
    "app/api/__init__.py",
    "app/strategies/__init__.py",
    "app/models/__init__.py",
    "app/services/__init__.py"
]

def get_coverage_command():
    """Get the coverage command for pytest."""
    cmd = [
        "pytest",
        "--cov=app",
        "--cov-branch",
        "--cov-report=html",
        "--cov-report=xml",
        "--cov-report=json",
        "--cov-report=term-missing",
        "--cov-fail-under=80"
    ]
    
    # Add omit patterns
    for omit_pattern in COVERAGE_CONFIG["omit"]:
        cmd.extend(["--cov-omit", omit_pattern])
    
    return cmd

def get_coverage_summary():
    """Get coverage summary information."""
    return {
        "total_coverage_threshold": COVERAGE_CONFIG["fail_under"],
        "module_thresholds": MODULE_THRESHOLDS,
        "critical_files": CRITICAL_FILES,
        "low_priority_files": LOW_PRIORITY_FILES,
        "html_report": HTML_REPORT_CONFIG["directory"],
        "xml_report": XML_REPORT_CONFIG["output"],
        "json_report": JSON_REPORT_CONFIG["output"]
    }

if __name__ == "__main__":
    print("Coverage Configuration:")
    print(f"Command: {' '.join(get_coverage_command())}")
    print(f"Summary: {get_coverage_summary()}")
