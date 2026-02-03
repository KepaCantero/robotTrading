"""
Test suite for app.backtesting.profile_batch_backtester_refactored

Tests the refactored service layer architecture with proper mocking of external dependencies.
Addresses TST-004: Ensure external dependencies (ComprehensiveBacktestRunner, services) are properly mocked.

Coverage:
- Service layer initialization
- Profile generation with service delegation
- Fallback tracking (thread-safe)
- Error handling with structured logging
- Multi-strategy validation
- Temporary config cleanup
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from datetime import datetime
from pathlib import Path
import tempfile
import threading
from decimal import Decimal

from app.backtesting.profile_batch_backtester_refactored import (
    ProfileBatchBacktester,
)
from app.backtesting.services import (
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


class TestProfileBatchBacktesterRefactoredImport:
    """Test module imports and initialization for refactored version."""

    def test_import_profile_batch_backtester_refactored(self):
        """Test that ProfileBatchBacktester (refactored) can be imported."""
        from app.backtesting.profile_batch_backtester_refactored import ProfileBatchBacktester
        assert ProfileBatchBacktester is not None

    def test_import_service_models(self):
        """Test that service layer models can be imported."""
        from app.backtesting.services import (
            ProfileResultDB,
            BaselineOptimizationComparison,
            OptimizedStrategy,
            ProfileResult,
        )
        assert ProfileResultDB is not None
        assert BaselineOptimizationComparison is not None
        assert OptimizedStrategy is not None
        assert ProfileResult is not None


class TestServiceLayerInitialization:
    """Test service layer initialization."""

    def test_initialization_with_service_layer(self):
        """Test initialization creates all service layer components."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000
  medio: 100000
  alto: 500000

investment_horizons:
  corto: 6
  medio: 12
  largo: 24

optimization:
  n_trials: 10

validation:
  walk_forward:
    n_windows: 3
  monte_carlo:
    n_simulations: 100
  out_of_sample:
    start_date: "2024-01-01"
    end_date: "2024-06-30"

acceptance_criteria:
  min_sharpe: 0.5
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        
                        # Verify all services are initialized
                        assert backtester.config_service is not None
                        assert backtester.fallback_tracker is not None
                        assert backtester.database_service is not None
                        assert backtester.metrics_service is not None
                        assert backtester.report_service is not None
                        assert backtester.profile_gen_service is not None
                        assert backtester.batch_exec_service is not None
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_initialization_missing_config(self):
        """Test initialization with missing config file."""
        with pytest.raises(FileNotFoundError):
            ProfileBatchBacktester(config_path="nonexistent_config.yaml")


class TestProfileGenerationWithServiceLayer:
    """Test profile generation using ProfileGenerationService."""

    def test_generate_all_profiles_delegates_to_service(self):
        """Test that generate_all_profiles delegates to ProfileGenerationService."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000
  medio: 100000
  alto: 500000

investment_horizons:
  corto: 6
  medio: 12
  largo: 24
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        profiles = backtester.generate_all_profiles()
                        
                        # Verify profiles generated correctly
                        assert isinstance(profiles, list)
                        assert len(profiles) > 0
                        assert all(isinstance(p, InputProfile) for p in profiles)
                        
                        # Verify calculation: 5 objectives × 3 risks × 3 tiers × 3 horizons = 135
                        # (assuming 3 horizons from config)
                        assert len(profiles) == 135  # 5 × 3 × 3 × 3
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_investment_horizons_dict_format(self):
        """Test loading investment horizons from dict format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  short: 12
  medium: 24
  long: 36
  very_long: 60
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        horizons = backtester.config_service.load_investment_horizons()
                        
                        # Should load dict values
                        assert horizons == [12, 24, 36, 60]
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_investment_horizons_list_format(self):
        """Test loading investment horizons from list format."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons: [6, 12, 18, 24]
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        horizons = backtester.config_service.load_investment_horizons()
                        
                        # Should load list directly
                        assert horizons == [6, 12, 18, 24]
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestFallbackTracker:
    """Test FallbackTracker thread-safe functionality."""

    def test_fallback_metrics_initialization(self):
        """Test that fallback metrics initialize correctly."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        metrics = backtester.get_fallback_metrics()
                        
                        # Should return dict with zero counts
                        assert isinstance(metrics, dict)
                        assert "profile_config_loader_fallback_count" in metrics
                        assert "profile_strategy_mapper_fallback_count" in metrics
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_fallback_tracker_thread_safety(self):
        """Test that FallbackTracker is thread-safe for parallel execution."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        
                        # Simulate parallel fallback tracking
                        def increment_fallback():
                            for _ in range(100):
                                backtester.fallback_tracker.increment_fallback_counter("test_source")
                        
                        threads = [threading.Thread(target=increment_fallback) for _ in range(10)]
                        for t in threads:
                            t.start()
                        for t in threads:
                            t.join()
                        
                        # Should have 10 threads × 100 increments = 1000
                        metrics = backtester.get_fallback_metrics()
                        assert metrics.get("test_source_fallback_count", 0) == 1000
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestMultiStrategyValidation:
    """Test multi-strategy mode validation (P2-003 fix)."""

    def test_multi_strategy_validation_with_mapper(self):
        """Test that multi_strategy mode validates ProfileStrategyMapper."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        # Mock ProfileStrategyMapper
                        with patch('app.backtesting.profile_batch_backtester_refactored.create_profile_mapper') as mock_mapper:
                            mock_mapper.return_value = MagicMock()
                            
                            backtester = ProfileBatchBacktester(config_path=config_path)
                            
                            # Create test profile
                            profile = InputProfile(
                                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                                risk_tolerance=RiskTolerance.ALTO,
                                capital_initial=Decimal("100000"),
                            )
                            
                            # Should not raise ValueError
                            try:
                                # This would normally run full pipeline, but we're just testing validation
                                # We'll mock the internal methods to avoid actual execution
                                with patch.object(backtester, '_create_profile_config', return_value={}):
                                    with patch.object(backtester, '_run_baseline', return_value={}):
                                        with patch.object(backtester, '_run_optimization_pipeline', return_value=MagicMock()):
                                            with patch.object(backtester.database_service, 'store_result'):
                                                result = backtester.run_single_profile(profile, multi_strategy=True)
                                                # If we get here without ValueError, validation passed
                            except ValueError as e:
                                if "ProfileStrategyMapper not initialized" in str(e):
                                    pytest.fail("Multi-strategy validation failed unexpectedly")
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_multi_strategy_validation_without_mapper_raises_error(self):
        """Test that multi_strategy mode raises ValueError without mapper."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        # Mock create_profile_mapper to return None
                        with patch('app.backtesting.profile_batch_backtester_refactored.create_profile_mapper', return_value=None):
                            backtester = ProfileBatchBacktester(config_path=config_path)
                            
                            # Create test profile
                            profile = InputProfile(
                                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                                risk_tolerance=RiskTolerance.ALTO,
                                capital_initial=Decimal("100000"),
                            )
                            
                            # Should raise ValueError
                            with pytest.raises(ValueError) as exc_info:
                                backtester.run_single_profile(profile, multi_strategy=True)
                            
                            assert "ProfileStrategyMapper not initialized" in str(exc_info.value)
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestErrorHandlingWithStructuredLogging:
    """Test error handling with structured logging context (P1-002 fix)."""

    def test_baseline_error_logging_context(self):
        """Test that baseline errors include structured context."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        
                        profile = InputProfile(
                            objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                            risk_tolerance=RiskTolerance.ALTO,
                            capital_initial=Decimal("100000"),
                        )
                        
                        # Mock _run_baseline to fail
                        with patch.object(backtester, '_run_baseline') as mock_baseline:
                            mock_baseline.side_effect = RuntimeError("Test error")
                            
                            # Mock logger to capture the error
                            with patch('app.backtesting.profile_batch_backtester_refactored.logger') as mock_logger:
                                try:
                                    backtester.run_single_profile(profile)
                                except RuntimeError:
                                    pass
                                
                                # Verify error was logged with context
                                error_calls = [call for call in mock_logger.error.call_args_list]
                                assert len(error_calls) > 0
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestTemporaryConfigCleanup:
    """Test temporary config file cleanup (resource leak prevention)."""

    def test_temp_config_cleanup_on_success(self):
        """Test that temp config files are cleaned up on success."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        # Patch ComprehensiveBacktestRunner to avoid actual execution
                        with patch('app.backtesting.profile_batch_backtester_refactored.ComprehensiveBacktestRunner') as MockRunner:
                            mock_instance = MockRunner.return_value
                            mock_instance.run_baseline_backtest.return_value = [{
                                "sharpe_ratio": 1.5,
                                "total_pnl": 10000,
                            }]
                            
                            backtester = ProfileBatchBacktester(config_path=config_path)
                            
                            profile = InputProfile(
                                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                                risk_tolerance=RiskTolerance.ALTO,
                                capital_initial=Decimal("100000"),
                            )
                            
                            # Run baseline to create temp config
                            config = backtester._create_profile_config(profile)
                            result = backtester._run_baseline(profile, config)
                            
                            # Check for leftover temp files in output_dir
                            temp_files = list(Path(backtester.output_dir).glob("temp_*.yaml"))
                            # Temp files should be cleaned up
                            assert len(temp_files) == 0 or all(f.exists() for f in temp_files) is False
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_temp_config_cleanup_on_error(self):
        """Test that temp config files are cleaned up even on error."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        # Patch ComprehensiveBacktestRunner to raise error
                        with patch('app.backtesting.profile_batch_backtester_refactored.ComprehensiveBacktestRunner') as MockRunner:
                            mock_instance = MockRunner.return_value
                            mock_instance.run_baseline_backtest.side_effect = RuntimeError("Test error")
                            
                            backtester = ProfileBatchBacktester(config_path=config_path)
                            
                            profile = InputProfile(
                                objetivo_inversion=ObjectivoInversion.MAXIMIZAR_CAPITAL,
                                risk_tolerance=RiskTolerance.ALTO,
                                capital_initial=Decimal("100000"),
                            )
                            
                            # Run baseline to create temp config (will fail)
                            config = backtester._create_profile_config(profile)
                            result = backtester._run_baseline(profile, config)
                            
                            # Should return empty metrics and clean up temp file
                            assert result.get("sharpe_ratio", 0) == 0
                            
                            # Check for leftover temp files
                            temp_files = list(Path(backtester.output_dir).glob("temp_*.yaml"))
                            assert len(temp_files) == 0
        finally:
            Path(config_path).unlink(missing_ok=True)


class TestServiceDelegation:
    """Test that methods properly delegate to service layer."""

    def test_get_best_strategy_delegates_to_database_service(self):
        """Test that get_best_strategy delegates to DatabaseService."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        
                        # Mock database service
                        mock_best_config = {"sharpe_ratio": 2.0}
                        with patch.object(backtester.database_service, 'get_best_strategy', return_value=mock_best_config):
                            result = backtester.get_best_strategy("maximizar_capital", "medio", "alto")
                            
                            # Verify delegation
                            backtester.database_service.get_best_strategy.assert_called_once_with(
                                "maximizar_capital", "medio", "alto"
                            )
                            assert result == mock_best_config
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_generate_comparison_report_delegates_to_report_service(self):
        """Test that generate_comparison_report delegates to ReportGenerationService."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        
                        # Mock results
                        backtester.results = {"test_profile": MagicMock()}
                        
                        # Mock report service
                        mock_html = "<html>Report</html>"
                        with patch.object(backtester.report_service, 'generate_comparison_report', return_value=mock_html):
                            result = backtester.generate_comparison_report()
                            
                            # Verify delegation
                            backtester.report_service.generate_comparison_report.assert_called_once_with(
                                backtester.results
                            )
                            assert result == mock_html
        finally:
            Path(config_path).unlink(missing_ok=True)

    def test_export_results_delegates_to_report_service(self):
        """Test that export_results delegates to ReportGenerationService."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            config_content = """
database:
  url: "sqlite:///test.db"

output_dir: "test_output"

capital_tiers:
  bajo: 50000

investment_horizons:
  corto: 6
"""
            f.write(config_content)
            config_path = f.name

        try:
            with patch('app.backtesting.services.database_service.create_engine'):
                with patch('app.backtesting.services.database_service.sessionmaker'):
                    with patch('app.backtesting.services.database_service.Base.metadata.create_all'):
                        backtester = ProfileBatchBacktester(config_path=config_path)
                        
                        # Mock results
                        backtester.results = {"test_profile": MagicMock()}
                        
                        # Mock report service
                        mock_path = Path("test_export.json")
                        with patch.object(backtester.report_service, 'export_results', return_value=mock_path):
                            result = backtester.export_results(format="json")
                            
                            # Verify delegation
                            backtester.report_service.export_results.assert_called_once_with(
                                backtester.results, "json"
                            )
                            assert result == mock_path
        finally:
            Path(config_path).unlink(missing_ok=True)
