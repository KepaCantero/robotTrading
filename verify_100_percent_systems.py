#!/usr/bin/env python3
"""
Comprehensive System Availability Verification Script

This script verifies that all 21 required systems are available and properly importable.
It's designed for CI/CD integration and provides detailed error reporting.

Usage:
    python verify_100_percent_systems.py
    # Returns exit code 0 if all systems available, 1 otherwise
"""

import sys
import importlib
import traceback
from pathlib import Path
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum


class SystemStatus(Enum):
    """System verification status."""
    AVAILABLE = "✅"
    FAILED = "❌"
    WARNING = "⚠️"


@dataclass
class SystemCheckResult:
    """Result of a system verification check."""
    name: str
    status: SystemStatus
    message: str
    error_details: str = ""
    required_modules: List[str] = None

    def __post_init__(self):
        if self.required_modules is None:
            self.required_modules = []


class SystemVerifier:
    """Main system verification class."""

    def __init__(self):
        self.base_path = Path(__file__).parent / "app"
        self.results: List[SystemCheckResult] = []
        self.system_definitions = self._get_system_definitions()

    def _get_system_definitions(self) -> Dict[str, dict]:
        """Define all 21 systems with their verification requirements."""
        return {
            # Main Systems (9)
            "backtesting_engine": {
                "description": "Comprehensive backtesting framework",
                "required_paths": [
                    "app/backtesting",
                    "app/backtesting/comprehensive_backtest_runner.py",
                    "app/backtesting/metrics.py",
                    "app/backtesting/validation",
                ],
                "required_imports": [
                    "app.backtesting.comprehensive_backtest_runner",
                    "app.backtesting.metrics",
                ],
                "critical_features": [
                    "walk_forward_validation",
                    "triple_barrier",
                    "meta_labeling",
                ],
            },
            "live_trading": {
                "description": "Live trading execution system",
                "required_paths": [
                    "app/services/live_trading",
                ],
                "required_imports": [
                    "app.services.live_trading.broker_adapters.alpaca_client",
                ],
                "critical_features": [
                    "broker_adapter",
                    "order_execution",
                ],
            },
            "paper_trading": {
                "description": "Paper trading simulation system",
                "required_paths": [
                    "app/simulation",
                    "app/simulation/exchange.py",
                    "app/simulation/market_mechanics.py",
                ],
                "required_imports": [
                    "app.simulation.exchange",
                    "app.simulation.market_mechanics",
                ],
                "critical_features": [
                    "paper_trading",
                    "simulation",
                ],
            },
            "strategies": {
                "description": "Trading strategies framework",
                "required_paths": [
                    "app/strategies",
                    "app/strategies/base.py",
                    "app/strategies/factory.py",
                    "app/strategies/momentum_modular",
                ],
                "required_imports": [
                    "app.strategies.base",
                    "app.strategies.factory",
                ],
                "critical_features": [
                    "momentum",
                    "mean_reversion",
                    "pairs_trading",
                ],
            },
            "risk_engine": {
                "description": "Risk management engine",
                "required_paths": [
                    "app/engines/risk_engine",
                    "app/engines/risk_engine/var_calculators",
                    "app/engines/risk_engine/drawdown_controllers",
                ],
                "required_imports": [
                    "app.engines.risk_engine.var_calculators",
                    "app.engines.risk_engine.drawdown_controllers",
                ],
                "critical_features": [
                    "var_calculation",
                    "drawdown_control",
                    "stress_testing",
                ],
            },
            "portfolio_engine": {
                "description": "Portfolio management engine",
                "required_paths": [
                    "app/engines/portfolio_engine",
                    "app/engines/portfolio_engine/optimizers",
                ],
                "required_imports": [
                    "app.engines.portfolio_engine.meta_learners",
                    "app.engines.portfolio_engine.optimizers",
                ],
                "critical_features": [
                    "optimization",
                    "rebalancing",
                    "meta_learning",
                ],
            },
            "data_engine": {
                "description": "Data acquisition and processing",
                "required_paths": [
                    "app/engines/data_engine",
                    "app/engines/data_engine/sources",
                    "app/engines/data_engine/cache",
                ],
                "required_imports": [
                    "app.engines.data_engine.sources.ohlcv_sources",
                    "app.engines.data_engine.cache.distributed_cache",
                ],
                "critical_features": [
                    "data_sources",
                    "caching",
                    "streaming",
                ],
            },
            "context_engine": {
                "description": "Market context analysis",
                "required_paths": [
                    "app/engines/context_engine",
                    "app/engines/context_engine/regime_detectors",
                    "app/engines/context_engine/volatility_analyzers",
                ],
                "required_imports": [
                    "app.engines.context_engine.regime_detectors.hmm_regime_detector",
                    "app.engines.context_engine.volatility_analyzers.garch_analyzer",
                ],
                "critical_features": [
                    "regime_detection",
                    "volatility_analysis",
                    "correlation_analysis",
                ],
            },
            "execution_engine": {
                "description": "Order execution and microstructure",
                "required_paths": [
                    "app/engines/execution_engine",
                    "app/engines/execution_engine/microstructure",
                ],
                "required_imports": [
                    "app.engines.execution_engine.microstructure.microstructure_engine",
                    "app.engines.execution_engine.microstructure.almgren_chriss_model",
                ],
                "critical_features": [
                    "order_execution",
                    "microstructure",
                    "algorithmic_trading",
                ],
            },

            # Compliance Systems (12)
            "ernest_chan": {
                "description": "Ernest Chan quantitative trading methods",
                "required_paths": [
                    "app/services/factor_models.py",
                    "app/services/regime_detection_chan.py",
                    "app/services/execution_algorithms.py",
                    "app/services/optimization_chan.py",
                ],
                "required_imports": [
                    "app.services.factor_models",
                    "app.services.regime_detection_chan",
                    "app.services.execution_algorithms",
                    "app.services.optimization_chan",
                ],
                "critical_features": [
                    "factor_models",
                    "regime_detection",
                    "execution_algorithms",
                    "optimization",
                ],
            },
            "narang": {
                "description": "Inside the Black Box (Narang) implementation",
                "required_paths": [
                    "app/services/risk_models_narang.py",
                    "app/services/execution_narang.py",
                    "app/services/transaction_costs.py",
                    "app/services/portfolio_construction_narang.py",
                ],
                "required_imports": [
                    "app.services.risk_models_narang",
                    "app.services.execution_narang",
                    "app.services.transaction_costs",
                ],
                "critical_features": [
                    "alpha_generation",
                    "risk_models",
                    "transaction_costs",
                    "portfolio_construction",
                ],
            },
            "lopez_de_prado": {
                "description": "Lopez de Prado advances in financial ML",
                "required_paths": [
                    "app/backtesting/labeling/meta_labeling.py",
                    "app/backtesting/validation/cross_validation.py",
                    "app/backtesting/financial_ml.py",
                    "app/backtesting/labeling/bet_sizing.py",
                ],
                "required_imports": [
                    "app.backtesting.labeling.meta_labeling",
                    "app.backtesting.validation.cross_validation",
                    "app.backtesting.financial_ml",
                ],
                "critical_features": [
                    "sample_weights",
                    "purged_cv",
                    "meta_labeling",
                    "bet_sizing",
                ],
            },
            "tomasini": {
                "description": "Tomasini systematic trading architecture",
                "required_paths": [
                    "app/engines/event_engine/tomasini_event_queue.py",
                    "app/backtesting/validation/walk_forward_validator_enhanced.py",
                ],
                "required_imports": [
                    "app.engines.event_engine.tomasini_event_queue",
                ],
                "critical_features": [
                    "event_queue",
                    "walk_forward",
                    "architecture",
                ],
            },
            "hastie": {
                "description": "Hastie statistical learning methods",
                "required_paths": [
                    "app/backtesting/model_selection.py",
                ],
                "required_imports": [
                    "app.backtesting.model_selection",
                ],
                "critical_features": [
                    "statistical_learning",
                    "model_selection",
                    "cross_validation",
                ],
            },
            "harris": {
                "description": "Harris trading and exchanges microstructure",
                "required_paths": [
                    "app/microstructure",
                    "app/microstructure/order_flow.py",
                    "app/microstructure/trading_mechanisms.py",
                    "app/simulation/microstructure.py",
                ],
                "required_imports": [
                    "app.microstructure.order_flow",
                    "app.microstructure.trading_mechanisms",
                ],
                "critical_features": [
                    "order_flow",
                    "trading_mechanisms",
                    "market_structure",
                ],
            },
            "ohara": {
                "description": "O'Hara market microstructure theory",
                "required_paths": [
                    "app/microstructure/liquidity.py",
                    "app/microstructure/price_discovery.py",
                    "app/simulation/order_book.py",
                ],
                "required_imports": [
                    "app.microstructure.liquidity",
                    "app.microstructure.price_discovery",
                ],
                "critical_features": [
                    "liquidity",
                    "price_discovery",
                    "order_book",
                ],
            },
            "percival": {
                "description": "Percival architecture patterns",
                "required_paths": [
                    "app/domain",
                    "app/application",
                    "app/infrastructure",
                ],
                "required_imports": [
                    "app.domain.entities.backtest",
                    "app.domain.repositories.backtest_repository",
                ],
                "critical_features": [
                    "clean_architecture",
                    "domain_entities",
                    "repositories",
                ],
            },
            "hull": {
                "description": "Hull risk management (VaR, Greeks, stress testing)",
                "required_paths": [
                    "app/engines/risk_engine/var_calculators",
                    "app/engines/risk_engine/greeks_calculator.py",
                    "app/engines/risk_engine/stress_testers",
                ],
                "required_imports": [
                    "app.engines.risk_engine.var_calculators.var_calculators",
                    "app.engines.risk_engine.greeks_calculator",
                ],
                "critical_features": [
                    "var_calculation",
                    "greeks",
                    "stress_testing",
                ],
            },
            "google_sre": {
                "description": "Google SRE practices",
                "required_paths": [
                    "app/sre/monitoring/golden_signals.py",
                    "app/sre/automation/toil_tracker.py",
                    "app/sre/error_budgets/error_budget_manager.py",
                ],
                "required_imports": [
                    "app.sre.monitoring.golden_signals",
                    "app.sre.automation.toil_tracker",
                    "app.sre.error_budgets.error_budget_manager",
                ],
                "critical_features": [
                    "golden_signals",
                    "toil_tracking",
                    "error_budgets",
                ],
            },
            "beck_tdd": {
                "description": "Beck TDD patterns and property-based testing",
                "required_paths": [
                    "tests/unit/property_tests",
                ],
                "required_imports": [],
                "critical_features": [
                    "property_based_tests",
                    "tdd_patterns",
                    "hypothesis_tests",
                ],
            },
            "martin_arch": {
                "description": "Martin Clean Architecture implementation",
                "required_paths": [
                    "app/domain/entities",
                    "app/application/use_cases",
                    "app/infrastructure/persistence",
                ],
                "required_imports": [
                    "app.domain.entities.backtest",
                    "app.application.use_cases.run_backtest_use_case",
                ],
                "critical_features": [
                    "use_cases",
                    "entities",
                    "repositories",
                    "dependency_injection",
                ],
            },
        }

    def check_file_exists(self, file_path: str) -> bool:
        """Check if a file or directory exists."""
        full_path = self.base_path.parent / file_path
        return full_path.exists()

    def check_import(self, import_path: str) -> Tuple[bool, str]:
        """Try to import a module and return success status with error message."""
        try:
            importlib.import_module(import_path)
            return True, ""
        except ImportError as e:
            return False, f"ImportError: {str(e)}"
        except Exception as e:
            return False, f"{type(e).__name__}: {str(e)}"

    def verify_system(self, system_name: str, system_def: dict) -> SystemCheckResult:
        """Verify a single system."""
        required_paths = system_def.get("required_paths", [])
        required_imports = system_def.get("required_imports", [])
        critical_features = system_def.get("critical_features", [])

        errors = []
        missing_modules = []

        # Check file paths
        for path in required_paths:
            if not self.check_file_exists(path):
                errors.append(f"Missing path: {path}")

        # Check imports
        for imp in required_imports:
            success, error_msg = self.check_import(imp)
            if not success:
                errors.append(f"Import failed: {imp} - {error_msg}")
                missing_modules.append(imp)

        # Determine status
        if not errors:
            return SystemCheckResult(
                name=system_name,
                status=SystemStatus.AVAILABLE,
                message=f"Available - All {len(required_paths)} paths and {len(required_imports)} modules verified",
                required_modules=critical_features,
            )
        else:
            return SystemCheckResult(
                name=system_name,
                status=SystemStatus.FAILED,
                message=f"FAILED - {len(errors)} error(s)",
                error_details="\n".join(errors),
                required_modules=missing_modules,
            )

    def verify_all_systems(self) -> None:
        """Verify all 21 systems."""
        print("\n" + "═" * 65)
        print("SYSTEM AVAILABILITY VERIFICATION (21/21)")
        print("═" * 65 + "\n")

        for system_name, system_def in self.system_definitions.items():
            result = self.verify_system(system_name, system_def)
            self.results.append(result)

            # Print result immediately
            status_symbol = result.status.value
            print(f"{status_symbol} {system_name:20} - {result.message}")

            if result.status == SystemStatus.FAILED and result.error_details:
                print(f"   Details:\n{self._indent(result.error_details, 6)}")
            print()

    def _indent(self, text: str, spaces: int) -> str:
        """Indent multiline text."""
        indent = " " * spaces
        return "\n".join(indent + line for line in text.split("\n"))

    def print_summary(self) -> None:
        """Print verification summary."""
        available = sum(1 for r in self.results if r.status == SystemStatus.AVAILABLE)
        failed = sum(1 for r in self.results if r.status == SystemStatus.FAILED)
        total = len(self.results)
        percentage = (available / total) * 100 if total > 0 else 0

        print("\n" + "═" * 65)
        print("SUMMARY")
        print("═" * 65)
        print(f"Available: {available}/{total} ({percentage:.1f}%)")
        print(f"Target: {total}/{total} (100%)")
        print(f"Failed: {failed}/{total}")

        if failed > 0:
            failed_systems = [r.name for r in self.results if r.status == SystemStatus.FAILED]
            print(f"\nMissing/Failing Systems:")
            for system in failed_systems:
                result = next(r for r in self.results if r.name == system)
                print(f"  - {system}")
                if result.required_modules:
                    print(f"    Missing modules: {', '.join(result.required_modules[:3])}")
                    if len(result.required_modules) > 3:
                        print(f"    ... and {len(result.required_modules) - 3} more")

        print("\n" + "═" * 65)

        # Overall status
        if available == total:
            print("Status: ✅ ALL SYSTEMS OPERATIONAL")
            print("═" * 65 + "\n")
            return 0
        else:
            print(f"Status: ❌ NOT READY - Missing {failed} system(s)")
            print("═" * 65 + "\n")
            return 1

    def generate_detailed_report(self) -> str:
        """Generate detailed report for CI/CD logs."""
        report = []
        report.append("# System Availability Detailed Report\n")

        for result in self.results:
            report.append(f"## {result.name}")
            report.append(f"Status: {result.status.name}")
            report.append(f"Description: {self.system_definitions[result.name]['description']}")

            if result.status == SystemStatus.FAILED:
                report.append(f"Errors:\n{result.error_details}")

            report.append("")

        return "\n".join(report)

    def run(self) -> int:
        """Run full verification and return exit code."""
        try:
            self.verify_all_systems()
            exit_code = self.print_summary()

            # Generate detailed report if there are failures
            if exit_code != 0:
                detailed_report = self.generate_detailed_report()
                report_path = Path(__file__).parent / "system_verification_report.md"
                report_path.write_text(detailed_report)
                print(f"Detailed report saved to: {report_path}\n")

            return exit_code

        except Exception as e:
            print(f"\n❌ VERIFICATION SCRIPT ERROR: {str(e)}")
            print(traceback.format_exc())
            return 1


def main():
    """Main entry point."""
    verifier = SystemVerifier()
    exit_code = verifier.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
