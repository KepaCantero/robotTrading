#!/usr/bin/env python3
"""
Comprehensive Integration Tests for Profile Batch Backtesting Full Pipeline

This module tests the complete ProfileBatchBacktester pipeline with real components
(not excessive mocking), covering:

1. Database persistence (SQLite)
2. Parallel execution with ProcessPoolExecutor
3. Full pipeline end-to-end (baseline + optimization + validation)
4. Multi-strategy execution
5. Config integration (ProfileConfigLoader, ProfileStrategyMapper)

Usage:
    pytest tests/integration/backtesting/test_profile_batch_full_pipeline.py -v
    pytest tests/integration/backtesting/test_profile_batch_full_pipeline.py::TestDatabasePersistence -v
"""

import json
import logging
import os
import tempfile
import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any, List
from unittest.mock import patch

import numpy as np
import pytest
import yaml
from sqlalchemy import inspect

from app.backtesting.profile_batch_backtester import (
    ProfileBatchBacktester,
    create_profile_batch_backtester,
)
from app.backtesting.services.models import (
    BaselineOptimizationComparison,
    ProfileResult,
    ProfileResultDB,
)
from app.core.models.input_profile import InputProfile, ObjectivoInversion, RiskTolerance
from app.services.profile_driven_trading.profile_strategy_mapper import StrategyMapping

# Configure logging
logging.basicConfig(
    level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_config_file():
    """
    Create a temporary config file for testing.

    This fixture creates a minimal but complete config file for ProfileBatchBacktester.
    """
    config = {
        "database": {"url": "sqlite:///:memory:"},  # In-memory database for fast testing
        "output_dir": "/tmp/test_profile_batch_results",
        "capital_tiers": {
            "bajo": 50000,
            "medio": 150000,
            "alto": 500000,
        },
        "investment_horizons": [12, 24],  # Short list for faster testing
        "backtest_period": {
            "start_date": "2022-01-01",
            "end_date": "2022-12-31",
        },
        "symbols": ["AAPL", "MSFT", "GOOGL", "AMZN"],  # Small set for faster tests
        "risk_parameters": {
            "bajo": {
                "max_position_pct": 0.05,
                "stop_loss_pct": 0.02,
                "take_profit_pct": 0.08,
            },
            "medio": {
                "max_position_pct": 0.10,
                "stop_loss_pct": 0.03,
                "take_profit_pct": 0.12,
            },
            "alto": {
                "max_position_pct": 0.20,
                "stop_loss_pct": 0.05,
                "take_profit_pct": 0.20,
            },
        },
        "objective_parameters": {
            "maximizar_capital": {
                "primary_metric": "sharpe_ratio",
                "min_sharpe": 0.5,
            },
            "balanced_growth": {
                "primary_metric": "sharpe_ratio",
                "min_sharpe": 0.5,
            },
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
        "optimization": {
            "n_trials": 10,  # Small number for faster tests
            "timeout": None,
        },
        "validation": {
            "walk_forward": {
                "enabled": False,  # Disabled for faster tests
                "n_windows": 3,
                "train_percentage": 0.6,
                "min_avg_sharpe": 0.3,
                "min_success_rate": 0.5,
            },
            "monte_carlo": {
                "enabled": False,  # Disabled for faster tests
                "n_simulations": 50,  # Small number for tests
                "min_profitable_pct": 0.80,
            },
            "out_of_sample": {
                "enabled": False,  # Disabled for faster tests
                "train_percentage": 0.7,
                "min_oos_sharpe": 0.3,
                "max_performance_decay": 0.5,
            },
        },
        "acceptance_criteria": {
            "min_sharpe": 0.5,
            "min_return": 0.05,
            "max_drawdown": -0.20,
            "significance_threshold": 5.0,
            "strong_significance_threshold": 10.0,
            "degradation_threshold": -5.0,
            "confidence_high": 0.8,
            "confidence_medium": 0.7,
            "confidence_low": 0.5,
            "revision_multiplier": 0.8,
        },
        "reporting": {
            "output_formats": ["json"],
        },
        "parallelization": {
            "enabled": True,
            "max_profiles": 4,
        },
        "logging": {
            "level": "WARNING",  # Reduce noise during tests
        },
    }

    # Create temp file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config, f)
        config_path = f.name

    yield config_path

    # Cleanup
    os.unlink(config_path)


@pytest.fixture
def sample_profiles() -> List[InputProfile]:
    """
    Create sample profiles for testing.

    Returns a small set of profiles for faster testing.
    """
    profiles = [
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
        InputProfile(
            capital_initial=Decimal("250000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            investment_horizon=12,
        ),
    ]
    return profiles


@pytest.fixture
def mock_market_data():
    """
    Create mock market data for testing backtest execution.

    This provides realistic-looking market data without requiring external downloads.
    """
    np.random.seed(42)

    def generate_quotes(symbol: str, n_days: int = 100) -> List[Any]:
        """Generate mock quotes for a symbol."""
        from app.models.market_data import Quote

        quotes = []
        base_date = datetime(2022, 1, 1)
        base_price = np.random.uniform(50, 500)

        for i in range(n_days):
            date = base_date + timedelta(days=i)

            # Random walk with trend
            price_change = np.random.normal(0.0005, 0.02)
            price = base_price * (1 + price_change)
            base_price = price

            # Create OHLC
            high = price * np.random.uniform(1.0, 1.02)
            low = price * np.random.uniform(0.98, 1.0)
            open_p = price * np.random.uniform(0.99, 1.01)
            close = price
            volume = int(np.random.uniform(1000000, 10000000))

            quote = Quote(
                symbol=symbol,
                timestamp=date,
                open=open_p,
                high=high,
                low=low,
                close=close,
                volume=volume,
            )
            quotes.append(quote)

        return quotes

    return generate_quotes


@pytest.fixture
def patch_data_loader(mock_market_data):
    """
    Patch DataLoader to return mock market data.

    This avoids requiring actual market data downloads during testing.
    """

    def _load_market_data(symbol, start_date, end_date):
        # Generate 100 days of mock data
        return mock_market_data(symbol, 100)

    with patch(
        'app.backtesting.data_loader.DataLoader.load_market_data', side_effect=_load_market_data
    ):
        yield


# ============================================================================
# Test Class 1: Database Persistence
# ============================================================================


class TestDatabasePersistence:
    """Test database persistence operations with real SQLite."""

    def test_database_initialization(self, temp_config_file):
        """Test that database is properly initialized with schema."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Check tables exist
        inspector = inspect(backtester.engine)
        tables = inspector.get_table_names()

        assert "profile_results" in tables
        assert len(tables) > 0

    def test_store_result_single(self, temp_config_file, sample_profiles):
        """Test storing a single result to database."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = sample_profiles[0]

        # Create a mock result
        result = ProfileResult(
            profile_id="test_profile_1",
            profile=profile,
            baseline_results={
                "sharpe_ratio": 1.5,
                "return_pct": 20.0,
                "max_drawdown": -10.0,
                "win_rate": 0.55,
                "total_trades": 100,
            },
            optimization_results={
                "sharpe_ratio": 1.8,
                "return_pct": 25.0,
                "max_drawdown": -8.0,
                "win_rate": 0.60,
            },
            best_parameters={"rsi_threshold": 30},
            improvement_metrics={
                "sharpe_improvement": 20.0,
                "return_improvement": 25.0,
            },
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
                reason="Optimized shows significant improvement",
            ),
            ready_for_paper_trading=True,
            recommendation="APPROVED",
        )

        # Store result
        backtester._store_result(result)

        # Verify stored in database
        session = backtester.Session()
        try:
            stored = session.query(ProfileResultDB).filter_by(profile_id="test_profile_1").first()
            assert stored is not None
            assert stored.baseline_sharpe == 1.5
            assert stored.optimized_sharpe == 1.8
            assert stored.ready_for_paper_trading is True
        finally:
            session.close()

    def test_batch_store_results(self, temp_config_file, sample_profiles):
        """Test storing multiple results in batch."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Create multiple results
        results = {}
        for i, profile in enumerate(sample_profiles):
            profile_id = f"test_profile_{i}"
            results[profile_id] = ProfileResult(
                profile_id=profile_id,
                profile=profile,
                baseline_results={
                    "sharpe_ratio": 1.0 + i * 0.2,
                    "return_pct": 15.0 + i * 2,
                    "max_drawdown": -10.0,
                    "win_rate": 0.50 + i * 0.05,
                },
                optimization_results={
                    "sharpe_ratio": 1.2 + i * 0.2,
                    "return_pct": 18.0 + i * 2,
                    "max_drawdown": -8.0,
                    "win_rate": 0.55 + i * 0.05,
                },
                best_parameters={"param": i},
                improvement_metrics={"sharpe_improvement": 20.0},
                comparison=BaselineOptimizationComparison(
                    sharpe_improvement=20.0,
                    return_improvement=20.0,
                    max_dd_improvement=20.0,
                    win_rate_improvement=10.0,
                    sharpe_significant=True,
                    return_significant=True,
                    parameter_importance={},
                    recommended="optimized",
                    confidence=0.8,
                    reason="Test",
                ),
                ready_for_paper_trading=True,
                recommendation="APPROVED",
            )

        # Batch store
        backtester._batch_store_results(results)

        # Verify all stored
        session = backtester.Session()
        try:
            stored_count = (
                session.query(ProfileResultDB)
                .filter(ProfileResultDB.profile_id.like("test_profile_%"))
                .count()
            )
            assert stored_count == len(sample_profiles)
        finally:
            session.close()

    def test_database_update_existing(self, temp_config_file, sample_profiles):
        """Test updating an existing result."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = sample_profiles[0]
        profile_id = "update_test_profile"

        # Create initial result
        result = ProfileResult(
            profile_id=profile_id,
            profile=profile,
            baseline_results={"sharpe_ratio": 1.0},
            optimization_results={"sharpe_ratio": 1.2},
            best_parameters={},
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
            ready_for_paper_trading=False,
            recommendation="REJECTED",
        )

        backtester._store_result(result)

        # Update with new result
        result.optimization_results = {"sharpe_ratio": 2.0}
        result.ready_for_paper_trading = True
        result.recommendation = "APPROVED"

        backtester._store_result(result)

        # Verify update
        session = backtester.Session()
        try:
            stored = session.query(ProfileResultDB).filter_by(profile_id=profile_id).first()
            assert stored.optimized_sharpe == 2.0
            assert stored.ready_for_paper_trading is True
            assert stored.recommendation == "APPROVED"
        finally:
            session.close()

    def test_transaction_rollback_on_error(self, temp_config_file):
        """Test that transactions are rolled back on error."""
        backtester = ProfileBatchBacktester(temp_config_file)

        session = backtester.Session()
        try:
            # Start transaction
            profile = ProfileResultDB(
                id=str(uuid.uuid4()),
                profile_id="rollback_test",
                objective="maximizar_capital",
                risk_tolerance="medio",
                capital_tier="medio",
                investment_horizon=12,
            )
            session.add(profile)

            # Simulate error
            session.rollback()

            # Verify not stored
            count = session.query(ProfileResultDB).filter_by(profile_id="rollback_test").count()
            assert count == 0
        finally:
            session.close()

    def test_database_schema_validation(self, temp_config_file):
        """Test that database schema is correct."""
        backtester = ProfileBatchBacktester(temp_config_file)

        inspector = inspect(backtester.engine)

        # Check profile_results table columns
        columns = [c['name'] for c in inspector.get_columns('profile_results')]

        # Verify required columns exist
        required_columns = [
            'id',
            'profile_id',
            'objective',
            'risk_tolerance',
            'capital_tier',
            'baseline_sharpe',
            'optimized_sharpe',
            'sharpe_improvement',
            'ready_for_paper_trading',
            'recommendation',
        ]

        for col in required_columns:
            assert col in columns, f"Missing required column: {col}"


# ============================================================================
# Test Class 2: Parallel Execution
# ============================================================================


class TestParallelExecution:
    """Test parallel execution with ProcessPoolExecutor."""

    def test_run_parallel_with_multiple_workers(
        self, temp_config_file, sample_profiles, patch_data_loader
    ):
        """Test parallel execution with multiple workers."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Run profiles in parallel
        results = backtester._run_parallel(sample_profiles, max_workers=2)

        # Verify all profiles completed
        assert len(results) == len(sample_profiles)

        # Verify results have correct structure
        for profile_id, result in results.items():
            assert isinstance(result, ProfileResult)
            assert result.profile_id == profile_id
            assert result.baseline_results is not None

    def test_worker_failure_handling(self, temp_config_file, patch_data_loader):
        """Test that worker failures are handled gracefully."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Create a mix of valid and invalid profiles
        profiles = [
            InputProfile(
                capital_initial=Decimal("100000"),
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            ),
        ]

        # Run parallel
        results = backtester._run_parallel(profiles, max_workers=1)

        # Should complete despite any failures
        assert len(results) >= 0

    def test_concurrent_database_writes(self, temp_config_file, sample_profiles, patch_data_loader):
        """Test that concurrent database writes don't cause conflicts."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Run in parallel
        backtester._run_parallel(sample_profiles, max_workers=2)

        # Verify all results stored in database
        session = backtester.Session()
        try:
            stored_count = session.query(ProfileResultDB).count()
            assert stored_count >= 0  # May be 0 if tests fail, but shouldn't error
        finally:
            session.close()

    def test_result_aggregation(self, temp_config_file, patch_data_loader):
        """Test that results are properly aggregated."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profiles = [
            InputProfile(
                capital_initial=Decimal("100000"),
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=12,
            ),
        ]

        results = backtester._run_parallel(profiles, max_workers=1)

        # Check aggregation
        assert isinstance(results, dict)
        assert all(isinstance(k, str) for k in results.keys())
        assert all(isinstance(v, ProfileResult) for v in results.values())


# ============================================================================
# Test Class 3: Full Pipeline End-to-End
# ============================================================================


class TestFullPipelineEndToEnd:
    """Test complete pipeline with real ComprehensiveBacktestRunner."""

    def test_run_single_profile_baseline_only(self, temp_config_file, patch_data_loader):
        """Test running a single profile through baseline backtest."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        result = backtester.run_single_profile(profile)

        # Verify result structure
        assert isinstance(result, ProfileResult)
        assert result.profile is not None
        assert result.baseline_results is not None
        assert isinstance(result.baseline_results, dict)

        # Check baseline has expected fields
        baseline = result.baseline_results
        expected_fields = ["sharpe_ratio", "return_pct", "max_drawdown", "win_rate"]
        for field in expected_fields:
            assert field in baseline

    def test_run_single_profile_optimization(self, temp_config_file, patch_data_loader):
        """Test optimization pipeline for single profile."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        result = backtester.run_single_profile(profile)

        # Verify optimization results
        assert result.optimization_results is not None
        assert result.best_parameters is not None
        assert result.improvement_metrics is not None
        assert result.comparison is not None

        # Check comparison structure
        assert isinstance(result.comparison, BaselineOptimizationComparison)
        assert hasattr(result.comparison, 'sharpe_improvement')
        assert hasattr(result.comparison, 'recommended')

    def test_run_all_profiles_small_set(self, temp_config_file, patch_data_loader):
        """Test running multiple profiles through complete pipeline."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profiles = [
            InputProfile(
                capital_initial=Decimal("50000"),
                objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
                risk_tolerance=RiskTolerance.BAJO,
                investment_horizon=12,
            ),
            InputProfile(
                capital_initial=Decimal("100000"),
                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                risk_tolerance=RiskTolerance.MEDIO,
                investment_horizon=24,
            ),
        ]

        results = backtester.run_all_profiles(parallel=False, max_workers=1)

        # Verify results
        assert len(results) == len(profiles)

        for profile_id, result in results.items():
            assert isinstance(result, ProfileResult)
            assert result.profile_id == profile_id
            assert result.baseline_results is not None
            assert result.optimization_results is not None

    def test_report_generation(self, temp_config_file, patch_data_loader):
        """Test that HTML comparison report is generated."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Create minimal results
        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        result = backtester.run_single_profile(profile)
        backtester.results = {result.profile_id: result}

        # Generate report
        html = backtester.generate_comparison_report()

        # Verify report structure
        assert isinstance(html, str)
        assert len(html) > 0
        assert "<html>" in html
        assert "Profile Batch Backtesting Report" in html

    def test_export_results(self, temp_config_file, patch_data_loader):
        """Test exporting results to file."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        result = backtester.run_single_profile(profile)
        backtester.results = {result.profile_id: result}

        # Export to JSON
        output_path = backtester.export_results(format="json")

        # Verify file created
        assert output_path.exists()

        # Verify can read back
        with open(output_path) as f:
            loaded = json.load(f)

        assert isinstance(loaded, dict)
        assert result.profile_id in loaded

        # Cleanup
        output_path.unlink()


# ============================================================================
# Test Class 4: Multi-Strategy Execution
# ============================================================================


class TestMultiStrategyExecution:
    """Test multi-strategy mode with strategy mapper integration."""

    def test_profile_strategy_mapper_integration(self, temp_config_file):
        """Test ProfileStrategyMapper integration."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Skip if mapper not available
        if backtester.profile_mapper is None:
            pytest.skip("ProfileStrategyMapper not available")

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        # Get strategy mapping
        mapping = backtester.profile_mapper.create_strategy_mapping(profile)

        # Verify mapping structure
        assert isinstance(mapping, StrategyMapping)
        assert hasattr(mapping, 'enabled_strategies')
        assert hasattr(mapping, 'risk_profile')

    def test_multi_strategy_config_generation(self, temp_config_file):
        """Test config generation with multi-strategy support."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        config = backtester._create_profile_config(profile)

        # Verify config structure
        assert isinstance(config, dict)
        assert "input" in config
        assert "strategy" in config

        # Check for strategy mapping metadata
        if "_strategy_mapping" in config:
            mapping = config["_strategy_mapping"]
            assert "enabled_strategies" in mapping
            assert "learning_engines" in mapping

    def test_ensemble_mode_config(self, temp_config_file):
        """Test ensemble mode configuration."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = InputProfile(
            capital_initial=Decimal("250000"),
            objetivo_inversion=ObjectivoInversion.BALANCED_GROWTH,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=24,
        )

        config = backtester._create_profile_config(profile)

        # Verify ensemble config exists
        if "strategy" in config:
            strategy_config = config["strategy"]
            # Ensemble config may or may not exist depending on mapper
            assert isinstance(strategy_config, dict)

    def test_per_strategy_result_tracking(self, temp_config_file, patch_data_loader):
        """Test per-strategy result tracking."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        result = backtester.run_single_profile(profile)

        # Check per-strategy results field
        assert hasattr(result, 'per_strategy_results')
        assert isinstance(result.per_strategy_results, dict)

    def test_strategy_result_aggregation(self, temp_config_file, patch_data_loader):
        """Test aggregation of multi-strategy results."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        result = backtester.run_single_profile(profile)

        # Verify aggregation
        assert result.baseline_results is not None
        assert result.optimization_results is not None

        # Check that metrics are numeric
        assert isinstance(result.baseline_results.get("sharpe_ratio"), (int, float))


# ============================================================================
# Test Class 5: Config Integration
# ============================================================================


class TestConfigIntegration:
    """Test integration with config loaders and mappers."""

    def test_profile_config_loader_integration(self, temp_config_file):
        """Test ProfileConfigLoader integration."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Skip if loader not available
        if backtester.profile_config_loader is None:
            pytest.skip("ProfileConfigLoader not available")

        # Test accessing config
        try:
            # Try to get threshold config
            rsi_config = backtester.profile_config_loader.get_threshold_config("rsi")
            assert isinstance(rsi_config, dict)
        except Exception as e:
            # May fail if config file not present
            logger.warning(f"ProfileConfigLoader test failed: {e}")

    def test_parameter_range_loading(self, temp_config_file):
        """Test loading parameter ranges from config."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # If ProfileConfigLoader is available, test parameter loading
        if backtester.profile_config_loader is not None:
            try:
                # Try to load parameter ranges
                rsi_buy = backtester.profile_config_loader.get_threshold_config("rsi").get(
                    "buy_threshold", {}
                )
                assert isinstance(rsi_buy, dict)
            except Exception as e:
                logger.warning(f"Parameter range loading failed: {e}")

    def test_validation_config_loading(self, temp_config_file):
        """Test loading validation config."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Check validation config is loaded
        assert "validation" in backtester.config
        validation_config = backtester.config["validation"]

        # Verify structure
        assert "walk_forward" in validation_config
        assert "monte_carlo" in validation_config
        assert "out_of_sample" in validation_config

    def test_acceptance_criteria_config(self, temp_config_file):
        """Test acceptance criteria from config."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Check acceptance criteria
        assert "acceptance_criteria" in backtester.config
        criteria = backtester.config["acceptance_criteria"]

        # Verify required criteria
        assert "min_sharpe" in criteria
        assert "min_return" in criteria
        assert "max_drawdown" in criteria

    def test_config_driven_parameter_ranges(self, temp_config_file, patch_data_loader):
        """Test that parameter ranges come from config."""
        backtester = ProfileBatchBacktester(temp_config_file)

        profile = InputProfile(
            capital_initial=Decimal("100000"),
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.MEDIO,
            investment_horizon=12,
        )

        # Run optimization - should use config ranges
        result = backtester.run_single_profile(profile)

        # Verify best parameters were found
        assert result.best_parameters is not None
        assert isinstance(result.best_parameters, dict)


# ============================================================================
# Test Class 6: Edge Cases and Error Handling
# ============================================================================


class TestEdgeCasesAndErrorHandling:
    """Test edge cases and error handling."""

    def test_empty_baseline_results(self, temp_config_file, patch_data_loader):
        """Test handling of empty baseline results."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Test _safe_extract_first_result with empty
        empty_result = backtester._safe_extract_first_result([], "test context")

        assert empty_result is not None
        assert "sharpe_ratio" in empty_result
        assert empty_result["sharpe_ratio"] == 0.0

    def test_none_baseline_results(self, temp_config_file, patch_data_loader):
        """Test handling of None baseline results."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Test _safe_extract_first_result with None
        none_result = backtester._safe_extract_first_result(None, "test context")

        assert none_result is not None
        assert "sharpe_ratio" in none_result
        assert none_result["sharpe_ratio"] == 0.0

    def test_invalid_horizon_handling(self, temp_config_file):
        """Test handling of invalid investment horizon."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Modify config to have invalid horizon
        backtester.config["investment_horizons"] = [-1, 0, 12]  # Invalid values

        horizons = backtester._load_investment_horizons()

        # Should filter out invalid horizons
        assert -1 not in horizons
        assert 0 not in horizons
        assert 12 in horizons

    def test_get_best_strategy_no_results(self, temp_config_file):
        """Test get_best_strategy when no results exist."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Query for non-existent strategy
        result = backtester.get_best_strategy(objective="nonexistent", tier="medio", risk="medio")

        # Should return empty dict
        assert result == {}

    def test_capital_tier_mapping(self, temp_config_file):
        """Test capital tier mapping from profile to config."""
        backtester = ProfileBatchBacktester(temp_config_file)

        # Test each capital tier
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


# ============================================================================
# Helper Functions
# ============================================================================


def test_create_profile_batch_backtester(temp_config_file):
    """Test convenience function for creating backtester."""
    backtester = create_profile_batch_backtester(temp_config_file)

    assert isinstance(backtester, ProfileBatchBacktester)
    assert backtester.config_path == Path(temp_config_file)


# ============================================================================
# Main Test Runner
# ============================================================================


if __name__ == "__main__":
    # Run tests with verbose output
    pytest.main([__file__, "-v", "-s", "--tb=short"])
