"""
Unit tests for core backtesting modules.
"""

import pytest
from decimal import Decimal
from pathlib import Path
from datetime import datetime
from typing import List, Any, Dict

from app.backtesting.core.config_loader import BacktestConfigLoader
from app.backtesting.core.executor import (
    BacktestExecutor,
    SimpleBacktestExecutor,
    BacktestExecutorFactory,
)
from app.backtesting.core.orchestrator import (
    BacktestDefaults,
    BacktestOrchestrator,
    BoundedResults,
    OrchestrationResult,
)
from app.backtesting.core.facade import BacktestRunnerFacade, create_backtest_runner
from app.backtesting.models import BacktestConfig


class TestBacktestDefaults:
    """Test BacktestDefaults constants."""

    def test_defaults_are_positive(self):
        """Verify default values are positive where expected."""
        assert BacktestDefaults.COMMISSION > 0
        assert BacktestDefaults.SLIPPAGE > 0
        assert BacktestDefaults.INITIAL_CAPITAL > 0
        assert BacktestDefaults.MAX_POSITION_SIZE > 0

    def test_metric_thresholds_are_sensible(self):
        """Verify metric thresholds are logically ordered."""
        assert BacktestDefaults.SHARPE_RATIO_EXCELLENT > BacktestDefaults.SHARPE_RATIO_GOOD
        assert BacktestDefaults.SHARPE_RATIO_GOOD > BacktestDefaults.SHARPE_RATIO_WARNING
        assert BacktestDefaults.WIN_RATE_EXCELLENT > BacktestDefaults.WIN_RATE_GOOD
        assert BacktestDefaults.WIN_RATE_GOOD > BacktestDefaults.WIN_RATE_WARNING


class TestBoundedResults:
    """Test BoundedResults container."""

    def test_initial_state(self):
        """Test initial state of container."""
        results = BoundedResults(maxlen=10)
        assert len(results) == 0
        assert results.get_all() == []

    def test_add_single_result(self):
        """Test adding single result."""
        results = BoundedResults(maxlen=10)
        results.add({'test': 'value'})
        assert len(results) == 1
        assert results.get_all()[0] == {'test': 'value'}

    def test_extend_results(self):
        """Test extending with multiple results."""
        results = BoundedResults(maxlen=10)
        results.extend(
            [
                {'test': 'value1'},
                {'test': 'value2'},
                {'test': 'value3'},
            ]
        )
        assert len(results) == 3

    def test_get_latest(self):
        """Test getting latest results."""
        results = BoundedResults(maxlen=10)
        for i in range(5):
            results.add({'index': i})

        latest = results.get_latest(2)
        assert len(latest) == 2
        assert latest[0]['index'] == 3
        assert latest[1]['index'] == 4

    def test_clear(self):
        """Test clearing results."""
        results = BoundedResults(maxlen=10)
        results.add({'test': 'value'})
        results.clear()
        assert len(results) == 0

    def test_maxlen_enforcement(self):
        """Test that maxlen is enforced."""
        results = BoundedResults(maxlen=5)
        for i in range(10):
            results.add({'index': i})

        # Should have less than or equal to maxlen
        assert len(results) <= 5


class TestBacktestConfigLoader:
    """Test BacktestConfigLoader."""

    def test_load_from_valid_file(self, tmp_path):
        """Test loading from valid YAML file."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
backtest:
  initial_capital: 100000
  commission_per_trade: 1.0
  slippage: 0.1
  max_position_size: 0.20

input:
  start_date: "2023-01-01"
  end_date: "2023-12-31"
"""
        )

        loader = BacktestConfigLoader(str(config_file))
        assert loader.raw_config is not None
        assert 'backtest' in loader.raw_config

    def test_get_backtest_config(self, tmp_path):
        """Test getting BacktestConfig object."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
backtest:
  initial_capital: 100000
  commission_per_trade: 1.0
  slippage: 0.1
"""
        )

        loader = BacktestConfigLoader(str(config_file))
        config = loader.get_backtest_config()

        assert config.initial_capital == Decimal('100000')
        assert config.commission_per_trade == Decimal('1.0')
        assert config.slippage_percentage == Decimal('0.1')

    def test_file_not_found(self):
        """Test FileNotFoundError for missing file."""
        with pytest.raises(FileNotFoundError):
            BacktestConfigLoader("/nonexistent/path.yaml")

    def test_get_sections(self, tmp_path):
        """Test getting configuration sections."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
strategy:
  name: test_strategy
  enabled: true

execution:
  parallel: true
  max_workers: 4
"""
        )

        loader = BacktestConfigLoader(str(config_file))

        strategy_config = loader.get_strategy_config()
        assert strategy_config['name'] == 'test_strategy'

        execution_config = loader.get_execution_config()
        assert execution_config['parallel'] is True


class TestBacktestExecutor:
    """Test BacktestExecutor classes."""

    def test_simple_executor_validate_inputs(self):
        """Test input validation."""
        config = BacktestConfig(
            initial_capital=Decimal('100000'),
            commission_per_trade=Decimal('1.0'),
            slippage_percentage=Decimal('0.1'),
        )

        executor = SimpleBacktestExecutor(config)

        # Should raise for empty quotes
        with pytest.raises(ValueError, match="Quotes cannot be empty"):
            executor.validate_inputs([], None)

        # Should raise for None strategy
        with pytest.raises(ValueError, match="Strategy cannot be None"):
            executor.validate_inputs([{}], None)

    def test_executor_factory(self):
        """Test executor factory."""
        config = BacktestConfig(
            initial_capital=Decimal('100000'),
            commission_per_trade=Decimal('1.0'),
            slippage_percentage=Decimal('0.1'),
        )

        # Test simple executor
        executor = BacktestExecutorFactory.create(config, executor_type='simple')
        assert isinstance(executor, SimpleBacktestExecutor)

        # Test parallel executor
        from app.backtesting.core.executor import ParallelBacktestExecutor

        executor = BacktestExecutorFactory.create(config, executor_type='parallel')
        assert isinstance(executor, ParallelBacktestExecutor)

        # Test process pool executor
        from app.backtesting.core.executor import ProcessPoolBacktestExecutor

        executor = BacktestExecutorFactory.create(config, executor_type='process', max_workers=4)
        assert isinstance(executor, ProcessPoolBacktestExecutor)

        # Test invalid executor type
        with pytest.raises(ValueError, match="Unknown executor type"):
            BacktestExecutorFactory.create(config, executor_type='invalid_type')


class TestOrchestrationResult:
    """Test OrchestrationResult."""

    def test_empty_results(self):
        """Test summary with no results."""
        result = OrchestrationResult([])
        assert result.summary['total'] == 0
        assert result.summary['successful'] == 0
        assert result.summary['failed'] == 0

    def test_summary_with_dict_results(self):
        """Test summary with dictionary results."""
        results = [
            {'final_capital': 110000, 'sharpe_ratio': 1.5},
            {'final_capital': 105000, 'sharpe_ratio': 1.2},
            {'final_capital': -5000, 'sharpe_ratio': 0.8},  # Failed (negative)
        ]

        result = OrchestrationResult(results)
        summary = result.summary

        assert summary['total'] == 3
        assert summary['successful'] == 2
        assert summary['failed'] == 1

    def test_filter_results(self):
        """Test filtering results."""
        results = [
            {'test_type': 'baseline', 'sharpe_ratio': 1.5},
            {'test_type': 'learning', 'sharpe_ratio': 1.2},
            {'test_type': 'baseline', 'sharpe_ratio': 1.8},
        ]

        orchestration_result = OrchestrationResult(results)
        filtered = orchestration_result.filter_results(test_type='baseline')

        assert len(filtered) == 2


class TestBacktestOrchestrator:
    """Test BacktestOrchestrator."""

    def test_initialization(self):
        """Test orchestrator initialization."""
        config = BacktestConfig(
            initial_capital=Decimal('100000'),
            commission_per_trade=Decimal('1.0'),
            slippage_percentage=Decimal('0.1'),
        )

        orchestrator = BacktestOrchestrator(config)
        assert orchestrator.config == config
        assert orchestrator.execution_count == 0

    def test_execution_count_increments(self):
        """Test that execution count increments."""
        config = BacktestConfig(
            initial_capital=Decimal('100000'),
            commission_per_trade=Decimal('1.0'),
            slippage_percentage=Decimal('0.1'),
        )

        orchestrator = BacktestOrchestrator(config)

        # Mock executor that returns a result
        from unittest.mock import Mock

        mock_executor = Mock()
        mock_result = Mock()
        mock_result.final_capital = Decimal('110000')
        mock_result.total_return = Decimal('10.0')
        mock_result.performance = None
        mock_result.strategy_name = 'test'
        mock_executor.execute.return_value = mock_result

        orchestrator.executor = mock_executor
        orchestrator._run_single([], Mock())

        assert orchestrator.execution_count == 1


class TestBacktestRunnerFacade:
    """Test BacktestRunnerFacade."""

    def test_initialization(self, tmp_path):
        """Test facade initialization."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
backtest:
  initial_capital: 100000

input:
  start_date: "2023-01-01"
  end_date: "2023-12-31"

reporting:
  output_directory: "/tmp/test_reports"
"""
        )

        facade = BacktestRunnerFacade(str(config_file))
        assert facade.backtest_config is not None
        assert facade.backtest_config.initial_capital == Decimal('100000')

    def test_create_backtest_runner_factory(self, tmp_path):
        """Test factory function."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
backtest:
  initial_capital: 100000

input:
  start_date: "2023-01-01"
  end_date: "2023-12-31"

reporting:
  output_directory: "/tmp/test_reports"
"""
        )

        facade = create_backtest_runner(str(config_file))
        assert isinstance(facade, BacktestRunnerFacade)

    def test_clear_results(self, tmp_path):
        """Test clearing results."""
        config_file = tmp_path / "test_config.yaml"
        config_file.write_text(
            """
backtest:
  initial_capital: 100000

input:
  start_date: "2023-01-01"
  end_date: "2023-12-31"

reporting:
  output_directory: "/tmp/test_reports"
"""
        )

        facade = BacktestRunnerFacade(str(config_file))
        facade.results.add({'test': 'value'})
        assert len(facade.results) == 1

        facade.clear_results()
        assert len(facade.results) == 0
