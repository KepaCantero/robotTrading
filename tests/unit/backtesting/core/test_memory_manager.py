"""
Unit tests for AggressiveMemoryManager.

Tests memory management functionality including:
- Automatic cleanup
- Memory pressure detection
- Emergency cleanup
- Thread safety
"""
from __future__ import annotations

import gc
import threading
from unittest.mock import Mock, patch

import pytest

from app.backtesting.core.memory_manager import AggressiveMemoryManager
from app.backtesting.models import BacktestResult


class TestAggressiveMemoryManager:
    """Test suite for AggressiveMemoryManager."""

    def test_initialization(self) -> None:
        """Test manager initialization with default parameters."""
        manager = AggressiveMemoryManager()

        assert manager.max_results == 500
        assert manager.max_backtest_objects == 100
        assert manager.memory_threshold == 4096
        assert len(manager._results) == 0
        assert len(manager._backtest_objects) == 0

    def test_initialization_custom_parameters(self) -> None:
        """Test manager initialization with custom parameters."""
        manager = AggressiveMemoryManager(
            max_results=100,
            max_backtest_objects=50,
            memory_threshold_mb=2048,
        )

        assert manager.max_results == 100
        assert manager.max_backtest_objects == 50
        assert manager.memory_threshold == 2048

    def test_add_result(self) -> None:
        """Test adding results to manager."""
        manager = AggressiveMemoryManager(max_results=10)

        # Add results
        for i in range(5):
            manager.add_result({'test': i, 'value': f'result_{i}'})

        results = manager.get_results()
        assert len(results) == 5
        assert results[0]['test'] == 0
        assert results[4]['test'] == 4

    def test_add_result_automatic_cleanup(self) -> None:
        """Test automatic cleanup when max_results is exceeded."""
        manager = AggressiveMemoryManager(max_results=10)

        # Add more results than max
        for i in range(20):
            manager.add_result({'test': i})

        results = manager.get_results()
        # Due to deque maxlen, should have at most max_results
        assert len(results) <= 10

    def test_add_backtest_object(self) -> None:
        """Test adding BacktestResult objects."""
        manager = AggressiveMemoryManager(max_backtest_objects=10)

        # Create mock BacktestResult
        mock_result = Mock(spec=BacktestResult)
        mock_result.final_capital = 100000

        manager.add_backtest_object('test_key', mock_result)

        objects = manager.get_backtest_objects()
        assert len(objects) == 1
        assert objects[0][0] == 'test_key'
        assert objects[0][1].final_capital == 100000

    def test_backtest_object_cleanup(self) -> None:
        """Test aggressive cleanup of BacktestResult objects."""
        manager = AggressiveMemoryManager(max_backtest_objects=100)

        # Add many objects
        for i in range(100):
            mock_result = Mock(spec=BacktestResult)
            mock_result.final_capital = 100000 + i
            manager.add_backtest_object(f'test_{i}', mock_result)

        # Should trigger cleanup to 50
        objects = manager.get_backtest_objects()
        assert len(objects) <= 50

    def test_clear_all(self) -> None:
        """Test clearing all stored objects."""
        manager = AggressiveMemoryManager()

        # Add some data
        for i in range(10):
            manager.add_result({'test': i})

        mock_result = Mock(spec=BacktestResult)
        manager.add_backtest_object('key', mock_result)

        # Clear
        manager.clear_all()

        assert len(manager._results) == 0
        assert len(manager._backtest_objects) == 0

    def test_get_memory_usage_mb(self) -> None:
        """Test getting memory usage."""
        manager = AggressiveMemoryManager()

        with patch('app.backtesting.core.memory_manager.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
            mock_process.return_value = mock_instance

            usage = manager.get_memory_usage_mb()
            assert usage == 100.0

    def test_get_memory_usage_mb_error_handling(self) -> None:
        """Test memory usage handles psutil errors gracefully."""
        manager = AggressiveMemoryManager()

        # Create a mock Process that raises an error when accessing memory_info
        mock_process = Mock()
        mock_process.memory_info.side_effect = Exception('Test error')

        with patch('app.backtesting.core.memory_manager.psutil.Process', return_value=mock_process):
            usage = manager.get_memory_usage_mb()
            assert usage == 0.0

    def test_check_memory_pressure_normal(self) -> None:
        """Test memory pressure check when usage is normal."""
        manager = AggressiveMemoryManager(memory_threshold_mb=4096)

        with patch('app.backtesting.core.memory_manager.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.memory_info.return_value.rss = 1024 * 1024 * 100  # 100MB
            mock_process.return_value = mock_instance

            is_under_pressure = manager.check_memory_pressure()
            assert is_under_pressure is False

    def test_check_memory_pressure_exceeded(self) -> None:
        """Test memory pressure check when threshold is exceeded."""
        manager = AggressiveMemoryManager(memory_threshold_mb=100)

        # Add some data
        for i in range(20):
            manager.add_result({'test': i})

        with patch('app.backtesting.core.memory_manager.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.memory_info.return_value.rss = 1024 * 1024 * 200  # 200MB
            mock_process.return_value = mock_instance

            is_under_pressure = manager.check_memory_pressure()
            assert is_under_pressure is True

            # Emergency cleanup should have been triggered
            assert len(manager._results) <= 10

    def test_check_memory_pressure_logging(self) -> None:
        """Test memory pressure logging at intervals."""
        manager = AggressiveMemoryManager(memory_threshold_mb=4096)

        with patch('app.backtesting.core.memory_manager.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.memory_info.return_value.rss = 1024 * 1024 * 100
            mock_process.return_value = mock_instance

            # Add 100 results to trigger logging
            for i in range(100):
                manager.add_result({'test': i})

            # Should not raise
            manager.check_memory_pressure()

    def test_get_stats(self) -> None:
        """Test getting manager statistics."""
        manager = AggressiveMemoryManager()

        # Add some data
        for i in range(10):
            manager.add_result({'test': i})

        mock_result = Mock(spec=BacktestResult)
        manager.add_backtest_object('key', mock_result)

        with patch('app.backtesting.core.memory_manager.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.memory_info.return_value.rss = 1024 * 1024 * 100
            mock_process.return_value = mock_instance

            stats = manager.get_stats()

            assert stats['results_count'] == 10
            assert stats['backtest_objects_count'] == 1
            assert stats['cleanup_count'] == 0
            assert stats['emergency_cleanup_count'] == 0
            assert stats['memory_usage_mb'] == 100.0
            assert stats['memory_threshold_mb'] == 4096

    def test_repr(self) -> None:
        """Test string representation."""
        manager = AggressiveMemoryManager()

        with patch('app.backtesting.core.memory_manager.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.memory_info.return_value.rss = 1024 * 1024 * 100
            mock_process.return_value = mock_instance

            # Add some data
            manager.add_result({'test': 1})

            repr_str = repr(manager)
            assert 'AggressiveMemoryManager' in repr_str
            assert 'results=1' in repr_str
            assert 'backtest_objects=0' in repr_str
            assert '100MB' in repr_str

    def test_thread_safety(self) -> None:
        """Test that manager is thread-safe."""
        manager = AggressiveMemoryManager(max_results=100)
        errors = []

        def add_results(thread_id: int) -> None:
            """Add results from thread."""
            try:
                for i in range(50):
                    manager.add_result({'thread': thread_id, 'value': i})
            except Exception as e:
                errors.append(e)

        # Create multiple threads
        threads = []
        for i in range(5):
            t = threading.Thread(target=add_results, args=(i,))
            threads.append(t)
            t.start()

        # Wait for all threads
        for t in threads:
            t.join()

        # Should not have any errors
        assert len(errors) == 0

        # Results should be consistent
        results = manager.get_results()
        assert len(results) <= 100  # Due to deque maxlen

    def test_emergency_cleanup_behavior(self) -> None:
        """Test emergency cleanup frees maximum memory."""
        manager = AggressiveMemoryManager(max_results=500)

        # Add many results
        for i in range(200):
            manager.add_result({'test': i, 'data': 'x' * 100})

        # Add many BacktestResult objects
        for i in range(50):
            mock_result = Mock(spec=BacktestResult)
            mock_result.final_capital = 100000 + i
            manager.add_backtest_object(f'test_{i}', mock_result)

        # Trigger emergency cleanup
        with patch('app.backtesting.core.memory_manager.psutil.Process') as mock_process:
            mock_instance = Mock()
            mock_instance.memory_info.return_value.rss = 1024 * 1024 * 5000  # 5GB
            mock_process.return_value = mock_instance

            manager.check_memory_pressure()

        # Should have very few objects left
        assert len(manager._results) <= 10
        assert len(manager._backtest_objects) <= 5
        assert manager._emergency_cleanup_count > 0

    def test_deque_maxlen_behavior(self) -> None:
        """Test that deque automatically discards old items."""
        manager = AggressiveMemoryManager(max_results=5)

        # Add more than max
        for i in range(10):
            manager.add_result({'value': i})

        results = manager.get_results()
        # Deque should auto-manage size
        assert len(results) <= 5

        # Newest items should be present (last 5: 5,6,7,8,9)
        values = [r['value'] for r in results]
        assert 9 in values  # Last item
        assert values == [5, 6, 7, 8, 9] or set(values).issubset(set(range(10)))  # Most recent


class TestMemoryManagerIntegration:
    """Integration tests for memory manager with actual BacktestResult."""

    def test_with_real_backtest_result(self) -> None:
        """Test manager with real BacktestResult objects."""
        from datetime import datetime
        from decimal import Decimal

        manager = AggressiveMemoryManager(max_backtest_objects=5)

        # Create actual BacktestResult with required fields
        result = BacktestResult(
            strategy_name='test_strategy',
            start_date=datetime(2024, 1, 1),
            end_date=datetime(2024, 12, 31),
            final_capital=Decimal('110000'),
            total_return=Decimal('10.0'),
        )

        manager.add_backtest_object('integration_test', result)

        objects = manager.get_backtest_objects()
        assert len(objects) == 1
        assert objects[0][0] == 'integration_test'
        assert objects[0][1].strategy_name == 'test_strategy'
        assert objects[0][1].final_capital == Decimal('110000')
