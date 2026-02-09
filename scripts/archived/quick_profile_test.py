#!/usr/bin/env python3
"""
Quick Profile Test Suite (1-Day).

Tests all investor profile combinations with baseline, optimization, and learning engines.

Follows:
- SOLID principles (SRP, OCP, LSP, ISP, DIP) - rules/python/03-solid-principles.md
- Testing standards (AAA pattern, parametrized tests) - rules/python/06-testing.md
- Backtesting Framework - rules/python/50-backtesting-framework.md
- Code quality (type hints, docstrings, logging)

Backtest Types Supported:
- Baseline: Reference performance without ML
- Learning Engines: supervised, deep, reinforcement, transformer
- Optimization: Grid search, Optuna hyperparameter optimization
- Stress Tests: Monte Carlo simulation

Silent Killers Detection:
- PERF-002: Garbage collection between profiles (OOM prevention)
- TRD-005: NaN detection and valid weights validation
- Idempotency: Unique run IDs (UUID) for each execution
"""

from __future__ import annotations

import gc
import logging
import sys
import uuid
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from itertools import product
from pathlib import Path
from typing import Protocol

import yaml

from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
    TaxResidence,
)


# ============================================================================
# Types & Protocols
# ============================================================================

class TestStatus(Enum):
    """Test execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class TestConfig:
    """Configuration for comprehensive profile testing."""
    start_date: str
    end_date: str
    symbols: list[str]
    n_trials: int = 3
    timeout: int = 30
    parallel: bool = False
    max_workers: int = 1

    @property
    def days(self) -> int:
        """Calculate number of days in test period."""
        from datetime import datetime
        start = datetime.fromisoformat(self.start_date)
        end = datetime.fromisoformat(self.end_date)
        return (end - start).days


@dataclass
class TestResult:
    """Result of a single profile test.

    Includes validation fields to detect silent failures:
    - has_valid_weights: Ensures optimization produced valid portfolio weights
    - nan_count: Detects NaN values in results (silent killer)
    """
    profile_id: str
    status: TestStatus
    baseline_return: float | None = None
    optimized_return: float | None = None
    improvement_pct: float = 0.0
    error_message: str | None = None
    execution_time: float = 0.0
    # TRD-005: Validación de outputs silenciosos
    has_valid_weights: bool = False
    nan_count: int = 0


@dataclass
class TestSummary:
    """Summary of all test results."""
    total: int = 0
    passed: int = 0
    failed: int = 0
    results: dict[str, TestResult] = field(default_factory=dict)

    @property
    def pass_rate(self) -> float:
        """Calculate pass rate."""
        return self.passed / self.total if self.total > 0 else 0.0

    def add_result(self, result: TestResult) -> None:
        """Add a test result."""
        self.results[result.profile_id] = result
        self.total += 1
        if result.status == TestStatus.PASSED:
            self.passed += 1
        elif result.status == TestStatus.FAILED:
            self.failed += 1

    def get_by_objective(self, objective: ObjectivoInversion) -> list[TestResult]:
        """Get results filtered by objective."""
        return [
            r for r in self.results.values()
            if objective.value in r.profile_id
        ]


# ============================================================================
# Protocols for Dependency Injection (DIP)
# ============================================================================

class ProfileGenerator(Protocol):
    """Protocol for profile generation."""

    def generate(self) -> list[InputProfile]:
        """Generate all profile combinations."""
        ...


class BacktestRunner(Protocol):
    """Protocol for backtest execution."""

    def run_single(self, profile: InputProfile) -> TestResult:
        """Run a single profile test."""
        ...


class ResultReporter(Protocol):
    """Protocol for result reporting."""

    def report(self, summary: TestSummary) -> None:
        """Generate test report."""
        ...


# ============================================================================
# Profile Generator (SRP)
# ============================================================================

class ComprehensiveProfileGenerator:
    """Generates all investor profile combinations.

    Single Responsibility: Create profile objects.

    Each run generates unique IDs to prevent collisions across test executions.
    """

    # Fixed capital tiers by risk level
    CAPITALS: dict[RiskTolerance, Decimal] = {
        RiskTolerance.BAJO: Decimal("50000"),
        RiskTolerance.MEDIO: Decimal("150000"),
        RiskTolerance.ALTO: Decimal("500000"),
    }

    # Investment horizons (months)
    HORIZONS: list[int] = [12, 24, 36, 60]

    def __init__(
        self,
        objectives: list[ObjectivoInversion] | None = None,
        risks: list[RiskTolerance] | None = None,
        run_id: str | None = None,
    ) -> None:
        """Initialize profile generator.

        Args:
            objectives: List of investment objectives (default: all)
            risks: List of risk tolerances (default: all)
            run_id: Unique run identifier for idempotency protection (default: UUID)
        """
        self._objectives = objectives or list(ObjectivoInversion)
        self._risks = risks or list(RiskTolerance)
        # Generate unique run ID to prevent ID collisions across executions
        self._run_id = run_id or uuid.uuid4().hex[:8]
        self._tax_residence = TaxResidence(
            country_code="US",
            country_name="United States",
            base_currency="USD",
        )

    def generate(self) -> list[InputProfile]:
        """Generate all profile combinations.

        Returns:
            List of InputProfile objects with unique IDs (run_id suffix).
        """
        profiles = []

        for objetivo, riesgo, horizon in product(
            self._objectives,
            self._risks,
            self.HORIZONS,
        ):
            capital = self.CAPITALS[riesgo]

            # Unique ID prevents collisions across test executions
            profile = InputProfile(
                input_id=f"test_{self._run_id}_{objetivo.value}_{riesgo.value}_h{horizon}",
                capital_initial=capital,
                objetivo_inversion=objetivo,
                risk_tolerance=riesgo,
                investment_horizon=horizon,
                tax_residence=self._tax_residence,
            )
            profiles.append(profile)

        logging.info(
            "Generated %d profile combinations (run_id=%s): %d objectives × %d risks × %d horizons",
            len(profiles),
            self._run_id,
            len(self._objectives),
            len(self._risks),
            len(self.HORIZONS),
        )

        return profiles


# ============================================================================
# Backtest Runner (SRP + DIP)
# ============================================================================

class ProfileBacktestRunner:
    """Executes backtest for a single profile.

    Single Responsibility: Run profile test and return result.
    """

    def __init__(self, config: TestConfig, output_dir: Path) -> None:
        """Initialize backtest runner.

        Args:
            config: Test configuration.
            output_dir: Output directory for results.
        """
        self._config = config
        self._output_dir = output_dir
        self._backtester: ProfileBatchBacktester | None = None

    def _initialize_backtester(self) -> None:
        """Initialize the backtester with configuration."""
        if self._backtester is None:
            config_path = self._create_config()
            self._backtester = ProfileBatchBacktester(str(config_path))
            logging.info("ProfileBatchBacktester initialized")

    def _create_config(self) -> Path:
        """Create backtest configuration YAML.

        Returns:
            Path to configuration file.
        """
        config = {
            "database": {
                "url": f"sqlite:///{self._output_dir / 'test_results.db'}"
            },
            "output_dir": str(self._output_dir),
            "capital_tiers": {
                "bajo": 50000,
                "medio": 150000,
                "alto": 500000,
            },
            "investment_horizons": {
                "short": 12,
                "medium": 24,
                "long": 36,
                "very_long": 60,
            },
            "backtest_period": {
                "start_date": self._config.start_date,
                "end_date": self._config.end_date,
            },
            "input": {
                "symbols": self._config.symbols,
                "start_date": self._config.start_date,
                "end_date": self._config.end_date,
            },
            "parallel_execution": {
                "enabled": self._config.parallel,
                "max_workers": self._config.max_workers,
            },
            "optimization": {
                "enabled": True,
                "n_trials": self._config.n_trials,
                "timeout": self._config.timeout,
            },
            "learning_engines": {
                "enabled": True,
                "types": ["supervised", "reinforcement"],
            },
            "reporting": {
                "output_directory": str(self._output_dir / "reports"),
                "generate_html": False,
                "generate_json": True,
            },
        }

        config_path = self._output_dir / "test_config.yaml"
        with open(config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)

        return config_path

    def run_single(self, profile: InputProfile) -> TestResult:
        """Run a single profile test (AAA pattern).

        Arrange: Initialize backtester.
        Act: Execute profile test.
        Assert: Capture and return result with validation.

        Args:
            profile: Profile to test.

        Returns:
            TestResult with execution details and silent failure detection.
        """
        import time
        import math

        # Arrange
        self._initialize_backtester()
        assert self._backtester is not None

        start_time = time.time()

        # Act
        try:
            result_obj = self._backtester.run_single_profile(
                profile,
                multi_strategy=True,
            )

            # Extract metrics
            baseline_return = None
            optimized_return = None
            improvement = 0.0

            if result_obj and hasattr(result_obj, 'baseline_metrics'):
                baseline_return = result_obj.baseline_metrics.get('total_return')
            if result_obj and hasattr(result_obj, 'optimized_metrics'):
                optimized_return = result_obj.optimized_metrics.get('total_return')
            if result_obj and hasattr(result_obj, 'improvement_pct'):
                improvement = result_obj.improvement_pct

            # TRD-005: Detect silent failures (NaN, invalid weights)
            nan_count = 0
            has_valid_weights = True

            # Check for NaN in returns
            for val in [baseline_return, optimized_return]:
                if val is not None and math.isnan(val):
                    nan_count += 1

            # Check if optimization produced valid results
            if optimized_return is None or (isinstance(optimized_return, float) and math.isnan(optimized_return)):
                has_valid_weights = False

            # If all returns are 0 or None, optimization likely failed silently
            if (baseline_return == 0 or baseline_return is None) and (optimized_return == 0 or optimized_return is None):
                has_valid_weights = False

            # Assert (implicit - test passed if no exception)
            return TestResult(
                profile_id=profile.input_id,
                status=TestStatus.PASSED,
                baseline_return=baseline_return,
                optimized_return=optimized_return,
                improvement_pct=improvement,
                execution_time=time.time() - start_time,
                has_valid_weights=has_valid_weights,
                nan_count=nan_count,
            )

        except Exception as e:
            # Assert - test failed
            return TestResult(
                profile_id=profile.input_id,
                status=TestStatus.FAILED,
                error_message=str(e),
                execution_time=time.time() - start_time,
                has_valid_weights=False,
                nan_count=0,
            )


# ============================================================================
# Result Reporter (SRP)
# ============================================================================

class ConsoleResultReporter:
    """Reports test results to console.

    Single Responsibility: Generate console reports.
    """

    def report(self, summary: TestSummary) -> None:
        """Generate test summary report.

        Args:
            summary: Test summary to report.
        """
        self._print_header(summary)
        self._print_by_objective(summary)
        self._print_failures(summary)
        self._print_silent_failures(summary)  # TRD-005: Detect silent failures
        self._print_footer(summary)

    def _print_header(self, summary: TestSummary) -> None:
        """Print report header."""
        logging.info("=" * 80)
        logging.info("COMPREHENSIVE PROFILE TEST - FINAL SUMMARY")
        logging.info("=" * 80)
        logging.info("Total Profiles: %d", summary.total)
        logging.info("Passed: %d (%.1f%%)", summary.passed, 100 * summary.pass_rate)
        logging.info("Failed: %d (%.1f%%)", summary.failed, 100 * (1 - summary.pass_rate))

    def _print_by_objective(self, summary: TestSummary) -> None:
        """Print results grouped by objective."""
        logging.info("")
        logging.info("Results by Objective:")

        for obj in ObjectivoInversion:
            results = summary.get_by_objective(obj)
            if results:
                passed = sum(1 for r in results if r.status == TestStatus.PASSED)
                total = len(results)
                logging.info("  %s: %d/%d passed", obj.value, passed, total)

    def _print_failures(self, summary: TestSummary) -> None:
        """Print failure details."""
        failures = [r for r in summary.results.values() if r.status == TestStatus.FAILED]

        if failures:
            logging.info("")
            logging.info("Failed Profiles (showing first 20):")
            for result in failures[:20]:
                logging.info("  %s: %s", result.profile_id, result.error_message)
            if len(failures) > 20:
                logging.info("  ... and %d more", len(failures) - 20)

    def _print_silent_failures(self, summary: TestSummary) -> None:
        """Print TRD-005 silent failure warnings (NaN, invalid weights)."""
        # Check for silent failures (tests that passed but have invalid data)
        silent_failures = [
            r for r in summary.results.values()
            if r.status == TestStatus.PASSED and (not r.has_valid_weights or r.nan_count > 0)
        ]

        if silent_failures:
            logging.info("")
            logging.warning("⚠️  SILENT FAILURES DETECTED (TRD-005)")
            logging.warning("The following profiles PASSED but have invalid data:")
            for result in silent_failures[:10]:
                warnings = []
                if not result.has_valid_weights:
                    warnings.append("invalid weights")
                if result.nan_count > 0:
                    warnings.append(f"{result.nan_count} NaN values")
                logging.warning("  %s: %s", result.profile_id, ", ".join(warnings))
            if len(silent_failures) > 10:
                logging.warning("  ... and %d more", len(silent_failures) - 10)

    def _print_footer(self, summary: TestSummary) -> None:
        """Print report footer."""
        self._print_best_configs(summary)
        logging.info("")
        logging.info("=" * 80)
        logging.info("TEST COMPLETED")
        logging.info("=" * 80)

    def _print_best_configs(self, summary: TestSummary) -> None:
        """Print best configurations by objective."""
        logging.info("")
        logging.info("Best Configurations by Objective:")

        for obj in ObjectivoInversion:
            obj_results = summary.get_by_objective(obj)
            passed_results = [r for r in obj_results if r.status == TestStatus.PASSED]

            if passed_results:
                best = max(passed_results, key=lambda r: r.improvement_pct)
                logging.info(
                    "  %s: %s (%.2f%% improvement)",
                    obj.value,
                    best.profile_id,
                    best.improvement_pct,
                )


# ============================================================================
# Test Orchestrator (OCP - extensible)
# ============================================================================

class ProfileTestOrchestrator:
    """Orchestrates comprehensive profile testing.

    Uses Dependency Injection for all components (DIP).
    """

    def __init__(
        self,
        config: TestConfig,
        generator: ProfileGenerator,
        runner: BacktestRunner,
        reporter: ResultReporter,
    ) -> None:
        """Initialize orchestrator with dependencies.

        Args:
            config: Test configuration.
            generator: Profile generator (DIP).
            runner: Backtest runner (DIP).
            reporter: Result reporter (DIP).
        """
        self._config = config
        self._generator = generator
        self._runner = runner
        self._reporter = reporter

    def run_all(self) -> TestSummary:
        """Run all profile tests.

        Returns:
            TestSummary with all results.
        """
        logging.info("=" * 80)
        logging.info("COMPREHENSIVE PROFILE TEST - Starting")
        logging.info("=" * 80)
        logging.info("Test Period: %s to %s (%d days)",
                     self._config.start_date,
                     self._config.end_date,
                     self._config.days)
        logging.info("Symbols: %d total (50 ETFs, 50 Stocks, 50 Dividends)",
                     len(self._config.symbols))
        logging.info("=" * 80)

        # Generate all profiles
        profiles = self._generator.generate()

        # Run tests
        summary = self._execute_tests(profiles)

        # Generate report
        self._reporter.report(summary)

        return summary

    def _execute_tests(self, profiles: list[InputProfile]) -> TestSummary:
        """Execute all tests with progress tracking.

        PERF-002: Includes garbage collection between profile runs to prevent
        memory accumulation from ML models in learning engines.

        Args:
            profiles: List of profiles to test.

        Returns:
            TestSummary with all results.
        """
        summary = TestSummary()

        for i, profile in enumerate(profiles, 1):
            # Log progress
            self._log_progress(i, len(profiles), profile)

            # Run test
            result = self._runner.run_single(profile)
            summary.add_result(result)

            # PERF-002: Defensive garbage collection to prevent OOM
            # ML models (supervised, reinforcement) may accumulate in memory
            gc.collect()

            # Progress update every 10 profiles
            if i % 10 == 0:
                self._log_progress_update(summary)

        return summary

    def _log_progress(self, current: int, total: int, profile: InputProfile) -> None:
        """Log test progress."""
        logging.info("-" * 80)
        logging.info("Testing Profile %d/%d: %s", current, total, profile.input_id)
        logging.info("  Objective: %s", profile.objetivo_inversion.value)
        logging.info("  Risk Level: %s", profile.risk_tolerance.value)
        logging.info("  Capital: $%s", f"{profile.capital_initial:,.0f}")
        logging.info("  Horizon: %d months", profile.investment_horizon)
        logging.info("  Progress: %.1f%%", 100 * current / total)

    def _log_progress_update(self, summary: TestSummary) -> None:
        """Log periodic progress update."""
        logging.info("=" * 80)
        logging.info("PROGRESS UPDATE: %d completed, %d failed",
                     summary.passed, summary.failed)
        logging.info("=" * 80)


# ============================================================================
# Symbol Lists (Data)
# ============================================================================

class SymbolUniverse:
    """Available trading symbols by category.

    Categories:
    - ETFS: Exchange Traded Funds (50 symbols)
    - STOCKS: US Stocks (50 symbols)
    - DIVIDENDOS: Dividend-paying stocks (50 symbols)
    - CRYPTOS: Cryptocurrencies (50 symbols)
    - FOREX: Forex currency pairs (50 symbols)
    """

    ETFS: list[str] = [
        "SPY", "QQQ", "IWM", "GLD", "SLV", "TLT", "IEF", "SHY", "HYG", "LQD",
        "XLE", "XLF", "XLK", "XLU", "XLV", "XLY", "XLP", "XLB", "XLRE", "XLI",
        "VTI", "VOO", "IVV", "AGG", "BND", "VWO", "EFA", "VXUS", "VNQ", "REM",
        "IJR", "IJH", "IJS", "IVE", "IVW", "VOT", "VOE", "VGT", "VHT", "VFH",
        "VAW", "VIS", "VCR", "VDC", "PGX", "XTL", "FTX", "MUB", "GDX", "USO",
    ]

    STOCKS: list[str] = [
        "AAPL", "MSFT", "GOOGL", "GOOG", "AMZN", "TSLA", "META", "NVDA", "AMD", "INTC",
        "CRM", "ORCL", "ADBE", "CSCO", "AVGO", "QCOM", "TXN", "IBM", "AMAT", "MU",
        "NOW", "SHOP", "SQ", "TWLO", "ZM", "DOCU", "SNOW", "PLTR", "U", "DNDR",
        "JPM", "BAC", "WFC", "C", "GS", "MS", "BLK", "SCHW", "USB", "PNC",
        "JNJ", "PFE", "UNH", "ABT", "T", "VZ", "KO", "PG", "MRK", "MDT",
    ]

    DIVIDENDOS: list[str] = [
        "O", "MAIN", "STAG", "REIT", "VICI", "WPC", "OHI", "MPW", "ADC", "BRX",
        "NTST", "GOOD", "LTC", "NYMT", "HR", "ARR", "ECC", "EFC", "THL", "ORC",
        "SCI", "CHMI", "SACH", "NYCB", "BMNM", "FSEC", "TCPC", "CCPT", "ACP", "SRG",
        "MO", "PM", "BTI", "IMP", "VGR", "BATS", "ITC", "KDP", "MCK", "CAH",
        "WBA", "TAP", "KMB", "CL", "ESS", "EQR", "AVB", "EIX", "D", "SO",
    ]

    CRYPTOS: list[str] = [
        "BTCUSD", "ETHUSD", "BNBUSD", "XRPUSD", "ADAUSD", "DOGEUSD", "SOLUSD", "MATICUSD",
        "DOTUSD", "LTCUSD", "SHIBUSD", "TRXUSD", "AVAXUSD", "LINKUSD", "ATOMUSD", "UNIUSD",
        "XMRUSD", "ETCUSD", "XLMUSD", "BCHUSD", "ALGOUSD", "VETUSD", "FILUSD", "ICPUSD",
        "HBARUSD", "LRCUSD", "AXSUSD", "SANDUSD", "MANAUSD", "CROUSD", "COMPUSD", "GRTUSD",
        "THETAUSD", "AAVEUSD", "EOSUSD", "MKRUSD", "KSMUSD", "RUNEUSD", "ZECUSD", "CAKEUSD",
        "NEARUSD", "FLOWUSD", "APEUSD", "GMTUSD", "ROSEUSD", "FTMUSD", "CELOUSD", "AUDIOUSD",
        "CRVUSD", "SPELLUSD", "LUNCUSD", "KLAYUSD", "HOTUSD", "IMXUSD", "SNXUSD", "ENJUSD",
    ]

    FOREX: list[str] = [
        "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD", "EURGBP",
        "EURJPY", "GBPJPY", "EURCHF", "EURAUD", "EURNZD", "EURCAD", "GBPCHF", "GBPAUD",
        "GBPCAD", "GBPNZD", "AUDJPY", "AUDCHF", "AUDCAD", "AUDNZD", "NZDJPY", "NZDCHF",
        "NZDCAD", "CADJPY", "CADCHF", "CHFJPY", "EURSEK", "EURNOK", "EURPLN", "EURCZK",
        "EURHUF", "EURTRY", "EURZAR", "USDMXN", "USDBRL", "USDCLP", "USDCOP", "USDPEN",
        "USDRUB", "USDINR", "USDPKR", "USDIDR", "USDMYR", "USDPHP", "USDSGD", "USDHKD",
        "USDTHB", "USDKRW", "USDVND", "USDCNY", "USDTWD", "EURTRY", "USDZAR", "GBPTRY",
    ]

    @classmethod
    def all_symbols(cls) -> list[str]:
        """Get all symbols from all categories."""
        return cls.ETFS + cls.STOCKS + cls.DIVIDENDOS + cls.CRYPTOS + cls.FOREX

    @classmethod
    def symbols_by_category(cls, category: str) -> list[str]:
        """Get symbols for a specific category.

        Args:
            category: One of 'etfs', 'stocks', 'dividendos', 'cryptos', 'forex'

        Returns:
            List of symbols for the category
        """
        categories = {
            'etfs': cls.ETFS,
            'stocks': cls.STOCKS,
            'dividendos': cls.DIVIDENDOS,
            'cryptos': cls.CRYPTOS,
            'forex': cls.FOREX,
        }
        return categories.get(category.lower(), [])


# ============================================================================
# Main Entry Point
# ============================================================================

def main() -> int:
    """Main entry point for comprehensive profile testing.

    Test Period: 1 day (quick validation)
    Backtest Types: Profile-based baseline + optimization + learning engines

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    # Configure logging
    output_dir = Path("results/quick_profile_test")
    output_dir.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler(output_dir / "test.log"),
        ],
    )

    # Calculate 1-day test period (most recent 1 trading day)
    end_date = datetime.now().date()
    # Go back approximately 2 calendar days to get 1 trading day
    start_date = end_date - timedelta(days=2)

    # Create test configuration (1 day, minimal symbols for speed)
    config = TestConfig(
        start_date=str(start_date),
        end_date=str(end_date),
        # Use minimal symbols for 1-day test (5 from each category = 25 total)
        symbols=SymbolUniverse.ETFS[:5] + SymbolUniverse.STOCKS[:5] +
                SymbolUniverse.DIVIDENDOS[:5] + SymbolUniverse.CRYPTOS[:5] +
                SymbolUniverse.FOREX[:5],
        n_trials=1,  # Minimal for 1-day speed
        timeout=15,
    )

    logging.info("=" * 80)
    logging.info("COMPREHENSIVE PROFILE TEST - 1-Day Quick Validation")
    logging.info("=" * 80)
    logging.info("Test Period: %s to %s (1 trading day)", start_date, end_date)
    logging.info("Total Symbols: %d (5 from each category: ETFs, Stocks, Dividendos, Cryptos, Forex)",
                 len(config.symbols))
    logging.info("Profile Combinations: 60 (5 objectives × 3 risks × 4 horizons)")
    logging.info("Optimization Trials: %d per profile", config.n_trials)
    logging.info("=" * 80)

    # Create components (DIP)
    generator = ComprehensiveProfileGenerator()
    runner = ProfileBacktestRunner(config, output_dir)
    reporter = ConsoleResultReporter()

    # Run tests (OCP - can swap components)
    orchestrator = ProfileTestOrchestrator(config, generator, runner, reporter)
    summary = orchestrator.run_all()

    # Return exit code
    return 0 if summary.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
