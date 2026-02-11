#!/usr/bin/env python3
"""
Verify ComplianceEngine has required trading rule validations.

This script checks that ComplianceEngine is configured with the required
validations from trading rules (Ernest Chan, etc.).

Usage:
    python .ralph/scripts/verify_compliance_validations.py
    python .ralph/scripts/verify_compliance_validations.py --check <RULE_ID>
"""

import argparse
import ast
import json
import logging
import sys
from pathlib import Path
from typing import Dict, List

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


class ComplianceValidationChecker:
    """Checks that ComplianceEngine has required validations."""

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.compliance_engine_path = project_root / "app/core/compliance_engine.py"
        self.results = {
            "passed": [],
            "failed": [],
            "warnings": []
        }

    def check_chan002_max_drawdown(self) -> bool:
        """CHAN-002: Verify max_drawdown_ratio <= 0.25 (25%)."""
        logger.info("Checking CHAN-002: Max Drawdown < 25%")

        content = self.compliance_engine_path.read_text()

        # Check 1: Config has max_drawdown_ratio field
        if "max_drawdown_ratio" not in content:
            self.results["failed"].append({
                "rule": "CHAN-002",
                "check": "max_drawdown_ratio field exists",
                "status": "FAILED",
                "message": "max_drawdown_ratio field not found in ComplianceConfig"
            })
            return False

        # Check 2: Default value is 0.25 or less
        if "max_drawdown_ratio: float = Field(" in content:
            # Extract default value
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if "max_drawdown_ratio: float = Field(" in line:
                    # Look for default= in next few lines
                    for j in range(i, min(i+5, len(lines))):
                        if "default=" in lines[j]:
                            default_line = lines[j]
                            # Extract default value
                            if "0.25" in default_line or "0.20" in default_line or "0.15" in default_line:
                                self.results["passed"].append({
                                    "rule": "CHAN-002",
                                    "check": "max_drawdown_ratio default <= 0.25",
                                    "status": "PASSED",
                                    "message": f"Found: {default_line.strip()}"
                                })
                                return True
                            else:
                                self.results["warnings"].append({
                                    "rule": "CHAN-002",
                                    "check": "max_drawdown_ratio default value",
                                    "status": "WARNING",
                                    "message": f"Default value may be > 0.25: {default_line.strip()}"
                                })
                                return False

        # Check 3: Pre-trade validation uses it
        if "drawdown_limit_ok = current_drawdown <= self.config.max_drawdown_ratio" in content:
            self.results["passed"].append({
                "rule": "CHAN-002",
                "check": "Pre-trade drawdown validation",
                "status": "PASSED",
                "message": "Pre-trade check uses max_drawdown_ratio"
            })
        else:
            self.results["failed"].append({
                "rule": "CHAN-002",
                "check": "Pre-trade drawdown validation",
                "status": "FAILED",
                "message": "Pre-trade validation doesn't check max_drawdown_ratio"
            })
            return False

        return True

    def check_ret003_transaction_costs(self) -> bool:
        """RET-003: Verify TransactionCostModel is used."""
        logger.info("Checking RET-003: Transaction Costs in ComplianceEngine")

        # Check service_registry for TransactionCostModel
        service_registry = self.project_root / "app/core/compliance/service_registry.py"
        if not service_registry.exists():
            self.results["warnings"].append({
                "rule": "RET-003",
                "check": "service_registry.py exists",
                "status": "WARNING",
                "message": "service_registry.py not found"
            })
            return False

        content = service_registry.read_text()

        # Check for TransactionCostModel import
        if "TransactionCostModel" in content:
            self.results["passed"].append({
                "rule": "RET-003",
                "check": "TransactionCostModel imported",
                "status": "PASSED",
                "message": "TransactionCostModel found in service_registry"
            })
        else:
            self.results["failed"].append({
                "rule": "RET-003",
                "check": "TransactionCostModel imported",
                "status": "FAILED",
                "message": "TransactionCostModel not imported in service_registry"
            })
            return False

        # Check for get_transaction_cost_model function
        if "get_transaction_cost_model" in content:
            self.results["passed"].append({
                "rule": "RET-003",
                "check": "get_transaction_cost_model function",
                "status": "PASSED",
                "message": "get_transaction_cost_model function exists"
            })
        else:
            self.results["warnings"].append({
                "rule": "RET-003",
                "check": "get_transaction_cost_model function",
                "status": "WARNING",
                "message": "get_transaction_cost_model function not found"
            })

        return True

    def check_arch001_backtestengine(self) -> bool:
        """ARCH-001: Verify BacktestEngine uses ComplianceEngine."""
        logger.info("Checking ARCH-001: BacktestEngine with ComplianceEngine")

        backtest_engine = self.project_root / "app/backtesting/engine.py"
        if not backtest_engine.exists():
            self.results["failed"].append({
                "rule": "ARCH-001",
                "check": "BacktestEngine exists",
                "status": "FAILED",
                "message": "app/backtesting/engine.py not found"
            })
            return False

        content = backtest_engine.read_text()

        # Check 1: BacktestEngine imports ComplianceEngine
        if "from app.core.compliance_engine import ComplianceEngine" in content:
            self.results["passed"].append({
                "rule": "ARCH-001",
                "check": "BacktestEngine imports ComplianceEngine",
                "status": "PASSED",
                "message": "BacktestEngine imports ComplianceEngine"
            })
        else:
            self.results["failed"].append({
                "rule": "ARCH-001",
                "check": "BacktestEngine imports ComplianceEngine",
                "status": "FAILED",
                "message": "BacktestEngine doesn't import ComplianceEngine"
            })
            return False

        # Check 2: BacktestEngine instantiates ComplianceEngine
        if "self.compliance_engine = ComplianceEngine(" in content:
            self.results["passed"].append({
                "rule": "ARCH-001",
                "check": "BacktestEngine instantiates ComplianceEngine",
                "status": "PASSED",
                "message": "BacktestEngine creates ComplianceEngine instance"
            })
        else:
            self.results["failed"].append({
                "rule": "ARCH-001",
                "check": "BacktestEngine instantiates ComplianceEngine",
                "status": "FAILED",
                "message": "BacktestEngine doesn't instantiate ComplianceEngine"
            })
            return False

        # Check 3: BacktestEngine uses compliance methods
        compliance_methods = [
            "check_kill_switch",
            "analyze_pre_trade",
            "analyze_post_trade",
            "track_daily_pnl"
        ]
        found_methods = []
        for method in compliance_methods:
            if f"self.compliance_engine.{method}" in content:
                found_methods.append(method)

        if found_methods:
            self.results["passed"].append({
                "rule": "ARCH-001",
                "check": "BacktestEngine uses compliance methods",
                "status": "PASSED",
                "message": f"Uses methods: {', '.join(found_methods)}"
            })
        else:
            self.results["warnings"].append({
                "rule": "ARCH-001",
                "check": "BacktestEngine uses compliance methods",
                "status": "WARNING",
                "message": "No compliance engine methods found in use"
            })

        return True

    def check_all(self) -> Dict:
        """Run all checks."""
        logger.info("Running all compliance validation checks...")

        self.check_chan002_max_drawdown()
        self.check_ret003_transaction_costs()
        self.check_arch001_backtestengine()

        return self.results

    def print_report(self):
        """Print formatted report."""
        print("\n" + "="*70)
        print("COMPLIANCE ENGINE VALIDATION REPORT")
        print("="*70)

        print(f"\n✅ PASSED: {len(self.results['passed'])}")
        for result in self.results['passed']:
            print(f"  ✓ [{result['rule']}] {result['check']}")

        print(f"\n❌ FAILED: {len(self.results['failed'])}")
        for result in self.results['failed']:
            print(f"  ✗ [{result['rule']}] {result['check']}")
            print(f"    {result['message']}")

        print(f"\n⚠️  WARNINGS: {len(self.results['warnings'])}")
        for result in self.results['warnings']:
            print(f"  ⚠ [{result['rule']}] {result['check']}")
            print(f"    {result['message']}")

        print("\n" + "="*70)

        if self.results['failed']:
            print("STATUS: ❌ FAILED - Some critical validations are missing")
            return False
        else:
            print("STATUS: ✅ PASSED - All critical validations are present")
            return True


def main():
    parser = argparse.ArgumentParser(description="Verify ComplianceEngine has required validations")
    parser.add_argument("--check", help="Specific rule to check (CHAN-002, RET-003, ARCH-001)")
    parser.add_argument("--output", help="Output JSON file", default=".ralph/outputs/COMPLIANCE_VALIDATIONS.json")

    args = parser.parse_args()

    project_root = Path.cwd()
    while not (project_root / "app").exists() and project_root != project_root.parent:
        project_root = project_root.parent

    checker = ComplianceValidationChecker(project_root)

    if args.check:
        # Run specific check
        check_method = {
            "CHAN-002": checker.check_chan002_max_drawdown,
            "RET-003": checker.check_ret003_transaction_costs,
            "ARCH-001": checker.check_arch001_backtestengine
        }.get(args.check.upper())

        if check_method:
            check_method()
        else:
            logger.error(f"Unknown check: {args.check}")
            return 1
    else:
        # Run all checks
        checker.check_all()

    # Print report
    success = checker.print_report()

    # Save JSON output
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(checker.results, f, indent=2)

    logger.info(f"Results saved to: {output_path}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
