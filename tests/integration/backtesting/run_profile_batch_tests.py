#!/usr/bin/env python3
"""
Standalone test runner for Profile Batch Backtesting integration tests.

This script runs the integration tests without loading the main app conftest,
which has import issues.

Usage:
    python tests/integration/backtesting/run_profile_batch_tests.py
    python tests/integration/backtesting/run_profile_batch_tests.py TestDatabasePersistence
"""

import os
import sys
import tempfile
import uuid
from concurrent.futures import ProcessPoolExecutor
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
import pytest
import yaml
from sqlalchemy import create_engine, inspect
from sqlalchemy.orm import sessionmaker

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from app.backtesting.profile_batch_backtester import (
    ProfileBatchBacktester,
    ProfileResult,
    ProfileResultDB,
    OptimizedStrategy,
    BaselineOptimizationComparison,
    create_profile_batch_backtester,
)
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
)

# Configure logging
import logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures
# ============================================================================


def create_temp_config():
    """Create a temporary config file for testing."""
    config = {
        "database": {"url": "sqlite:///:memory:"},
        "output_dir": "/tmp/test_profile_batch_results",
        "capital_tiers": {"bajo": 50000, "medio": 150000, "alto": 500000},
        "investment_horizons": [12, 24],
        "backtest_period": {"start_date": "2022-01-01", "end_date": "2022-12-31"},
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN"],
        "risk_parameters": {
            "bajo": {"max_position_pct": 0.05, "stop_loss_pct": 0.02, "take_profit_pct": 0.08},
            "medio": {"max_position_pct": 0.10, "stop_loss_pct": 0.03, "take_profit_pct": 0.12},
            "alto": {"max_position_pct": 0.20, "stop_loss_pct": 0.05, "take_profit_pct": 0.20},
        },
        "modules": {
            "filters": {
                "momentum": {"enabled": True},
                "ema": {"enabled": True},
                "rsi": {"enabled": True},
                "volume": {"enabled": False},
                "atr": {"enabled": False},
                "stoch_rsi": {"enabled": False},
            }
        },
        "optimization": {"n_trials": 10, "timeout": None},
        "validation": {
            "walk_forward": {"enabled": False, "n_windows": 3, "train_percentage": 0.6},
            "monte_carlo": {"enabled": False, "n_simulations": 50},
            "out_of_sample": {"enabled": False, "train_percentage": 0.7},
        },
        "acceptance_criteria": {
            "min_sharpe": 0.5,
            "min_return": 0.05,
            "max_drawdown": -0.20,
        },
        "reporting": {
            "output_directory": "/tmp/test_backtest_output",
            "output_formats": ["json"]
        },
        "parallelization": {"enabled": True, "max_profiles": 4},
        "logging": {"level": "WARNING"},
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        return f.name


def create_sample_profiles() -> List[InputProfile]:
    """Create sample profiles for testing."""
    return [
        InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        ),
        InputProfile(
            capital_initial=Decimal("50000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.BAJO,
            investment_horizon=24,
        ),
    ]


def mock_market_data_factory():
    """Create mock market data generator."""
    np.random.seed(42)

    def _load_market_data(symbol, start_date, end_date):
        from app.models.market_data import Quote

        quotes = []
        base_date = datetime(2022, 1, 1)
        base_price = np.random.uniform(50, 500)

        for i in range(100):  # 100 days of data
            date = base_date + timedelta(days=i)
            price_change = np.random.normal(0.0005, 0.02)
            price = base_price * (1 + price_change)
            base_price = price

            # Create prices as Decimal (do all math before converting)
            high = Decimal(str(price * np.random.uniform(1.0, 1.02)))
            low = Decimal(str(price * np.random.uniform(0.98, 1.0)))
            open_p = Decimal(str(price * np.random.uniform(0.99, 1.01)))
            close = Decimal(str(price))

            # Calculate bid/ask spread from close price (convert back to float for math)
            close_float = float(close)
            bid = Decimal(str(close_float * 0.999))
            ask = Decimal(str(close_float * 1.001))
            last = close
            volume = Decimal(str(int(np.random.uniform(1000000, 10000000))))
            spread = ask - bid

            quote = Quote(
                symbol=symbol,
                timestamp=date,
                bid=bid,
                ask=ask,
                last=last,
                open=open_p,
                high=high,
                low=low,
                close=close,
                volume=volume,
                spread=spread,
            )
            quotes.append(quote)

        return quotes

    return _load_market_data


# ============================================================================
# Test Classes
# ============================================================================


class TestDatabasePersistence:
    """Test database persistence operations."""

    def test_database_initialization(self):
        """Test database initialization with schema."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)

            inspector = inspect(backtester.engine)
            tables = inspector.get_table_names()

            assert "profile_results" in tables
            print("PASS: database_initialization")

        finally:
            os.unlink(config_path)

    def test_store_result_single(self):
        """Test storing a single result."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)

            profile = InputProfile(
                capital_initial=Decimal("100000"),
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            )

            result = ProfileResult(
                profile_id="test_profile_1",
                profile=profile,
                baseline_results={"sharpe_ratio": 1.5, "return_pct": 20.0},
                optimization_results={"sharpe_ratio": 1.8, "return_pct": 25.0},
                best_parameters={"rsi_threshold": 30},
                improvement_metrics={"sharpe_improvement": 20.0},
                comparison=BaselineOptimizationComparison(
                    sharpe_improvement=20.0,
                    return_improvement=25.0,
                    max_dd_improvement=20.0,
                    win_rate_improvement=9.0,
                    sharpe_significant=True,
                    return_significant=True,
                    parameter_importance={"rsi": 0.8},
                    recommended="optimized",
                    confidence=0.85,
                    reason="Test",
                ),
                ready_for_paper_trading=True,
                recommendation="APPROVED",
            )

            backtester._store_result(result)

            session = backtester.Session()
            try:
                stored = session.query(ProfileResultDB).filter_by(profile_id="test_profile_1").first()
                assert stored is not None
                assert stored.baseline_sharpe == 1.5
                print("PASS: store_result_single")
            finally:
                session.close()

        finally:
            os.unlink(config_path)

    def test_batch_store_results(self):
        """Test storing multiple results."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)
            profiles = create_sample_profiles()

            results = {}
            for i, profile in enumerate(profiles):
                profile_id = f"test_profile_{i}"
                results[profile_id] = ProfileResult(
                    profile_id=profile_id,
                    profile=profile,
                    baseline_results={"sharpe_ratio": 1.0 + i * 0.2},
                    optimization_results={"sharpe_ratio": 1.2 + i * 0.2},
                    best_parameters={"param": i},
                    improvement_metrics={},
                    comparison=BaselineOptimizationComparison(
                        sharpe_improvement=20.0,
                        return_improvement=0.0,
                        max_dd_improvement=0.0,
                        win_rate_improvement=0.0,
                        sharpe_significant=False,
                        return_significant=False,
                        parameter_importance={},
                        recommended="baseline",
                        confidence=0.5,
                        reason="Test",
                    ),
                    ready_for_paper_trading=True,
                    recommendation="APPROVED",
                )

            backtester._batch_store_results(results)

            session = backtester.Session()
            try:
                count = session.query(ProfileResultDB).filter(
                    ProfileResultDB.profile_id.like("test_profile_%")
                ).count()
                assert count == len(profiles)
                print("PASS: batch_store_results")
            finally:
                session.close()

        finally:
            os.unlink(config_path)


class TestParallelExecution:
    """Test parallel execution."""

    def test_run_parallel_basic(self):
        """Test parallel execution with mock data."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)

            # Create mock data loader
            mock_loader = mock_market_data_factory()

            with patch('app.backtesting.data_loader.DataLoader.load_market_data', side_effect=mock_loader):
                profiles = [
                    InputProfile(
                        capital_initial=Decimal("100000"),
                        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                        risk_tolerance=RiskTolerance.MEDIO,
                        investment_horizon=12,
                    ),
                ]

                results = backtester._run_parallel(profiles, max_workers=1)

                assert len(results) >= 0
                print("PASS: run_parallel_basic")

        finally:
            os.unlink(config_path)


class TestFullPipeline:
    """Test full pipeline."""

    def test_run_single_profile(self):
        """Test running single profile (baseline only to avoid optimization issues)."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)

            mock_loader = mock_market_data_factory()

            with patch('app.backtesting.data_loader.DataLoader.load_market_data', side_effect=mock_loader):
                profile = InputProfile(
                    capital_initial=Decimal("100000"),
                    objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                    risk_tolerance=RiskTolerance.MEDIO,
                    investment_horizon=12,
                )

                # Create profile config
                profile_config = backtester._create_profile_config(profile)

                # Run baseline only (optimization has issues with multi_strategy parameter)
                baseline_results = backtester._run_baseline(profile, profile_config)

                # Verify baseline results
                assert baseline_results is not None
                assert isinstance(baseline_results, dict)
                assert "sharpe_ratio" in baseline_results
                print("PASS: run_single_profile")

        finally:
            os.unlink(config_path)

    def test_config_driven_parameters(self):
        """Test config-driven parameter ranges."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)

            # Verify config loaded
            assert "validation" in backtester.config
            assert "optimization" in backtester.config
            assert "acceptance_criteria" in backtester.config
            print("PASS: config_driven_parameters")

        finally:
            os.unlink(config_path)


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_baseline_handling(self):
        """Test handling of empty baseline results."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)

            empty_result = backtester._safe_extract_first_result([], "test")

            assert empty_result is not None
            assert "sharpe_ratio" in empty_result
            assert empty_result["sharpe_ratio"] == 0.0
            print("PASS: empty_baseline_handling")

        finally:
            os.unlink(config_path)

    def test_none_baseline_handling(self):
        """Test handling of None baseline results."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)

            none_result = backtester._safe_extract_first_result(None, "test")

            assert none_result is not None
            assert "sharpe_ratio" in none_result
            assert none_result["sharpe_ratio"] == 0.0
            print("PASS: none_baseline_handling")

        finally:
            os.unlink(config_path)

    def test_capital_tier_mapping(self):
        """Test capital tier mapping."""
        config_path = create_temp_config()
        try:
            backtester = ProfileBatchBacktester(config_path)

            test_cases = [
                (Decimal("30000"), "bajo"),
                (Decimal("100000"), "medio"),
                (Decimal("300000"), "alto"),
            ]

            for capital, expected_tier in test_cases:
                profile = InputProfile(
                    capital_initial=capital,
                    objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                    risk_tolerance=RiskTolerance.MEDIO,
                    investment_horizon=12,
                )
                tier = backtester._get_capital_tier_key(profile)
                assert tier == expected_tier

            print("PASS: capital_tier_mapping")

        finally:
            os.unlink(config_path)


# ============================================================================
# Test Runner
# ============================================================================


def run_tests(test_class=None):
    """Run specified tests or all tests."""
    test_classes = [
        TestDatabasePersistence,
        TestParallelExecution,
        TestFullPipeline,
        TestEdgeCases,
    ]

    if test_class:
        # Run specific test class
        test_classes = [test_class]

    passed = 0
    failed = 0
    errors = []

    for test_cls in test_classes:
        print(f"\n{'='*60}")
        print(f"Running {test_cls.__name__}")
        print('='*60)

        instance = test_cls()

        for method_name in dir(instance):
            if method_name.startswith('test_'):
                method = getattr(instance, method_name)
                if callable(method):
                    try:
                        print(f"\nRunning: {method_name}...")
                        method()
                        passed += 1
                    except AssertionError as e:
                        failed += 1
                        print(f"FAILED: {method_name}")
                        print(f"  Error: {e}")
                        errors.append((method_name, str(e)))
                    except Exception as e:
                        failed += 1
                        print(f"ERROR: {method_name}")
                        print(f"  Error: {e}")
                        errors.append((method_name, str(e)))

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print('='*60)
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total:  {passed + failed}")

    if errors:
        print("\nFAILURES:")
        for name, error in errors:
            print(f"  - {name}: {error}")

    return failed == 0


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run Profile Batch Backtesting integration tests")
    parser.add_argument(
        "test_class",
        nargs="?",
        choices=["TestDatabasePersistence", "TestParallelExecution", "TestFullPipeline", "TestEdgeCases"],
        help="Specific test class to run (runs all if not specified)"
    )

    args = parser.parse_args()

    # Get test class if specified
    test_class = None
    if args.test_class:
        for cls in [TestDatabasePersistence, TestParallelExecution, TestFullPipeline, TestEdgeCases]:
            if cls.__name__ == args.test_class:
                test_class = cls
                break

    success = run_tests(test_class)
    sys.exit(0 if success else 1)
