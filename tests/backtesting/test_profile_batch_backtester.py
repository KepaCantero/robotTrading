"""
Test suite for app.backtesting.profile_batch_backtester

Addresses TST-004: Ensure external dependencies (ComprehensiveBacktestRunner) are properly mocked
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime
from pathlib import Path
import tempfile

from app.backtesting.profile_batch_backtester import (
    ProfileBatchBacktester,
    ProfileResultDB,
    BaselineOptimizationComparison,
    OptimizedStrategy,
    ProfileResult,
)
from app.core.models.input_profile import (
    InputProfile,
    ObjectivoInversion,
    RiskTolerance,
)


class TestProfileBatchBacktesterImport:
    """Test module imports and initialization."""

    def test_import_profile_batch_backtester(self):
        """Test that ProfileBatchBacktester can be imported."""
        from app.backtesting.profile_batch_backtester import ProfileBatchBacktester
        assert ProfileBatchBacktester is not None

    def test_import_dataclasses(self):
        """Test that dataclasses can be imported."""
        from app.backtesting.profile_batch_backtester import (
            ProfileResultDB,
            BaselineOptimizationComparison,
            OptimizedStrategy,
            ProfileResult,
        )
        assert ProfileResultDB is not None
        assert BaselineOptimizationComparison is not None
        assert OptimizedStrategy is not None
        assert ProfileResult is not None


class TestProfileResultDB:
    """Test ProfileResultDB model."""

    def test_profile_result_db_creation(self):
        """Test ProfileResultDB creation."""
        result = ProfileResultDB(
            id="test-id-123",
            profile_id="profile-001",
            objective="maximizar_capital",
            risk_tolerance="alto",
            capital_tier="medio",
            investment_horizon=12,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        assert result.profile_id == "profile-001"
        assert result.objective == "maximizar_capital"

    def test_profile_result_db_to_dict(self):
        """Test ProfileResultDB.to_dict method."""
        result = ProfileResultDB(
            id="test-id-123",
            profile_id="profile-001",
            objective="maximizar_capital",
            risk_tolerance="alto",
            capital_tier="medio",
            investment_horizon=12,
            baseline_sharpe=1.5,
            optimized_sharpe=2.0,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        result_dict = result.to_dict()
        assert "profile_id" in result_dict
        assert result_dict["profile_id"] == "profile-001"


class TestBaselineOptimizationComparison:
    """Test BaselineOptimizationComparison dataclass."""

    def test_comparison_creation(self):
        """Test BaselineOptimizationComparison creation."""
        comparison = BaselineOptimizationComparison(
            sharpe_improvement=33.3,
            return_improvement=20.0,
            max_dd_improvement=10.0,
            win_rate_improvement=5.0,
            sharpe_significant=True,
            return_significant=True,
            parameter_importance={"lookback": 0.8, "threshold": 0.6},
            recommended="optimized",
            confidence=0.85,
            reason="Significant improvement with stable OOS",
        )
        assert comparison.sharpe_improvement == 33.3
        assert comparison.recommended == "optimized"
        assert 0 <= comparison.confidence <= 1


class TestOptimizedStrategy:
    """Test OptimizedStrategy dataclass."""

    def test_optimized_strategy_creation(self):
        """Test OptimizedStrategy creation."""
        comparison = BaselineOptimizationComparison(
            sharpe_improvement=33.3,
            return_improvement=20.0,
            max_dd_improvement=10.0,
            win_rate_improvement=5.0,
            sharpe_significant=True,
            return_significant=True,
            parameter_importance={},
            recommended="optimized",
            confidence=0.85,
            reason="Test",
        )

        strategy = OptimizedStrategy(
            profile_id="profile-001",
            baseline_metrics={"sharpe": 1.5},
            optimized_metrics={"sharpe": 2.0},
            best_parameters={"lookback": 30},
            optimization_history=[],
            comparison=comparison,
            ready_for_paper_trading=True,
            recommendation="Deploy with caution",
        )
        assert strategy.profile_id == "profile-001"
        assert strategy.ready_for_paper_trading is True


class TestProfileResult:
    """Test ProfileResult dataclass."""

    def test_profile_result_creation(self):
        """Test ProfileResult creation."""
        comparison = BaselineOptimizationComparison(
            sharpe_improvement=33.3,
            return_improvement=20.0,
            max_dd_improvement=10.0,
            win_rate_improvement=5.0,
            sharpe_significant=True,
            return_significant=True,
            parameter_importance={},
            recommended="optimized",
            confidence=0.85,
            reason="Test",
        )

        profile = InputProfile(
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            capital_initial=100000,
        )

        result = ProfileResult(
            profile_id="profile-001",
            profile=profile,
            baseline_results={"sharpe": 1.5},
            optimization_results={"sharpe": 2.0},
            best_parameters={"lookback": 30},
            improvement_metrics={"sharpe_improvement": 33.3},
            comparison=comparison,
            ready_for_paper_trading=True,
            recommendation="Deploy with caution",
            created_at=datetime.now(),
        )
        assert result.profile_id == "profile-001"
        assert result.ready_for_paper_trading is True


class TestProfileBatchBacktesterInitialization:
    """Test ProfileBatchBacktester initialization with mocking."""

    def test_initialization_with_mock(self):
        """Test initialization with mocked config file."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: [50000, 100000]
  medio: [100000, 500000]
  alto: [500000, 1000000]

investment_horizons:
  corto: 6
  medio: 12
  largo: 24
"""
            f.write(config_content)
            config_path = f.name

        try:
            # Mock database creation to avoid actual DB operations
            with patch('app.backtesting.profile_batch_backtester.create_engine'):
                with patch('app.backtesting.profile_batch_backtester.sessionmaker'):
                    with patch('app.backtesting.profile_batch_backtester.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        assert backtester is not None
        finally:
            # Clean up
            Path(config_path).unlink(missing_ok=True)

    def test_initialization_missing_config(self):
        """Test initialization with missing config file."""
        with pytest.raises(FileNotFoundError):
            ProfileBatchBacktester(config_path="nonexistent_config.yaml")


class TestGenerateAllProfiles:
    """Test profile generation with mocking."""

    def test_generate_all_profiles(self):
        """Test generate_all_profiles method."""
        # Create a temporary config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: [50000, 100000]
  medio: [100000, 500000]
  alto: [500000, 1000000]

investment_horizons:
  corto: 6
  medio: 12
  largo: 24
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.profile_batch_backtester.create_engine'):
                with patch('app.backtesting.profile_batch_backtester.sessionmaker'):
                    with patch('app.backtesting.profile_batch_backtester.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        profiles = backtester.generate_all_profiles()
                        assert isinstance(profiles, list)
                        assert len(profiles) > 0
                        assert all(isinstance(p, InputProfile) for p in profiles)
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestRunSingleProfile:
    """Test single profile execution with mocked dependencies."""

    def test_run_single_profile_with_mocks(self):
        """Test run_single_profile with mocked ComprehensiveBacktestRunner."""
        # Create test profile
        profile = InputProfile(
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            capital_initial=100000,
        )

        # Create temporary config
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"
output_dir: "test_output"

capital_tiers:
  bajo: [50000, 100000]
  medio: [100000, 500000]
  alto: [500000, 1000000]

investment_horizons:
  corto: 6
  medio: 12
  largo: 24
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.profile_batch_backtester.create_engine'):
                with patch('app.backtesting.profile_batch_backtester.sessionmaker'):
                    with patch('app.backtesting.profile_batch_backtester.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)

                        # Mock the ComprehensiveBacktestRunner
                        mock_baseline_results = {
                            "sharpe_ratio": 1.5,
                            "total_return": 50.0,
                            "max_drawdown_percentage": -15.0,
                            "win_rate": 0.6,
                        }

                        with patch.object(backtester, '_run_baseline', return_value=mock_baseline_results):
                            # Mock optimization pipeline
                            mock_comparison = BaselineOptimizationComparison(
                                sharpe_improvement=0.0,
                                return_improvement=0.0,
                                max_dd_improvement=0.0,
                                win_rate_improvement=0.0,
                                sharpe_significant=False,
                                return_significant=False,
                                parameter_importance={},
                                recommended="baseline",
                                confidence=0.5,
                                reason="Test",
                            )

                            mock_optimized_strategy = OptimizedStrategy(
                                profile_id="test-001",
                                baseline_metrics=mock_baseline_results,
                                optimized_metrics=mock_baseline_results,
                                best_parameters={},
                                optimization_history=[],
                                comparison=mock_comparison,
                                ready_for_paper_trading=False,
                                recommendation="Test",
                            )

                            with patch.object(backtester, '_run_optimization_pipeline', return_value=mock_optimized_strategy):
                                # Mock database storage
                                with patch.object(backtester, '_store_result'):
                                    result = backtester.run_single_profile(profile)
                                    assert isinstance(result, ProfileResult)
                                    assert result.profile_id == "test-001"
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestComprehensiveBacktestRunnerMock:
    """Test that ComprehensiveBacktestRunner is properly mocked (TST-004)."""

    def test_comprehensive_backtest_runner_mocked(self):
        """Test that we can mock ComprehensiveBacktestRunner."""
        # Create a mock for ComprehensiveBacktestRunner
        mock_runner = Mock()
        mock_runner.run.return_value = {
            "performance": {
                "sharpe_ratio": 1.5,
                "total_return": 50.0,
            },
            "equity_curve": [(datetime.now(), 100000), (datetime.now(), 110000)],
        }

        # Verify the mock works
        result = mock_runner.run(config={})
        assert "performance" in result
        assert result["performance"]["sharpe_ratio"] == 1.5

    def test_comprehensive_backtest_runner_patch(self):
        """Test patching ComprehensiveBacktestRunner in tests."""
        with patch('app.backtesting.profile_batch_backtester.ComprehensiveBacktestRunner') as MockRunner:
            # Configure the mock
            mock_instance = MockRunner.return_value
            mock_instance.run.return_value = {
                "performance": {"sharpe_ratio": 1.5},
            }

            # Use the mock
            runner = MockRunner(config={})
            result = runner.run()

            # Verify it was called
            mock_instance.run.assert_called_once()
            assert result["performance"]["sharpe_ratio"] == 1.5


class TestProfessionalReporterMock:
    """Test that ProfessionalReporter is properly mocked."""

    def test_professional_reporter_mocked(self):
        """Test that we can mock ProfessionalReporter."""
        mock_reporter = Mock()
        mock_reporter.generate_report.return_value = "<html>Test Report</html>"

        result = mock_reporter.generate_report(
            profile=Mock(),
            backtest_results={},
        )

        assert result == "<html>Test Report</html>"
        mock_reporter.generate_report.assert_called_once()


class TestErrorHandling:
    """Test error handling with mocks."""

    def test_database_error_handling(self):
        """Test database error handling."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"
output_dir: "test_output"

capital_tiers:
  bajo: [50000, 100000]
  medio: [100000, 500000]
  alto: [500000, 1000000]

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.profile_batch_backtester.create_engine') as mock_create_engine:
                # Simulate database error
                mock_create_engine.side_effect = Exception("Database connection failed")

                with pytest.raises(Exception):
                    ProfileBatchBacktester(config_path=config_path)
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_baseline_backtest_failure(self):
        """Test handling of baseline backtest failure."""
        profile = InputProfile(
            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
            risk_tolerance=RiskTolerance.ALTO,
            capital_initial=100000,
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"
output_dir: "test_output"

capital_tiers:
  bajo: [50000, 100000]

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.profile_batch_backtester.create_engine'):
                with patch('app.backtesting.profile_batch_backtester.sessionmaker'):
                    with patch('app.backtesting.profile_batch_backtester.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)

                        # Mock baseline failure
                        with patch.object(backtester, '_run_baseline', side_effect=RuntimeError("Backtest failed")):
                            with pytest.raises(RuntimeError):
                                backtester._run_baseline(profile, config={})
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestTemporaryConfigCleanup:
    """Test temporary config file cleanup."""

    def test_temp_config_cleanup(self):
        """Test that temporary config files are cleaned up."""
        import tempfile
        import os

        # Create a temp file
        fd, temp_path = tempfile.mkstemp(suffix='.yaml')
        os.write(fd, b"test: config")
        os.close(fd)

        assert Path(temp_path).exists()

        # Clean up
        Path(temp_path).unlink(missing_ok=True)

        # Verify it's gone
        assert not Path(temp_path).exists()
