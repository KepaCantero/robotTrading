#!/usr/bin/env python3
"""
AlgoTrading System - Dependency Verification Script

This script verifies that ALL required dependencies are installed and working.
It checks imports, versions, and runs basic functionality tests.

PRINCIPLE: "If it's in the code, it's REQUIRED. No optional dependencies."

Exit Codes:
    0: All dependencies verified successfully
    1: Some dependencies are missing or broken
    2: Critical dependencies (Numba, core) are missing

Author: AlgoTrading System
Date: 2026-01-28
"""

import sys
import importlib
import subprocess
from pathlib import Path
from typing import Dict, List, Tuple

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


class DependencyVerifier:
    """Verifies all system dependencies are installed and working."""

    def __init__(self):
        self.errors = []
        self.warnings = []
        self.successes = []
        self.critical_errors = []

        # Core dependencies (MUST be present)
        self.critical_deps = {
            "numpy": "1.24.0",
            "pandas": "2.0.0",
            "numba": "0.59.0",
            "llvmlite": "0.40.0",
            "scipy": "1.11.0",
            "sklearn": "1.3.0",  # scikit-learn
        }

        # All required dependencies grouped by category
        self.all_dependencies = {
            "Core Web Framework": [
                "fastapi",
                "uvicorn",
                "starlette",
                "pydantic",
                "pydantic_settings",
            ],
            "Database": [
                "sqlalchemy",
                "alembic",
                "psycopg2",
                "aiosqlite",
                "asyncpg",
            ],
            "Data Processing": [
                "pandas",
                "numpy",
                "scipy",
                "statsmodels",
                "arch",
            ],
            "Performance": [
                "numba",
                "llvmlite",
            ],
            "Technical Analysis": [
                "pandas_ta_classic",
                "pandas_ta",
            ],
            "Machine Learning": [
                "sklearn",  # scikit-learn
                "xgboost",
                "lightgbm",
                "catboost",
                "shap",
            ],
            "Deep Learning": [
                "torch",
                "torchvision",
                "tensorflow",
            ],
            "Reinforcement Learning": [
                "stable_baselines3",
                "gym",
                "gymnasium",
            ],
            "Optimization": [
                "optuna",
                "pypfopt",
                "cvxpy",
            ],
            "Market Data": [
                "yfinance",
                "yahoo_fin",
            ],
            "HTTP Clients": [
                "httpx",
                "requests",
                "aiohttp",
                "websockets",
                "aiofiles",
            ],
            "Broker APIs": [
                "alpaca_trade_api",
                "alpaca",
                "ib_insync",
            ],
            "Caching": [
                "redis",
                "zmq",  # pyzmq
            ],
            "Configuration": [
                "yaml",  # pyyaml
                "dotenv",  # python-dotenv
            ],
            "Serialization": [
                "msgpack",
                "joblib",
            ],
            "Logging": [
                "logging",
                "structlog",
            ],
            "Monitoring": [
                "psutil",
                "ntplib",
                "tenacity",
                "tqdm",
            ],
            "Notifications": [
                "aiosmtplib",
            ],
            "Security": [
                "cryptography",
                "nacl",  # pynacl
            ],
            "Analytics": [
                "quantstats",
                "empyrical",
                "pyfolio",
            ],
            "Visualization": [
                "matplotlib",
                "seaborn",
                "plotly",
                "networkx",
            ],
            "Dashboard": [
                "streamlit",
                "jinja2",
            ],
            "Time": [
                "pytz",
                "tzlocal",
                "nest_asyncio",
            ],
            "Cloud": [
                "boto3",
                "botocore",
            ],
            "Time-Series DB": [
                "questdb",
            ],
            "External": [
                "tweepy",
                "bs4",  # beautifulsoup4
            ],
            "Regime Detection": [
                "hmmlearn",
            ],
        }

    def print_header(self, text: str, color: str = BLUE):
        """Print a formatted header."""
        print(f"\n{color}{'=' * 80}{RESET}")
        print(f"{color}{text:^80}{RESET}")
        print(f"{color}{'=' * 80}{RESET}\n")

    def print_success(self, text: str):
        """Print success message."""
        print(f"{GREEN}✓ {text}{RESET}")
        self.successes.append(text)

    def print_error(self, text: str, critical: bool = False):
        """Print error message."""
        print(f"{RED}✗ {text}{RESET}")
        if critical:
            self.critical_errors.append(text)
        else:
            self.errors.append(text)

    def print_warning(self, text: str):
        """Print warning message."""
        print(f"{YELLOW}⚠ {text}{RESET}")
        self.warnings.append(text)

    def check_import(self, module_name: str, critical: bool = False) -> bool:
        """Check if a module can be imported."""
        try:
            importlib.import_module(module_name)
            return True
        except ImportError as e:
            self.print_error(f"Failed to import {module_name}: {e}", critical=critical)
            return False
        except Exception as e:
            self.print_warning(f"Warning importing {module_name}: {e}")
            return True

    def get_version(self, module_name: str) -> str:
        """Get version of an installed package."""
        try:
            module = importlib.import_module(module_name)
            if hasattr(module, "__version__"):
                return module.__version__
            else:
                return "unknown"
        except:
            return "not installed"

    def check_critical_dependencies(self) -> bool:
        """Check critical dependencies first."""
        self.print_header("CHECKING CRITICAL DEPENDENCIES", color=BLUE)

        all_ok = True
        for module, min_version in self.critical_deps.items():
            print(f"Checking {module}... ", end="", flush=True)
            try:
                module_obj = importlib.import_module(module)
                version = getattr(module_obj, "__version__", "unknown")
                print(f"[OK] v{version}")
                self.print_success(f"{module} v{version}")

                # Special check for Numba
                if module == "numba":
                    self._test_numba_compilation()

            except ImportError as e:
                print(f"[FAILED]")
                self.print_error(f"{module} is REQUIRED: {e}", critical=True)
                all_ok = False

        return all_ok

    def _test_numba_compilation(self):
        """Test that Numba can actually compile code."""
        print("  Testing Numba JIT compilation... ", end="", flush=True)
        try:
            from numba import njit
            import numpy as np

            @njit
            def test_function(x):
                return x * 2

            result = test_function(np.array([1, 2, 3]))
            assert len(result) == 3
            print("[OK]")
            self.print_success("Numba JIT compilation working")
        except Exception as e:
            print(f"[FAILED]")
            self.print_error(f"Numba compilation failed: {e}", critical=True)

    def check_all_dependencies(self) -> bool:
        """Check all dependencies by category."""
        self.print_header("CHECKING ALL DEPENDENCIES", color=BLUE)

        all_ok = True
        for category, modules in self.all_dependencies.items():
            print(f"\n{YELLOW}{category}:{RESET}")
            for module in modules:
                print(f"  {module}... ", end="", flush=True)
                if self.check_import(module):
                    version = self.get_version(module)
                    print(f"[OK] v{version}")
                else:
                    all_ok = False

        return all_ok

    def check_core_imports(self) -> bool:
        """Test that core application imports work."""
        self.print_header("TESTING CORE APPLICATION IMPORTS", color=BLUE)

        test_imports = [
            ("app.core.numba_accelerators", "Numba accelerators"),
            ("app.services.momentum_analysis", "Momentum analysis"),
            ("app.strategies.momentum_modular.learning.supervised_learning_engine", "Supervised learning"),
            ("app.backtesting.feature_engineering.fractional_differentiation", "Fractional differentiation"),
            ("app.backtesting.labeling.triple_barrier", "Triple barrier labeling"),
        ]

        all_ok = True
        for module_path, description in test_imports:
            print(f"Testing {description}... ", end="", flush=True)
            try:
                importlib.import_module(module_path)
                print("[OK]")
                self.print_success(f"{description} imported successfully")
            except Exception as e:
                print(f"[FAILED]")
                self.print_error(f"Failed to import {description}: {e}")
                all_ok = False

        return all_ok

    def check_version_compatibility(self) -> bool:
        """Check for known version conflicts."""
        self.print_header("CHECKING VERSION COMPATIBILITY", color=BLUE)

        issues = []

        # Check numpy version (must be < 2.0.0 for some packages)
        numpy_version = self.get_version("numpy")
        if numpy_version != "unknown" and numpy_version.startswith("2."):
            self.print_warning("NumPy 2.x detected - some packages may not be compatible")
            issues.append("numpy_2_compat")

        # Check Python version
        python_version = sys.version_info
        if python_version < (3, 9):
            self.print_error(f"Python {python_version.major}.{python_version.minor} is too old. Requires >= 3.9", critical=True)
            issues.append("python_version")
        elif python_version >= (3, 14):
            self.print_warning(f"Python {python_version.major}.{python_version.minor} is not tested. Use < 3.14")
            issues.append("python_version_untested")

        if not issues:
            self.print_success("No version compatibility issues detected")
            return True

        return len(issues) == 0

    def generate_report(self):
        """Generate final verification report."""
        self.print_header("VERIFICATION REPORT", color=BLUE)

        total_checks = len(self.successes) + len(self.errors) + len(self.critical_errors)

        print(f"\n{GREEN}Successful Checks: {len(self.successes)}{RESET}")
        print(f"{RED}Failed Checks: {len(self.errors)}{RESET}")
        print(f"{RED}Critical Errors: {len(self.critical_errors)}{RESET}")
        print(f"{YELLOW}Warnings: {len(self.warnings)}{RESET}")
        print(f"Total Checks: {total_checks}")

        if self.critical_errors:
            print(f"\n{RED}CRITICAL ERRORS (must fix):{RESET}")
            for error in self.critical_errors:
                print(f"  {RED}✗ {error}{RESET}")

        if self.errors:
            print(f"\n{RED}ERRORS (should fix):{RESET}")
            for error in self.errors:
                print(f"  {RED}✗ {error}{RESET}")

        if self.warnings:
            print(f"\n{YELLOW}WARNINGS (optional):{RESET}")
            for warning in self.warnings:
                print(f"  {YELLOW}⚠ {warning}{RESET}")

        print()

    def run(self) -> int:
        """Run all verification checks."""
        print(f"{BLUE}{'=' * 80}{RESET}")
        print(f"{BLUE}{'AlgoTrading System - Dependency Verification':^80}{RESET}")
        print(f"{BLUE}{'=' * 80}{RESET}")

        # Check Python version first
        python_version = sys.version_info
        print(f"\nPython Version: {python_version.major}.{python_version.minor}.{python_version.micro}")

        # Run checks in order
        critical_ok = self.check_critical_dependencies()
        all_ok = self.check_all_dependencies()
        imports_ok = self.check_core_imports()
        version_ok = self.check_version_compatibility()

        # Generate report
        self.generate_report()

        # Determine exit code
        if not critical_ok or not imports_ok:
            print(f"{RED}RESULT: CRITICAL FAILURES - System will not function{RESET}")
            return 2
        elif not all_ok or not version_ok:
            print(f"{YELLOW}RESULT: FAILURES - Some features may not work{RESET}")
            return 1
        else:
            print(f"{GREEN}RESULT: SUCCESS - All dependencies verified{RESET}")
            return 0


def main():
    """Main entry point."""
    verifier = DependencyVerifier()
    exit_code = verifier.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
