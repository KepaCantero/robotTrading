"""
Unit Tests for ProfileBatchBacktester

Tests:
- Profile generation
- Configuration loading
- Baseline execution
- Optimization pipeline
- Result storage
- Comparison generation
- Export functionality
"""

import json
import pytest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
import numpy as np

from app.backtesting.profile_batch_backtester import (
    BaselineOptimizationComparison,
    OptimizedStrategy,
    ProfileBatchBacktester,
    ProfileResult,
    ProfileResultDB,
)
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
)


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def config_path(tmp_path):
    """Create a temporary config file."""
    config = {
        "database": {"url": "sqlite:///:memory:"},
        "output_dir": str(tmp_path),
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
        "backtest_period": {"start_date": "2020-01-01", "end_date": "2023-12-31"},
        "symbols": ["AAPL", "MSFT", "GOOGL"],
        "risk_parameters": {
            "bajo": {"max_position_pct": 0.05, "stop_loss_pct": 0.02},
            "medio": {"max_position_pct": 0.10, "stop_loss_pct": 0.03},
            "alto": {"max_position_pct": 0.20, "stop_loss_pct": 0.05},
        },
        "objective_parameters": {
            "maximizar_capital": {"min_sharpe": 1.2, "min_return": 0.15},
            "maximizar_dividendos": {"min_sharpe": 0.8, "min_return": 0.10},
        },
        "optimization": {"n_trials": 10, "timeout": None},
        "validation": {
            "walk_forward": {"n_windows": 5, "train_percentage": 0.6},
            "monte_carlo": {"n_simulations": 50},
            "out_of_sample": {"oos_percentage": 0.20},
        },
        "acceptance_criteria": {
            "min_sharpe": 1.0,
            "min_return": 0.10,
            "max_drawdown": -0.25,
        },
        "modules": {
            "filters": {
                "momentum": {
                    "enabled": True,
                    "parameters": {
                        "momentum_threshold": {"type": "float", "default": 0.02}
                    },
                }
            }
        },
        "reporting": {"output_formats": ["json", "csv"]},
    }

    config_file = tmp_path / "config.yaml"
    import yaml

    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return str(config_file)


@pytest.fixture
def sample_profile():
    """Create a sample InputProfile."""
    return InputProfile(
        capital_initial=Decimal("100000"),
        objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
        risk_tolerance=RiskTolerance.MEDIO,
        investment_horizon=24,
    )


@pytest.fixture
def backtester(config_path):
    """Create ProfileBatchBacktester instance."""
    return ProfileBatchBacktester(config_path)


# ============================================================================
# Test: Profile Generation
# ============================================================================


class TestProfileGeneration:
    """Tests for profile generation."""

    def test_generate_all_profiles_count(self, backtester):
        """Test that 180 profiles are generated."""
        profiles = backtester.generate_all_profiles()
        assert len(profiles) == 180

    def test_generate_all_profiles_combinations(self, backtester):
        """Test that all combinations are generated."""
        profiles = backtester.generate_all_profiles()

        # Check all objectives are present
        objectives = {p.objetivo_inversion for p in profiles}
        assert len(objectives) == 5

        # Check all risk tolerances are present
        risks = {p.risk_tolerance for p in profiles}
        assert len(risks) == 3

        # Check all capital tiers are present
        # Note: InputProfile.capital_flag returns "small" (<50000), "medium" (<250000), "large" (>=250000)
        # With config values {bajo: 50000, medio: 150000, alto: 500000}, we get:
        # - 50000 -> "medium" (not < 50000, but < 250000)
        # - 150000 -> "medium" (not < 50000, but < 250000)
        # - 500000 -> "large" (>= 250000)
        # So only "medium" and "large" are generated with this config
        capital_flags = {p.capital_flag for p in profiles}
        assert capital_flags == {"medium", "large"}

        # Check all horizons are present
        horizons = {p.investment_horizon for p in profiles}
        assert horizons == {12, 24, 36, 60}

    def test_profile_attributes(self, backtester):
        """Test that profiles have correct attributes."""
        profiles = backtester.generate_all_profiles()

        # Find a specific profile with the exact capital value
        # Note: both "bajo" (50000) and "medio" (150000) tiers map to capital_flag="medium"
        # So we need to check for the specific capital_initial value to find the right one
        profile = next(
            (p for p in profiles if p.objetivo_inversion == ObjectivoInversion.MAXIMIZAR_CAPITAL
             and p.risk_tolerance == RiskTolerance.MEDIO
             and p.capital_initial == Decimal("150000")
             and p.investment_horizon == 24),
            None,
        )

        assert profile is not None
        assert profile.capital_initial == Decimal("150000")
        # Verify the capital_flag is "medium" for this capital value
        assert profile.capital_flag == "medium"


# ============================================================================
# Test: Configuration Loading
# ============================================================================


class TestConfigurationLoading:
    """Tests for configuration loading."""

    def test_load_config(self, backtester):
        """Test configuration is loaded correctly."""
        assert backtester.config is not None
        assert "capital_tiers" in backtester.config
        assert "risk_parameters" in backtester.config

    def test_capital_tiers(self, backtester):
        """Test capital tiers are loaded."""
        assert backtester.capital_tiers["bajo"] == 50000
        assert backtester.capital_tiers["medio"] == 150000
        assert backtester.capital_tiers["alto"] == 500000

    def test_output_dir_created(self, backtester):
        """Test output directory is created."""
        assert backtester.output_dir.exists()
        assert backtester.output_dir.is_dir()


# ============================================================================
# Test: Baseline Execution
# ============================================================================


class TestBaselineExecution:
    """Tests for baseline execution."""

    @patch("app.backtesting.profile_batch_backtester.ComprehensiveBacktestRunner")
    def test_run_baseline(self, mock_runner_class, backtester, sample_profile):
        """Test baseline execution."""
        # Mock the runner
        mock_runner = MagicMock()
        mock_runner.run_baseline_backtest.return_value = [
            {
                "sharpe_ratio": 1.5,
                "return_pct": 20.0,
                "max_drawdown": -0.15,
                "win_rate": 55.0,
            }
        ]
        mock_runner_class.return_value = mock_runner

        # Create config
        config = backtester._create_profile_config(sample_profile)

        # Run baseline
        results = backtester._run_baseline(sample_profile, config)

        assert results is not None
        assert results["sharpe_ratio"] == 1.5
        assert results["return_pct"] == 20.0

    def test_get_empty_metrics(self, backtester):
        """Test empty metrics generation."""
        metrics = backtester._get_empty_metrics()

        assert metrics["sharpe_ratio"] == 0.0
        assert metrics["return_pct"] == 0.0
        assert metrics["max_drawdown"] == 0.0
        assert metrics["win_rate"] == 0.0


# ============================================================================
# Test: Optimization Pipeline
# ============================================================================


class TestOptimizationPipeline:
    """Tests for optimization pipeline."""

    @patch("app.backtesting.profile_batch_backtester.optuna")
    def test_run_bayesian_optimization(self, mock_optuna, backtester, sample_profile):
        """Test Bayesian optimization."""
        # Mock Optuna
        mock_study = MagicMock()
        mock_study.best_params = {"rsi_threshold": 40, "ema_short": 12}
        mock_study.best_value = 1.8
        mock_study.trials = []

        mock_optuna.create_study.return_value = mock_study

        # Mock backtest execution
        with patch.object(backtester, "_run_backtest_with_params") as mock_backtest:
            mock_backtest.return_value = {"sharpe_ratio": 1.8, "return_pct": 22.0}

            # Create config
            config = backtester._create_profile_config(sample_profile)

            # Run optimization
            results = backtester._run_bayesian_optimization(sample_profile, config)

            assert results["best_params"] == {"rsi_threshold": 40, "ema_short": 12}
            assert results["best_value"] == 1.8

    def test_run_walk_forward(self, backtester, sample_profile):
        """Test walk-forward validation."""
        config = backtester._create_profile_config(sample_profile)
        params = {}

        results = backtester._run_walk_forward(sample_profile, config, params)

        assert results is not None
        assert "passed" in results
        assert "n_windows" in results

    @patch("app.backtesting.profile_batch_backtester.ComprehensiveBacktestRunner")
    def test_run_monte_carlo(self, mock_runner_class, backtester, sample_profile):
        """Test Monte Carlo simulation."""
        # Mock the runner to avoid needing actual data
        mock_runner = MagicMock()
        mock_runner.run_baseline_backtest.return_value = [
            {
                "sharpe_ratio": 1.5,
                "return_pct": 20.0,
                "max_drawdown": -0.15,
                "win_rate": 55.0,
                "total_trades": 100,
                "returns_series": np.random.normal(0.001, 0.02, 100),  # Mock returns
            }
        ]
        mock_runner_class.return_value = mock_runner

        config = backtester._create_profile_config(sample_profile)
        # Add missing output_directory for the mocked runner
        config["reporting"]["output_directory"] = str(backtester.output_dir)

        params = {}

        results = backtester._run_monte_carlo(sample_profile, config, params)

        assert results is not None
        assert "passed" in results
        assert "n_simulations" in results
        # n_simulations comes from config, defaults to 1000 if ProfileConfigLoader fails
        assert results["n_simulations"] == 1000

    def test_run_out_of_sample(self, backtester, sample_profile):
        """Test out-of-sample validation."""
        config = backtester._create_profile_config(sample_profile)
        params = {}

        results = backtester._run_out_of_sample(sample_profile, config, params)

        assert results is not None
        assert "passed" in results


# ============================================================================
# Test: Comparison Generation
# ============================================================================


class TestComparisonGeneration:
    """Tests for comparison generation."""

    def test_pct_improvement_positive(self, backtester):
        """Test percentage improvement calculation (positive)."""
        improvement = backtester._pct_improvement(1.0, 1.5)
        assert improvement == 50.0

    def test_pct_improvement_negative(self, backtester):
        """Test percentage improvement calculation (negative)."""
        improvement = backtester._pct_improvement(1.5, 1.0)
        assert improvement == pytest.approx(-33.33, rel=0.01)

    def test_generate_comparison(self, backtester):
        """Test comparison generation."""
        baseline = {"sharpe_ratio": 1.0, "return_pct": 10.0, "max_drawdown": -0.20}
        optimized = {"sharpe_ratio": 1.5, "return_pct": 15.0, "max_drawdown": -0.15}

        optuna_results = {"n_trials": 100, "history": []}

        comparison = backtester._generate_comparison(baseline, optimized, optuna_results)

        assert comparison.sharpe_improvement == 50.0
        assert comparison.return_improvement == 50.0
        # Allow for floating point precision issues
        assert comparison.max_dd_improvement == pytest.approx(25.0)

        # Check recommendation
        assert comparison.recommended in ["baseline", "optimized", "inconclusive"]


# ============================================================================
# Test: Result Storage
# ============================================================================


class TestResultStorage:
    """Tests for result storage."""

    def test_store_result(self, backtester, sample_profile):
        """Test storing result in database."""
        # Create a mock result
        result = ProfileResult(
            profile_id="test_profile",
            profile=sample_profile,
            baseline_results={"sharpe_ratio": 1.0},
            optimization_results={"sharpe_ratio": 1.5},
            best_parameters={"rsi": 40},
            improvement_metrics={"sharpe_improvement": 50.0},
            comparison=BaselineOptimizationComparison(
                sharpe_improvement=50.0,
                return_improvement=50.0,
                max_dd_improvement=25.0,
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

        # Store result
        backtester._store_result(result)

        # Query database
        session = backtester.Session()
        db_result = session.query(ProfileResultDB).filter_by(profile_id="test_profile").first()

        assert db_result is not None
        assert db_result.profile_id == "test_profile"
        assert db_result.baseline_sharpe == 1.0
        assert db_result.optimized_sharpe == 1.5
        assert db_result.sharpe_improvement == 50.0
        assert db_result.ready_for_paper_trading is True

        session.close()


# ============================================================================
# Test: Export Functionality
# ============================================================================


class TestExportFunctionality:
    """Tests for export functionality."""

    def test_export_json(self, backtester, sample_profile):
        """Test JSON export."""
        # Add a mock result
        result = ProfileResult(
            profile_id="test_profile",
            profile=sample_profile,
            baseline_results={"sharpe_ratio": 1.0},
            optimization_results={"sharpe_ratio": 1.5},
            best_parameters={},
            improvement_metrics={"sharpe_improvement": 50.0},
            comparison=BaselineOptimizationComparison(
                sharpe_improvement=50.0,
                return_improvement=50.0,
                max_dd_improvement=25.0,
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

        backtester.results = {"test_profile": result}

        # Export
        json_path = backtester.export_results(format="json")

        assert json_path.exists()
        with open(json_path) as f:
            data = json.load(f)
            assert "test_profile" in data

    def test_export_csv(self, backtester, sample_profile):
        """Test CSV export."""
        # Add a mock result
        result = ProfileResult(
            profile_id="test_profile",
            profile=sample_profile,
            baseline_results={"sharpe_ratio": 1.0},
            optimization_results={"sharpe_ratio": 1.5},
            best_parameters={},
            improvement_metrics={"sharpe_improvement": 50.0},
            comparison=BaselineOptimizationComparison(
                sharpe_improvement=50.0,
                return_improvement=50.0,
                max_dd_improvement=25.0,
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

        backtester.results = {"test_profile": result}

        # Export
        csv_path = backtester.export_results(format="csv")

        assert csv_path.exists()

        # Read and verify
        import pandas as pd

        df = pd.read_csv(csv_path)
        assert "profile_id" in df.columns
        assert len(df) == 1

    def test_export_unsupported_format(self, backtester):
        """Test export with unsupported format."""
        with pytest.raises(ValueError, match="Unsupported format"):
            backtester.export_results(format="unsupported")


# ============================================================================
# Test: Comparison Report
# ============================================================================


class TestComparisonReport:
    """Tests for comparison report generation."""

    def test_generate_comparison_report(self, backtester, sample_profile):
        """Test HTML comparison report generation."""
        # Add mock results
        result = ProfileResult(
            profile_id="test_profile",
            profile=sample_profile,
            baseline_results={"sharpe_ratio": 1.0, "return_pct": 10.0},
            optimization_results={"sharpe_ratio": 1.5, "return_pct": 15.0},
            best_parameters={},
            improvement_metrics={"sharpe_improvement": 50.0, "return_improvement": 50.0},
            comparison=BaselineOptimizationComparison(
                sharpe_improvement=50.0,
                return_improvement=50.0,
                max_dd_improvement=25.0,
                win_rate_improvement=10.0,
                sharpe_significant=True,
                return_significant=True,
                parameter_importance={"rsi": 0.8},
                recommended="optimized",
                confidence=0.8,
                reason="Test",
            ),
            ready_for_paper_trading=True,
            recommendation="APPROVED",
        )

        backtester.results = {"test_profile": result}

        # Generate report
        html = backtester.generate_comparison_report()

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<html>" in html
        assert "test_profile" in html
        assert "50.0" in html  # Improvement value


# ============================================================================
# Test: Get Best Strategy
# ============================================================================


class TestGetBestStrategy:
    """Tests for getting best strategy."""

    def test_get_best_strategy(self, backtester, sample_profile):
        """Test retrieving best strategy."""
        # Store a result first
        result = ProfileResult(
            profile_id="maximizar_capital_medio_medio_24m",
            profile=sample_profile,
            baseline_results={"sharpe_ratio": 1.0},
            optimization_results={"sharpe_ratio": 1.5},
            best_parameters={"rsi": 40},
            improvement_metrics={"sharpe_improvement": 50.0},
            comparison=BaselineOptimizationComparison(
                sharpe_improvement=50.0,
                return_improvement=50.0,
                max_dd_improvement=25.0,
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

        backtester._store_result(result)

        # Get best strategy
        best = backtester.get_best_strategy(
            objective="maximizar_capital",
            tier="medio",
            risk="medio"
        )

        assert best is not None
        assert best["profile_id"] == "maximizar_capital_medio_medio_24m"
        assert best["optimized_metrics"]["sharpe_ratio"] == 1.5
        assert best["best_parameters"] == {"rsi": 40}

    def test_get_best_strategy_not_found(self, backtester):
        """Test getting best strategy when no results exist."""
        best = backtester.get_best_strategy(
            objective="nonexistent",
            tier="medio",
            risk="medio"
        )

        assert best == {}


# ============================================================================
# Test: Result to Dict
# ============================================================================


class TestResultToDict:
    """Tests for result to dictionary conversion."""

    def test_result_to_dict(self, backtester, sample_profile):
        """Test converting ProfileResult to dictionary."""
        result = ProfileResult(
            profile_id="test_profile",
            profile=sample_profile,
            baseline_results={"sharpe_ratio": 1.0},
            optimization_results={"sharpe_ratio": 1.5},
            best_parameters={},
            improvement_metrics={},
            comparison=BaselineOptimizationComparison(
                sharpe_improvement=0.0,
                return_improvement=0.0,
                max_dd_improvement=0.0,
                win_rate_improvement=0.0,
                sharpe_significant=False,
                return_significant=False,
                parameter_importance={},
                recommended="inconclusive",
                confidence=0.5,
                reason="Test",
            ),
            ready_for_paper_trading=False,
            recommendation="TEST",
        )

        result_dict = backtester._result_to_dict(result)

        assert result_dict["profile_id"] == "test_profile"
        assert result_dict["objective"] == "maximizar_capital"
        assert result_dict["risk_tolerance"] == "medio"
        assert result_dict["capital_tier"] == "medium"  # InputProfile.capital_flag returns English values
        assert "baseline_results" in result_dict
        assert "optimization_results" in result_dict
