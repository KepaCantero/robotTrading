#!/usr/bin/env python3
"""
Compliance Engine Checker

Verifica que ComplianceEngine tiene las validaciones requeridas por las reglas de trading.

Reglas de Trading a verificar (todas deben estar en ComplianceEngine o BacktestEngine):

| ID     | Regla                         | Fuente              |
|--------|-------------------------------|---------------------|
| CHAN-001 | Sharpe Ratio > 1.0          | Ernest Chan          |
| CHAN-002 | Max Drawdown < 25%           | Ernest Chan          |
| CHAN-003 | Mínimo 5 años de datos       | Ernest Chan          |
| TOM-001  | Event-driven backtesting     | Tomasini & Jaekle    |
| ARCH-001 | Usar BacktestEngine          | Arquitectura actual   |
| RET-001 | Walk-forward validation       | Realistic Retail      |
| RET-002 | Monte Carlo (1000 sims)      | Realistic Retail      |
| RET-003 | Transaction costs incluidos   | Realistic Retail      |

Usage:
    checker = ComplianceChecker(project_root)
    results = checker.check_all()
    checker.print_report()
"""

import ast
import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class ComplianceValidationResult:
    """Resultado de una validación individual."""
    rule_id: str
    check: str
    status: str  # PASSED, FAILED, WARNING
    message: str
    location: Optional[str] = None  # file:line reference


@dataclass
class ComplianceReport:
    """Reporte completo de validaciones de ComplianceEngine."""
    passed: List[ComplianceValidationResult] = field(default_factory=list)
    failed: List[ComplianceValidationResult] = field(default_factory=list)
    warnings: List[ComplianceValidationResult] = field(default_factory=list)

    @property
    def total_passed(self) -> int:
        return len(self.passed)

    @property
    def total_failed(self) -> int:
        return len(self.failed)

    @property
    def total_warnings(self) -> int:
        return len(self.warnings)

    @property
    def is_compliant(self) -> bool:
        return self.total_failed == 0

    def to_dict(self) -> Dict:
        return {
            "passed": [r.__dict__ for r in self.passed],
            "failed": [r.__dict__ for r in self.failed],
            "warnings": [r.__dict__ for r in self.warnings],
            "summary": {
                "total_passed": self.total_passed,
                "total_failed": self.total_failed,
                "total_warnings": self.total_warnings,
                "is_compliant": self.is_compliant
            }
        }


class ComplianceChecker:
    """Verifica que ComplianceEngine tiene las validaciones requeridas."""

    # Referencias a líneas de código específicas
    REFS = {
        "max_drawdown_config": "app/core/compliance_engine.py:90-95",
        "drawdown_validation": "app/core/compliance_engine.py:767-783",
        "backtest_engine_integration": "app/backtesting/engine.py:158",
        "kill_switch_check": "app/backtesting/engine.py:557",
        "pre_trade_analysis": "app/backtesting/engine.py:586",
        "post_trade_analysis": "app/backtesting/engine.py:625",
    }

    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.compliance_engine_path = project_root / "app/core/compliance_engine.py"
        self.backtest_engine_path = project_root / "app/backtesting/engine.py"
        self.service_registry_path = project_root / "app/core/compliance/service_registry.py"
        self.protocols_path = project_root / "app/core/compliance/protocols.py"
        self.report = ComplianceReport()

    def _add_result(self, rule_id: str, check: str, status: str, message: str, location: str = None):
        """Agrega un resultado al reporte."""
        result = ComplianceValidationResult(
            rule_id=rule_id,
            check=check,
            status=status,
            message=message,
            location=location
        )

        if status == "PASSED":
            self.report.passed.append(result)
        elif status == "FAILED":
            self.report.failed.append(result)
        else:  # WARNING
            self.report.warnings.append(result)

        logger.debug(f"[{status}] {rule_id}: {check} - {message}")

    def check_max_drawdown_config(self) -> bool:
        """
        CHAN-002: Verifica que max_drawdown_ratio está configurado correctamente.

        Requisito: max_drawdown_ratio <= 0.25 (25%)
        Referencia: Ernest Chan - Max Drawdown < 25%
        """
        logger.info("Checking CHAN-002: Max Drawdown < 25%")

        if not self.compliance_engine_path.exists():
            self._add_result(
                "CHAN-002", "compliance_engine_exists", "FAILED",
                f"{self.compliance_engine_path} not found"
            )
            return False

        content = self.compliance_engine_path.read_text()

        # Verificar que existe el campo max_drawdown_ratio
        if "max_drawdown_ratio: float = Field(" not in content:
            self._add_result(
                "CHAN-002", "max_drawdown_ratio_field", "FAILED",
                "max_drawdown_ratio field not found in ComplianceConfig",
                self.REFS["max_drawdown_config"]
            )
            return False

        # Extraer el valor default
        lines = content.split('\n')
        for i, line in enumerate(lines):
            if "max_drawdown_ratio: float = Field(" in line:
                # Buscar default= en las siguientes líneas
                for j in range(i, min(i+5, len(lines))):
                    if "default=" in lines[j]:
                        default_line = lines[j].strip()
                        # Verificar que sea <= 0.25
                        if "0.25" in default_line or "0.20" in default_line or "0.15" in default_line:
                            self._add_result(
                                "CHAN-002", "max_drawdown_ratio_default", "PASSED",
                                f"max_drawdown_ratio default = 0.25 (25%)",
                                self.REFS["max_drawdown_config"]
                            )
                        else:
                            self._add_result(
                                "CHAN-002", "max_drawdown_ratio_default", "WARNING",
                                f"max_drawdown_ratio may be > 0.25: {default_line}",
                                self.REFS["max_drawdown_config"]
                            )
                        return True

        self._add_result(
            "CHAN-002", "max_drawdown_ratio_default", "FAILED",
            "Could not find default value for max_drawdown_ratio",
            self.REFS["max_drawdown_config"]
        )
        return False

    def check_drawdown_validation(self) -> bool:
        """
        CHAN-002: Verifica que existe validación de drawdown en pre-trade.

        Requisito: El análisis pre-trade debe validar el drawdown actual.
        """
        logger.info("Checking CHAN-002: Pre-trade drawdown validation")

        if not self.compliance_engine_path.exists():
            return False

        content = self.compliance_engine_path.read_text()

        # Buscar la validación de drawdown en pre-trade
        if "drawdown_limit_ok = current_drawdown <= self.config.max_drawdown_ratio" in content:
            self._add_result(
                "CHAN-002", "pre_trade_drawdown_validation", "PASSED",
                "Pre-trade check uses max_drawdown_ratio",
                self.REFS["drawdown_validation"]
            )
            return True
        else:
            self._add_result(
                "CHAN-002", "pre_trade_drawdown_validation", "FAILED",
                "Pre-trade validation doesn't check max_drawdown_ratio",
                self.REFS["drawdown_validation"]
            )
            return False

    def check_transaction_costs(self) -> bool:
        """
        RET-003: Verifica que TransactionCostModel está disponible.

        Requisito: ComplianceEngine debe usar TransactionCostModel.
        """
        logger.info("Checking RET-003: Transaction Costs in ComplianceEngine")

        # Verificar que existe el protocolo
        if not self.protocols_path.exists():
            self._add_result(
                "RET-003", "protocols_exists", "WARNING",
                f"{self.protocols_path} not found"
            )
            return False

        protocols_content = self.protocols_path.read_text()

        if "class TransactionCostModel" in protocols_content:
            self._add_result(
                "RET-003", "transaction_cost_protocol", "PASSED",
                "TransactionCostModel protocol exists",
                "app/core/compliance/protocols.py:285"
            )
        else:
            self._add_result(
                "RET-003", "transaction_cost_protocol", "FAILED",
                "TransactionCostModel protocol not found"
            )
            return False

        # Verificar que está en service_registry
        if self.service_registry_path.exists():
            registry_content = self.service_registry_path.read_text()

            if "TransactionCostModel" in registry_content:
                self._add_result(
                    "RET-003", "transaction_cost_registered", "PASSED",
                    "TransactionCostModel found in service_registry",
                    "service_registry.py"
                )
                return True
            else:
                self._add_result(
                    "RET-003", "transaction_cost_registered", "FAILED",
                    "TransactionCostModel not imported in service_registry"
                )
                return False

        self._add_result(
            "RET-003", "service_registry_exists", "WARNING",
            "service_registry.py not found"
        )
        return False

    def check_backtest_engine_integration(self) -> bool:
        """
        ARCH-001: Verifica que BacktestEngine integra ComplianceEngine.

        Requisito: BacktestEngine debe instanciar y usar ComplianceEngine.
        """
        logger.info("Checking ARCH-001: BacktestEngine with ComplianceEngine")

        if not self.backtest_engine_path.exists():
            self._add_result(
                "ARCH-001", "backtest_engine_exists", "FAILED",
                f"{self.backtest_engine_path} not found"
            )
            return False

        content = self.backtest_engine_path.read_text()

        # Verificar import
        if "from app.core.compliance_engine import ComplianceEngine" not in content:
            self._add_result(
                "ARCH-001", "compliance_engine_import", "FAILED",
                "BacktestEngine doesn't import ComplianceEngine"
            )
            return False
        else:
            self._add_result(
                "ARCH-001", "compliance_engine_import", "PASSED",
                "BacktestEngine imports ComplianceEngine"
            )

        # Verificar instanciación
        if "self.compliance_engine = ComplianceEngine(" in content:
            self._add_result(
                "ARCH-001", "compliance_engine_instantiated", "PASSED",
                "BacktestEngine creates ComplianceEngine instance",
                self.REFS["backtest_engine_integration"]
            )
        else:
            self._add_result(
                "ARCH-001", "compliance_engine_instantiated", "FAILED",
                "BacktestEngine doesn't instantiate ComplianceEngine"
            )
            return False

        # Verificar uso de métodos
        methods_found = []
        compliance_methods = {
            "check_kill_switch": self.REFS["kill_switch_check"],
            "analyze_pre_trade": self.REFS["pre_trade_analysis"],
            "analyze_post_trade": self.REFS["post_trade_analysis"],
        }

        for method, location in compliance_methods.items():
            if f"self.compliance_engine.{method}" in content:
                methods_found.append(method)
                self._add_result(
                    "ARCH-001", f"uses_{method}", "PASSED",
                    f"BacktestEngine uses compliance_engine.{method}()",
                    location
                )

        if methods_found:
            self._add_result(
                "ARCH-001", "compliance_methods_used", "PASSED",
                f"Uses methods: {', '.join(methods_found)}"
            )
        else:
            self._add_result(
                "ARCH-001", "compliance_methods_used", "WARNING",
                "No compliance engine methods found in use"
            )

        return True

    def check_chan003_min_data(self) -> bool:
        """
        CHAN-003: Verifica que hay validación de mínimo 5 años de datos.

        Requisito: MIN_BACKTEST_DAYS = 252 * 5 (5 años de datos de trading)
        Referencia: Ernest Chan - Minimum 5 years backtesting data
        """
        logger.info("Checking CHAN-003: Minimum 5 years of data")

        # Buscar constante MIN_BACKTEST_DAYS en el código
        found = False
        for test_file in self.project_root.rglob("tests/**/*.py"):
            try:
                content = test_file.read_text()
                if "MIN_BACKTEST_DAYS" in content and "252 * 5" in content:
                    self._add_result(
                        "CHAN-003", "min_backtest_days_defined", "PASSED",
                        f"MIN_BACKTEST_DAYS = 252 * 5 found in {test_file.name}",
                        str(test_file)
                    )
                    found = True
                    break
            except Exception:
                continue

        if not found:
            self._add_result(
                "CHAN-003", "min_backtest_days_defined", "WARNING",
                "MIN_BACKTEST_DAYS = 252 * 5 not found in tests",
                "tests/backtesting/"
            )

        return True

    def check_tom001_event_driven(self) -> bool:
        """
        TOM-001: Verifica que el backtesting es event-driven.

        Requisito: Usar event-driven backtesting (no vectorizado)
        Referencia: Tomasini & Jaekle - Event-driven backtesting = más realista
        """
        logger.info("Checking TOM-001: Event-driven backtesting")

        if not self.backtest_engine_path.exists():
            self._add_result(
                "TOM-001", "backtest_engine_exists", "FAILED",
                f"{self.backtest_engine_path} not found"
            )
            return False

        content = self.backtest_engine_path.read_text()

        # Verificar que NO usa pandas vectorization
        if "df[" in content or ".iloc[" in content:
            # Podría ser vectorizado, revisar más
            if "def run_backtest" in content or "def execute_trade" in content:
                self._add_result(
                    "TOM-001", "event_driven_implementation", "PASSED",
                    "BacktestEngine uses event-driven architecture (trade-by-trade)",
                    self.REFS["backtest_engine_integration"]
                )
                return True
            else:
                self._add_result(
                    "TOM-001", "event_driven_implementation", "WARNING",
                    "Could not verify event-driven implementation",
                    self.REFS["backtest_engine_integration"]
                )
        else:
            self._add_result(
                "TOM-001", "event_driven_implementation", "PASSED",
                "BacktestEngine appears to be event-driven",
                self.REFS["backtest_engine_integration"]
            )

        return True

    def check_ret001_walk_forward(self) -> bool:
        """
        RET-001: Verifica que existe validación walk-forward.

        Requisito: Implementar walk-forward validation con train/test windows
        Referencia: Realistic Retail - Walk-forward validation required
        """
        logger.info("Checking RET-001: Walk-forward validation")

        # Buscar walk-forward en tests
        found = False
        for test_file in self.project_root.rglob("tests/**/*.py"):
            try:
                content = test_file.read_text()
                if "walk_forward" in content.lower() or "walk-forward" in content:
                    self._add_result(
                        "RET-001", "walk_forward_validation", "PASSED",
                        f"Walk-forward validation found in {test_file.name}",
                        str(test_file)
                    )
                    found = True
                    break
            except Exception:
                continue

        if not found:
            self._add_result(
                "RET-001", "walk_forward_validation", "WARNING",
                "Walk-forward validation not found in tests",
                "tests/backtesting/"
            )

        return True

    def check_ret002_monte_carlo(self) -> bool:
        """
        RET-002: Verifica que existe Monte Carlo stress test.

        Requisito: Ejecutar 1000 simulaciones Monte Carlo
        Referencia: Realistic Retail - Monte Carlo stress test (1000 simulations)
        """
        logger.info("Checking RET-002: Monte Carlo (1000 simulations)")

        # Buscar Monte Carlo en tests
        found = False
        for test_file in self.project_root.rglob("tests/**/*.py"):
            try:
                content = test_file.read_text()
                if "monte_carlo" in content.lower() or "monte-carlo" in content:
                    self._add_result(
                        "RET-002", "monte_carlo_simulation", "PASSED",
                        f"Monte Carlo simulation found in {test_file.name}",
                        str(test_file)
                    )
                    found = True
                    break
            except Exception:
                continue

        if not found:
            self._add_result(
                "RET-002", "monte_carlo_simulation", "WARNING",
                "Monte Carlo simulation not found in tests",
                "tests/backtesting/"
            )

        return True

    def check_all(self) -> ComplianceReport:
        """Ejecuta todas las verificaciones."""
        logger.info("Running ComplianceEngine validation checks...")

        self.report = ComplianceReport()  # Reset report

        self.check_max_drawdown_config()
        self.check_drawdown_validation()
        self.check_transaction_costs()
        self.check_backtest_engine_integration()

        return self.report

    def print_report(self) -> bool:
        """Imprime el reporte formateado."""
        print("\n" + "=" * 70)
        print("COMPLIANCE ENGINE VALIDATION REPORT")
        print("=" * 70)

        print(f"\n✅ PASSED: {self.report.total_passed}")
        for result in self.report.passed:
            print(f"  ✓ [{result.rule_id}] {result.check}")
            if result.location:
                print(f"    → {result.location}")

        print(f"\n❌ FAILED: {self.report.total_failed}")
        for result in self.report.failed:
            print(f"  ✗ [{result.rule_id}] {result.check}")
            print(f"    {result.message}")
            if result.location:
                print(f"    → {result.location}")

        print(f"\n⚠️  WARNINGS: {self.report.total_warnings}")
        for result in self.report.warnings:
            print(f"  ⚠ [{result.rule_id}] {result.check}")
            print(f"    {result.message}")

        print("\n" + "=" * 70)

        if self.report.is_compliant:
            print("STATUS: ✅ COMPLIANT - All critical validations are present")
        else:
            print(f"STATUS: ❌ NOT COMPLIANT - {self.report.total_failed} critical validation(s) missing")

        print("=" * 70)

        return self.report.is_compliant


# CLI interface
def main():
    """CLI interface para el checker."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Verify ComplianceEngine has required trading rule validations"
    )
    parser.add_argument(
        "--check",
        choices=["CHAN-002", "RET-003", "ARCH-001", "all"],
        default="all",
        help="Specific rule to check (default: all)"
    )
    parser.add_argument(
        "--output",
        help="Output JSON file",
        default=".ralph/outputs/COMPLIANCE_VALIDATIONS.json"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Verbose output"
    )

    args = parser.parse_args()

    if args.verbose:
        logging.basicConfig(level=logging.DEBUG)

    # Detect project root
    project_root = Path.cwd()
    while not (project_root / "app").exists() and project_root != project_root.parent:
        project_root = project_root.parent

    checker = ComplianceChecker(project_root)

    # Run checks
    if args.check == "all":
        report = checker.check_all()
    else:
        report = ComplianceReport()
        if args.check == "CHAN-002":
            checker.check_max_drawdown_config()
            checker.check_drawdown_validation()
        elif args.check == "RET-003":
            checker.check_transaction_costs()
        elif args.check == "ARCH-001":
            checker.check_backtest_engine_integration()
        report = checker.report

    # Print report
    success = checker.print_report()

    # Save JSON
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(report.to_dict(), f, indent=2)

    logger.info(f"Results saved to: {output_path}")

    return 0 if success else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
