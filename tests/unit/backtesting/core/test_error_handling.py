"""
Unit tests for error handling and retry logic.

Tests error handling functionality including:
- Mutex error detection
- Training retry logic
- Subprocess fallback
- Safe execution wrappers
"""
from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from tenacity import RetryError

from app.backtesting.core.error_handling import (
    MutexError,
    SubprocessTimeoutError,
    TrainingError,
    _train_in_subprocess,
    is_mutex_error,
    log_and_suppress,
    safe_execute,
    train_with_retry,
)


class TestMutexErrorDetection:
    """Test suite for mutex error detection."""

    def test_is_mutex_error_with_mutex_string(self) -> None:
        """Test detection of 'mutex' in error message."""
        error = Exception("mutex lock failed")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_with_lock_string(self) -> None:
        """Test detection of 'lock' in error message."""
        error = Exception("thread lock timeout")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_with_blocking_string(self) -> None:
        """Test detection of 'blocking' in error message."""
        error = Exception("operation is blocking")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_with_thread_string(self) -> None:
        """Test detection of 'thread' in error message."""
        error = Exception("thread initialization error")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_with_openblas(self) -> None:
        """Test detection of OpenBLAS errors."""
        error = Exception("openblas thread error")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_with_mkl(self) -> None:
        """Test detection of MKL errors."""
        error = Exception("mkl threading issue")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_with_torch(self) -> None:
        """Test detection of PyTorch errors."""
        error = Exception("torch threading error")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_case_insensitive(self) -> None:
        """Test case-insensitive detection."""
        error = Exception("MUTEX LOCK FAILED")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_in_exception_type(self) -> None:
        """Test detection in exception type name."""

        class MutexLockError(Exception):
            pass

        error = MutexLockError("some message")
        assert is_mutex_error(error) is True

    def test_is_mutex_error_negative(self) -> None:
        """Test negative case - non-mutex error."""
        error = ValueError("invalid input")
        assert is_mutex_error(error) is False

    def test_is_mutex_error_with_none(self) -> None:
        """Test handling of None input."""
        assert is_mutex_error(None) is False

    def test_is_mutex_error_with_non_exception(self) -> None:
        """Test handling of non-exception objects."""
        assert is_mutex_error("string") is False
        assert is_mutex_error(123) is False


class TestTrainingRetry:
    """Test suite for training retry logic."""

    def test_train_with_retry_success(self) -> None:
        """Test successful training without retries."""
        strategy = Mock()
        strategy.learning_engine = Mock()
        strategy.learning_engine.train.return_value = None

        result = train_with_retry(strategy, 'supervised')

        assert result is True
        strategy.learning_engine.train.assert_called_once()

    def test_train_with_retry_no_learning_engine(self) -> None:
        """Test handling when learning engine is not initialized."""
        strategy = Mock()
        strategy.learning_engine = None

        result = train_with_retry(strategy, 'supervised')

        assert result is False

    def test_train_with_retry_mutex_retries(self) -> None:
        """Test retry on mutex error."""
        strategy = Mock()
        strategy.learning_engine = Mock()

        # First call raises mutex error, second succeeds
        strategy.learning_engine.train.side_effect = [
            RuntimeError("mutex lock failed"),
            None,
        ]

        result = train_with_retry(strategy, 'supervised')

        assert result is True
        assert strategy.learning_engine.train.call_count == 2

    def test_train_with_retry_max_retries_exceeded(self) -> None:
        """Test failure after max retries."""
        strategy = Mock()
        strategy.learning_engine = Mock()

        # Always fail with mutex error
        strategy.learning_engine.train.side_effect = RuntimeError("mutex lock failed")

        with pytest.raises(MutexError):
            train_with_retry(strategy, 'supervised')

    def test_train_with_retry_non_mutex_error(self) -> None:
        """Test that non-mutex errors are not retried."""
        strategy = Mock()
        strategy.learning_engine = Mock()

        strategy.learning_engine.train.side_effect = ValueError("invalid data")

        with pytest.raises(TrainingError):
            train_with_retry(strategy, 'supervised')

        # Should only be called once (no retry for non-mutex errors)
        assert strategy.learning_engine.train.call_count == 1


class TestSubprocessTraining:
    """Test suite for subprocess training fallback."""

    def test_train_in_subprocess_success(self) -> None:
        """Test successful subprocess training."""
        strategy = Mock()
        strategy.__module__ = 'app.strategies.test'
        strategy.__class__.__name__ = 'TestStrategy'

        with patch('multiprocessing.get_context') as mock_get_context:
            mock_ctx = Mock()
            mock_get_context.return_value = mock_ctx

            # Mock queue with success result
            mock_queue = Mock()
            mock_queue.empty.return_value = False
            mock_queue.get.return_value = (True, 'Training completed')

            mock_ctx.Queue.return_value = mock_queue
            mock_ctx.Process.return_value.join.return_value = None
            mock_ctx.Process.return_value.is_alive.return_value = False

            result = _train_in_subprocess(strategy, 'deep', timeout=60)

            assert result is True

    def test_train_in_subprocess_failure(self) -> None:
        """Test subprocess training failure."""
        strategy = Mock()
        strategy.__module__ = 'app.strategies.test'
        strategy.__class__.__name__ = 'TestStrategy'

        with patch('multiprocessing.get_context') as mock_get_context:
            mock_ctx = Mock()
            mock_get_context.return_value = mock_ctx

            # Mock queue with error result
            mock_queue = Mock()
            mock_queue.empty.return_value = False
            mock_queue.get.return_value = (False, 'Training failed')

            mock_ctx.Queue.return_value = mock_queue
            mock_ctx.Process.return_value.join.return_value = None
            mock_ctx.Process.return_value.is_alive.return_value = False

            result = _train_in_subprocess(strategy, 'deep', timeout=60)

            assert result is False

    def test_train_in_subprocess_timeout(self) -> None:
        """Test subprocess training timeout."""
        strategy = Mock()
        strategy.__module__ = 'app.strategies.test'
        strategy.__class__.__name__ = 'TestStrategy'

        with patch('multiprocessing.get_context') as mock_get_context:
            mock_ctx = Mock()
            mock_get_context.return_value = mock_ctx

            mock_queue = Mock()
            mock_ctx.Queue.return_value = mock_queue

            # Process is still alive (timeout)
            mock_process = Mock()
            mock_process.is_alive.return_value = True
            mock_process.join.return_value = None
            mock_process.terminate.return_value = None
            mock_process.kill.return_value = None

            mock_ctx.Process.return_value = mock_process

            with pytest.raises(SubprocessTimeoutError):
                _train_in_subprocess(strategy, 'deep', timeout=1)

    def test_train_in_subprocess_no_result(self) -> None:
        """Test subprocess training with no result in queue."""
        strategy = Mock()
        strategy.__module__ = 'app.strategies.test'
        strategy.__class__.__name__ = 'TestStrategy'

        with patch('multiprocessing.get_context') as mock_get_context:
            mock_ctx = Mock()
            mock_get_context.return_value = mock_ctx

            # Empty queue
            mock_queue = Mock()
            mock_queue.empty.return_value = True

            mock_ctx.Queue.return_value = mock_queue
            mock_ctx.Process.return_value.join.return_value = None
            mock_ctx.Process.return_value.is_alive.return_value = False

            result = _train_in_subprocess(strategy, 'deep', timeout=60)

            assert result is False


class TestSafeExecute:
    """Test suite for safe execution wrapper."""

    def test_safe_execute_success(self) -> None:
        """Test successful execution."""

        def func(x: int) -> int:
            return x * 2

        result = safe_execute(func, 5)
        assert result == 10

    def test_safe_execute_with_args_and_kwargs(self) -> None:
        """Test execution with both args and kwargs."""

        def func(a: int, b: int, c: int = 0) -> int:
            return a + b + c

        result = safe_execute(func, 1, 2, c=3)
        assert result == 6

    def test_safe_execute_exception_handling(self) -> None:
        """Test exception handling with default return."""

        def func() -> None:
            raise ValueError("Test error")

        result = safe_execute(func, default_return=42)
        assert result == 42

    def test_safe_execute_no_default_return(self) -> None:
        """Test exception handling without default return."""

        def func() -> None:
            raise ValueError("Test error")

        result = safe_execute(func)
        assert result is None

    def test_safe_execute_logging(self) -> None:
        """Test error logging."""

        def func() -> None:
            raise ValueError("Test error")

        with patch('app.backtesting.core.error_handling.logger') as mock_logger:
            safe_execute(func, log_errors=True)

            mock_logger.error.assert_called_once()

    def test_safe_execute_no_logging(self) -> None:
        """Test suppressing error logging."""

        def func() -> None:
            raise ValueError("Test error")

        with patch('app.backtesting.core.error_handling.logger') as mock_logger:
            safe_execute(func, log_errors=False)

            mock_logger.error.assert_not_called()


class TestLogAndSuppress:
    """Test suite for log_and_suppress decorator."""

    def test_log_and_suppress_success(self) -> None:
        """Test successful function execution."""

        @log_and_suppress((ValueError,), "Calculation failed")
        def calculate(x: int) -> int:
            return x * 2

        result = calculate(5)
        assert result == 10

    def test_log_and_suppress_exception_caught(self) -> None:
        """Test exception suppression."""

        @log_and_suppress((ValueError,), "Calculation failed", default_return=0)
        def calculate(x: int) -> int:
            raise ValueError("Invalid input")

        result = calculate(-1)
        assert result == 0

    def test_log_and_suppress_different_exception(self) -> None:
        """Test that different exceptions are not caught."""

        @log_and_suppress((ValueError,), "Calculation failed")
        def calculate(x: int) -> int:
            raise TypeError("Wrong type")

        with pytest.raises(TypeError):
            calculate("not an int")

    def test_log_and_suppress_multiple_exception_types(self) -> None:
        """Test catching multiple exception types."""

        @log_and_suppress((ValueError, TypeError), "Calculation failed", default_return=-1)
        def calculate(x: int) -> int:
            raise TypeError("Wrong type")

        result = calculate("not an int")
        assert result == -1

    def test_log_and_suppress_logging(self) -> None:
        """Test that exceptions are logged."""

        @log_and_suppress((ValueError,), "Calculation failed", default_return=0)
        def calculate(x: int) -> int:
            raise ValueError("Invalid input")

        with patch('app.backtesting.core.error_handling.logger') as mock_logger:
            calculate(-1)

            mock_logger.warning.assert_called_once()
            assert "Calculation failed" in str(mock_logger.warning.call_args)


class TestMutexError:
    """Test suite for MutexError exception."""

    def test_mutex_error_creation(self) -> None:
        """Test creating MutexError."""
        error = MutexError("Test mutex error")
        assert str(error) == "Test mutex error"

    def test_mutex_error_is_exception(self) -> None:
        """Test that MutexError is an Exception."""
        error = MutexError("Test")
        assert isinstance(error, Exception)

    def test_mutex_error_with_cause(self) -> None:
        """Test MutexError with underlying cause."""
        original = RuntimeError("mutex lock")
        try:
            raise MutexError("Mutex detected") from original
        except MutexError as error:
            assert str(error) == "Mutex detected"
            assert error.__cause__ is original


class TestTrainingError:
    """Test suite for TrainingError exception."""

    def test_training_error_creation(self) -> None:
        """Test creating TrainingError."""
        error = TrainingError("Training failed")
        assert str(error) == "Training failed"

    def test_training_error_is_exception(self) -> None:
        """Test that TrainingError is an Exception."""
        error = TrainingError("Test")
        assert isinstance(error, Exception)


class TestSubprocessTimeoutError:
    """Test suite for SubprocessTimeoutError exception."""

    def test_subprocess_timeout_creation(self) -> None:
        """Test creating SubprocessTimeoutError."""
        error = SubprocessTimeoutError("Timeout after 300s")
        assert str(error) == "Timeout after 300s"

    def test_subprocess_timeout_is_training_error(self) -> None:
        """Test that SubprocessTimeoutError is a TrainingError."""
        error = SubprocessTimeoutError("Timeout")
        assert isinstance(error, TrainingError)

    def test_subprocess_timeout_is_exception(self) -> None:
        """Test that SubprocessTimeoutError is an Exception."""
        error = SubprocessTimeoutError("Timeout")
        assert isinstance(error, Exception)
